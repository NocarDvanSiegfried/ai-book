import os
import aiohttp
from aiogram import Bot, Dispatcher, executor, types
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()
API_TOKEN = os.getenv("TELEGRAM_TOKEN")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000/v1")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

async def get_recommendations(user_id: int):
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BACKEND_URL}/users/{user_id}/recommendations",
                                json={"date": "2025-10-02"}) as resp:
            return await resp.json()

@dp.message_handler(commands=["start"])
async def start_cmd(message: types.Message):
    await message.answer("Привет! Я 📚 AI-Book бот. Введи /recommend чтобы получить книги.")

@dp.message_handler(commands=["recommend"])
async def recommend_cmd(message: types.Message):
    user_id = message.from_user.id
    recs = await get_recommendations(user_id)

    if not recs or "books" not in recs:
        await message.answer("Нет рекомендаций. Попробуй /quiz.")
        return

    for rec in recs["books"]:
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("👍 Лайк", callback_data=f"like:{rec['id']}"),
               types.InlineKeyboardButton("❌ Скрыть", callback_data=f"hide:{rec['id']}"))
        await message.answer_photo(
            photo=rec.get("coverUrl", ""),
            caption=f"📖 {rec['title']} — {rec['authors']}\n\n"
                    f"{rec['description']}\n\n💡 {rec.get('reason','')}",
            reply_markup=kb
        )

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
