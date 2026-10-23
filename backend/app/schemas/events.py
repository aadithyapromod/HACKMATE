from enum import Enum
from datetime import datetime, timezone
from typing import Any, Dict
from pydantic import BaseModel, Field


class EventType(str, Enum):
    PROJECT_STATUS = "project.status"
    TASK_UPDATED = "task.updated"
    AGENT_STATUS = "agent.status"
    BUILD_LOG = "build.log"
    BUILD_COMPLETED = "build.completed"
    PREVIEW_READY = "preview.ready"
    PROJECT_COMPLETED = "project.completed"
    PROJECT_FAILED = "project.failed"


class AgentEvent(BaseModel):
    event_type: EventType
    project_id: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    data: Dict[str, Any] = Field(default_factory=dict)
