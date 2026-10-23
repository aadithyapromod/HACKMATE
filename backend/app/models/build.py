import uuid
from enum import Enum
from typing import Optional, List
from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, utc_now


class BuildStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    CANCELLED = "CANCELLED"


class BuildTrigger(str, Enum):
    INITIAL_BUILD = "INITIAL_BUILD"
    REPAIR_ATTEMPT = "REPAIR_ATTEMPT"
    MANUAL_REBUILD = "MANUAL_REBUILD"


class BuildRun(Base):
    __tablename__ = "build_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    trigger_type: Mapped[BuildTrigger] = mapped_column(
        String(32), default=BuildTrigger.INITIAL_BUILD, nullable=False
    )
    status: Mapped[BuildStatus] = mapped_column(
        String(32), default=BuildStatus.QUEUED, nullable=False, index=True
    )
    exit_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="build_runs")
    logs: Mapped[List["BuildLogChunk"]] = relationship(
        "BuildLogChunk", back_populates="build_run", cascade="all, delete-orphan", order_by="BuildLogChunk.timestamp"
    )


class BuildLogChunk(Base):
    __tablename__ = "build_log_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    build_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("build_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stream: Mapped[str] = mapped_column(String(16), default="stdout", nullable=False)  # stdout, stderr, system
    message: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    # Relationships
    build_run: Mapped["BuildRun"] = relationship("BuildRun", back_populates="logs")
