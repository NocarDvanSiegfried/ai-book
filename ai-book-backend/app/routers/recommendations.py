from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os, aiohttp, json

router = APIRouter()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3.1:free")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY is not set")

class Prefs(BaseModel):
    favorites: list[str] = []
    genres: list[str] = []
    authors: list[str] = []

PROMPT = (
    "Ты рекомендательный ассистент по книгам.\n"
    "Дано:\n"
    "- Любимые книги: {favorites}\n"
    "- Любимые жанры: {genres}\n"
    "- Любимые авторы: {authors}\n\n"
    "Сформируй РОВНО 5 рекомендаций и верни ТОЛЬКО JSON-массив без лишнего текста:\n"
    '[{{"title": "Название", "author": "Автор", "why": "Короткое объяснение"}}]\n'
)

async def call_llm(prefs: Prefs) -> list[dict]:
    prompt_text = PROMPT.format(
        favorites=", ".join(prefs.favorites) if prefs.favorites else "-",
        genres=", ".join(prefs.genres) if prefs.genres else "-",
        authors=", ".join(prefs.authors) if prefs.authors else "-",
    )

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://example.com",
        "X-Title": "ai-book-backend",
    }
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": "Отвечай строго по инструкции, без лишнего текста."},
            {"role": "user", "content": prompt_text},
        ],
        "response_format": {"type": "json_object"},
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(f"{OPENROUTER_BASE_URL}/chat/completions",
                                headers=headers, json=payload, timeout=60) as resp:
            text = await resp.text()
            if resp.status != 200:
                raise HTTPException(status_code=resp.status, detail=f"OpenRouter error: {text}")
            data = json.loads(text)
            content = data["choices"][0]["message"]["content"]

    # Попробуем распарсить JSON
    try:
        parsed = json.loads(content)
        if isinstance(parsed, list):
            items = parsed
        elif isinstance(parsed, dict):
            items = parsed.get("items") or parsed.get("books") or parsed.get("recommendations")
            if not isinstance(items, list):
                raise ValueError("JSON is not a list")
        else:
            raise ValueError("Unexpected JSON type")
    except Exception:
        # Фолбэк, если пришёл не-JSON
        items, seen = [], set()
        for line in content.splitlines():
            line = line.strip("-• \t")
            if not line:
                continue
            title = line
            author, why = "", ""
            if "—" in line:
                a, b = line.split("—", 1)
                title, author = a.strip(), b.strip()
            if ":" in line:
                _, why = line.split(":", 1)
                why = why.strip()
            key = (title.lower(), author.lower())
            if title and key not in seen:
                items.append({"title": title, "author": author, "why": why})
                seen.add(key)
            if len(items) >= 5:
                break

    # Нормализуем и обрежем до 5
    norm = []
    for it in items[:5]:
        norm.append({
            "title": (it.get("title") or "").strip(),
            "author": (it.get("author") or "").strip(),
            "why": (it.get("why") or "").strip(),
        })
    if not any(n["title"] for n in norm):
        norm = [
            {"title": "1984", "author": "Джордж Оруэлл", "why": "Антиутопия для любителей классики/фантастики."},
            {"title": "Цветы для Элджернона", "author": "Дэниел Киз", "why": "Эмоциональная научная фантастика."},
            {"title": "Марсианин", "author": "Энди Вейер", "why": "Инженерная научная фантастика."},
            {"title": "Мастер и Маргарита", "author": "М. Булгаков", "why": "Классика с мистикой и сатирой."},
            {"title": "Задача трёх тел", "author": "Лю Цысинь", "why": "Большая научная идея и масштаб."},
        ]
    return norm

@router.post("/v1/users/{user_id}/recommendations")
async def recommend(user_id: int, prefs: Prefs):
    books = await call_llm(prefs)
    return {"user_id": user_id, "books": books}
