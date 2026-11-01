# =====================================================================
# Функціонал Тето
# =====================================================================
import random
import requests
from datetime import datetime
import google.generativeai as genai
from google.api_core import exceptions

from config import chat_sessions, current_word_of_the_day, last_word_of_the_day_date, safety_settings
from config import genai as _configured_genai
from database import load_history, load_user_gender
from Teto_codes import API_KEYS
from Teto_list import (
    ERROR_MESSAGES, SYSTEM_PROMPT, words_for_the_day,
)

# =================================================
# Підключення декількох Gemini у Тето
# =================================================
class KeyProvider:
    def __init__(self, keys):
        self.keys = keys
        self.current_index = 0

    def get_current_key(self):
        return self.keys[self.current_index]

    def switch_to_next(self):
        self.current_index = (self.current_index + 1) % len(self.keys)
        return self.get_current_key()

key_provider = KeyProvider(API_KEYS)

# ===========================================================
# Головний диспетчер, який обробляє ВСІ текстові повідомлення
# ===========================================================
async def get_chat_session(user_id):
    if user_id not in chat_sessions:
        history_db = load_history(user_id)
        gender = load_user_gender(user_id)
        dynamic_system_prompt = SYSTEM_PROMPT

        if gender:
            g_text = "хлопець" if gender == "male" else "дівчина"
            dynamic_system_prompt += f"\nПам'ятай: твій співрозмовник — {g_text}. Використовуй відповідні закінчення."

        current_key = key_provider.get_current_key()
        genai.configure(api_key=current_key)

        current_model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',
            safety_settings=safety_settings,
            system_instruction=dynamic_system_prompt
        )
        if not history_db:
            history_db = [
                {"role": "user", "parts": [f"Ось твоя інструкція: {dynamic_system_prompt}"]},
                {"role": "model", "parts": ["Привіт! *радісно підстрибую і махаю руками* Ох, я так чекала на розмову! Обіцяю бути найкращою подругою і використовувати тільки круті текстові смайли! (◕‿◕)♡ Що у тебе нового? Розповідай швидше!"]}
            ]
        chat_sessions[user_id] = current_model.start_chat(history=history_db)
    return chat_sessions[user_id]

async def get_chat_response(user_id, text):
    for _ in range(len(API_KEYS)):
        key = key_provider.get_current_key()
        try:
            genai.configure(api_key=key)
            chat = await get_chat_session(user_id)
            if not chat:
                key_provider.switch_to_next()
                continue

            response = await chat.send_message_async(text)
            return response.text

        except (exceptions.ResourceExhausted, exceptions.InternalServerError):
            print(f"[-] Ключ вичерпано або збій: {key[:10]}... Перемикаюсь.")
            key_provider.switch_to_next()
            if user_id in chat_sessions:
                del chat_sessions[user_id]
            continue

        except Exception as e:
            print(f"[-] Критична помилка: {e}")
            break

    return None

# ===============================
# Кнопки
# ===============================
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def get_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Погода сьогодні💫", callback_data="weather")],
        [InlineKeyboardButton(text="Передбачення на сьогодні🎫", callback_data="future")],
        [InlineKeyboardButton(text="Картинка🖼️", callback_data="image")],
        [InlineKeyboardButton(text="Історичний Факт📝", callback_data="fact")],
        [InlineKeyboardButton(text="Цікавий наголос💥", callback_data="sound")],
        [InlineKeyboardButton(text="Музика🎧", callback_data="music")],
        [InlineKeyboardButton(text="Слово дня від Тето📖", callback_data="word_of_day")],
        [InlineKeyboardButton(text="Відгук📥", callback_data="feedback")]
    ])

def get_gender_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Чоловік 🧍‍♂️", callback_data="gender_male")],
        [InlineKeyboardButton(text="Жінка 🧍‍♀️", callback_data="gender_female")]
    ])

# ==============================
# Функція погоди
# ==============================
def get_weather(city, api_key):
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=ua"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        temp = data["main"]["temp"]
        humidity = data["main"]["humidity"]
        wind_speed = data["wind"]["speed"]
        description = data["weather"][0]["description"]
        return f"Погода на сьогодні:\n🌡 Температура: {temp}°C\n💧 Вологість: {humidity}%\n💨 Вітер: {wind_speed} м/с\n☁ Стан: {description}"
    except requests.exceptions.RequestException as e:
        print(f"[-] Помилка запиту до OpenWeatherMap API: {e}")
        return random.choice(ERROR_MESSAGES)
    except KeyError as e:
        print(f"[-] Не вдалося розібрати дані погоди (KeyError): {e} в {data}")
        return random.choice(ERROR_MESSAGES)
    except Exception as e:
        print(f"[-] Невідома помилка у функції погоди: {e}")
        return random.choice(ERROR_MESSAGES)

# ==============================
# Функція для "Слова дня"
# ==============================
def get_word_of_the_day():
    # Значення з config.py змінюємо через модуль config, щоб усі модулі бачили оновлення.
    import config
    today = datetime.now().date()

    if config.last_word_of_the_day_date != today:
        config.current_word_of_the_day = random.choice(words_for_the_day)
        config.last_word_of_the_day_date = today
    return config.current_word_of_the_day
