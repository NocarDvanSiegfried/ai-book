from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class BookBase(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    cover_url: Optional[str] = None
    authors: Optional[str] = None
    reason: Optional[str] = None

    class Config:
        orm_mode = True

class RecommendationOut(BaseModel):
    userId: int
    books: List[BookBase]
    generated_at: datetime
