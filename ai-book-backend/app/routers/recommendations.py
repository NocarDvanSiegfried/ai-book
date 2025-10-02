from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import AsyncSessionLocal, User, Book, Recommendation
from app.models import RecommendationRequest, RecommendationResponse, BookOut
from app.llm import ask_llm

router = APIRouter()

async def get_db():
    async with AsyncSessionLocal() as s:
        yield s

@router.post("/v1/users/{user_id}/recommendations", response_model=RecommendationResponse)
async def recommend(user_id: int, payload: RecommendationRequest, db: AsyncSession = Depends(get_db)):
    # upsert user (минимально)
    user = await db.get(User, user_id)
    if not user:
        user = User(id=user_id)
        db.add(user)

    # LLM
    llm_books = await ask_llm(payload.favorites, payload.genres, payload.authors)
    out: list[BookOut] = []

    # сохранение в БД и выдача
    rank = 1
    for it in llm_books:
        # простая дедупликация по title
        q = await db.execute(select(Book).where(Book.title == it["title"]))
        book = q.scalar_one_or_none()
        if not book:
            book = Book(title=it["title"], authors=it.get("author"))
            db.add(book)
            await db.flush()
        rec = Recommendation(user_id=user_id, book_id=book.id, rank=rank, reason=it.get("reason"))
        db.add(rec)
        out.append(BookOut(title=book.title, author=book.authors, reason=rec.reason))
        rank += 1

    await db.commit()
    return RecommendationResponse(books=out)
