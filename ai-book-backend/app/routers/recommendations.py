from fastapi import APIRouter
from pydantic import BaseModel
import os, aiohttp

router = APIRouter()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3.1:free")

class RecommendationRequest(BaseModel):
    preferences: list[str]

class RecommendationResponse(BaseModel):
    books: list[dict]

async def query_llm(preferences: list[str]) -> list[dict]:
    async with aiohttp.ClientSession() as session:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": OPENROUTER_MODEL,
            "messages": [
                {"role": "system", "content": "Ты умный помощник по книгам."},
                {"role": "user", "content": f"Мне нравятся {', '.join(preferences)}. Посоветуй 3 книги."}
            ],
        }
        async with session.post("https://openrouter.ai/api/v1/chat/completions",
                                headers=headers, json=payload) as resp:
            data = await resp.json()
            text = data["choices"][0]["message"]["content"]

            # Простейший парсинг LLM-ответа в список книг
            books = [{"title": line.strip(), "author": "?"}
                     for line in text.split("\n") if line.strip()]
            return books

@router.post("/recommendations", response_model=RecommendationResponse)
async def recommend(req: RecommendationRequest):
    books = await query_llm(req.preferences)
    return {"books": books}
