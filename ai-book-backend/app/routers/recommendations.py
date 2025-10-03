from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os, aiohttp, json

router = APIRouter()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3.1:free")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

if not OPENROUTER_API_KEY:
    # чтобы ошибка была явная, а не 500 "где-то внутри"
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
    '[{"title": "Название", "author": "Автор", "why": "Короткое объяснение"}]\n'
)

async def call_llm(prefs: Prefs) -> list[dict]:
    # Подготовим текст запроса
    prompt_text = PROMPT.format(
        favorites=", ".join(prefs.favorites) if prefs.favorites else "-",
        genres=", ".join(prefs.genres) if prefs.genres else "-",
        authors=", ".join(prefs.authors) if prefs.authors else "-",
    )

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        # не обязательно, но рекомендуется openrouter-ом
        "HTTP-Referer": "https://example.com",
        "X-Title": "ai-book-backend",
    }
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": "Отвечай кратко и строго по инструкции."},
            {"role": "user", "content": prompt_text},
        ],
        # опционально — чуть строже формат
        "response_format": {"type": "json_object"},
        # или temperature/other настройки
        # "temperature": 0.7,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(f"{OPENROUTER_BASE_URL}/chat/completions",
                                headers=headers, json=payload, timeout=60) as resp:
            text = await resp.text()
            if resp.status != 200:
                # пробросим статус и тело чтобы в логах было понятно
                raise HTTPException(status_code=resp.status, detail=f"OpenRouter error: {text}")

            data = json.loads(text)
            content = data["choices"][0]["message"]["content"]

    # Пробуем распарсить JSON из content
    try:
        # content может быть либо JSON-массивом, либо объектом с массивом внутри
        parsed = json.loads(content)
        if isinstance(parsed, list):
            items = parsed
        elif isinstance(parsed, dict):
            # попробуем самые вероятные ключи
            items = parsed.get("items") or parsed.get("books") or parsed.get("recommendations")
            if not isinstance(items, list):
                raise ValueError("JSON is not a list")
        else:
            raise ValueError("Unexpected JSON type")
    except Exception:
        # На случай, если модель прислала текст: вытащим простым эвристическим парсером
        items = []
        for line in content.splitlines():
            line = line.strip("-• \t")
            if not line:
                continue
            # Ожидаем формат: Название — Автор: объяснение
            parts = line.split("—")
            title = parts[0].strip() if parts else line
            author = parts[1].strip() if len(parts) > 1 else ""
            # "why" после двоеточия
            why = ""
            if ":" in line:
                why = line.split(":", 1)[1].strip()
            items.append({"title": title, "author": author, "why": why})
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
    # Фолбэк если пусто — чтобы бот не падал
    if not any(n["title"] for n in norm):
        norm = [
            {"title": "1984", "author": "Джордж Оруэлл", "why": "Антиутопия, резонирует с вашей классикой/фантастикой."},
            {"title": "Цветы для Элджернона", "author": "Дэниел Киз", "why": "Эмоциональная научная фантастика."},
            {"title": "Марсианин", "author": "Энди Вейер", "why": "Научная фантастика с инженерным уклоном."},
            {"title": "Мастер и Маргарита", "author": "М. Булгаков", "why": "Классика с мистикой и сатирой."},
            {"title": "Три тела", "author": "Лю Цысинь", "why": "Большая научная идея и масштаб."},
        ]
    return norm

@router.post("/v1/users/{user_id}/recommendations")
async def recommend(user_id: int, prefs: Prefs):
    books = await call_llm(prefs)
    return {"user_id": user_id, "books": books}
