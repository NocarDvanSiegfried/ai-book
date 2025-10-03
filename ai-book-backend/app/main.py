# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Инициализация БД при старте приложения
from app.db import init_db

# Роутеры (эндпоинты)
from app.routers import recommendations, profile, quiz


def create_app() -> FastAPI:
    app = FastAPI(title="AI Book Backend", version="1.0.0")

    # CORS на всякий случай (можно убрать, если не нужно)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Подключаем роутеры
    app.include_router(recommendations.router)
    app.include_router(profile.router)
    app.include_router(quiz.router)

    @app.get("/")
    async def root():
        return {"ok": True, "service": "ai-book-backend"}

    # Хук запуска приложения — здесь вызовем init_db()
    @app.on_event("startup")
    async def on_startup():
        # создаёт файл БД и таблицы, если их нет
        await init_db()

    return app


app = create_app()
