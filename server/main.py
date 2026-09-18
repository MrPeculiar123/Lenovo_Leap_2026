from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.auth import router as auth_router
from routers.onboarding import router as onboarding_router

app = FastAPI(
    title="Learning Navigator API"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(onboarding_router, prefix="/api")

@app.get("/")
def root():
    return {
        "message": "Learning Navigator API is running"
    }