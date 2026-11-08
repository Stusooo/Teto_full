# =====================================================================
# Хендлери Тето
# =====================================================================

import asyncio
import random
import re
from datetime import datetime

from aiogram import types, F
from aiogram.filters import CommandStart, Command
from aiogram.utils.chat_action import ChatActionSender
from aiogram.types import (
    FSInputFile,
    BotCommand,
    BotCommandScopeDefault
)
from database import load_user_city, save_user_city
users_awaiting_city = set()

from config import (
    bot,
    dp,
    user_gender,
    user_awaiting_feedback,
    last_message_time
)

from database import (
    load_user_gender,
    save_user_gender,
    save_message
)

from functions import (
    get_gender_keyboard,
    get_weather,
    get_word_of_the_day,
    get_chat_response
)

from Teto_codes import WEATHER_API_KEY, channel_id

from Teto_list import (
    HELLO_TETO,
    GENDER_SUCCESS_MESSAGES,
    FEEDBACK_SUCCESS_MESSAGES,
    ERROR_MESSAGES,
    GENDER_REQUEST_MESSAGES,
    FEEDBACK_REQUEST_MESSAGES,
    future_Teto,
    image_Teto,
    history_facts,
    music_Teto,
    sound
)


# =================================================
# Реєстрація команд у синьому меню Telegram
# =================================================

async def set_main_menu(bot_instance):
    commands = [
        BotCommand(command="start", description="Запуск бота"),
        BotCommand(command="weather", description="Погода сьогодні"),
        BotCommand(command="future", description="Передбачення"),
        BotCommand(command="image", description="Картинка"),
        BotCommand(command="fact", description="Історичний факт"),
        BotCommand(command="sound", description="Цікавий наголос"),
        BotCommand(command="music", description="Музика"),
        BotCommand(command="word", description="Слово дня"),
        BotCommand(command="feedback", description="Залишити відгук")
    ]

    await bot_instance.set_my_commands(
        commands,
        scope=BotCommandScopeDefault()
    )


# =================================================
# Перевірка статі користувача
# =================================================

async def _ensure_gender(message: types.Message):
    user_id = message.from_user.id

    if user_id not in user_gender:
        db_gender = load_user_gender(user_id)

        if db_gender:
            user_gender[user_id] = db_gender

        else:
            await message.answer(
                random.choice(GENDER_REQUEST_MESSAGES),
                reply_markup=get_gender_keyboard()
            )
            return False

    return True


# =================================================
# Перша зустріч із Тето
# =================================================

@dp.message(CommandStart())
async def handle_start(message: types.Message):
    user_id = message.from_user.id
    current_time = datetime.now()

    gender_from_db = load_user_gender(user_id)

    if gender_from_db:
        user_gender[user_id] = gender_from_db

        await message.answer(
            random.choice(HELLO_TETO)
        )

    else:
        await message.answer(
            random.choice(GENDER_REQUEST_MESSAGES),
            reply_markup=get_gender_keyboard()
        )

    last_message_time[user_id] = current_time


# =================================================
# Вибір статі
# =================================================

@dp.callback_query(F.data.startswith("gender_"))
async def set_gender(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    gender_chosen = callback.data.split("_")[1]

    user_gender[user_id] = gender_chosen
    save_user_gender(user_id, gender_chosen)

    await callback.message.delete()

    await callback.message.answer(
        random.choice(GENDER_SUCCESS_MESSAGES)
    )

    last_message_time[user_id] = datetime.now()
    await callback.answer()


# =================================================
# /weather — погода
# =================================================
@dp.message(Command("weather"))
async def handle_weather(message: types.Message):
    user_id = message.from_user.id
    city = load_user_city(user_id)

    if not city:
        users_awaiting_city.add(user_id)
        await message.answer("🌍 У якому місті подивитися погоду?")
        return

    status, weather_info = await asyncio.to_thread(
        get_weather, city, WEATHER_API_KEY
    )

    if status == "ok":
        await message.answer(weather_info)
    elif status == "not_found":
        users_awaiting_city.add(user_id)
        await message.answer("Не вдалося знайти збережене місто. Напиши його назву ще раз.")
    else:
        await message.answer(random.choice(ERROR_MESSAGES))


# =================================================
# /future — передбачення
# =================================================

@dp.message(Command("future"))
async def future_command(message: types.Message):
    if not await _ensure_gender(message):
        return

    async with ChatActionSender.typing(
        bot=bot,
        chat_id=message.chat.id
    ):
        await asyncio.sleep(1)

        await message.answer(
            f"🏹 Тето дивиться у майбутнє:\n"
            f"{random.choice(future_Teto)}"
        )

    last_message_time[message.from_user.id] = datetime.now()


# =================================================
# /image — картинка
# =================================================

@dp.message(Command("image"))
async def image_command(message: types.Message):
    if not await _ensure_gender(message):
        return

    try:
        image_path = random.choice(image_Teto)
        photo = FSInputFile(image_path)

        async with ChatActionSender.upload_photo(
            bot=bot,
            chat_id=message.chat.id
        ):
            await asyncio.sleep(1)
            await message.answer_photo(photo)

    except Exception as e:
        print(f"[-] Помилка відправки картинки: {e}")
        await message.answer(random.choice(ERROR_MESSAGES))

    last_message_time[message.from_user.id] = datetime.now()


# =================================================
# /fact — історичний факт
# =================================================

@dp.message(Command("fact"))
async def fact_command(message: types.Message):
    if not await _ensure_gender(message):
        return

    async with ChatActionSender.typing(
        bot=bot,
        chat_id=message.chat.id
    ):
        await asyncio.sleep(1)

        await message.answer(
            f"📝 Історичний факт:\n"
            f"{random.choice(history_facts)}"
        )

    last_message_time[message.from_user.id] = datetime.now()


# =================================================
# /sound — правильний наголос
# =================================================

@dp.message(Command("sound"))
async def sound_command(message: types.Message):
    if not await _ensure_gender(message):
        return

    async with ChatActionSender.typing(
        bot=bot,
        chat_id=message.chat.id
    ):
        await asyncio.sleep(1)

        await message.answer(
            f"💥 Правильний наголос:\n"
            f"{random.choice(sound)}"
        )

    last_message_time[message.from_user.id] = datetime.now()


# =================================================
# /music — музика
# =================================================

@dp.message(Command("music"))
async def music_command(message: types.Message):
    if not await _ensure_gender(message):
        return

    try:
        music_path = random.choice(music_Teto)
        audio = FSInputFile(music_path)

        await message.answer("🎧 Ось музика від Тето:")

        async with ChatActionSender.upload_voice(
            bot=bot,
            chat_id=message.chat.id
        ):
            await asyncio.sleep(1)
            await message.answer_audio(audio)

    except Exception as e:
        print(f"[-] Помилка відправки музики: {e}")
        await message.answer(random.choice(ERROR_MESSAGES))

    last_message_time[message.from_user.id] = datetime.now()


# =================================================
# /word — слово дня
# =================================================

@dp.message(Command("word"))
async def word_command(message: types.Message):
    if not await _ensure_gender(message):
        return

    word = get_word_of_the_day()

    async with ChatActionSender.typing(
        bot=bot,
        chat_id=message.chat.id
    ):
        await asyncio.sleep(1)

        await message.answer(
            f"📖 Слово дня від Тето: '{word}'"
        )

    last_message_time[message.from_user.id] = datetime.now()


# =================================================
# /feedback — відгук
# =================================================

@dp.message(Command("feedback"))
async def feedback_command(message: types.Message):
    if not await _ensure_gender(message):
        return

    user_awaiting_feedback[message.from_user.id] = True

    await message.answer(
        random.choice(FEEDBACK_REQUEST_MESSAGES)
    )

    last_message_time[message.from_user.id] = datetime.now()


# =================================================
# Обробка звичайних текстових повідомлень
# =================================================

@dp.message(F.text & ~F.text.startswith("/"))
async def handle_all_messages(message: types.Message):
    user_id = message.from_user.id
    current_time = datetime.now()

    last_message_time[user_id] = current_time

    if user_id in users_awaiting_city:
        city = message.text.strip()

        status, weather_info = await asyncio.to_thread(
            get_weather, city, WEATHER_API_KEY
        )

        if status == "not_found":
            await message.answer(
                "❌ Не знайшла такого міста. Спробуй ще раз."
            )
            return

        if status == "error":
            await message.answer(
                random.choice(ERROR_MESSAGES)
            )
            return

        save_user_city(user_id, city)
        users_awaiting_city.discard(user_id)

        await message.answer(
            f"📍 Місто {city} збережено!\n\n{weather_info}"
        )
        return

    if not await _ensure_gender(message):
        return

    # -------------------------------------------------
    # Отримання та відправка відгуку
    # -------------------------------------------------

    if user_awaiting_feedback.get(user_id) is True:
        user_name = message.from_user.full_name

        username = (
            f"@{message.from_user.username}"
            if message.from_user.username
            else "немає ніка"
        )

        feedback_text = (
            f"📥 ---НОВИЙ ВІДГУК!---\n"
            f"Від: {user_name} ({username})\n"
            f"ID: {user_id}\n"
            f"Текст: {message.text}"
        )

        try:
            await bot.send_message(
                channel_id,
                feedback_text
            )

        except Exception as e:
            print(f"[-] Помилка відправки в канал: {e}")

            await message.answer(
                random.choice(ERROR_MESSAGES)
            )
            return

        user_awaiting_feedback[user_id] = False

        await message.answer(
            random.choice(FEEDBACK_SUCCESS_MESSAGES)
        )
        return

    # -------------------------------------------------
    # Звичайне спілкування через Gemini
    # -------------------------------------------------

    async with ChatActionSender.typing(
        bot=bot,
        chat_id=message.chat.id
    ):
        response = await get_chat_response(
            user_id,
            message.text
        )

        if response:
            clean_text = re.sub(
                r"\*.*?\*",
                "",
                response
            ).strip()

            await asyncio.sleep(1.5)
            await message.answer(clean_text)

            save_message(user_id, "user", message.text)
            save_message(user_id, "model", response)

        else:
            await message.answer(
                random.choice(ERROR_MESSAGES)
            )


# =================================================
# Невідомі команди
# =================================================

@dp.message(F.text.startswith("/"))
async def unknown_command(message: types.Message):
    await message.answer(
        "Не знаю такої команди. "
        "Скористайся меню Telegram, щоб переглянути доступні команди."
    )