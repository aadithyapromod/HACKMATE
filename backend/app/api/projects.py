from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.project import Project, ProjectStatus
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectDetailResponse, ProjectListResponse
from app.services.orchestrator import orchestration_service
from app.core.errors import InvalidStateTransitionError, ProjectNotFoundError

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(payload: ProjectCreate, db: AsyncSession = Depends(get_db)):
    """Creates a new project record in QUEUED status."""
    title = payload.title or payload.prompt.strip().split("\n")[0][:60]
    
    project = Project(
        title=title,
        prompt=payload.prompt,
        reference_url=payload.reference_url,
        framework="react-vite",
        status=ProjectStatus.QUEUED,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves paginated list of projects."""
    count_stmt = select(func.count()).select_from(Project)
    total = await db.scalar(count_stmt) or 0

    stmt = select(Project).order_by(Project.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    projects = result.scalars().all()

    return ProjectListResponse(total=total, items=projects)


@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieves full project details including tasks and build history."""
    stmt = (
        select(Project)
        .options(
            selectinload(Project.tasks),
            selectinload(Project.build_runs)
        )
        .where(Project.id == project_id)
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found."
        )

    return project


@router.post("/{project_id}/start")
async def start_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """Triggers the autonomous generation and build pipeline."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found."
        )

    if orchestration_service.is_project_running(project_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Project '{project_id}' is already executing."
        )

    await orchestration_service.start_pipeline(project_id)
    return {"message": "Pipeline initiated successfully.", "project_id": project_id, "status": "ANALYZING"}


@router.post("/{project_id}/cancel")
async def cancel_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """Cancels an in-flight build or generation pipeline."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found."
        )

    cancelled = await orchestration_service.cancel_pipeline(project_id)
    if not cancelled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project '{project_id}' does not have an active background job."
        )

    return {"message": "Cancellation request submitted.", "project_id": project_id}
