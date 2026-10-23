from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db
from app.services.runner_service import runner_service
from app.config import settings
from datetime import datetime, timezone

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Comprehensive readiness probe verifying DB, Docker daemon, and runner mode."""
    # 1. Database check
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    # 2. Docker daemon check
    docker_ok, docker_reason = await runner_service.check_docker_available()

    return {
        "status": "healthy" if db_ok else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": settings.ENVIRONMENT,
        "services": {
            "database": {
                "status": "connected" if db_ok else "unreachable",
                "type": "sqlite" if "sqlite" in settings.DATABASE_URL else "postgresql",
            },
            "runner": {
                "configured_type": settings.RUNNER_TYPE,
                "docker_available": docker_ok,
                "docker_status": docker_reason,
                "local_dev_fallback_enabled": settings.ENABLE_LOCAL_DEV_RUNNER,
            },
            "ai": {
                "configured": bool(settings.GEMINI_API_KEY),
                "model": settings.GEMINI_MODEL,
            }
        }
    }
