import aiosqlite
import os

DB_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DB_DIR, "app.db")

async def init_db():
    os.makedirs(DB_DIR, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            lang TEXT,
            preferred_genres TEXT,
            preferred_authors TEXT
        )""")
        await db.execute("""
        CREATE TABLE IF NOT EXISTS quiz (
            user_id INTEGER PRIMARY KEY,
            q1_favorite_book TEXT,
            q2_books_per_year INTEGER
        )""")
        await db.commit()

async def upsert_profile(user_id:int, username, lang, genres, authors):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO profiles(user_id, username, lang, preferred_genres, preferred_authors)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            username=excluded.username,
            lang=excluded.lang,
            preferred_genres=excluded.preferred_genres,
            preferred_authors=excluded.preferred_authors
        """, (user_id, username, lang, ",".join(genres), ",".join(authors)))
        await db.commit()

async def get_profile(user_id:int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id, username, lang, preferred_genres, preferred_authors FROM profiles WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
        if not row: return None
        return {
            "user_id": row[0],
            "username": row[1],
            "lang": row[2],
            "preferred_genres": row[3].split(",") if row[3] else [],
            "preferred_authors": row[4].split(",") if row[4] else [],
        }

async def upsert_quiz(user_id:int, q1, q2):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO quiz(user_id, q1_favorite_book, q2_books_per_year)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            q1_favorite_book=excluded.q1_favorite_book,
            q2_books_per_year=excluded.q2_books_per_year
        """, (user_id, q1, q2))
        await db.commit()

async def get_quiz(user_id:int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id, q1_favorite_book, q2_books_per_year FROM quiz WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
        if not row: return None
        return {"user_id": row[0], "q1_favorite_book": row[1], "q2_books_per_year": row[2]}
