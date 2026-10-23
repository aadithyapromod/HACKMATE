from fastapi import APIRouter
from app.api.health import router as health_router
from app.api.projects import router as projects_router

api_router = APIRouter(prefix="/api")
api_router.include_router(health_router)
api_router.include_router(projects_router)

__all__ = ["api_router"]
