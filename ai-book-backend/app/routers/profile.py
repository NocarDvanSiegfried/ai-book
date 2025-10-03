from fastapi import APIRouter, HTTPException
from app.models import ProfileIn, ProfileOut
from app.db import upsert_profile, get_profile

router = APIRouter(prefix="/v1/users", tags=["profile"])

@router.get("/{user_id}/profile", response_model=ProfileOut)
async def read_profile(user_id: int):
    data = await get_profile(user_id)
    if not data:
        raise HTTPException(404, "profile not found")
    return data

@router.put("/{user_id}/profile", response_model=ProfileOut)
async def write_profile(user_id: int, body: ProfileIn):
    await upsert_profile(
        user_id=user_id,
        username=body.username,
        lang=body.lang,
        genres=body.preferred_genres,
        authors=body.preferred_authors
    )
    data = await get_profile(user_id)
    return data
