import os, json, aiohttp
from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException
from dotenv import load_dotenv

load_dotenv()  # подхватить /root/ai-book/ai-book-backend/.env

router = APIRouter()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3.1:free")
if not OPENROUTER_API_KEY:
    # пусть сервис поднимется, но запросы вернут 500 с нормальной ошибкой
    pass

class Prefs(BaseModel):
    favorites: List[str] = Field(default_factory=list)
    genres:    List[str] = Field(default_factory=list)
    authors:   List[str] = Field(default_factory=list)

class BookOut(BaseModel):
    title:  str
    author: Optional[str] = None
    reason: Optional[str] = None

class RecommendationResponse(BaseModel):
    books: List[BookOut]

PROMPT = """Ты — помощник по книгам.
На вход: любимые книги, жанры, авторы.
Верни РОВНО JSON массив объектов c полями title, author, reason (без пояснений и текста вокруг).
Пример:
[
  {"title": "Дюна", "author": "Фрэнк Герберт", "reason": "эпическая НФ"},
  {"title": "1984", "author": "Джордж Оруэлл", "reason": "антиутопия"}
]
Теперь сгенерируй 5 рекомендаций по пользователю:
Любимые книги: {favorites}
Жанры: {genres}
Авторы: {authors}
"""

async def call_llm(prefs: Prefs) -> List[BookOut]:
    if not OPENROUTER_API_KEY:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY не задан в .env backend-а")

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": "Ты умный ассистент по книгам."},
            {"role": "user",   "content": PROMPT.format(
                favorites=", ".join(prefs.favorites) or "-",
                genres=", ".join(prefs.genres) or "-",
                authors=", ".join(prefs.authors) or "-",
            )}
        ],
        "temperature": 0.7,
    }
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession() as s:
        async with s.post("https://openrouter.ai/api/v1/chat/completions",
                          headers=headers, json=payload) as r:
            if r.status >= 400:
                text = await r.text()
                raise HTTPException(status_code=502, detail=f"OpenRouter {r.status}: {text}")
            data = await r.json()

    content = data["choices"][0]["message"]["content"]
    # пытаемся разобрать JSON из ответа
    try:
        items = json.loads(content)
        out = []
        for it in items:
            out.append(BookOut(
                title=str(it.get("title", "")).strip(),
                author=(it.get("author") or None),
                reason=(it.get("reason") or None),
            ))
        return out
    except Exception:
        # fallback — если модель прислала текст, а не JSON
        return [BookOut(title=line.strip()) for line in content.split("\n") if line.strip()][:5]

@router.post("/v1/users/{user_id}/recommendations", response_model=RecommendationResponse)
async def recommend(user_id: int, prefs: Prefs):
    books = await call_llm(prefs)
    return {"books": books}
