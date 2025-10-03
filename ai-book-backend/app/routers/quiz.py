from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.db import upsert_quiz, get_quiz

router = APIRouter(prefix="/v1", tags=["quiz"])

class QuizIn(BaseModel):
    q1_favorite_book: Optional[str] = None
    q2_books_per_year: Optional[int] = None

class QuizOut(BaseModel):
    user_id: int
    q1_favorite_book: Optional[str] = None
    q2_books_per_year: Optional[int] = None

@router.post("/users/{user_id}/quiz", response_model=QuizOut)
async def write_quiz(user_id: int, payload: QuizIn):
    await upsert_quiz(user_id, payload.q1_favorite_book, payload.q2_books_per_year)
    q = await get_quiz(user_id)
    return QuizOut(**q)

@router.get("/users/{user_id}/quiz", response_model=QuizOut)
async def read_quiz(user_id: int):
    q = await get_quiz(user_id)
    if not q:
        raise HTTPException(404, "Quiz not found")
    return QuizOut(**q)
