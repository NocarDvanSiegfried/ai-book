import logging
import os
import json
import requests
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext

# --- ENV ---
API_TOKEN = os.getenv("TELEGRAM_TOKEN")
BACKEND_BASE = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")

if not API_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN is not set")

# --- Bot basics ---
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# Храним последние рекомендации, чтобы по callback показывать пояснение
# { user_id: [{"title":..,"author":..,"why":..}, ...] }
last_recs = {}

# --- Keyboards ---
def main_menu_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📚 Рекомендации").add("🧩 Викторина").add("👤 Профиль")
    return kb

def info_button(i: int):
    ikb = types.InlineKeyboardMarkup()
    ikb.add(types.InlineKeyboardButton(text="🛈 Пояснение", callback_data=f"info:{i}"))
    return ikb

# --- States ---
class RecoFSM(StatesGroup):
    wait_books = State()
    wait_genres = State()
    wait_authors = State()

class QuizFSM(StatesGroup):
    q1 = State()
    q2 = State()

# --- Handlers ---

@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    await message.answer("Привет! Выбери действие:", reply_markup=main_menu_kb())

@dp.message_handler(lambda m: m.text == "📚 Рекомендации")
async def reco_start(message: types.Message, state: FSMContext):
    await state.finish()
    await RecoFSM.wait_books.set()
    await message.answer(
        "Напиши 2–3 любимые книги через запятую (например: Маленький принц, Дюна, Три товарища)",
        reply_markup=types.ReplyKeyboardRemove()
    )

@dp.message_handler(state=RecoFSM.wait_books)
async def reco_books(message: types.Message, state: FSMContext):
    books = [x.strip() for x in message.text.split(",") if x.strip()]
    await state.update_data(favorites=books)
    await RecoFSM.wait_genres.set()
    await message.answer("Окей! Теперь жанры (через запятую): фантастика, классика, детектив ...")

@dp.message_handler(state=RecoFSM.wait_genres)
async def reco_genres(message: types.Message, state: FSMContext):
    genres = [x.strip() for x in message.text.split(",") if x.strip()]
    await state.update_data(genres=genres)
    await RecoFSM.wait_authors.set()
    await message.answer("И пару любимых авторов (через запятую), или '-' если нет:")

@dp.message_handler(state=RecoFSM.wait_authors)
async def reco_authors(message: types.Message, state: FSMContext):
    authors = []
    if message.text.strip() != "-":
        authors = [x.strip() for x in message.text.split(",") if x.strip()]

    data = await state.get_data()
    favorites = data.get("favorites", [])
    genres = data.get("genres", [])

    await message.answer("Готовлю рекомендации…")

    try:
        url = f"{BACKEND_BASE}/v1/users/{message.from_user.id}/recommendations"
        payload = {"favorites": favorites, "genres": genres, "authors": authors}
        resp = requests.post(url, json=payload, timeout=30)
        if resp.status_code != 200:
            await message.answer(f"Сервер вернул {resp.status_code}:\n{resp.text}")
            await state.finish()
            await message.answer("Вернулся в главное меню.", reply_markup=main_menu_kb())
            return

        data = resp.json()
        books = data.get("books", [])
        if not books:
            await message.answer("Пока нет рекомендаций 😕", reply_markup=main_menu_kb())
            await state.finish()
            return

        # сохраним на пользователя
        last_recs[message.from_user.id] = books

        # отправим по одной с кнопкой "🛈 Пояснение"
        for i, b in enumerate(books):
            title = b.get("title", "Без названия")
            author = b.get("author", "Автор неизвестен")
            await message.answer(f"📖 {title} — {author}", reply_markup=info_button(i))

        await state.finish()
        await message.answer("Готово! Можешь выбрать другое действие ↘️", reply_markup=main_menu_kb())

    except Exception as e:
        await message.answer(f"Ошибка: {e}")
        await state.finish()
        await message.answer("Вернулся в главное меню.", reply_markup=main_menu_kb())

@dp.callback_query_handler(lambda c: c.data and c.data.startswith("info:"))
async def on_info(call: types.CallbackQuery):
    try:
        idx = int(call.data.split(":")[1])
        books = last_recs.get(call.from_user.id, [])
        if 0 <= idx < len(books):
            why = books[idx].get("why", "Без пояснения")
            await call.answer()  # закрыть "часики"
            await call.message.answer(f"🛈 {why}")
        else:
            await call.answer("Нет данных", show_alert=True)
    except Exception:
        await call.answer("Ошибка", show_alert=True)

@dp.message_handler(lambda m: m.text == "🧩 Викторина")
async def quiz_start(message: types.Message, state: FSMContext):
    await state.finish()
    await QuizFSM.q1.set()
    await message.answer("Вопрос 1: Какая твоя любимая книга?")

@dp.message_handler(state=QuizFSM.q1)
async def quiz_q1(message: types.Message, state: FSMContext):
    await state.update_data(fav_book=message.text.strip())
    await QuizFSM.q2.set()
    await message.answer("Вопрос 2: Сколько книг ты читаешь в год? (цифрой)")

@dp.message_handler(state=QuizFSM.q2)
async def quiz_q2(message: types.Message, state: FSMContext):
    # можно валидировать число, но оставим просто
    await state.finish()
    await message.answer("Супер! Теперь нажми «📚 Рекомендации» и получи подборку.", reply_markup=main_menu_kb())

@dp.message_handler(lambda m: m.text == "👤 Профиль")
async def profile(message: types.Message):
    await message.answer("Скоро здесь появятся настройки профиля 🙂", reply_markup=main_menu_kb())

# fallback
@dp.message_handler()
async def fallback(message: types.Message):
    await message.answer("Выбери действие в меню ниже 👇", reply_markup=main_menu_kb())

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
