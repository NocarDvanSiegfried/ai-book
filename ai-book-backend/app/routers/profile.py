from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.db import get_profile, upsert_profile

router = APIRouter(prefix="/v1", tags=["profile"])

class ProfileIn(BaseModel):
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    lang: str = "ru"
    preferred_genres: list[str] = Field(default_factory=list)
    preferred_authors: list[str] = Field(default_factory=list)

@router.get("/users/{user_id}/profile")
async def get_user_profile(user_id: int):
    prof = await get_profile(user_id)
    if not prof:
        # пусто — так и скажем клиенту
        raise HTTPException(404, "Profile not found")
    return prof

@router.put("/users/{user_id}/profile")
async def put_user_profile(user_id: int, body: ProfileIn):
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
