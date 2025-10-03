from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import os, aiohttp, asyncio, json, re
from typing import List, Optional

router = APIRouter(prefix="/v1", tags=["recommendations"])

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3.1:free")

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
    "Ответ строго в JSON-массиве объектов с полями title, author, reason. Без пояснений."
)

FALLBACK = [
    {"title": "Солярис", "author": "Станислав Лем", "reason": "Философская фантастика классического уровня"},
    {"title": "451 градус по Фаренгейту", "author": "Рэй Брэдбери", "reason": "Классика антиутопии о ценности книг"},
    {"title": "Убийство в Восточном экспрессе", "author": "Агата Кристи", "reason": "Эталон детективного сюжета"},
    {"title": "Игра Эндера", "author": "Орсон Скотт Кард", "reason": "Динамичная НФ с этическими дилеммами"},
    {"title": "Ночной полет", "author": "Антуан де Сент-Экзюпери", "reason": "Философская проза автора 'Маленького принца'"},
]

async def _call_llm(prefs: BookPref) -> List[BookOut]:
    # если нет ключа — сразу даём запасной список
    if not OPENROUTER_API_KEY:
        return [BookOut(**x) for x in FALLBACK]

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
                {"role": "system", "content": "Отвечай строго в JSON-массиве."},
                {"role": "user", "content": prompt_text},
            ],
        }
        try:
            async with session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers, json=payload, timeout=60
            ) as resp:
                if resp.status >= 400:
                    # вернем запасной список с маппингом на 502
                    raise HTTPException(502, f"LLM HTTP {resp.status}: {await resp.text()}")
                data = await resp.json()
        except asyncio.TimeoutError:
            raise HTTPException(504, "LLM timeout")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(502, f"LLM transport error: {e}")

    content = data["choices"][0]["message"]["content"]

    # Лояльный парсер JSON (вырезаем первый массив из текста)
    match = re.search(r"\[\s*{.*}\s*\]", content, re.S)
    raw = match.group(0) if match else content
    try:
        arr = json.loads(raw)
        if not isinstance(arr, list):
            raise ValueError("not a list")
    except Exception:
        # если модель ответила не-JSON — деградация в список строк
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
            out.append(BookOut(title=title, author=author, reason=reason))
        else:
            # элемент — строка
            s = str(it).strip()
            if s:
                out.append(BookOut(title=s))
    return out[:5] if out else [BookOut(**x) for x in FALLBACK[:5]]

@router.post("/users/{user_id}/recommendations", response_model=RecResponse)
async def recommend(user_id: int, prefs: BookPref):
    books = await _call_llm(prefs)
    return {"books": books}
