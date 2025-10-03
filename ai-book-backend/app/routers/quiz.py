from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from app.db import get_quiz, upsert_quiz

router = APIRouter(prefix="/v1", tags=["quiz"])

class QuizIn(BaseModel):
    q1_favorite_book: Optional[str] = None
    q2_books_per_year: Optional[int] = None

@router.get("/users/{user_id}/quiz")
async def quiz_get(user_id: int):
    q = await get_quiz(user_id)
    return q or {}

@router.post("/users/{user_id}/quiz")
async def quiz_post(user_id: int, body: QuizIn):
    await upsert_quiz(user_id, body.q1_favorite_book or "", body.q2_books_per_year or 0)
    return {"ok": True}
