import os
import logging
import aiohttp
from aiogram import Bot, Dispatcher, executor, types
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
BACKEND_URL = os.getenv("BACKEND_URL")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)

# ---- Start ----
@dp.message_handler(commands=["start"])
async def start_cmd(message: types.Message):
    await message.answer("👋 Привет! Я AI-Book бот.\n\n"
                         "Доступные команды:\n"
                         "/recommend — получить рекомендации\n"
                         "/quiz — викторина")

# ---- Quiz ----
@dp.message_handler(commands=["quiz"])
async def quiz_cmd(message: types.Message):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Вопрос 1", "Вопрос 2")
    await message.answer("📖 Викторина: выбери вопрос:", reply_markup=kb)

@dp.message_handler(lambda m: m.text.startswith("Вопрос"))
async def quiz_questions(message: types.Message):
    if "1" in message.text:
        await message.answer("❓ Вопрос 1: Какая твоя любимая книга?")
    elif "2" in message.text:
        await message.answer("❓ Вопрос 2: Сколько книг ты читаешь в год?")

# ---- Recommend ----
async def get_recommendations(user_id: int, favorites: list[str]):
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BACKEND_URL}/v1/users/{user_id}/recommendations",
                                json={"favorites": favorites}) as resp:
            if resp.status == 200:
                return await resp.json()
            return {"error": f"Backend error {resp.status}"}

@dp.message_handler(commands=["recommend"])
async def recommend_cmd(message: types.Message):
    user_id = message.from_user.id
    recs = await get_recommendations(user_id, ["Маленький принц", "Гарри Поттер"])
    if "recommendations" in recs:
        await message.answer("📚 Вот что я советую:\n" + recs["recommendations"])
    else:
        await message.answer("⚠️ Не удалось получить рекомендации.")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
