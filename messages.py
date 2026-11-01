# ======================================================================
# Хендлери
# ======================================================================
import asyncio
import random
import re
from datetime import datetime
from aiogram import types, F
from aiogram.filters import CommandStart
from aiogram.utils.chat_action import ChatActionSender

from config import bot, dp, user_gender, user_interaction_mode, user_awaiting_feedback, last_message_time
from database import load_user_gender, save_user_gender, save_message
from functions import get_main_keyboard, get_gender_keyboard, get_weather, get_word_of_the_day, get_chat_response
from Teto_codes import WEATHER_API_KEY, channel_id
from Teto_list import (
    HELLO_TETO, GENDER_SUCCESS_MESSAGES, FEEDBACK_SUCCESS_MESSAGES,
    MENU_REQUEST_MESSAGES, ERROR_MESSAGES, GENDER_REQUEST_MESSAGES,
    FEEDBACK_REQUEST_MESSAGES, future_Teto, image_Teto, history_facts,
    music_Teto, sound,
)
from aiogram.types import FSInputFile

# ===============================
# При першій зустрічі
# ===============================
@dp.message(CommandStart())
async def handle_start(message: types.Message):
    user_id = message.from_user.id
    current_time = datetime.now()

    gender_from_db = load_user_gender(user_id)

    if gender_from_db:
        user_gender[user_id] = gender_from_db
        user_interaction_mode[user_id] = "button_mode"
        await message.answer(random.choice(HELLO_TETO), reply_markup=get_main_keyboard())
    else:
        await message.answer(random.choice(GENDER_REQUEST_MESSAGES), reply_markup=get_gender_keyboard())

    last_message_time[user_id] = current_time

@dp.callback_query(F.data.startswith("gender_"))
async def set_gender(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    gender_chosen = callback.data.split("_")[1]
    user_gender[user_id] = gender_chosen

    save_user_gender(user_id, gender_chosen)

    user_interaction_mode[user_id] = "button_mode"
    await callback.message.delete()
    await callback.message.answer(random.choice(GENDER_SUCCESS_MESSAGES), reply_markup=get_main_keyboard())
    await callback.answer()

# ===============================
# Обробка натискань кнопок функціоналу
# ===============================
@dp.callback_query()
async def handle_callbacks(callback: types.CallbackQuery):
    await callback.answer()

    user_id = callback.from_user.id
    data = callback.data
    current_time = datetime.now()

    if user_id not in user_gender:
        await bot.send_chat_action(callback.chat.id, action="typing")
        await callback.message.answer(random.choice(GENDER_REQUEST_MESSAGES), reply_markup=get_gender_keyboard())
        return

    if user_interaction_mode.get(user_id) == "button_mode":
        if data == "weather":
            weather_info = get_weather("Рівне", WEATHER_API_KEY)
            async with ChatActionSender.typing(bot=bot, chat_id=callback.message.chat.id):
                await asyncio.sleep(1)
                await callback.message.answer(weather_info)

        elif data == "future":
            async with ChatActionSender.typing(bot=bot, chat_id=callback.message.chat.id):
                await asyncio.sleep(1)
                await callback.message.answer(f"🏹Тето дивиться у майбутнє:\n {random.choice(future_Teto)}")

        elif data == "image":
            image_path = random.choice(image_Teto)
            photo = FSInputFile(image_path)
            async with ChatActionSender.upload_photo(bot=bot, chat_id=callback.message.chat.id):
                await asyncio.sleep(1)
                await callback.message.answer_photo(photo)
        elif data == "fact":
            async with ChatActionSender.typing(bot=bot, chat_id=callback.message.chat.id):
                await asyncio.sleep(1)
                await callback.message.answer(f"📝 Історичний факт:\n {random.choice(history_facts)}")

        elif data == "music":
            music_path = random.choice(music_Teto)
            audio = FSInputFile(music_path)
            async with ChatActionSender.upload_voice(bot=bot, chat_id=callback.message.chat.id):
                await callback.message.answer("🎧 Ось музика від Тето:")
                await asyncio.sleep(1.5)
            await callback.message.answer_audio(audio)

        elif data == "word_of_day":
            word = get_word_of_the_day()
            async with ChatActionSender.typing(bot=bot, chat_id=callback.message.chat.id):
                await asyncio.sleep(1)
                await callback.message.answer(f"📖 Слово дня від Тето: '{word}'")

        elif data == "sound":
            async with ChatActionSender.typing(bot=bot, chat_id=callback.message.chat.id):
                await asyncio.sleep(1)
                await callback.message.answer(f"💥Правильний наголос:\n {(random.choice(sound))}")

        elif data == "feedback":
            user_awaiting_feedback[user_id] = True
            await callback.message.answer(random.choice(FEEDBACK_REQUEST_MESSAGES))
            await callback.answer()
    last_message_time[user_id] = current_time

# ===========================================================
# Головний диспетчер, який обробляє ВСІ текстові повідомлення
# ===========================================================
@dp.message(F.text)
async def handle_all_messages(message: types.Message):
    user_id = message.from_user.id
    user_text = message.text.lower().strip()
    current_time = datetime.now()

    last_message_time[user_id] = current_time

    # --- ПЕРЕВІРКА НА СТАТЬ (з бази або словника) ---
    if user_id not in user_gender:
        db_gender = load_user_gender(user_id)
        if db_gender:
            user_gender[user_id] = db_gender
        else:
            await bot.send_chat_action(message.chat.id, action="typing")
            await message.answer(random.choice(GENDER_REQUEST_MESSAGES), reply_markup=get_gender_keyboard())
            return

    # ===================================
    # Блок фідбеку
    # ===================================
    # --- ПЕРЕВІРКА НА РЕЖИМ ФІДБЕКА ---
    if user_awaiting_feedback.get(user_id) is True:
        user_name = message.from_user.full_name
        username = f"@{message.from_user.username}" if message.from_user.username else "немає ніка"
        back_text = message.text.replace("*", "").replace("_", "").replace("`", "")
        feedback_text = (
            f"📥 ---НОВИЙ ВІДГУК!---\t\n"
            f"Від: {user_name} ({username})\n"
            f"ID: {user_id}\n"
            f"Текст: {back_text}"
        )
        try:
            await bot.send_message(channel_id, feedback_text)
        except Exception as e:
            print(f"[-] Помилка відправки в канал: {e}")
        await message.answer(random.choice(FEEDBACK_SUCCESS_MESSAGES))
        user_awaiting_feedback[user_id] = False
        return

    # =============================================
    # Перевірки з тим, що саме написав користувач
    # =============================================
    # --- ПЕРЕВІРКА НА КОМАНДУ "повернути кнопки" ---
    if any(word in user_text for word in ["кнопки", "buttons", "меню", "menu"]):
        user_interaction_mode[user_id] = "button_mode"
        await bot.send_chat_action(message.chat.id, action="typing")
        await message.answer(random.choice(MENU_REQUEST_MESSAGES), reply_markup=get_main_keyboard())
        return

    # --- ОБРОБКА ЧАТУ --- (частина ШІ)
    async with ChatActionSender.typing(bot=bot, chat_id=message.chat.id):
        response = await get_chat_response(user_id, message.text)
        if response:
            clean_text = re.sub(r'\*.*?\*', '', response).strip()
            await asyncio.sleep(1.5)
            await message.answer(clean_text)
            save_message(user_id, "user", message.text)
            save_message(user_id, "model", response)
        else:
            await message.answer(random.choice(ERROR_MESSAGES))
