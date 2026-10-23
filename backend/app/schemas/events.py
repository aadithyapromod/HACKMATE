from enum import Enum
from typing import Optional, Any, Dict
from pydantic import BaseModel
from app.db.base import utc_now


class SSEEventType(str, Enum):
    STATUS_CHANGED = "status_changed"
    TASK_UPDATED = "task_updated"
    FILE_WRITTEN = "file_written"
    BUILD_LOG = "build_log"
    REPAIR_ATTEMPT = "repair_attempt"
    BUILD_COMPLETED = "build_completed"
    HEARTBEAT = "heartbeat"
    ERROR = "error"


class SSEMessage(BaseModel):
    event: SSEEventType
    data: Dict[str, Any]

    def format_sse(self) -> str:
        import json
        payload = json.dumps(self.data, default=str)
        return f"event: {self.event.value}\ndata: {payload}\n\n"
