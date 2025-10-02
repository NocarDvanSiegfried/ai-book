import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Float
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data.db")

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)             # tg id
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    lang = Column(String, nullable=True)
    preferred_genres = Column(Text, nullable=True)
    preferred_authors = Column(Text, nullable=True)

class Book(Base):
    __tablename__ = "books"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    authors = Column(String, nullable=True)        # csv для простоты
    year = Column(Integer, nullable=True)
    language = Column(String, nullable=True)
    genres = Column(String, nullable=True)         # csv
    tags = Column(String, nullable=True)           # csv
    description = Column(Text, nullable=True)
    cover_url = Column(String, nullable=True)
    rating = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Recommendation(Base):
    __tablename__ = "recommendations"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    book_id = Column(Integer, ForeignKey("books.id"))
    rank = Column(Integer, nullable=True)
    score = Column(Float, nullable=True)
    reason = Column(Text, nullable=True)
