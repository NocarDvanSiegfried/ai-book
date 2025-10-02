from fastapi import FastAPI
from app.models import RecommendationRequest, RecommendationResponse
from app.llm_agent import DummyLLM

app = FastAPI(title="AI Book Backend")

llm = DummyLLM()

@app.get("/")
async def root():
    return {"message": "AI Book Backend is running"}

@app.post("/recommendations", response_model=RecommendationResponse)
async def recommend(request: RecommendationRequest):
    books = llm.get_recommendations(request.preferences)
    return {"books": books}
