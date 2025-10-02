from fastapi import FastAPI
from app.routers import recommendations

app = FastAPI(title="AI-Book Backend", version="1.0.0")

@app.get("/")
async def root():
    return {"ok": True, "service": "ai-book-backend"}

app.include_router(recommendations.router, prefix="")
