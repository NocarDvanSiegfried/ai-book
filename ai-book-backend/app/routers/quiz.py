from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app import db

router = APIRouter(prefix="/v1", tags=["quiz"])

class QuizIn(BaseModel):
    q1_favorite_book: str
    q2_books_per_year: int

@router.post("/users/{user_id}/quiz")
async def upsert_quiz(user_id: int, q: QuizIn):
    await db.upsert_quiz(user_id, q.q1_favorite_book, q.q2_books_per_year)
    return {"ok": True}

@router.get("/users/{user_id}/quiz")
async def get_quiz(user_id: int):
    res = await db.get_quiz(user_id)
    if not res:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return res
