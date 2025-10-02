from fastapi import FastAPI
from app.db import Base, engine
from app.routers import recommendations

app = FastAPI(title="AI-Book Backend", version="1.1.0")

@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/")
async def root():
    return {"message": "AI-Book backend OK"}

app.include_router(recommendations.router)
