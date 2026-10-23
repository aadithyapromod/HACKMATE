from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.task import TaskStatus


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    sequence_order: int
    title: str
    description: str
    status: TaskStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
