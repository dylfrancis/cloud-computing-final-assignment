from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import get_settings
from app.db import engine
from app.routers import auth, dashboard, households, ml, uploads


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Retail Insights API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(households.router)
    app.include_router(uploads.router)
    app.include_router(dashboard.router)
    app.include_router(ml.router)

    @app.get("/healthz")
    async def healthz(response: Response) -> dict[str, str]:
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {"status": "degraded", "db": "unreachable"}
        return {"status": "ok", "db": "ok"}

    return app


app = create_app()
