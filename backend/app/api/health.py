from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: str


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Returns the current operational status of the HackMate backend service."""
    return HealthResponse(
        status="ok",
        service="hackmate-backend",
        timestamp=datetime.now(timezone.utc).isoformat()
    )
