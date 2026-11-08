# =============================================
# Рандомна гіфка в рандомний час
# =============================================
import asyncio
import random
from aiogram.types import FSInputFile
from config import bot, user_gender, last_message_time, chat_sessions
from Teto_list import gif_Teto, random_text_Teto, good_messages
from datetime import datetime, timedelta
from functions import remember_exchange

async def random_gif_sender():
    while True:
        time_sleep = random.randint(15800, 21000)
        await asyncio.sleep(time_sleep)
        all_users = list(user_gender.keys())
        for user_id in all_users:
            asyncio.create_task(send_individual_gif(user_id))

async def send_individual_gif(user_id):
    random_send = random.randint(100, 3600)
    await asyncio.sleep(random_send)
    try:
        gif_path = random.choice(gif_Teto)
        gif = FSInputFile(gif_path)
        random_caption_to_gif = random.choice(random_text_Teto)

        await bot.send_animation(
            user_id,
            gif,
            caption=random_caption_to_gif
        )

        remember_exchange(
            user_id,
            "Тето самостійно надіслала користувачу GIF.",
            f"Тето надіслала GIF. Підпис: {random_caption_to_gif}"
        )

    except Exception as e:
        print(f"[-] Не вдалося порадувати гіфкою юзера {user_id}: {e}")
# ==============================================
# Рандомне повідомлення в рандомний час
# ==============================================
async def random_message_sender():
    while True:
        time_sleep = random.randint(14400, 86400)
        await asyncio.sleep(time_sleep)
        all_users = list(user_gender.keys())
        for user_id in all_users:
            asyncio.create_task(send_individual_message(user_id))
            await asyncio.sleep(0.5)

async def send_individual_message(user_id):
    random_send = random.randint(1, 3600*6)
    await asyncio.sleep(random_send)

    current_hour = datetime.now().hour
    if current_hour < 9 or current_hour >= 21:
        print(f"Зараз {current_hour}:00. Тето спить і не турбує юзера {user_id}")
        return

    is_long_pause = False
    current_time = datetime.now()

    if user_id in last_message_time:
        time_diff = current_time - last_message_time[user_id]
        if time_diff > timedelta(hours=12):
            is_long_pause = True

    if is_long_pause:
        if user_id in chat_sessions:
            try:
                good_message = random.choice(good_messages)
                await bot.send_message(user_id, good_message)

                remember_exchange(
                    user_id,
                    "Тето самостійно вирішила написати користувачу після тривалої паузи.",
                    good_message
                )

                last_message_time[user_id] = datetime.now()

            except Exception as e:
                print(f"Не вдалося порадувати повідомленням юзера {user_id}: {e}")