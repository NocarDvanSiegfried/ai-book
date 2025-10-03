from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db import upsert_quiz, get_quiz

router = APIRouter(prefix="/v1", tags=["quiz"])

class QuizIn(BaseModel):
    q1_favorite_book: str
    q2_books_per_year: int

class QuizOut(QuizIn):
    user_id: int

@router.post("/users/{user_id}/quiz", response_model=QuizOut)
async def save_quiz(user_id: int, body: QuizIn):
    await upsert_quiz(user_id, body.q1_favorite_book, body.q2_books_per_year)
    q = await get_quiz(user_id)
    return q

@router.get("/users/{user_id}/quiz", response_model=QuizOut)
async def read_quiz(user_id: int):
    q = await get_quiz(user_id)
    if not q:
        raise HTTPException(404, "Quiz not found")
    return q
