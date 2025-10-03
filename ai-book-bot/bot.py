import os
import requests
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ========= Конфиг =========
API_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Базовый URL бэкенда. Можно задать:
# BACKEND_URL=http://127.0.0.1:8000  ИЛИ  BACKEND_URL=http://127.0.0.1:8000/v1
_BASE = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
API_V1 = _BASE if _BASE.endswith("/v1") else f"{_BASE}/v1"

def api(path: str) -> str:
    # path передаём вида "/users/123/..."
    return f"{API_V1}{path}"

# ========= Бот =========
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Память на процесс (простая, не БД)
user_session: dict[int, dict] = {}   # для мастера рекомендаций
quiz_state: dict[int, dict] = {}     # для викторины
AUTO_MODE: dict[int, bool] = {}      # режим пользователя: True=авто-подбор, False=мастер

# ========= UI =========
def main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📚 Рекомендации", "🧩 Викторина", "👤 Профиль")
    return kb

def yesno_inline():
    return InlineKeyboardMarkup().add(
        InlineKeyboardButton("Авто", callback_data="quiz_auto"),
        InlineKeyboardButton("Мастер вопросов", callback_data="quiz_manual"),
    )

# ========= Хелперы =========
def has_any_prefs(user_id: int) -> bool:
    """Есть ли в бэкенде что-то про пользователя (квиз или профиль)"""
    try:
        r = requests.get(api(f"/users/{user_id}/quiz"), timeout=5)
        if r.status_code == 200 and r.json():
            return True
    except Exception:
        pass
    try:
        r = requests.get(api(f"/users/{user_id}/profile"), timeout=5)
        if r.status_code == 200 and r.json():
            return True
    except Exception:
        pass
    return False

def render_books(books: list[dict]) -> str:
    lines = []
    for b in books:
        title = b.get("title") or "Без названия"
        line = f"📖 {title}"
        if b.get("author"):
            line += f" — {b['author']}"
        if b.get("reason"):
            line += f"\n🛈 {b['reason']}"
        lines.append(line)
    return "\n\n".join(lines)

# ========= Команды =========
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("Привет! Выбери действие:", reply_markup=main_kb())

@dp.message_handler(commands=['mode'])
async def mode_toggle(message: types.Message):
    uid = message.from_user.id
    cur = AUTO_MODE.get(uid, True)
    AUTO_MODE[uid] = not cur
    state = "авто" if AUTO_MODE[uid] else "мастер"
    await message.answer(f"Режим по умолчанию: {state}.", reply_markup=main_kb())

# ========= Профиль =========
@dp.message_handler(lambda m: m.text == "👤 Профиль")
async def profile_show(message: types.Message):
    try:
        r = requests.get(api(f"/users/{message.from_user.id}/profile"), timeout=10)
        if r.status_code == 404:
            await message.answer("Профиль пока пуст. Пройди «📚 Рекомендации» или «🧩 Викторина».", reply_markup=main_kb())
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
        await message.answer(txt, reply_markup=main_kb())
    except Exception as e:
        await message.answer(f"Не удалось получить профиль: {e}", reply_markup=main_kb())

# ========= Рекомендации =========
@dp.message_handler(lambda m: m.text == "📚 Рекомендации")
async def rec_start(message: types.Message):
    uid = message.from_user.id
    # режим по умолчанию — авто
    auto = AUTO_MODE.get(uid, True)

    # если авто и есть хотя бы какие-то предпочтения — сразу дергаем бэкенд
    if auto and has_any_prefs(uid):
        await message.answer("Готовлю рекомендации…", reply_markup=main_kb())
        try:
            r = requests.post(
                api(f"/users/{uid}/recommendations"),
                json={"favorites": [], "genres": [], "authors": []},
                timeout=60,
            )
            r.raise_for_status()
            data = r.json()
            books = data.get("books", [])
            if not books:
                await message.answer("Пока нечего посоветовать 😔", reply_markup=main_kb())
                return
            await message.answer(render_books(books), reply_markup=main_kb())
            return
        except Exception as e:
            await message.answer(f"Ошибка запроса: {e}", reply_markup=main_kb())
            # Падаем в "мастер", если авто не получилось

    # мастер вопросов
    user_session[uid] = {"step": "books"}
    await message.answer(
        "Напиши 2–3 любимые книги через запятую (например: Маленький принц, Дюна, Три товарища)",
        reply_markup=main_kb()
    )

@dp.message_handler(lambda m: user_session.get(m.from_user.id, {}).get("step") == "books")
async def rec_books(message: types.Message):
    s = user_session[message.from_user.id]
    s["favorites"] = [x.strip() for x in message.text.split(",") if x.strip()]
    s["step"] = "genres"
    await message.answer("Окей! Теперь жанры (через запятую): фантастика, классика, детектив ...", reply_markup=main_kb())

@dp.message_handler(lambda m: user_session.get(m.from_user.id, {}).get("step") == "genres")
async def rec_genres(message: types.Message):
    s = user_session[message.from_user.id]
    s["genres"] = [x.strip() for x in message.text.split(",") if x.strip()]
    s["step"] = "authors"
    await message.answer("И пару любимых авторов (через запятую), или '-' если нет:", reply_markup=main_kb())

@dp.message_handler(lambda m: user_session.get(m.from_user.id, {}).get("step") == "authors")
async def rec_authors(message: types.Message):
    uid = message.from_user.id
    s = user_session[uid]
    s["authors"] = [] if message.text.strip() == "-" else [x.strip() for x in message.text.split(",") if x.strip()]
    s["step"] = None
    await message.answer("Готовлю рекомендации…", reply_markup=main_kb())

    try:
        # запрашиваем рекомендации
        r = requests.post(
            api(f"/users/{uid}/recommendations"),
            json={"favorites": s.get("favorites", []), "genres": s.get("genres", []), "authors": s.get("authors", [])},
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
        books = data.get("books", [])

        # параллельно сохраним профиль (best-effort)
        try:
            _ = requests.put(
                api(f"/users/{uid}/profile"),
                json={
                    "username": message.from_user.username,
                    "first_name": message.from_user.first_name,
                    "last_name": message.from_user.last_name,
                    "lang": "ru",
                    "preferred_genres": s.get("genres", []),
                    "preferred_authors": s.get("authors", []),
                },
                timeout=10,
            )
        except Exception:
            pass

        if not books:
            await message.answer("Пока нечего посоветовать 😔", reply_markup=main_kb())
            return

        await message.answer(render_books(books), reply_markup=main_kb())
    except Exception as e:
        await message.answer(f"Ошибка запроса: {e}", reply_markup=main_kb())

# ========= Викторина =========
@dp.message_handler(lambda m: m.text == "🧩 Викторина")
async def quiz_start(message: types.Message):
    quiz_state[message.from_user.id] = {"q": 1}
    await message.answer("Вопрос 1: Какая твоя любимая книга?", reply_markup=main_kb())

@dp.message_handler(lambda m: quiz_state.get(m.from_user.id, {}).get("q") == 1)
async def quiz_q1(message: types.Message):
    st = quiz_state[message.from_user.id]
    st["q1"] = message.text.strip()
    st["q"] = 2
    await message.answer("Вопрос 2: Сколько книг ты читаешь в год? (цифрой)", reply_markup=main_kb())

@dp.message_handler(lambda m: quiz_state.get(m.from_user.id, {}).get("q") == 2)
async def quiz_q2(message: types.Message):
    uid = message.from_user.id
    st = quiz_state[uid]
    try:
        n = int(message.text.strip())
    except:
        await message.answer("Нужно число. Например: 5", reply_markup=main_kb())
        return

    # сохраняем результаты в бэкенд
    try:
        r = requests.post(
            api(f"/users/{uid}/quiz"),
            json={"q1_favorite_book": st["q1"], "q2_books_per_year": n},
            timeout=10,
        )
        r.raise_for_status()
    except Exception as e:
        await message.answer(f"Не удалось сохранить результаты викторины: {e}", reply_markup=main_kb())
    finally:
        quiz_state.pop(uid, None)

    # Предложим как продолжать
    await message.answer("Готово! Как продолжим подборку?", reply_markup=yesno_inline())

@dp.callback_query_handler(lambda c: c.data in ("quiz_auto", "quiz_manual"))
async def quiz_next_step(call: types.CallbackQuery):
    uid = call.from_user.id
    choice = call.data
    AUTO_MODE[uid] = (choice == "quiz_auto")
    await call.answer()

    if choice == "quiz_auto" and has_any_prefs(uid):
        await call.message.answer("Готовлю рекомендации…", reply_markup=main_kb())
        try:
            r = requests.post(
                api(f"/users/{uid}/recommendations"),
                json={"favorites": [], "genres": [], "authors": []},
                timeout=60,
            )
            r.raise_for_status()
            books = r.json().get("books", [])
            if not books:
                await call.message.answer("Пока нечего посоветовать 😔", reply_markup=main_kb())
                return
            await call.message.answer(render_books(books), reply_markup=main_kb())
        except Exception as e:
            await call.message.answer(f"Ошибка запроса: {e}", reply_markup=main_kb())
    else:
        user_session[uid] = {"step": "books"}
        await call.message.answer(
            "Напиши 2–3 любимые книги через запятую (например: Маленький принц, Дюна, Три товарища)",
            reply_markup=main_kb()
        )

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
