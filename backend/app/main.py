from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router
from app.api_paths import router as paths_router
from app.api_session import router as session_router
from app.api_socratic import router as socratic_router
from app.config import settings
from app.telemetry import setup_otel
from app.workers.math_evaluator import shutdown_pool, warm_pool

app = FastAPI(title="Pegazus API", version="0.1.0")
setup_otel(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(session_router)
app.include_router(paths_router)
app.include_router(socratic_router)


@app.on_event("startup")
def _warm_pool() -> None:
    warm_pool()


@app.on_event("shutdown")
def _cool_pool() -> None:
    shutdown_pool()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "pegazus-api"}
