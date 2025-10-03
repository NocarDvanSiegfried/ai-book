# app/routers/profile.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from app.db import get_profile, upsert_profile

router = APIRouter(prefix="/v1", tags=["profile"])

class ProfileIn(BaseModel):
    username: Optional[str] = None
    first_name: Optional[str] = None  # не храним, но принимаем от бота (игнорируем)
    last_name: Optional[str] = None   # не храним, но принимаем от бота (игнорируем)
    lang: str = "ru"
    preferred_genres: List[str] = Field(default_factory=list)
    preferred_authors: List[str] = Field(default_factory=list)

class ProfileOut(BaseModel):
    user_id: int
    username: Optional[str] = None
    lang: str = "ru"
    preferred_genres: List[str] = Field(default_factory=list)
    preferred_authors: List[str] = Field(default_factory=list)

@router.get("/users/{user_id}/profile", response_model=ProfileOut)
async def read_profile(user_id: int):
    prof = await get_profile(user_id)
    if not prof:
        raise HTTPException(status_code=404, detail="profile_not_found")
    return ProfileOut(**prof)

@router.put("/users/{user_id}/profile", response_model=ProfileOut)
async def write_profile(user_id: int, body: ProfileIn):
    await upsert_profile(
        user_id=user_id,
        username=body.username,
        lang=body.lang,
        genres=body.preferred_genres,
        authors=body.preferred_authors,
    )
    prof = await get_profile(user_id)
    return ProfileOut(**prof)
