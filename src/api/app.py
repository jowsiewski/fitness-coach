from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import activities, fitness, nutrition, wellness


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Fitness Coach API",
        description="AI-powered personal cycling coach with Intervals.icu integration",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(activities.router)
    app.include_router(fitness.router)
    app.include_router(nutrition.router)
    app.include_router(wellness.router)

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/")
    async def root() -> dict[str, str]:
        return {
            "app": "Fitness Coach",
            "version": "0.1.0",
            "docs": "/docs",
        }

    return app
