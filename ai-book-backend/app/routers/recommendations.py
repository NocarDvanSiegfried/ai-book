# app/routers/recommendations.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import os, aiohttp, asyncio, json, re
from typing import List, Optional

router = APIRouter(prefix="/v1", tags=["recommendations"])

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3.1:free")
if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY is not set")

class BookPref(BaseModel):
    favorites: List[str] = Field(default_factory=list)
    genres: List[str] = Field(default_factory=list)
    authors: List[str] = Field(default_factory=list)

class BookOut(BaseModel):
    title: str
    author: Optional[str] = None
    reason: Optional[str] = None

class RecResponse(BaseModel):
    books: List[BookOut]

PROMPT = (
    "Ты книжный ассистент. Дай 5 рекомендаций.\n"
    "Любимые книги: {favorites}\n"
    "Жанры: {genres}\n"
    "Авторы: {authors}\n"
    "Ответ строго в JSON-массиве объектов с полями title, author, reason без лишнего текста."
)

async def _call_llm(prefs: BookPref) -> List[BookOut]:
    prompt_text = PROMPT.format(
        favorites=", ".join(prefs.favorites) or "-",
        genres=", ".join(prefs.genres) or "-",
        authors=", ".join(prefs.authors) or "-",
    )

    async with aiohttp.ClientSession() as session:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": OPENROUTER_MODEL,
            "messages": [
                {"role": "system", "content": "Отвечай кратко и по делу."},
                {"role": "user", "content": prompt_text},
            ],
        }
        async with session.post("https://openrouter.ai/api/v1/chat/completions",
                                headers=headers, json=payload, timeout=60) as resp:
            if resp.status >= 400:
                txt = await resp.text()
                raise HTTPException(502, f"LLM HTTP {resp.status}: {txt}")
            data = await resp.json()

    content = data["choices"][0]["message"]["content"]

    # Вытянуть JSON даже если модель добавила текст
    m = re.search(r"\[.*\]", content, re.S)
    raw = m.group(0) if m else content
    try:
        arr = json.loads(raw)
    except Exception:
        # fallback: список по строкам
        lines = [l.strip("-• \n") for l in content.splitlines() if l.strip()]
        arr = [{"title": l} for l in lines[:5]]

    out: List[BookOut] = []
    for it in arr:
        if isinstance(it, dict):
            title = (it.get("title") or "").strip()
            if not title:
                continue
            author = (it.get("author") or None)
            reason = (it.get("reason") or None)
        else:
            title = str(it).strip()
            if not title:
                continue
            author = None
            reason = None
        out.append(BookOut(title=title, author=author, reason=reason))
    return out[:5]

@router.post("/users/{user_id}/recommendations", response_model=RecResponse)
async def recommend(user_id: int, prefs: BookPref):
    try:
        books = await _call_llm(prefs)
        return {"books": books}
    except HTTPException:
        raise
    except asyncio.TimeoutError:
        raise HTTPException(504, "LLM timeout")
    except Exception as e:
        raise HTTPException(500, f"LLM error: {e}")
