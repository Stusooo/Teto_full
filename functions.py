# =====================================================================
# Функціонал Тето
# =====================================================================

import random
import requests
from datetime import datetime
import google.generativeai as genai
from google.api_core import exceptions
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import chat_sessions, safety_settings
from database import load_history, load_user_gender, save_exchange
from Teto_codes import API_KEYS
from Teto_list import SYSTEM_PROMPT, words_for_the_day


# =================================================
# Підключення декількох Gemini у Тето
# =================================================

class KeyProvider:
    def __init__(self, keys):
        self.keys = keys
        self.current_index = 0

    def get_current_key(self):
        if not self.keys:
            raise ValueError("Список API-ключів порожній.")
        return self.keys[self.current_index]

    def switch_to_next(self):
        if not self.keys:
            raise ValueError("Список API-ключів порожній.")
        self.current_index = (self.current_index + 1) % len(self.keys)
        return self.get_current_key()

key_provider = KeyProvider(API_KEYS)

# =================================================
# Створення або отримання сесії Gemini
# =================================================

async def get_chat_session(user_id):
    if user_id not in chat_sessions:
        history_db = load_history(user_id)
        gender = load_user_gender(user_id)
        dynamic_system_prompt = SYSTEM_PROMPT

        if gender:
            g_text = "хлопець" if gender == "male" else "дівчина"
            dynamic_system_prompt += (
                f"\nПам'ятай: твій співрозмовник — {g_text}. "
                "Використовуй відповідні закінчення.")

        current_key = key_provider.get_current_key()
        genai.configure(api_key=current_key)

        current_model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            safety_settings=safety_settings,
            system_instruction=dynamic_system_prompt)

        if not history_db:
            history_db = [
                {"role": "user", "parts": [f"Ось твоя інструкція: {dynamic_system_prompt}"]},
                {"role": "model",
                    "parts": [
                        "Привіт! *радісно підстрибую і махаю руками* "
                        "Ох, я так чекала на розмову! "
                        "Обіцяю бути найкращою подругою "
                        "і використовувати тільки круті текстові смайли! "
                        "(◕‿◕)♡ Що у тебе нового? Розповідай швидше!"]}
                ]
        chat_sessions[user_id] = current_model.start_chat(history=history_db)

    return chat_sessions[user_id]

# =================================================
# Головний запит до Gemini
# =================================================

async def get_chat_response(user_id, text):
    if not API_KEYS:
        print("[-] У Teto_codes.py немає API-ключів.")
        return None

    for _ in range(len(API_KEYS)):
        key = key_provider.get_current_key()

        try:
            genai.configure(api_key=key)
            chat = await get_chat_session(user_id)
            response = await chat.send_message_async(text)
            return response.text

        except (
            exceptions.ResourceExhausted,
            exceptions.InternalServerError):
            print( f"[-] Ключ вичерпано або збій: " f"{key[:10]}... Перемикаюсь.")
            key_provider.switch_to_next()
            chat_sessions.pop(user_id, None)
            continue

        except Exception as e:
            print(f"[-] Критична помилка Gemini: {e}")
            break

    return None

# =================================================
# Збереження взаємодій у спільну історію Тето
# =================================================

def remember_exchange(user_id, user_content, model_content):
    if not user_content or not model_content:
        return

    save_exchange(user_id, user_content, model_content)
    chat_sessions.pop(user_id, None) # Оновлюємо сесію Gemini під час наступного повідомлення

# =================================================
# Клавіатура вибору статі
# =================================================

def get_gender_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Чоловік 🧍‍♂️", callback_data="gender_male")],
            [InlineKeyboardButton(text="Жінка 🧍‍♀️", callback_data="gender_female")]])

# =================================================
# Функція погоди
# =================================================

def get_weather(city, api_key):
    url = "https://api.openweathermap.org/data/2.5/weather"
    try:
        response = requests.get(url, params={"q": city, "appid": api_key, "units": "metric", "lang": "ua"}, timeout=10)

        if response.status_code == 404:
            return "not_found", None

        response.raise_for_status()
        data = response.json()

        temp = data["main"]["temp"]
        humidity = data["main"]["humidity"]
        wind_speed = data["wind"]["speed"]
        description = data["weather"][0]["description"]

        weather_info = (
            f"Погода на сьогодні:\n"
            f"🌡 Температура: {temp}°C\n"
            f"💧 Вологість: {humidity}%\n"
            f"💨 Вітер: {wind_speed} м/с\n"
            f"☁ Стан: {description}")

        return "ok", weather_info

    except requests.exceptions.RequestException as e:
        print(f"[-] Помилка запиту до OpenWeatherMap API: {e}")
        return "error", None

    except (KeyError, ValueError, TypeError) as e:
        print(f"[-] Помилка обробки даних погоди: {e}")
        return "error", None

    except Exception as e:
        print(f"[-] Невідома помилка у функції погоди: {e}")
        return "error", None

# =================================================
# Слово дня
# =================================================

def get_word_of_the_day():
    import config
    today = datetime.now().date()

    if config.last_word_of_the_day_date != today:
        config.current_word_of_the_day = random.choice(words_for_the_day)
        config.last_word_of_the_day_date = today

    return config.current_word_of_the_day