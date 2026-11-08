# ==========================================================
# Аналіз фото, анімацій, стікерів та голосових повідомлень
# ==========================================================
import asyncio
import os
import random
import re
import cv2
import whisper
import io
import tempfile
from PIL import Image
from aiogram import types, F
from aiogram.utils.chat_action import ChatActionSender
from config import bot, dp, user_gender, safety_settings, last_message_time
from datetime import datetime
from database import load_user_gender, save_message
from functions import get_chat_session, get_gender_keyboard
from Teto_codes import API_KEYS
from Teto_list import (GENDER_REQUEST_MESSAGES, IMAGE_ERROR_MESSAGES, ERROR_MESSAGES, VOICE_ERROR_MESSAGES)
import google.generativeai as genai
from rlottie_python import LottieAnimation

# ==========================================================
# Отримання першого кадру медіа
# ==========================================================

def get_first_frame(file_path, file_bytes, media_type):

    if media_type == "webp":
        image = Image.open(io.BytesIO(file_bytes))
        image.seek(0)
        return image.convert("RGB")

    elif media_type == "gif":
        image = Image.open(io.BytesIO(file_bytes))
        image.seek(0)
        return image.convert("RGB")

    elif media_type in ("webm", "mp4"):
        temp_path = None

        try:
            with tempfile.NamedTemporaryFile(suffix=f".{media_type}", delete=False) as temp:
                temp.write(file_bytes)
                temp_path = temp.name

            cap = cv2.VideoCapture(temp_path)
            success, frame = cap.read()
            cap.release()

            if not success:
                raise Exception(f"Не вдалося отримати перший кадр {media_type.upper()}")

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            return Image.fromarray(frame_rgb)

        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

    elif media_type == "tgs":
        temp_path = None

        try:
            with tempfile.NamedTemporaryFile(suffix=".tgs", delete=False) as temp:
                temp.write(file_bytes)
                temp_path = temp.name

            with LottieAnimation.from_tgs(temp_path) as animation:
                frame = animation.render_pillow_frame(frame_num=0)
                return frame.convert("RGB")

        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

    else:
        raise ValueError(f"Невідомий тип медіа: {media_type}")

# ==========================================================
# Аналіз фото
# ==========================================================

@dp.message(F.photo)
async def handle_photo_message(message: types.Message):
    user_id = message.from_user.id

    if user_id not in user_gender:
        db_gender = load_user_gender(user_id)

        if db_gender:
            user_gender[user_id] = db_gender
        else:
            await bot.send_chat_action(message.chat.id, action="typing")
            await message.answer(
                random.choice(GENDER_REQUEST_MESSAGES),
                reply_markup=get_gender_keyboard())
            return

    async with ChatActionSender.typing(bot=bot, chat_id=message.chat.id):
        try:
            photo = message.photo[-1]
            file_info = await bot.get_file(photo.file_id)
            photo_buffer = await bot.download_file(file_info.file_path)
            image_data = photo_buffer.read()
            image_part = {"mime_type": "image/jpeg", "data": image_data}
            user_text = message.caption if message.caption else "Подивись на це зображення"

            chat = await get_chat_session(user_id)
            response = await chat.send_message_async([user_text, image_part])

            clean_text = re.sub(r'\*.*?\*', '', response.text).strip()
            await message.answer(clean_text)

            save_message(user_id, "user", f"[Фото]: {user_text}")
            save_message(user_id, "model", response.text)
            last_message_time[user_id] = datetime.now()

        except Exception as e:
            print(f"[-] Помилка аналізу фото: {e}")
            await message.answer(random.choice(IMAGE_ERROR_MESSAGES))

# ==========================================================
# Аналіз GIF та MP4
# ==========================================================

@dp.message(F.animation)
async def handle_animation(message: types.Message):
    user_id = message.from_user.id

    if user_id not in user_gender:
        db_gender = load_user_gender(user_id)

        if db_gender:
            user_gender[user_id] = db_gender
        else:
            await bot.send_chat_action(message.chat.id, action="typing")
            await message.answer(
                random.choice(GENDER_REQUEST_MESSAGES),
                reply_markup=get_gender_keyboard())
            return

    async with ChatActionSender.typing(bot=bot, chat_id=message.chat.id):
        try:
            animation = message.animation
            file_info = await bot.get_file(animation.file_id)
            file_buffer = await bot.download_file(file_info.file_path)
            file_bytes = file_buffer.read()

            media_type = ("mp4"
                if file_info.file_path.lower().endswith(".mp4")
                else "gif")

            analysis_img = get_first_frame(file_info.file_path, file_bytes, media_type)

            # ЕТАП 1: АНАЛІЗ ПЕРШОГО КАДРУ
            image_description = None
            for key in API_KEYS:
                try:
                    genai.configure(api_key=key)
                    model = genai.GenerativeModel("gemini-2.5-flash")

                    raw_analysis = await model.generate_content_async(
                        ["Що на цій картинці? Опиши коротко.", analysis_img],
                        safety_settings=safety_settings)
                    if raw_analysis.candidates and raw_analysis.candidates[0].finish_reason != 3:
                        image_description = raw_analysis.text
                        break

                except Exception:
                    continue

            if not image_description:
                await message.answer(random.choice(IMAGE_ERROR_MESSAGES))
                return

            # ЕТАП 2: РЕАКЦІЯ ТЕТО
            user_caption = message.caption if message.caption else "Подивись на це!"
            teto_request = (
                f"Користувач надіслав анімацію з описом: '{user_caption}'. "
                f"На першому кадрі анімації зображено: {image_description}. "
                "Відреагуй на це як Касане Тето, будь емоційною!")

            final_response = None
            for key in API_KEYS:
                try:
                    genai.configure(api_key=key)
                    chat = await get_chat_session(user_id)
                    final_response = await chat.send_message_async(teto_request)
                    break

                except Exception:
                    continue

            if final_response:
                clean_text = re.sub(r'\*.*?\*', '', final_response.text).strip()
                await message.answer(clean_text)
                save_message(user_id, "user", f"[Анімація]: {user_caption}\nОпис першого кадру: {image_description}")
                save_message(user_id, "model", final_response.text)
                last_message_time[user_id] = datetime.now()

            else:
                await message.answer(random.choice(ERROR_MESSAGES))

        except Exception as e:
            print(f"[-] Помилка в зчитуванні анімації: {e}")
            await message.answer(random.choice(ERROR_MESSAGES))

# ==========================================================
# Аналіз стікерів
# ==========================================================

@dp.message(F.sticker)
async def handle_sticker(message: types.Message):
    user_id = message.from_user.id

    if user_id not in user_gender:
        db_gender = load_user_gender(user_id)

        if db_gender:
            user_gender[user_id] = db_gender
        else:
            await bot.send_chat_action(message.chat.id, action="typing")
            await message.answer(
                random.choice(GENDER_REQUEST_MESSAGES),
                reply_markup=get_gender_keyboard()
            )
            return

    async with ChatActionSender.typing(bot=bot, chat_id=message.chat.id):
        try:
            sticker = message.sticker
            file_info = await bot.get_file(sticker.file_id)
            file_buffer = await bot.download_file(file_info.file_path)
            file_bytes = file_buffer.read()

            extension = os.path.splitext(file_info.file_path)[1].lower()

            if extension == ".tgs":
                media_type = "tgs"
            elif extension == ".webm":
                media_type = "webm"
            elif extension == ".webp":
                media_type = "webp"
            else:
                raise ValueError(f"Невідомий формат стікера: {extension}")

            analysis_img = get_first_frame(
                file_info.file_path,
                file_bytes,
                media_type)

            # ЕТАП 1: АНАЛІЗ СТІКЕРА

            image_description = None
            for key in API_KEYS:
                try:
                    genai.configure(api_key=key)
                    model = genai.GenerativeModel("gemini-2.5-flash")

                    response = await model.generate_content_async(
                        ["Опиши коротко, що зображено на цьому стікері.", analysis_img],
                        safety_settings=safety_settings)

                    if response.candidates and response.candidates[0].finish_reason != 3:
                        image_description = response.text
                        break

                except Exception:
                    continue

            if not image_description:
                await message.answer(random.choice(IMAGE_ERROR_MESSAGES))
                return

            # ЕТАП 2: РЕАКЦІЯ ТЕТО
            chat = await get_chat_session(user_id)
            teto_request = (
                f"Користувач надіслав стікер. "
                f"На першому кадрі зображено: {image_description}. "
                "Відреагуй на нього як Касане Тето, будь емоційною!")

            final_response = await chat.send_message_async(teto_request)
            clean_text = re.sub(r'\*.*?\*', '', final_response.text).strip()
            await message.answer(clean_text)

            save_message(user_id, "user", f"[Стікер]: {image_description}")
            save_message(user_id, "model", final_response.text)
            last_message_time[user_id] = datetime.now()

        except Exception as e:
            print(f"[-] Помилка аналізу стікера: {e}")
            await message.answer(random.choice(IMAGE_ERROR_MESSAGES))

# ==========================================================
# Зчитування голосових повідомлень
# ==========================================================

async def get_teto_response(user_id, text):
    chat = await get_chat_session(user_id)
    response = await asyncio.to_thread(chat.send_message, text)
    return response.text

model_w = whisper.load_model("base")

@dp.message(F.voice)
async def handle_voice_message(message: types.Message):
    user_id = message.from_user.id
    await bot.send_chat_action(message.chat.id, action="typing")
    voice_file_path = f"voice_{user_id}.ogg"

    try:
        # ЗАВАНТАЖЕННЯ
        file_id = message.voice.file_id
        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, voice_file_path)

        # РОЗПІЗНАВАННЯ
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, lambda: model_w.transcribe(voice_file_path, fp16=False))
        recognized_text = result["text"]

        if not recognized_text.strip():
            await bot.send_chat_action(message.chat.id, action="typing")
            await message.answer(random.choice(VOICE_ERROR_MESSAGES))
            return

        # ОТРИМАННЯ ВІДПОВІДІ GEMINI
        teto_answer = await get_teto_response(user_id, recognized_text)
        await bot.send_chat_action(message.chat.id, action="typing")
        await message.answer(teto_answer)

        save_message(user_id, "user", f"[Голосове повідомлення]: {recognized_text}")
        save_message(user_id, "model", teto_answer)
        last_message_time[user_id] = datetime.now()

    except Exception as e:
        print(f"[-] Помилка при зчитуванні гс: {e}")
        await bot.send_chat_action(message.chat.id, action="typing")
        await message.answer(random.choice(VOICE_ERROR_MESSAGES))

    finally:
        if os.path.exists(voice_file_path):
            os.remove(voice_file_path)
