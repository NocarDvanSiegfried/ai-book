from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, conint
from app.db import upsert_quiz, get_quiz

router = APIRouter(prefix="/v1", tags=["quiz"])

# Модель – гибкая: два «обязательных» первых, остальное в dict
class QuizPayload(BaseModel):
    q1_favorite_book: str | None = None
    q2_books_per_year: conint(ge=0) | None = None
    # расширенные:
    favorite_genres: list[str] = Field(default_factory=list)   # Q3
    preferred_length: str | None = None                        # Q4: short/medium/long
    mood: str | None = None                                    # Q5: cozy/dark/adventurous/…
    language: str | None = None                                # Q6: ru/en/…
    format: str | None = None                                  # Q7: ebook/audiobook/paper

@router.post("/users/{user_id}/quiz")
async def save_quiz(user_id:int, payload: QuizPayload):
    answers = {
        "favorite_genres": payload.favorite_genres,
        "preferred_length": payload.preferred_length,
        "mood": payload.mood,
        "language": payload.language,
        "format": payload.format,
    }
    await upsert_quiz(
        user_id=user_id,
        q1=payload.q1_favorite_book,
        q2=payload.q2_books_per_year,
        answers=answers
    )
    return {"ok": True}

@router.get("/users/{user_id}/quiz")
async def read_quiz(user_id:int):
    q = await get_quiz(user_id)
    if not q:
        raise HTTPException(404, "quiz not found")
    return q
