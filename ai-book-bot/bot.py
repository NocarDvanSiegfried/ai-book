import os
import requests
from aiogram import Bot, Dispatcher, executor, types

# --- ENV / API ---
API_TOKEN = os.getenv("TELEGRAM_TOKEN")

_BASE = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
API_V1 = _BASE if _BASE.endswith("/v1") else f"{_BASE}/v1"

def api(path: str) -> str:
    return f"{API_V1}{path}"

# --- BOT ---
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

def main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📚 Рекомендации", "🧩 Викторина", "👤 Профиль")
    return kb

def rec_mode_kb():
    ikb = types.InlineKeyboardMarkup()
    ikb.add(
        types.InlineKeyboardButton("⚡ Авто", callback_data="rec_auto"),
        types.InlineKeyboardButton("🛠 Мастер вопросов", callback_data="rec_master"),
    )
    return ikb

# --- SIMPLE STATE ---
quiz_cache = {}        # user_id -> {"q1": str, "q2": int}
wizard_state = {}      # user_id -> {"step": str, "favorites":[], "genres":[], "authors":[]}

# ===================== COMMON =====================

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("Привет! Выбери действие:", reply_markup=main_kb())

# ===================== PROFILE =====================

@dp.message_handler(lambda m: m.text == "👤 Профиль")
async def profile_show(message: types.Message):
    try:
        r = requests.get(api(f"/users/{message.from_user.id}/profile"), timeout=10)
        if r.status_code == 404:
            await message.answer(
                "Профиль пока пуст. Пройди «📚 Рекомендации» (Авто) или «🧩 Викторина».",
                reply_markup=main_kb()
            )
            return
        r.raise_for_status()
        p = r.json()
        txt = (
            "Профиль:\n"
            f"Имя: {p.get('first_name') or '-'} {p.get('last_name') or ''}\n"
            f"Язык: {p.get('lang') or 'ru'}\n"
            f"Жанры: {', '.join(p.get('preferred_genres', [])) or '-'}\n"
            f"Авторы: {', '.join(p.get('preferred_authors', [])) or '-'}"
        )
        await message.answer(txt, reply_markup=main_kb())
    except Exception as e:
        await message.answer(f"Не удалось получить профиль: {e}", reply_markup=main_kb())

# ===================== QUIZ =====================

@dp.message_handler(lambda m: m.text == "🧩 Викторина")
async def quiz_start(message: types.Message):
    quiz_cache[message.from_user.id] = {"q": 1}
    await message.answer("Вопрос 1: Какая твоя любимая книга?",
                         reply_markup=main_kb())

@dp.message_handler(lambda m: quiz_cache.get(m.from_user.id, {}).get("q") == 1)
async def quiz_q1(message: types.Message):
    st = quiz_cache[message.from_user.id]
    st["q1"] = message.text.strip()
    st["q"] = 2
    await message.answer("Вопрос 2: Сколько книг ты читаешь в год? (цифрой)",
                         reply_markup=main_kb())

@dp.message_handler(lambda m: quiz_cache.get(m.from_user.id, {}).get("q") == 2)
async def quiz_q2(message: types.Message):
    st = quiz_cache[message.from_user.id]
    try:
        st["q2"] = int(message.text.strip())
    except ValueError:
        await message.answer("Нужно число. Например: 5", reply_markup=main_kb())
        return

    # сохраняем на бэкенд (не обязательно для работы «Авто», но полезно)
    try:
        r = requests.post(
            api(f"/users/{message.from_user.id}/quiz"),
            json={"q1_favorite_book": st["q1"], "q2_books_per_year": st["q2"]},
            timeout=10
        )
        r.raise_for_status()
    except Exception:
        pass

    st["q"] = None
    await message.answer(
        "Готово! Как продолжим подборку?",
        reply_markup=main_kb()
    )
    await message.answer("Выбери режим:", reply_markup=rec_mode_kb())

# ===================== RECOMMENDATIONS =====================

@dp.message_handler(lambda m: m.text == "📚 Рекомендации")
async def rec_entry(message: types.Message):
    # ПЕРВЫМ ДЕЛОМ — всегда показать выбор режима
    await message.answer("Выбери режим:", reply_markup=rec_mode_kb())
    await message.answer("Можно вернуться в меню в любой момент.", reply_markup=main_kb())

# ---- Авто режим ----
@dp.callback_query_handler(lambda c: c.data == "rec_auto")
async def rec_auto(call: types.CallbackQuery):
    uid = call.from_user.id

    # собираем предпочтения: сначала из викторины, затем дополняем профилем
    favorites, genres, authors = [], [], []

    q = quiz_cache.get(uid)
    if q and q.get("q1"):
        favorites.append(q["q1"])

    try:
        pr = requests.get(api(f"/users/{uid}/profile"), timeout=10)
        if pr.status_code == 200:
            pdata = pr.json()
            genres = pdata.get("preferred_genres") or []
            authors = pdata.get("preferred_authors") or []
    except Exception:
        pass

    # если пусто — всё равно идём в LLM: он сможет дать «популярное» по умолчанию
    await bot.answer_callback_query(call.id)
    await bot.send_message(uid, "Готовлю рекомендации…", reply_markup=main_kb())

    try:
        r = requests.post(
            api(f"/users/{uid}/recommendations"),
            json={"favorites": favorites, "genres": genres, "authors": authors},
            timeout=60
        )
        r.raise_for_status()
        data = r.json()
        books = data.get("books", [])
        if not books:
            await bot.send_message(uid, "Пока нечего посоветовать 😔", reply_markup=main_kb())
            return

        # обновим профиль жанрами/авторами, если есть
        try:
            requests.post(
                api(f"/users/{uid}/profile"),
                json={
                    "username": call.from_user.username,
                    "first_name": call.from_user.first_name,
                    "last_name": call.from_user.last_name,
                    "lang": "ru",
                    "preferred_genres": genres,
                    "preferred_authors": authors,
                },
                timeout=10
            )
        except Exception:
            pass

        lines = []
        for b in books:
            line = f"📚 {b.get('title')}"
            if b.get("author"):
                line += f" — {b['author']}"
            if b.get("reason"):
                line += f"\n▫ {b['reason']}"
            lines.append(line)
        await bot.send_message(uid, "Готово! Рекомендации:", reply_markup=main_kb())
        await bot.send_message(uid, "\n\n".join(lines), reply_markup=main_kb())
    except requests.HTTPError as e:
        await bot.send_message(uid, f"Бэкенд вернул ошибку: {e}", reply_markup=main_kb())
    except Exception as e:
        await bot.send_message(uid, f"Ошибка запроса: {e}", reply_markup=main_kb())

# ---- Мастер вопросов ----
@dp.callback_query_handler(lambda c: c.data == "rec_master")
async def rec_master(call: types.CallbackQuery):
    uid = call.from_user.id
    wizard_state[uid] = {"step": "books", "favorites": [], "genres": [], "authors": []}
    await bot.answer_callback_query(call.id)
    await bot.send_message(uid,
        "Напиши 2–3 любимые книги через запятую (например: Маленький принц, Дюна, Три товарища)",
        reply_markup=main_kb()
    )

@dp.message_handler(lambda m: wizard_state.get(m.from_user.id, {}).get("step") == "books")
async def w_books(message: types.Message):
    st = wizard_state[message.from_user.id]
    st["favorites"] = [x.strip() for x in message.text.split(",") if x.strip()]
    st["step"] = "genres"
    await message.answer("Окей! Теперь жанры (через запятую): фантастика, классика, детектив ...",
                         reply_markup=main_kb())

@dp.message_handler(lambda m: wizard_state.get(m.from_user.id, {}).get("step") == "genres")
async def w_genres(message: types.Message):
    st = wizard_state[message.from_user.id]
    st["genres"] = [x.strip() for x in message.text.split(",") if x.strip()]
    st["step"] = "authors"
    await message.answer("И пару любимых авторов (через запятую), или '-' если нет:",
                         reply_markup=main_kb())

@dp.message_handler(lambda m: wizard_state.get(m.from_user.id, {}).get("step") == "authors")
async def w_authors(message: types.Message):
    uid = message.from_user.id
    st = wizard_state[uid]
    st["authors"] = [] if message.text.strip() == "-" else [x.strip() for x in message.text.split(",") if x.strip()]
    st["step"] = None

    await message.answer("Готовлю рекомендации…", reply_markup=main_kb())

    try:
        r = requests.post(
            api(f"/users/{uid}/recommendations"),
            json={"favorites": st["favorites"], "genres": st["genres"], "authors": st["authors"]},
            timeout=60
        )
        r.raise_for_status()
        data = r.json()
        books = data.get("books", [])
        if not books:
            await message.answer("Пока нечего посоветовать 😔", reply_markup=main_kb())
            return

        # сохраним предпочтения в профиль
        try:
            requests.post(
                api(f"/users/{uid}/profile"),
                json={
                    "username": message.from_user.username,
                    "first_name": message.from_user.first_name,
                    "last_name": message.from_user.last_name,
                    "lang": "ru",
                    "preferred_genres": st["genres"],
                    "preferred_authors": st["authors"],
                },
                timeout=10
            )
        except Exception:
            pass

        lines = []
        for b in books:
            line = f"📚 {b.get('title')}"
            if b.get("author"):
                line += f" — {b['author']}"
            if b.get("reason"):
                line += f"\n▫ {b['reason']}"
            lines.append(line)
        await message.answer("\n\n".join(lines), reply_markup=main_kb())
    except requests.HTTPError as e:
        await message.answer(f"Бэкенд вернул ошибку: {e}", reply_markup=main_kb())
    except Exception as e:
        await message.answer(f"Ошибка запроса: {e}", reply_markup=main_kb())
    finally:
        wizard_state.pop(uid, None)

# ===================================================

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
