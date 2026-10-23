from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import api_router

app = FastAPI(
    title="HackMate API",
    description="Agentic AI Hackathon Platform - API & Orchestration Service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes under /api
app.include_router(api_router)


@app.get("/", tags=["Root"])
def root():
    return {
        "service": "HackMate API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
    }
