import os, requests
from aiogram import Bot, Dispatcher, executor, types

API_TOKEN   = os.getenv("TELEGRAM_TOKEN")  # должен быть задан
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

if not API_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN is not set")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

def main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📚 Рекомендации", "🧩 Викторина", "👤 Профиль")
    return kb

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("Привет! Выбери действие:", reply_markup=main_kb())

# -------- Профиль --------
@dp.message_handler(lambda m: m.text == "👤 Профиль")
async def profile_show(message: types.Message):
    url = f"{BACKEND_URL}/v1/users/{message.from_user.id}/profile"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 404:
            await message.answer("Профиль пока пуст. Пройди «📚 Рекомендации» или «🧩 Викторина».")
            return
        r.raise_for_status()
        p = r.json()
        txt = (
            f"Профиль:\n"
            f"Имя: {p.get('first_name') or '-'} {p.get('last_name') or ''}\n"
            f"Язык: {p.get('lang') or 'ru'}\n"
            f"Жанры: {', '.join(p.get('preferred_genres', [])) or '-'}\n"
            f"Авторы: {', '.join(p.get('preferred_authors', [])) or '-'}"
        )
        await message.answer(txt)
    except Exception as e:
        await message.answer(f"Не удалось получить профиль: {e}")

# -------- Рекомендации --------
user_session = {}  # user_id -> dict

@dp.message_handler(lambda m: m.text == "📚 Рекомендации")
async def rec_start(message: types.Message):
    user_session[message.from_user.id] = {"step": "books"}
    await message.answer("Напиши 2–3 любимые книги через запятую (например: Маленький принц, Дюна, Три товарища)")

@dp.message_handler(lambda m: user_session.get(m.from_user.id, {}).get("step") == "books")
async def rec_books(message: types.Message):
    s = user_session[message.from_user.id]
    s["favorites"] = [x.strip() for x in message.text.split(",") if x.strip()]
    s["step"] = "genres"
    await message.answer("Окей! Теперь жанры (через запятую): фантастика, классика, детектив ...")

@dp.message_handler(lambda m: user_session.get(m.from_user.id, {}).get("step") == "genres")
async def rec_genres(message: types.Message):
    s = user_session[message.from_user.id]
    s["genres"] = [x.strip() for x in message.text.split(",") if x.strip()]
    s["step"] = "authors"
    await message.answer("И пару любимых авторов (через запятую), или '-' если нет:")

@dp.message_handler(lambda m: user_session.get(m.from_user.id, {}).get("step") == "authors")
async def rec_authors(message: types.Message):
    s = user_session[message.from_user.id]
    s["authors"] = [] if message.text.strip() == "-" else [x.strip() for x in message.text.split(",") if x.strip()]
    s["step"] = None
    await message.answer("Готовлю рекомендации…")
    try:
        url = f"{BACKEND_URL}/v1/users/{message.from_user.id}/recommendations"
        payload = {
            "favorites": s.get("favorites", []),
            "genres": s.get("genres", []),
            "authors": s.get("authors", []),
        }
        r = requests.post(url, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        books = data.get("books", [])
        if not books:
            await message.answer("Пока нечего посоветовать 😔")
            return

        # Сохраняем профиль
        prof_url = f"{BACKEND_URL}/v1/users/{message.from_user.id}/profile"
        try:
            _ = requests.put(prof_url, json={
                "username": message.from_user.username,
                "first_name": message.from_user.first_name,
                "last_name": message.from_user.last_name,
                "lang": "ru",
                "preferred_genres": s.get("genres", []),
                "preferred_authors": s.get("authors", []),
            }, timeout=10)
        except Exception:
            pass

        lines = []
        for b in books:
            line = f"📖 {b.get('title')}"
            if b.get("author"):
                line += f" — {b['author']}"
            if b.get("reason"):
                line += f"\n🛈 {b['reason']}"
            lines.append(line)
        await message.answer("\n\n".join(lines))
    except Exception as e:
        await message.answer(f"Ошибка запроса: {e}")

# -------- Викторина --------
quiz_state = {}  # user_id -> {"q": int, "q1": str}

@dp.message_handler(lambda m: m.text == "🧩 Викторина")
async def quiz_start(message: types.Message):
    quiz_state[message.from_user.id] = {"q": 1}
    await message.answer("Вопрос 1: Какая твоя любимая книга?")

@dp.message_handler(lambda m: quiz_state.get(m.from_user.id, {}).get("q") == 1)
async def quiz_q1(message: types.Message):
    st = quiz_state[message.from_user.id]
    st["q1"] = message.text.strip()
    st["q"] = 2
    await message.answer("Вопрос 2: Сколько книг ты читаешь в год? (цифрой)")

@dp.message_handler(lambda m: quiz_state.get(m.from_user.id, {}).get("q") == 2)
async def quiz_q2(message: types.Message):
    st = quiz_state[message.from_user.id]
    try:
        n = int(message.text.strip())
    except:
        await message.answer("Нужно число. Например: 5")
        return
    try:
        url = f"{BACKEND_URL}/v1/users/{message.from_user.id}/quiz"
        payload = {"q1_favorite_book": st["q1"], "q2_books_per_year": n}
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
    except Exception as e:
        await message.answer(f"Не удалось сохранить результаты викторины: {e}")
    finally:
        quiz_state.pop(message.from_user.id, None)

    await message.answer("Супер! Теперь нажми «📚 Рекомендации» и получи подборку.", reply_markup=main_kb())

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
