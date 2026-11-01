# ==========================================================
# Аналіз фото
# ==========================================================
import asyncio
import os
import random
import re
import cv2
import whisper
from PIL import Image
from aiogram import types, F
from aiogram.utils.chat_action import ChatActionSender

from config import bot, dp, user_gender, safety_settings
from database import load_user_gender, save_message
from functions import get_chat_session, get_gender_keyboard
from Teto_codes import API_KEYS
from Teto_list import GENDER_REQUEST_MESSAGES, IMAGE_ERROR_MESSAGES, ERROR_MESSAGES, VOICE_ERROR_MESSAGES
import google.generativeai as genai

@dp.message(F.photo)
async def handle_photo_message(message: types.Message):
    user_id = message.from_user.id

    if user_id not in user_gender:
        db_gender = load_user_gender(user_id)
        if db_gender:
            user_gender[user_id] = db_gender
        else:
            await bot.send_chat_action(message.chat.id, action="typing")
            await message.answer(random.choice(GENDER_REQUEST_MESSAGES), reply_markup=get_gender_keyboard())
            return

    async with ChatActionSender.typing(bot=bot, chat_id=message.chat.id):
        try:
            photo = message.photo[-1]
            file_info = await bot.get_file(photo.file_id)
            photo_buffer = await bot.download_file(file_info.file_path)
            image_data = photo_buffer.read()
            image_part = {
                "mime_type": "image/jpeg",
                "data": image_data
            }
            user_text = message.caption if message.caption else "Подивись на це зображення"
            chat = await get_chat_session(user_id)
            response = await chat.send_message_async([user_text, image_part])
            clean_text = re.sub(r'\*.*?\*', '', response.text).strip()
            await message.answer(clean_text)
            save_message(user_id, "user", f"[Фото]: {user_text}")
            save_message(user_id, "model", response.text)

        except Exception as e:
            print(f"[-] Помилка аналізу фото: {e}")
            await message.answer(random.choice(IMAGE_ERROR_MESSAGES))

# ========================================
# Аналіз гіфок
# ========================================
@dp.message(F.animation)
async def handle_animation(message: types.Message):
    user_id = message.from_user.id

    # --- ПЕРЕВІРКА СТАТЬ ---
    if user_id not in user_gender:
        db_gender = load_user_gender(user_id)
        if db_gender:
            user_gender[user_id] = db_gender
        else:
            await bot.send_chat_action(message.chat.id, action="typing")
            await message.answer(random.choice(GENDER_REQUEST_MESSAGES), reply_markup=get_gender_keyboard())
            return

    async with ChatActionSender.typing(bot=bot, chat_id=message.chat.id):
        try:
            # --- ЗАВАНТАЖЕННЯ МЕДІА ---
            animation = message.animation
            file_info = await bot.get_file(animation.file_id)
            gif_bytes = await bot.download_file(file_info.file_path)
            is_mp4 = file_info.file_path.lower().endswith('.mp4')
            if is_mp4:
                temp_video = f"temp_vid_{user_id}.mp4"
                with open(temp_video, "wb") as f:
                    f.write(gif_bytes.read())
                cap = cv2.VideoCapture(temp_video)
                success, frame = cap.read()
                cap.release()
                if os.path.exists(temp_video):
                    os.remove(temp_video)
                if not success:
                    raise Exception("Не вдалося отримати кадр з MP4")
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                analysis_img = Image.fromarray(frame_rgb)
            else:
                gif_bytes.seek(0)
                with Image.open(gif_bytes) as img:
                    img.seek(0)
                    analysis_img = img.convert("RGB")

            # --- ЕТАП 1: АНАЛІЗ ГІФКИ (+ПЕРЕБІР КЛЮЧІВ) ---
            image_description = None
            for key in API_KEYS:
                try:
                    genai.configure(api_key=key)
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    raw_analysis = await model.generate_content_async(
                        ["Що на цій картинці? Опиши коротко.", analysis_img],
                        safety_settings=safety_settings
                    )
                    if raw_analysis.candidates and raw_analysis.candidates[0].finish_reason != 3:
                        image_description = raw_analysis.text
                        break
                except Exception:
                    continue
            if not image_description:
                await message.answer(random.choice(IMAGE_ERROR_MESSAGES))
                return

            # --- ЕТАП 2: ВІДПОВІДЬ БОТА (ПЕРЕБІР КЛЮЧІВ) ---
            user_caption = message.caption if message.caption else "Подивись на це!"
            teto_request = (
                f"Користувач надіслав анімацію з описом: '{user_caption}'. "
                f"На самій анімації зображено: {image_description}. "
                f"Відреагуй на це як Касане Тето, будь емоційною!"
            )
            final_response = None
            for key in API_KEYS:
                try:
                    genai.configure(api_key=key)
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    chat = await get_chat_session(user_id)
                    response = await chat.send_message_async(teto_request)
                    final_response = response
                    break
                except Exception:
                    continue
            if final_response:
                clean_text = re.sub(r'\*.*?\*', '', final_response.text).strip()
                await message.answer(clean_text)
                user_text = message.caption if message.caption else "Що відбувається на цій гіфці?"
                save_message(user_id, "user", f"[Гіфка]: {user_text}")
                save_message(user_id, "model", final_response.text)
            else:
                await message.answer(random.choice(ERROR_MESSAGES))
        except Exception as e:
            print(f"[-] Помилка в зчитуванні гіфки: {e}")
            await message.answer(random.choice(ERROR_MESSAGES))

# ========================================
# Зчитування гс
# ========================================
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

        # РОЗПІЗНАВАННЯ (Whisper)
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: model_w.transcribe(voice_file_path, fp16=False))
        recognized_text = result['text']

        if not recognized_text.strip():
            await bot.send_chat_action(message.chat.id, action="typing")
            await message.answer(random.choice(VOICE_ERROR_MESSAGES))
            return

        # ОТРИМАННЯ ВІДПОВІДІ ВІД GEMINI
        teto_answer = await get_teto_response(user_id, recognized_text)
        await bot.send_chat_action(message.chat.id, action="typing")
        await message.answer(teto_answer)
    except Exception as e:
        print(f"[-] Помилка при зчитуванні гс: {e}")
        await bot.send_chat_action(message.chat.id, action="typing")
        await message.answer(random.choice(VOICE_ERROR_MESSAGES))

    finally:
        if os.path.exists(voice_file_path):
            os.remove(voice_file_path)

