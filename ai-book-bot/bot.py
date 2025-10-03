import os, requests
from aiogram import Bot, Dispatcher, executor, types

API_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not API_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN is not set")

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

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("Привет! Выбери действие:", reply_markup=main_kb())

# ---------- Профиль ----------
@dp.message_handler(lambda m: m.text == "👤 Профиль")
async def profile_show(message: types.Message):
    url = api(f"/users/{message.from_user.id}/profile")
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

# ---------- Быстрые рекомендации без опроса, если есть данные ----------
def _recommend_with(prefs: dict) -> list[dict]:
    """синхронный вызов бэкенда для простоты"""
    url = api(f"/users/{prefs['user_id']}/recommendations")
    payload = {
        "favorites": prefs.get("favorites", []),
        "genres": prefs.get("genres", []),
        "authors": prefs.get("authors", []),
    }
    r = requests.post(url, json=payload, timeout=60)
    r.raise_for_status()
    return r.json().get("books", [])

def _try_build_prefs_from_backend(uid: int) -> dict | None:
    """Пытаемся собрать prefs из профиля/викторины."""
    # 1) профиль
    try:
        pr = requests.get(api(f"/users/{uid}/profile"), timeout=5)
        if pr.status_code == 200:
            p = pr.json()
            return {
                "user_id": uid,
                "favorites": [],  # возьмём из квиза ниже, если будет
                "genres": p.get("preferred_genres", []),
                "authors": p.get("preferred_authors", []),
            }
    except Exception:
        pass
    # 2) квиз
    try:
        qz = requests.get(api(f"/users/{uid}/quiz"), timeout=5)
        if qz.status_code == 200:
            q = qz.json()
            answers = q.get("answers", {}) or {}
            genres = answers.get("favorite_genres", [])
            fav = q.get("q1_favorite_book")
            return {
                "user_id": uid,
                "favorites": [fav] if fav else [],
                "genres": genres,
                "authors": [],
            }
    except Exception:
        pass
    return None

# ---------- Рекомендации (диалоговый режим по-прежнему есть как fallback) ----------
user_session = {}

@dp.message_handler(lambda m: m.text == "📚 Рекомендации")
async def rec_start(message: types.Message):
    uid = message.from_user.id
    # Сначала попробуем быстрый путь
    prefs = _try_build_prefs_from_backend(uid)
    if prefs and (prefs["genres"] or prefs["favorites"] or prefs["authors"]):
        try:
            books = _recommend_with(prefs)
            if books:
                lines=[]
                for b in books:
                    line = f"📖 {b.get('title')}"
                    if b.get("author"):
                        line += f" — {b['author']}"
                    if b.get("reason"):
                        line += f"\n🛈 {b['reason']}"
                    lines.append(line)
                await message.answer("\n\n".join(lines))
                return
        except Exception as e:
            await message.answer(f"Не удалось получить рекомендации по профилю/викторине: {e}")

    # если нет данных — запускаем мастер
    user_session[uid] = {"step": "books"}
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
    uid = message.from_user.id
    s = user_session[uid]
    s["authors"] = [] if message.text.strip() == "-" else [x.strip() for x in message.text.split(",") if x.strip()]
    s["step"] = None
    await message.answer("Готовлю рекомендации…")
    try:
        books = _recommend_with({"user_id": uid,
                                 "favorites": s.get("favorites", []),
                                 "genres": s.get("genres", []),
                                 "authors": s.get("authors", [])})
        # обновим профиль предпочтениями
        try:
            requests.put(api(f"/users/{uid}/profile"), json={
                "username": message.from_user.username,
                "first_name": message.from_user.first_name,
                "last_name": message.from_user.last_name,
                "lang": "ru",
                "preferred_genres": s.get("genres", []),
                "preferred_authors": s.get("authors", []),
            }, timeout=8)
        except Exception:
            pass
        if not books:
            await message.answer("Пока нечего посоветовать 😔")
            return
        lines=[]
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

# ---------- Викторина 2.0 ----------
quiz_state = {}  # user_id -> {"q": int, ...}

QUESTS = [
    ("q1", "Вопрос 1: Какая твоя любимая книга?"),
    ("q2", "Вопрос 2: Сколько книг ты читаешь в год? (цифрой)"),
    ("genres", "Вопрос 3: Любимые жанры? (через запятую, например: фантастика, классика)"),
    ("length", "Вопрос 4: Какой объём предпочитаешь? (short/medium/long)"),
    ("mood", "Вопрос 5: Какое настроение книг нравится? (cozy/dark/adventurous/умное/романтичное …)"),
    ("lang", "Вопрос 6: На каком языке обычно читаешь? (ru/en/… )"),
    ("format", "Вопрос 7: Формат? (ebook/audiobook/paper)"),
]

@dp.message_handler(lambda m: m.text == "🧩 Викторина")
async def quiz_start(message: types.Message):
    quiz_state[message.from_user.id] = {"step": 0}
    await message.answer(QUESTS[0][1])

@dp.message_handler(lambda m: message.from_user.id in quiz_state)  # type: ignore
async def quiz_flow(message: types.Message):
    uid = message.from_user.id
    if uid not in quiz_state:
        return
    st = quiz_state[uid]
    idx = st.get("step", 0)
    key, _ = QUESTS[idx]

    text = message.text.strip()
    # валидации
    if key == "q2":
        try:
            int(text)
        except:
            await message.answer("Нужно число. Например: 5")
            return

    # сохраняем ответ
    st[key] = text
    idx += 1
    if idx < len(QUESTS):
        st["step"] = idx
        await message.answer(QUESTS[idx][1])
        return

    # закончили опрос -> шлём в бэкенд и отдаём рекомендации
    try:
        payload = {
            "q1_favorite_book": st.get("q1"),
            "q2_books_per_year": int(st.get("q2", "0") or 0),
            "favorite_genres": [x.strip() for x in st.get("genres","").split(",") if x.strip()],
            "preferred_length": st.get("length"),
            "mood": st.get("mood"),
            "language": st.get("lang"),
            "format": st.get("format"),
        }
        r = requests.post(api(f"/users/{uid}/quiz"), json=payload, timeout=10)
        r.raise_for_status()
        # обновим профиль базовыми предпочтениями (жанры)
        try:
            requests.put(api(f"/users/{uid}/profile"), json={
                "username": message.from_user.username,
                "first_name": message.from_user.first_name,
                "last_name": message.from_user.last_name,
                "lang": payload.get("language") or "ru",
                "preferred_genres": payload.get("favorite_genres", []),
                "preferred_authors": [],
            }, timeout=8)
        except Exception:
            pass

        # сразу рекомендации без опроса
        prefs = {
            "user_id": uid,
            "favorites": [payload["q1_favorite_book"]] if payload.get("q1_favorite_book") else [],
            "genres": payload.get("favorite_genres", []),
            "authors": [],
        }
        books = _recommend_with(prefs)
        if books:
            lines=[]
            for b in books:
                line = f"📖 {b.get('title')}"
                if b.get("author"):
                    line += f" — {b['author']}"
                if b.get("reason"):
                    line += f"\n🛈 {b['reason']}"
                lines.append(line)
            await message.answer("\n\n".join(lines), reply_markup=main_kb())
        else:
            await message.answer("Готово! Теперь нажми «📚 Рекомендации».", reply_markup=main_kb())
    except Exception as e:
        await message.answer(f"Не удалось сохранить/получить данные викторины: {e}", reply_markup=main_kb())
    finally:
        quiz_state.pop(uid, None)

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
