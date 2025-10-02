import logging
from aiogram import Bot, Dispatcher, executor, types
import requests
import os

API_TOKEN = os.getenv("TELEGRAM_TOKEN")
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000/v1/recommendations")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Фантастика", "Классика", "Что-то другое")
    await message.answer("Привет! 👋 Выбери жанр:", reply_markup=keyboard)

@dp.message_handler(lambda message: message.text in ["Фантастика", "Классика", "Что-то другое"])
async def handle_genre(message: types.Message):
    prefs = [message.text.lower()]
    response = requests.post(BACKEND_URL, json={"preferences": prefs})
    if response.status_code == 200:
        data = response.json()
        books = data.get("books", [])
        if books:
            text = "\n".join([f"📖 {b['title']} — {b['author']}" for b in books])
            await message.answer(f"Рекомендую:\n{text}")
        else:
            await message.answer("🤔 Пока нет рекомендаций")
    else:
        await message.answer("⚠️ Ошибка: не удалось получить рекомендации")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
