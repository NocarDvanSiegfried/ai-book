# bot.py
import os
import logging
import requests
from aiogram import Bot, Dispatcher, executor, types

# ---------- Конфиг ----------
logging.basicConfig(level=logging.INFO)
API_TOKEN = os.getenv("TELEGRAM_TOKEN")
BACKEND_URL = (os.getenv("BACKEND_URL", "http://127.0.0.1:8000/v1") or "").rstrip("/")

if not API_TOKEN:
    raise SystemExit("TELEGRAM_TOKEN не задан. Укажи в .env или EnvironmentFile systemd.")

# ---------- Инициализация бота ----------
bot = Bot(token=API_TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot)

# Память для сессий (простая in-memory)
user_session = {}  # user_id -> {step, favorites, genres, authors}
quiz_state   = {}  # user_id -> {q, q1}

def main_kb() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📚 Рекомендации", "🧩 Викторина", "👤 Профиль")
    return kb

# ---------- Хелперы HTTP ----------
def _get(url: str, **kw):
    return requests.get(url, timeout=kw.pop("timeout", 10), **kw)

def _post(url: str, **kw):
    return requests.post(url, timeout=kw.pop("timeout", 15), **kw)

def _put(url: str, **kw):
    return requests.put(url, timeout=kw.pop("timeout", 10), **kw)

# ---------- Команды ----------
@dp.message_handler(commands=["start", "help"])
async def cmd_start(message: types.Message):
    await message.answer("Привет! Выбери действие:", reply_markup=main_kb())

@dp.message_handler(commands=["cancel"])
async def cmd_cancel(message: types.Message):
    user_session.pop(message.from_user.id, None)
    quiz_state.pop(message.from_user.id, None)
    await message.answer("Ок, всё сбросил.", reply_markup=main_kb())

# ======================================================================
# Профиль
# ======================================================================
@dp.message_handler(lambda m: m.text == "👤 Профиль")
async def profile_show(message: types.Message):
    url = f"{BACKEND_URL}/users/{message.from_user.id}/profile"
    try:
        r = _get(url)
        if r.status_code == 404:
            await message.answer("Профиль пока пуст. Пройди «📚 Рекомендации» или «🧩 Викторина».")
            return
        r.raise_for_status()
        p = r.json()
        txt = (
            "<b>Профиль</b>\n"
            f"Имя: @{p.get('username') or '-'}\n"
            f"Язык: {p.get('lang') or 'ru'}\n"
            f"Жанры: {', '.join(p.get('preferred_genres', [])) or '-'}\n"
            f"Авторы: {', '.join(p.get('preferred_authors', [])) or '-'}"
        )
        await message.answer(txt)
    except Exception as e:
        await message.answer(f"Не удалось получить профиль: <code>{e}</code>")

# ======================================================================
# Рекомендации
# ======================================================================
@dp.message_handler(lambda m: m.text == "📚 Рекомендации")
async def rec_start(message: types.Message):
    user_session[message.from_user.id] = {"step": "books"}
    await message.answer(
        "Напиши 2–3 любимые книги через запятую (например: Маленький принц, Дюна, Три товарища)"
    )

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
    uid = message.from_user.id
    s = user_session[uid]
    s["authors"] = [] if message.text.strip() == "-" else [x.strip() for x in message.text.split(",") if x.strip()]
    s["step"] = None
    await message.answer("Готовлю рекомендации…")

    try:
        # Запрос рекомендаций
        url = f"{BACKEND_URL}/users/{uid}/recommendations"
        payload = {
            "favorites": s.get("favorites", []),
            "genres": s.get("genres", []),
            "authors": s.get("authors", []),
        }
        r = _post(url, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        books = data.get("books", []) or []

        if not books:
            await message.answer("Пока нечего посоветовать 😔")
            return

        # Сохранить предпочтения в профиль (схема БД: username/lang/genres/authors)
        prof_url = f"{BACKEND_URL}/users/{uid}/profile"
        _ = _put(
            prof_url,
            json={
                "username": message.from_user.username,
                "lang": "ru",
                "preferred_genres": s.get("genres", []),
                "preferred_authors": s.get("authors", []),
            },
        )

        # Выводим рекомендации
        lines = []
        for b in books:
            title = b.get("title") or "Без названия"
            author = b.get("author")
            reason = b.get("reason")
            line = f"📖 <b>{title}</b>"
            if author:
                line += f" — {author}"
            if reason:
                line += f"\n🛈 {reason}"
            lines.append(line)

        await message.answer("\n\n".join(lines))
    except requests.HTTPError as e:
        await message.answer(f"Сервер вернул ошибку: <code>{e.response.status_code}</code>\n{e.response.text}")
    except Exception as e:
        await message.answer(f"Ошибка запроса: <code>{e}</code>")
    finally:
        # завершаем сессию рекомендаций
        user_session.pop(uid, None)

# ======================================================================
# Викторина
# ======================================================================
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
    uid = message.from_user.id
    st = quiz_state[uid]
    try:
        n = int(message.text.strip())
    except Exception:
        await message.answer("Нужно число. Например: 5")
        return

    # сохраняем результаты викторины в бэкенд
    try:
        url = f"{BACKEND_URL}/users/{uid}/quiz"
        payload = {"q1_favorite_book": st["q1"], "q2_books_per_year": n}
        r = _post(url, json=payload)
        r.raise_for_status()
    except Exception as e:
        await message.answer(f"Не удалось сохранить результаты викторины: <code>{e}</code>")
    finally:
        quiz_state.pop(uid, None)

    await message.answer("Супер! Теперь нажми «📚 Рекомендации» и получи подборку.", reply_markup=main_kb())

# ---------- Точка входа ----------
if __name__ == "__main__":
    # skip_updates=True — пропускаем накопившиеся апдейты при рестарте сервиса
    executor.start_polling(dp, skip_updates=True)
