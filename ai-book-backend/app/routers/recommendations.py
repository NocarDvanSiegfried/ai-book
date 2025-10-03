# app/routers/recommendations.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os, aiohttp, asyncio

router = APIRouter()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3.1:free")

class BookPref(BaseModel):
    favorites: list[str] = []
    genres: list[str] = []
    authors: list[str] = []

async def query_llm(user_books: list[str], genres: list[str], authors: list[str]) -> str:
    if not OPENROUTER_API_KEY:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY is not set")

    prompt = (
        "Ты книжный рекомендатор. На основе предпочтений предложи 3 новые книги в формате:\n"
        "1) Название — Автор (жанр)\n"
        "2) ...\n"
        "3) ...\n\n"
        f"Любимые книги: {', '.join(user_books) or '—'}\n"
        f"Жанры: {', '.join(genres) or '—'}\n"
        f"Авторы: {', '.join(authors) or '—'}"
    )

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        # опционально, но полезно:
        "HTTP-Referer": "http://45.80.228.186/",
        "X-Title": "ai-book-backend",
    }
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": "Ты умный ассистент по книгам."},
            {"role": "user", "content": prompt},
        ],
    }

    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers, json=payload
        ) as resp:
            text = await resp.text()
            # если не 200 — отдадим понятное сообщение наружу
            if resp.status != 200:
                raise HTTPException(status_code=502, detail=f"OpenRouter {resp.status}: {text}")
            data = await resp.json()
            try:
                return data["choices"][0]["message"]["content"]
            except Exception:
                raise HTTPException(status_code=502, detail=f"OpenRouter bad payload: {text}")

@router.post("/v1/users/{user_id}/recommendations")
async def recommend_books(user_id: int, prefs: BookPref):
    recs = await query_llm(prefs.favorites, prefs.genres, prefs.authors)
    return {"user_id": user_id, "recommendations": recs}
