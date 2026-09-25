import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from routers.auth import router as auth_router
from routers.onboarding import router as onboarding_router
from routers.navigator import router as navigator_router
from services.checkpoint_store import close_checkpointer, initialize_checkpointer
from agent.graph import initialize_graphs
from core.logger import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    await initialize_checkpointer()
    initialize_graphs()
    yield
    await close_checkpointer()

app = FastAPI(
    title="PathForge API",
    lifespan=lifespan,
)

frontend_origins = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", settings.FRONTEND_ORIGINS).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(onboarding_router, prefix="/api")
app.include_router(navigator_router, prefix="/api")

@app.get("/")
def root():
    return {
        "message": "PathForge API is running",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "pathforge-api", "environment": settings.ENVIRONMENT}