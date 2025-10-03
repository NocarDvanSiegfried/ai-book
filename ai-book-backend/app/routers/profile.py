from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app import db

router = APIRouter(prefix="/v1", tags=["profile"])

class ProfileIn(BaseModel):
    username: str | None = None
    lang: str | None = "ru"
    preferred_genres: list[str] = []
    preferred_authors: list[str] = []

@router.post("/users/{user_id}/profile")
async def upsert_user_profile(user_id: int, p: ProfileIn):
    await db.upsert_profile(
        user_id=user_id,
        username=p.username,
        lang=p.lang,
        genres=p.preferred_genres,
        authors=p.preferred_authors,
    )
    return {"ok": True}

@router.get("/users/{user_id}/profile")
async def get_user_profile(user_id: int):
    prof = await db.get_profile(user_id)
    if not prof:
        raise HTTPException(status_code=404, detail="Profile not found")
    return prof
