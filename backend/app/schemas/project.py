from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator
from app.models.project import ProjectStatus
from app.schemas.task import TaskResponse
from app.schemas.build import BuildRunSummaryResponse


class ProjectCreate(BaseModel):
    prompt: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Detailed description or problem statement for the website."
    )
    title: Optional[str] = Field(
        None,
        max_length=255,
        description="Optional title. If omitted, will be derived automatically from the prompt."
    )
    reference_url: Optional[str] = Field(
        None,
        description="Optional reference website URL for design tokens or structure extraction."
    )

    @field_validator("reference_url")
    @classmethod
    def validate_reference_url(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        v = v.strip()
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("Reference URL must start with http:// or https://")
        return v


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    prompt: str
    reference_url: Optional[str] = None
    framework: str
    status: ProjectStatus
    current_repair_iteration: int
    error_message: Optional[str] = None
    preview_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ProjectDetailResponse(ProjectResponse):
    tasks: List[TaskResponse] = []
    build_runs: List[BuildRunSummaryResponse] = []


class ProjectListResponse(BaseModel):
    total: int
    items: List[ProjectResponse]
