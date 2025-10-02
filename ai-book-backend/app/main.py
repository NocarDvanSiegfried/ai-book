from fastapi import FastAPI
from app.routers import recommendations

app = FastAPI(title="AI Book Backend")

app.include_router(recommendations.router, prefix="/v1")

@app.get("/")
async def root():
    return {"message": "AI Book Backend is running"}
