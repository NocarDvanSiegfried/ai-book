import aiosqlite
import os
import json

DB_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DB_DIR, "app.db")

async def init_db():
    os.makedirs(DB_DIR, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        # profiles
        await db.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            lang TEXT,
            preferred_genres TEXT,
            preferred_authors TEXT
        )""")
        # quiz базовая
        await db.execute("""
        CREATE TABLE IF NOT EXISTS quiz (
            user_id INTEGER PRIMARY KEY,
            q1_favorite_book TEXT,
            q2_books_per_year INTEGER
        )""")
        # добавим колонку answers_json (мягко — через TRY/EXCEPT)
        try:
            await db.execute("ALTER TABLE quiz ADD COLUMN answers_json TEXT")
        except Exception:
            pass
        await db.commit()

async def upsert_profile(user_id:int, username=None, first_name=None, last_name=None,
                         lang="ru", genres=None, authors=None):
    genres = genres or []
    authors = authors or []
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO profiles(user_id, username, first_name, last_name, lang, preferred_genres, preferred_authors)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            username=excluded.username,
            first_name=excluded.first_name,
            last_name=excluded.last_name,
            lang=excluded.lang,
            preferred_genres=excluded.preferred_genres,
            preferred_authors=excluded.preferred_authors
        """, (user_id, username, first_name, last_name, lang, ",".join(genres), ",".join(authors)))
        await db.commit()

async def get_profile(user_id:int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            SELECT user_id, username, first_name, last_name, lang, preferred_genres, preferred_authors
            FROM profiles WHERE user_id=?""", (user_id,))
        row = await cur.fetchone()
        if not row:
            return None
        return {
            "user_id": row[0],
            "username": row[1],
            "first_name": row[2],
            "last_name": row[3],
            "lang": row[4],
            "preferred_genres": row[5].split(",") if row[5] else [],
            "preferred_authors": row[6].split(",") if row[6] else [],
        }

async def upsert_quiz(user_id:int, q1=None, q2=None, answers:dict|None=None):
    answers = answers or {}
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO quiz(user_id, q1_favorite_book, q2_books_per_year, answers_json)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            q1_favorite_book=excluded.q1_favorite_book,
            q2_books_per_year=excluded.q2_books_per_year,
            answers_json=excluded.answers_json
        """, (user_id, q1, q2, json.dumps(answers, ensure_ascii=False)))
        await db.commit()

async def get_quiz(user_id:int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            SELECT user_id, q1_favorite_book, q2_books_per_year, answers_json
            FROM quiz WHERE user_id=?""", (user_id,))
        row = await cur.fetchone()
        if not row:
            return None
        try:
            answers = json.loads(row[3]) if row[3] else {}
        except Exception:
            answers = {}
        return {
            "user_id": row[0],
            "q1_favorite_book": row[1],
            "q2_books_per_year": row[2],
            "answers": answers
        }
