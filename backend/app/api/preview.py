from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.project import Project, ProjectStatus
from app.services.workspace import workspace_service
from app.core.security import validate_workspace_path

router = APIRouter(prefix="/projects/{project_id}/preview", tags=["Preview"])


def _status_str(status_val) -> str:
    return status_val.value if hasattr(status_val, "value") else str(status_val)


@router.get("", response_model=dict)
async def get_preview_metadata(project_id: str, db: AsyncSession = Depends(get_db)):
    """Returns the preview status and URL for a project."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found."
        )

    dist_dir = workspace_service.get_project_dir(project_id) / "dist"
    has_dist = dist_dir.exists() and (dist_dir / "index.html").exists()

    status_str = _status_str(project.status)
    if status_str != ProjectStatus.READY.value or not has_dist:
        return {
            "project_id": project_id,
            "status": status_str,
            "is_ready": False,
            "preview_url": None,
            "error": project.error_message or "Build is in progress or has not completed."
        }

    return {
        "project_id": project_id,
        "status": ProjectStatus.READY.value,
        "is_ready": True,
        "preview_url": f"/api/v2/projects/{project_id}/preview/index.html",
        "error": None
    }


@router.get("/{asset_path:path}")
async def serve_preview_asset(
    project_id: str,
    asset_path: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Serves static built assets from workspace/projects/{id}/dist/ with sandbox security headers.
    Prevents path traversal and rejects non-ready projects.
    """
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found."
        )

    if _status_str(project.status) != ProjectStatus.READY.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Preview is not ready. Project status is '{_status_str(project.status)}'."
        )

    dist_dir = (workspace_service.get_project_dir(project_id) / "dist").resolve()
    if not dist_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Production distribution folder 'dist' was not found."
        )

    # Sanitize and resolve asset target
    clean_path = asset_path.replace("\\", "/").strip()
    if not clean_path or clean_path == "/":
        clean_path = "index.html"

    target_file = (dist_dir / clean_path).resolve()

    # Enforce path containment
    try:
        validate_workspace_path(dist_dir, target_file)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden asset path traversal."
        )

    if not target_file.exists() or not target_file.is_file():
        # Fallback to SPA index.html for client-side routing if asset has no file extension
        if "." not in clean_path and (dist_dir / "index.html").exists():
            target_file = (dist_dir / "index.html").resolve()
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asset '{clean_path}' not found."
            )

    # Determine media type
    media_type = None
    if target_file.suffix == ".html":
        media_type = "text/html"
    elif target_file.suffix == ".js":
        media_type = "application/javascript"
    elif target_file.suffix == ".css":
        media_type = "text/css"
    elif target_file.suffix == ".svg":
        media_type = "image/svg+xml"
    elif target_file.suffix == ".json":
        media_type = "application/json"

    response = FileResponse(
        path=target_file,
        media_type=media_type,
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-cache",
            "Content-Security-Policy": (
                "default-src 'self' 'unsafe-inline' 'unsafe-eval' data: blob: https:; "
                "frame-ancestors 'self' http://localhost:3000 http://127.0.0.1:3000;"
            )
        }
    )
    return response
