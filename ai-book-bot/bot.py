import logging
from aiogram import Bot, Dispatcher, executor, types
import requests
import os

# Токен бота задаём через переменную окружения TELEGRAM_TOKEN
API_TOKEN = os.getenv("TELEGRAM_TOKEN")
BACKEND_URL = "http://127.0.0.1:8000/recommendations"  # на сервере поменяй на http://<ip>:8000/recommendations

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# старт
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Фантастика", "Классика", "Что-то другое")
    await message.answer("Привет! Выбери жанр:", reply_markup=keyboard)

# обработка жанров
@dp.message_handler(lambda message: message.text in ["Фантастика", "Классика", "Что-то другое"])
async def handle_genre(message: types.Message):
    prefs = [message.text.lower()]
    response = requests.post(BACKEND_URL, json={"user_id": message.from_user.id, "preferences": prefs})
    
    if response.status_code == 200:
        data = response.json()
        books = data.get("books", [])
        if books:
            text = "\n".join([f"📖 {b['title']} — {b['author']}" for b in books])
            await message.answer(f"Вот рекомендации:\n{text}")
        else:
            await message.answer("🤔 Пока нет рекомендаций")
    else:
        await message.answer("⚠️ Ошибка: не удалось получить рекомендации")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
