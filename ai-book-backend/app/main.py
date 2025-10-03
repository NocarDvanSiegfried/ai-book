from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import init_db
from app.routers import recommendations, profile, quiz


def create_app() -> FastAPI:
    app = FastAPI(title="AI Book Backend", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(recommendations.router)
    app.include_router(profile.router)
    app.include_router(quiz.router)

    @app.get("/")
    async def root():
        return {"ok": True, "service": "ai-book-backend"}

    @app.on_event("startup")
    async def on_startup():
        await init_db()

    return app


app = create_app()
