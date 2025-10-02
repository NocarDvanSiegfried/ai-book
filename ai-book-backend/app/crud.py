from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app import models

async def get_user_by_telegram_id(db: AsyncSession, telegram_id: int):
    result = await db.execute(select(models.User).where(models.User.telegram_id == telegram_id))
    return result.scalars().first()

async def create_user(db: AsyncSession, telegram_id: int, username: str):
    user = models.User(telegram_id=telegram_id, username=username)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def get_books(db: AsyncSession, limit: int = 5):
    result = await db.execute(select(models.Book).limit(limit))
    return result.scalars().all()
