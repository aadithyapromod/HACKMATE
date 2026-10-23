from enum import Enum
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(BaseModel):
    id: str = Field(..., example="task-1")
    title: str = Field(..., example="Generate application files")
    description: str = Field(..., example="Generate the React application source")
    status: TaskStatus = Field(default=TaskStatus.PENDING, example=TaskStatus.PENDING)
