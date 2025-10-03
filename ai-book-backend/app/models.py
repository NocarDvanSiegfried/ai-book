from pydantic import BaseModel, Field
from typing import List, Optional

class ProfileIn(BaseModel):
    username: Optional[str] = None
    lang: Optional[str] = Field(default="ru")
    preferred_genres: List[str] = []
    preferred_authors: List[str] = []

class ProfileOut(ProfileIn):
    user_id: int

class QuizIn(BaseModel):
    q1_favorite_book: Optional[str] = None
    q2_books_per_year: Optional[int] = None

class QuizOut(QuizIn):
    user_id: int
