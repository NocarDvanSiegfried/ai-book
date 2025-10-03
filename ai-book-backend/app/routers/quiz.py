from fastapi import APIRouter, HTTPException
from app.models import QuizIn, QuizOut
from app.db import upsert_quiz, get_quiz

router = APIRouter(prefix="/v1/users", tags=["quiz"])

@router.get("/{user_id}/quiz", response_model=QuizOut)
async def read_quiz(user_id: int):
    data = await get_quiz(user_id)
    if not data:
        raise HTTPException(404, "quiz not found")
    return data

@router.post("/{user_id}/quiz", response_model=QuizOut)
async def write_quiz(user_id: int, body: QuizIn):
    await upsert_quiz(user_id, body.q1_favorite_book, body.q2_books_per_year)
    data = await get_quiz(user_id)
    return data
