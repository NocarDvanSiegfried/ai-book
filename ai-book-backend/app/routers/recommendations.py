from fastapi import APIRouter
from pydantic import BaseModel
import os, aiohttp

router = APIRouter()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3.1:free")

class BookPref(BaseModel):
    favorites: list[str] = []

async def query_llm(user_books: list[str]) -> str:
    async with aiohttp.ClientSession() as session:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": OPENROUTER_MODEL,
            "messages": [
                {"role": "system", "content": "Ты умный ассистент по книгам."},
                {"role": "user", "content": f"Мои любимые книги: {', '.join(user_books)}. Посоветуй 3 новых книги."}
            ],
        }
        async with session.post("https://openrouter.ai/api/v1/chat/completions",
                                headers=headers, json=payload) as resp:
            data = await resp.json()
            return data["choices"][0]["message"]["content"]

@router.post("/v1/users/{user_id}/recommendations")
async def recommend_books(user_id: int, prefs: BookPref):
    # здесь можно сохранять в БД предпочтения
    recommendations = await query_llm(prefs.favorites)
    return {"user_id": user_id, "recommendations": recommendations}
