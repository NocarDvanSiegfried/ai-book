from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

from app.db import get_profile, upsert_profile

router = APIRouter(prefix="/v1", tags=["profile"])

class ProfileIn(BaseModel):
    username: Optional[str] = None
    first_name: Optional[str] = None  # в БД не храним, но оставим для совместимости
    last_name: Optional[str] = None   # в БД не храним, но оставим для совместимости
    lang: Optional[str] = Field(default="ru")
    preferred_genres: List[str] = Field(default_factory=list)
    preferred_authors: List[str] = Field(default_factory=list)

class ProfileOut(BaseModel):
    user_id: int
    username: Optional[str] = None
    lang: Optional[str] = None
    preferred_genres: List[str] = Field(default_factory=list)
    preferred_authors: List[str] = Field(default_factory=list)

@router.get("/users/{user_id}/profile", response_model=ProfileOut)
async def read_profile(user_id: int):
    p = await get_profile(user_id)
    if not p:
        raise HTTPException(404, "Profile not found")
    return ProfileOut(**p)

@router.put("/users/{user_id}/profile", response_model=ProfileOut)
async def write_profile(user_id: int, payload: ProfileIn):
    await upsert_profile(
        user_id=user_id,
        username=payload.username,
        lang=payload.lang or "ru",
        genres=payload.preferred_genres,
        authors=payload.preferred_authors,
    )
    p = await get_profile(user_id)
    return ProfileOut(**p)
