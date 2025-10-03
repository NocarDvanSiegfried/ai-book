from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.db import get_profile, upsert_profile

router = APIRouter(prefix="/v1", tags=["profile"])

class ProfilePayload(BaseModel):
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    lang: str = "ru"
    preferred_genres: list[str] = Field(default_factory=list)
    preferred_authors: list[str] = Field(default_factory=list)

@router.get("/users/{user_id}/profile")
async def read_profile(user_id:int):
    p = await get_profile(user_id)
    if not p:
        raise HTTPException(404, "profile not found")
    return p

@router.put("/users/{user_id}/profile")
async def write_profile(user_id:int, payload: ProfilePayload):
    await upsert_profile(
        user_id=user_id,
        username=payload.username,
        first_name=payload.first_name,
        last_name=payload.last_name,
        lang=payload.lang,
        genres=payload.preferred_genres,
        authors=payload.preferred_authors,
    )
    return {"ok": True}
