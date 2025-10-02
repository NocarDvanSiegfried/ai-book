from pydantic import BaseModel, Field
from typing import List, Optional

class BookIn(BaseModel):
    title: str
    author: Optional[str] = None

class RecommendationRequest(BaseModel):
    favorites: List[str] = Field(default=[])
    genres: List[str] = Field(default=[])
    authors: List[str] = Field(default=[])

class BookOut(BaseModel):
    title: str
    author: str | None = None
    reason: str | None = None

class RecommendationResponse(BaseModel):
    books: list[BookOut]
