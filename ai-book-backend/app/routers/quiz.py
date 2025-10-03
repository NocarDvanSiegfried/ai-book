# app/routers/quiz.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.db import upsert_quiz, get_quiz

router = APIRouter(prefix="/v1", tags=["quiz"])

class QuizIn(BaseModel):
    q1_favorite_book: str
    q2_books_per_year: int

class QuizOut(BaseModel):
    user_id: int
    q1_favorite_book: Optional[str] = None
    q2_books_per_year: Optional[int] = None

@router.post("/users/{user_id}/quiz", response_model=QuizOut)
async def save_quiz(user_id: int, body: QuizIn):
    await upsert_quiz(user_id, body.q1_favorite_book, body.q2_books_per_year)
    data = await get_quiz(user_id)
    return QuizOut(**data)

@router.get("/users/{user_id}/quiz", response_model=QuizOut)
async def read_quiz(user_id: int):
    data = await get_quiz(user_id)
    if not data:
        raise HTTPException(status_code=404, detail="quiz_not_found")
    return QuizOut(**data)
