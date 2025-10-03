from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from app.db import get_profile, upsert_profile

router = APIRouter(prefix="/v1", tags=["profile"])

class ProfileIn(BaseModel):
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    lang: str = "ru"
    preferred_genres: List[str] = Field(default_factory=list)
    preferred_authors: List[str] = Field(default_factory=list)

@router.get("/users/{user_id}/profile")
async def profile_get(user_id: int):
    p = await get_profile(user_id)
    if not p:
        raise HTTPException(404, "profile not found")
    return p

@router.put("/users/{user_id}/profile")
async def profile_put(user_id: int, body: ProfileIn):
    await upsert_profile(
        user_id=user_id,
        username=body.username,
        first_name=body.first_name,
        last_name=body.last_name,
        lang=body.lang,
        genres=body.preferred_genres,
        authors=body.preferred_authors,
    )
    return {"ok": True}
