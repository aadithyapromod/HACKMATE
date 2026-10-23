from fastapi import APIRouter
from app.api.health import router as health_router
from app.api.projects import router as projects_router
from app.api.files import router as files_router
from app.api.events import router as events_router
from app.api.builds import router as builds_router
from app.api.integrations import router as integrations_router
from app.api.preview import router as preview_router

api_v2_router = APIRouter()

api_v2_router.include_router(health_router)
api_v2_router.include_router(projects_router)
api_v2_router.include_router(files_router)
api_v2_router.include_router(events_router)
api_v2_router.include_router(builds_router)
api_v2_router.include_router(integrations_router)
api_v2_router.include_router(preview_router)
