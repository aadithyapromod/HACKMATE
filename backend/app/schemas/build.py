from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.build import BuildStatus, BuildTrigger


class BuildLogChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    stream: str
    message: str
    timestamp: datetime


class BuildRunSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    attempt_number: int
    trigger_type: BuildTrigger
    status: BuildStatus
    exit_code: Optional[int] = None
    error_summary: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None


class BuildRunResponse(BuildRunSummaryResponse):
    logs: List[BuildLogChunkResponse] = []
