from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import SessionLocal
from app import crud, schemas
from datetime import datetime

router = APIRouter()

async def get_db():
    async with SessionLocal() as session:
        yield session

@router.post("/v1/users/{user_id}/recommendations", response_model=schemas.RecommendationOut)
async def recommend_books(user_id: int = Path(...), db: AsyncSession = Depends(get_db)):
    books = await crud.get_books(db, limit=5)

    # пока делаем мок — реальная логика: учитывать профиль, звать LLM (OpenRouter)
    rec_books = []
    for b in books:
        rec_books.append({
            "id": b.id,
            "title": b.title,
            "description": b.description,
            "cover_url": b.cover_url,
            "authors": b.authors_rel.name if b.authors_rel else "",
            "reason": "Рекомендуем, так как жанры совпадают"
        })

    return {"userId": user_id, "books": rec_books, "generated_at": datetime.utcnow()}
