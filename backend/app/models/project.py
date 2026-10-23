import uuid
from enum import Enum
from typing import List, Optional
from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, utc_now


class ProjectStatus(str, Enum):
    QUEUED = "QUEUED"
    ANALYZING = "ANALYZING"
    PLANNING = "PLANNING"
    GENERATING = "GENERATING"
    WRITING_FILES = "WRITING_FILES"
    BUILDING = "BUILDING"
    REPAIRING = "REPAIRING"
    READY = "READY"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    reference_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    framework: Mapped[str] = mapped_column(String(64), default="react-vite", nullable=False)
    status: Mapped[ProjectStatus] = mapped_column(
        String(32), default=ProjectStatus.QUEUED, nullable=False, index=True
    )
    current_repair_iteration: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    preview_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    tasks: Mapped[List["Task"]] = relationship(
        "Task", back_populates="project", cascade="all, delete-orphan", order_by="Task.sequence_order"
    )
    files: Mapped[List["GeneratedFile"]] = relationship(
        "GeneratedFile", back_populates="project", cascade="all, delete-orphan"
    )
    build_runs: Mapped[List["BuildRun"]] = relationship(
        "BuildRun", back_populates="project", cascade="all, delete-orphan", order_by="BuildRun.attempt_number"
    )
