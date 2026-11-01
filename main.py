# ==========================================================
# Запуск Тето
# ==========================================================
import asyncio

from config import bot, dp

# Імпорт модулів реєструє їхні @dp.message та @dp.callback_query хендлери.
# Порядок: спочатку текстові/кнопкові хендлери, потім медіа-хендлери.
import messages
import media

# Фонові функції підключаються з background.py.
from background import random_gif_sender, random_message_sender

async def main():
    print("Teto is alive...")
    asyncio.create_task(random_gif_sender())
    asyncio.create_task(random_message_sender())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
