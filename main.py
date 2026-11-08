# ==========================================================
# Запуск Тето
# ==========================================================
import asyncio
from config import bot, dp

# Імпорт модулів реєструє їхні @dp.message та @dp.callback_query хендлери.
# Порядок: спочатку текстові/кнопкові хендлери, потім медіа-хендлери.
from messages import set_main_menu
from background import random_gif_sender, random_message_sender # Фонові функції підключаються з background.py
import media

async def main():
    print("Teto is alive...")
    await set_main_menu(bot)
    asyncio.create_task(random_gif_sender())
    asyncio.create_task(random_message_sender())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())