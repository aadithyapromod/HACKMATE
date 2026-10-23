from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.project import Project
from app.models.file import GeneratedFile
from app.schemas.file import FileListResponse, FileMetadataResponse, FileDetailResponse
from app.services.workspace import workspace_service
from app.core.security import sanitize_relative_path

router = APIRouter(prefix="/projects/{project_id}", tags=["Files"])


@router.get("/files", response_model=FileListResponse)
async def list_project_files(project_id: str, db: AsyncSession = Depends(get_db)):
    """Lists all files synthesized for a project."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found."
        )

    stmt = select(GeneratedFile).where(GeneratedFile.project_id == project_id).order_by(GeneratedFile.file_path)
    result = await db.execute(stmt)
    files = result.scalars().all()

    return FileListResponse(
        project_id=project_id,
        total_files=len(files),
        files=[FileMetadataResponse.model_validate(f) for f in files]
    )


@router.get("/files/{file_path:path}", response_model=FileDetailResponse)
async def get_project_file(project_id: str, file_path: str, db: AsyncSession = Depends(get_db)):
    """Retrieves full content and metadata for a specific file in the project."""
    clean_path = sanitize_relative_path(file_path)
    stmt = (
        select(GeneratedFile)
        .where(GeneratedFile.project_id == project_id, GeneratedFile.file_path == clean_path)
    )
    result = await db.execute(stmt)
    file_record = result.scalar_one_or_none()

    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File '{clean_path}' not found in project '{project_id}'."
        )

    return FileDetailResponse.model_validate(file_record)


@router.get("/export")
async def export_project_zip(project_id: str, db: AsyncSession = Depends(get_db)):
    """Packages and streams the complete generated project codebase as a downloadable ZIP."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found."
        )

    try:
        zip_buffer = workspace_service.create_zip_archive(project_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project workspace files have not been generated yet."
        )

    filename = f"hackmate-{project_id[:8]}.zip"
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
