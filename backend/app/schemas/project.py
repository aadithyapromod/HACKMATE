from enum import Enum
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class ProjectStatus(str, Enum):
    CREATED = "created"
    PLANNING = "planning"
    GENERATING = "generating"
    BUILDING = "building"
    TESTING = "testing"
    REPAIRING = "repairing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProjectCreateRequest(BaseModel):
    idea: str = Field(..., description="Hackathon project idea (10-2000 characters)")

    @field_validator("idea")
    @classmethod
    def validate_idea(cls, v: str) -> str:
        trimmed = v.strip()
        if len(trimmed) < 10:
            raise ValueError("Idea must be at least 10 characters long after trimming whitespace.")
        if len(trimmed) > 2000:
            raise ValueError("Idea must not exceed 2000 characters.")
        return trimmed


class Project(BaseModel):
    id: str = Field(..., example="project-123")
    idea: str = Field(..., example="Build a student hackathon matching website")
    status: ProjectStatus = Field(default=ProjectStatus.CREATED, example=ProjectStatus.CREATED)
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        example="2026-10-23T10:00:00Z"
    )


class ErrorResponse(BaseModel):
    detail: str
