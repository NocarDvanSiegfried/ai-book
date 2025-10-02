from sqlalchemy import Column, Integer, String, Text, ForeignKey, Table, DateTime, Float
from sqlalchemy.orm import relationship
from app.db import Base
from datetime import datetime

# связь многие-ко-многим книги <-> жанры
book_genres = Table(
    "book_genres", Base.metadata,
    Column("book_id", ForeignKey("books.id"), primary_key=True),
    Column("genre_id", ForeignKey("genres.id"), primary_key=True)
)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    lang = Column(String, default="ru")
    preferred_genres = Column(String, nullable=True)
    preferred_authors = Column(String, nullable=True)

    recommendations = relationship("Recommendation", back_populates="user")

class Author(Base):
    __tablename__ = "authors"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    bio = Column(Text, nullable=True)
    birth_year = Column(Integer, nullable=True)
    country = Column(String, nullable=True)

    books = relationship("Book", back_populates="authors_rel")

class Book(Base):
    __tablename__ = "books"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    year = Column(Integer, nullable=True)
    language = Column(String, default="ru")
    cover_url = Column(String, nullable=True)
    rating = Column(Float, nullable=True)

    authors_id = Column(Integer, ForeignKey("authors.id"))
    authors_rel = relationship("Author", back_populates="books")

    genres = relationship("Genre", secondary=book_genres, back_populates="books")

class Genre(Base):
    __tablename__ = "genres"
    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True)
    name = Column(String, nullable=False)
    books = relationship("Book", secondary=book_genres, back_populates="genres")

class Recommendation(Base):
    __tablename__ = "recommendations"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    book_id = Column(Integer, ForeignKey("books.id"))
    reason = Column(Text, nullable=True)
    score = Column(Float, nullable=True)
    rank = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="recommendations")
    book = relationship("Book")
