from fastapi import FastAPI
from app.routes import recommend  # вместо app.llm_agent

app = FastAPI(title="AI Book Backend")

# подключаем роуты
app.include_router(recommend.router)

@app.get("/")
async def root():
    return {"message": "AI Book Backend is running"}
