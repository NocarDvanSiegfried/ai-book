import aiosqlite
import os

DB_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DB_DIR, "app.db")

async def _column_exists(db, table: str, col: str) -> bool:
    cur = await db.execute(f"PRAGMA table_info({table})")
    rows = await cur.fetchall()
    return any(r[1] == col for r in rows)

async def init_db():
    os.makedirs(DB_DIR, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
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
        # миграция, если таблица уже была без first_name/last_name
        if not await _column_exists(db, "profiles", "first_name"):
            await db.execute("ALTER TABLE profiles ADD COLUMN first_name TEXT")
        if not await _column_exists(db, "profiles", "last_name"):
            await db.execute("ALTER TABLE profiles ADD COLUMN last_name TEXT")

        await db.execute("""
        CREATE TABLE IF NOT EXISTS quiz (
            user_id INTEGER PRIMARY KEY,
            q1_favorite_book TEXT,
            q2_books_per_year INTEGER
        )""")
        await db.commit()

async def upsert_profile(user_id:int, username, first_name, last_name, lang, genres, authors):
    preferred_genres = ",".join(genres) if isinstance(genres, list) else (genres or "")
    preferred_authors = ",".join(authors) if isinstance(authors, list) else (authors or "")
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
        """, (user_id, username, first_name, last_name, lang, preferred_genres, preferred_authors))
        await db.commit()

async def get_profile(user_id:int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            SELECT user_id, username, first_name, last_name, lang, preferred_genres, preferred_authors
            FROM profiles WHERE user_id=?
        """, (user_id,))
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

async def upsert_quiz(user_id:int, q1, q2:int):
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
        if not row:
            return None
        return {"user_id": row[0], "q1_favorite_book": row[1], "q2_books_per_year": row[2]}
