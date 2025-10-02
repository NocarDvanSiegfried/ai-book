import os, logging, json, asyncio, aiohttp
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv("TELEGRAM_TOKEN")
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# --- Меню
def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📚 Рекомендации"),
           KeyboardButton("🧩 Викторина"),
           KeyboardButton("👤 Профиль"))
    return kb

# --- Память на пользователя (просто словарь в ОЗУ)
STATE = {}  # user_id -> {"favorites":[], "genres":[], "authors":[],"stage":""}

@dp.message_handler(commands=['start', 'menu'])
async def cmd_start(message: types.Message):
    await message.answer("Привет! Выбери действие:", reply_markup=main_menu())

# --- Рекомендации (быстрый сценарий)
@dp.message_handler(lambda m: m.text == "📚 Рекомендации")
async def rec_start(message: types.Message):
    uid = message.from_user.id
    STATE[uid] = {"favorites":[], "genres":[], "authors":[], "stage":"fav"}
    await message.answer("Напиши 2–3 любимые книги через запятую (например: Маленький принц, Дюна, Три товарища)")

@dp.message_handler(lambda m: STATE.get(m.from_user.id, {}).get("stage") == "fav")
async def rec_genres(message: types.Message):
    uid = message.from_user.id
    STATE[uid]["favorites"] = [x.strip() for x in message.text.split(",") if x.strip()]
    STATE[uid]["stage"] = "genres"
    await message.answer("Окей! Теперь жанры (через запятую): фантастика, классика, детектив ...")

@dp.message_handler(lambda m: STATE.get(m.from_user.id, {}).get("stage") == "genres")
async def rec_authors(message: types.Message):
    uid = message.from_user.id
    STATE[uid]["genres"] = [x.strip() for x in message.text.split(",") if x.strip()]
    STATE[uid]["stage"] = "authors"
    await message.answer("И пару любимых авторов (через запятую), или '-' если нет:")

@dp.message_handler(lambda m: STATE.get(m.from_user.id, {}).get("stage") == "authors")
async def rec_finish(message: types.Message):
    uid = message.from_user.id
    authors = [] if message.text.strip() == "-" else [x.strip() for x in message.text.split(",") if x.strip()]
    STATE[uid]["authors"] = authors

    payload = {
        "favorites": STATE[uid]["favorites"],
        "genres": STATE[uid]["genres"],
        "authors": STATE[uid]["authors"],
    }
    await message.answer("Готовлю рекомендации…")

    # POST на бэкенд
    try:
        async with aiohttp.ClientSession() as s:
            url = f"{BACKEND_URL}/v1/users/{uid}/recommendations"
            async with s.post(url, json=payload, timeout=120) as r:
                if r.status == 200:
                    data = await r.json()
                    books = data.get("books", [])
                    if not books:
                        await message.answer("Пока ничего не нашёл 😕", reply_markup=main_menu())
                        return
                    lines = [f"📖 <b>{b.get('title')}</b> — {b.get('author') or '—'}\n🛈 {b.get('reason') or ''}".strip() for b in books]
                    await message.answer("\n\n".join(lines), parse_mode="HTML", reply_markup=main_menu())
                else:
                    txt = await r.text()
                    await message.answer(f"Сервер вернул {r.status}:\n{txt}", reply_markup=main_menu())
    except Exception as e:
        await message.answer(f"Ошибка запроса: {e}", reply_markup=main_menu())

    STATE.pop(uid, None)

# --- Викторина (простой вариант из sequence)
@dp.message_handler(lambda m: m.text == "🧩 Викторина")
async def quiz_start(message: types.Message):
    uid = message.from_user.id
    STATE[uid] = {"favorites":[], "genres":[], "authors":[], "stage":"q1"}
    await message.answer("Вопрос 1: Какая твоя любимая книга?")

@dp.message_handler(lambda m: STATE.get(m.from_user.id, {}).get("stage") == "q1")
async def quiz_q2(message: types.Message):
    uid = message.from_user.id
    if message.text.strip():
        STATE[uid]["favorites"] = [message.text.strip()]
    STATE[uid]["stage"] = "q2"
    await message.answer("Вопрос 2: Сколько книг ты читаешь в год? (цифрой)")

@dp.message_handler(lambda m: STATE.get(m.from_user.id, {}).get("stage") == "q2")
async def quiz_done(message: types.Message):
    uid = message.from_user.id
    # тут ответ ни на что не влияет, просто завершаем сцену
    STATE[uid]["stage"] = None
    await message.answer("Супер! Теперь нажми «📚 Рекомендации» и получи подборку.", reply_markup=main_menu())

@dp.message_handler(lambda m: m.text == "👤 Профиль")
async def profile(message: types.Message):
    await message.answer("Скоро здесь появятся настройки профиля 🙂", reply_markup=main_menu())

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
