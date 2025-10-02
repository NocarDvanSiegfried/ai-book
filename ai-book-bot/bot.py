import logging
from aiogram import Bot, Dispatcher, executor, types
import aiohttp
import os

API_TOKEN = os.getenv("TELEGRAM_TOKEN")
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")  # На сервере укажи http://<ip>:8000

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# старт
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Фантастика", "Классика", "Что-то другое")
    await message.answer("Привет! 👋 Выбери жанр:", reply_markup=keyboard)

# обработка жанров
@dp.message_handler(lambda message: message.text in ["Фантастика", "Классика", "Что-то другое"])
async def handle_genre(message: types.Message):
    prefs = [message.text.lower()]

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/v1/users/{message.from_user.id}/recommendations",
            json={"favorites": prefs}
        ) as resp:
            if resp.status != 200:
                return await message.answer("⚠️ Ошибка: не удалось получить рекомендации")

            data = await resp.json()

    # Бекенд возвращает recommendations (строка от LLM)
    recs = data.get("recommendations", "🤔 Пока нет рекомендаций")
    await message.answer(f"📚 Вот, что я нашёл:\n\n{recs}")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
