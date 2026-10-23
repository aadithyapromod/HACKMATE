from enum import Enum
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(BaseModel):
    id: str = Field(..., json_schema_extra={"example": "task-1"})
    title: str = Field(..., json_schema_extra={"example": "Generate application files"})
    description: str = Field(..., json_schema_extra={"example": "Generate the React application source"})
    status: TaskStatus = Field(default=TaskStatus.PENDING)
