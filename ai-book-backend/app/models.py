from pydantic import BaseModel
from typing import List

class RecommendationRequest(BaseModel):
    user_id: int
    preferences: List[str]

class Book(BaseModel):
    title: str
    author: str

class RecommendationResponse(BaseModel):
    books: List[Book]
