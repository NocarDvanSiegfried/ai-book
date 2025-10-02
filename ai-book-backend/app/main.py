from fastapi import FastAPI
from app.routers import recommendations

app = FastAPI(title="AI-Book Backend")

app.include_router(recommendations.router)

@app.get("/")
def root():
    return {"msg": "AI-Book backend is running"}
