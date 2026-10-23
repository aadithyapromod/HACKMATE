from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.session import get_db
from app.models.project import Project
from app.models.build import BuildRun
from app.schemas.build import BuildRunResponse

router = APIRouter(prefix="/projects/{project_id}", tags=["Builds"])


@router.get("/builds", response_model=List[BuildRunResponse])
async def list_project_builds(project_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieves all historical sandbox build attempts and compiler logs for a project."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found."
        )

    stmt = (
        select(BuildRun)
        .options(selectinload(BuildRun.logs))
        .where(BuildRun.project_id == project_id)
        .order_by(BuildRun.attempt_number.desc())
    )
    result = await db.execute(stmt)
    builds = result.scalars().all()

    return builds
