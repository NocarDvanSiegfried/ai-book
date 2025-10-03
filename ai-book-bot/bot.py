# ai-book-bot/bot.py
import os, requests
from aiogram import Bot, Dispatcher, executor, types

API_TOKEN = os.getenv("TELEGRAM_TOKEN")

_BASE = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
API_V1 = _BASE if _BASE.endswith("/v1") else f"{_BASE}/v1"

def api(path: str) -> str:
    return f"{API_V1}{path}"

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

def main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📚 Рекомендации", "🧩 Викторина", "👤 Профиль")
    return kb

# ---- временное состояние мастера рекомендаций (если понадобится)
user_session: dict[int, dict] = {}
quiz_state: dict[int, dict] = {}

async def send(chat, text):
    await chat.answer(text, reply_markup=main_kb())

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_session.pop(message.from_user.id, None)
    quiz_state.pop(message.from_user.id, None)
    await send(message, "Привет! Выбери действие:")

# ---------- Профиль ----------
@dp.message_handler(lambda m: m.text == "👤 Профиль")
async def profile_show(message: types.Message):
    url = api(f"/users/{message.from_user.id}/profile")
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 404:
            await send(message, "Профиль пока пуст. Пройди «📚 Рекомендации» или «🧩 Викторина».")
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
        await send(message, txt)
    except Exception as e:
        await send(message, f"Не удалось получить профиль: {e}")

# ---------- Рекомендации ----------
def _safe_get(url, timeout=8):
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

@dp.message_handler(lambda m: m.text == "📚 Рекомендации")
async def rec_entry(message: types.Message):
    uid = message.from_user.id
    # Пытаемся собрать данные автоматически
    quiz = _safe_get(api(f"/users/{uid}/quiz"))
    prof = _safe_get(api(f"/users/{uid}/profile"))

    favorites = []
    genres = []
    authors = []

    if quiz and quiz.get("q1_favorite_book"):
        favorites = [quiz["q1_favorite_book"]]

    if prof:
        genres = prof.get("preferred_genres", []) or []
        authors = prof.get("preferred_authors", []) or []

    # Если есть хотя бы что-то — попробуем сразу дать рекомендации
    if favorites or genres or authors:
        await send(message, "Готовлю рекомендации…")
        try:
            url = api(f"/users/{uid}/recommendations")
            payload = {"favorites": favorites, "genres": genres, "authors": authors}
            r = requests.post(url, json=payload, timeout=60)
            r.raise_for_status()
            data = r.json()
            books = data.get("books", [])
            if not books:
                await send(message, "Пока нечего посоветовать 😔")
                return

            # Автообновим профиль предпочтениями (если есть жанры/авторы)
            if genres or authors:
                prof_url = api(f"/users/{uid}/profile")
                try:
                    _ = requests.put(prof_url, json={
                        "username": message.from_user.username,
                        "first_name": message.from_user.first_name,
                        "last_name": message.from_user.last_name,
                        "lang": "ru",
                        "preferred_genres": genres,
                        "preferred_authors": authors,
                    }, timeout=8)
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
            await send(message, "\n\n".join(lines))
            return
        except Exception as e:
            await send(message, f"Ошибка запроса: {e}")

    # Иначе — короткий мастер (3 вопроса)
    user_session.pop(uid, None)
    user_session[uid] = {"step": "books"}
    await send(message, "Напиши 2–3 любимые книги через запятую (например: Маленький принц, Дюна, Три товарища)")

@dp.message_handler(lambda m: user_session.get(m.from_user.id, {}).get("step") == "books")
async def rec_books(message: types.Message):
    uid = message.from_user.id
    s = user_session[uid]
    s["favorites"] = [x.strip() for x in (message.text or "").split(",") if x.strip()]
    s["step"] = "genres"
    await send(message, "Окей! Теперь жанры (через запятую): фантастика, классика, детектив ...")

@dp.message_handler(lambda m: user_session.get(m.from_user.id, {}).get("step") == "genres")
async def rec_genres(message: types.Message):
    uid = message.from_user.id
    s = user_session[uid]
    s["genres"] = [x.strip() for x in (message.text or "").split(",") if x.strip()]
    s["step"] = "authors"
    await send(message, "И пару любимых авторов (через запятую), или '-' если нет:")

@dp.message_handler(lambda m: user_session.get(m.from_user.id, {}).get("step") == "authors")
async def rec_authors(message: types.Message):
    uid = message.from_user.id
    txt = (message.text or "").strip()
    if txt in ("📚 Рекомендации", "🧩 Викторина", "👤 Профиль", "/start", "/cancel"):
        return

    s = user_session[uid]
    s["authors"] = [] if txt == "-" else [x.strip() for x in txt.split(",") if x.strip()]
    s["step"] = None
    await send(message, "Готовлю рекомендации…")
    try:
        url = api(f"/users/{uid}/recommendations")
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
            await send(message, "Пока нечего посоветовать 😔")
            return

        # Сохраняем предпочтения в профиль
        prof_url = api(f"/users/{uid}/profile")
        try:
            _ = requests.put(prof_url, json={
                "username": message.from_user.username,
                "first_name": message.from_user.first_name,
                "last_name": message.from_user.last_name,
                "lang": "ru",
                "preferred_genres": s.get("genres", []),
                "preferred_authors": s.get("authors", []),
            }, timeout=8)
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
        await send(message, "\n\n".join(lines))
    except Exception as e:
        await send(message, f"Ошибка запроса: {e}")
    finally:
        user_session.pop(uid, None)

# ---------- Викторина ----------
@dp.message_handler(lambda m: m.text == "🧩 Викторина")
async def quiz_start(message: types.Message):
    uid = message.from_user.id
    quiz_state.pop(uid, None)
    quiz_state[uid] = {"q": 1}
    await send(message, "Вопрос 1: Какая твоя любимая книга?")

@dp.message_handler(lambda m: quiz_state.get(m.from_user.id, {}).get("q") == 1)
async def quiz_q1(message: types.Message):
    uid = message.from_user.id
    st = quiz_state[uid]
    st["q1"] = (message.text or "").strip()
    st["q"] = 2
    await send(message, "Вопрос 2: Сколько книг ты читаешь в год? (цифрой)")

@dp.message_handler(lambda m: quiz_state.get(m.from_user.id, {}).get("q") == 2)
async def quiz_q2(message: types.Message):
    uid = message.from_user.id
    st = quiz_state[uid]
    try:
        n = int((message.text or "").strip())
    except:
        await send(message, "Нужно число. Например: 5")
        return
    try:
        url = api(f"/users/{uid}/quiz")
        payload = {"q1_favorite_book": st["q1"], "q2_books_per_year": n}
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
    except Exception as e:
        await send(message, f"Не удалось сохранить результаты викторины: {e}")
    finally:
        quiz_state.pop(uid, None)
    await send(message, "Готово! Теперь можешь нажать «📚 Рекомендации». Я буду учитывать твою любимую книгу.")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
