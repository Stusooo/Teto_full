# ==============================
# Ініціалізація і вхід у Gemini
# ==============================
from aiogram import Bot, Dispatcher
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from Teto_codes import TELEGRAM_TOKEN, API_KEYS

# Спільні bot і dp використовуються в messages.py, media.py та main.py.
bot = Bot(TELEGRAM_TOKEN)
dp = Dispatcher()

genai.configure(api_key=API_KEYS[0])
safety_settings = {
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}
# gemini-2.5-flash - 25 запитів на день?, тупі обмеження (ЗАРАЗ ВИКОРИСТОВУЄТЬСЯ)

# ========================================================
# Словники - як пам'ять бота:
# ========================================================
# Ці словники спільні для всіх модулів, щоб вони бачили один і той самий стан.
chat_sessions = {}
last_message_time = {}
user_gender = {}
user_interaction_mode = {}
user_awaiting_feedback = {}
current_word_of_the_day = None
last_word_of_the_day_date = None
