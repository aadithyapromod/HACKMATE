from typing import List
from fastapi import APIRouter, BackgroundTasks, HTTPException, status, Depends
from fastapi.responses import StreamingResponse

from app.schemas.project import Project, ProjectCreateRequest, ErrorResponse
from app.schemas.task import Task
from app.schemas.files import FileListResponse, BuildResult
from app.services.project_service import ProjectService, get_project_service
from app.services.event_service import EventService, get_event_service
from app.orchestrator.pipeline import ProjectPipeline, get_pipeline

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post(
    "",
    response_model=Project,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def create_project(
    request: ProjectCreateRequest,
    service: ProjectService = Depends(get_project_service),
) -> Project:
    """Create a new project from a hackathon concept."""
    try:
        project = service.create_project(request.idea)
        return project
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/{project_id}",
    response_model=Project,
    responses={
        404: {"model": ErrorResponse, "description": "Project not found"},
    },
)
def get_project(
    project_id: str,
    service: ProjectService = Depends(get_project_service),
) -> Project:
    """Retrieve stored project state by ID."""
    project = service.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    return project


@router.post(
    "/{project_id}/start",
    response_model=Project,
    responses={
        404: {"model": ErrorResponse, "description": "Project not found"},
    },
)
async def start_project(
    project_id: str,
    background_tasks: BackgroundTasks,
    service: ProjectService = Depends(get_project_service),
    pipeline: ProjectPipeline = Depends(get_pipeline),
) -> Project:
    """Transition project to planning status and launch the agentic pipeline as a background task."""
    project = service.set_status_planning(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    # Schedule the async pipeline; FastAPI BackgroundTasks correctly awaits coroutines.
    background_tasks.add_task(pipeline.run, project_id)
    return project


@router.get(
    "/{project_id}/tasks",
    response_model=List[Task],
    responses={
        404: {"model": ErrorResponse, "description": "Project not found"},
    },
)
def get_project_tasks(
    project_id: str,
    service: ProjectService = Depends(get_project_service),
) -> List[Task]:
    """Retrieve tasks created during planning and execution."""
    tasks = service.get_tasks(project_id)
    if tasks is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    return tasks


@router.get(
    "/{project_id}/events",
    responses={
        404: {"model": ErrorResponse, "description": "Project not found"},
        200: {
            "description": "Server-Sent Events streaming real-time status and logs",
            "content": {"text/event-stream": {}},
        },
    },
)
def get_project_events(
    project_id: str,
    service: ProjectService = Depends(get_project_service),
    event_service: EventService = Depends(get_event_service),
):
    """Subscribe to Server-Sent Events for a project."""
    project = service.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )

    generator = event_service.subscribe(project_id, project.status.value)
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/{project_id}/files",
    response_model=FileListResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Project not found"},
    },
)
def get_project_files(
    project_id: str,
    service: ProjectService = Depends(get_project_service),
) -> FileListResponse:
    """Retrieve generated application source files."""
    files = service.get_files(project_id)
    if files is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    return FileListResponse(files=files)


@router.get(
    "/{project_id}/preview",
    response_model=BuildResult,
    responses={
        404: {"model": ErrorResponse, "description": "Project not found"},
    },
)
def get_project_preview(
    project_id: str,
    service: ProjectService = Depends(get_project_service),
) -> BuildResult:
    """Retrieve current build result and preview server status."""
    preview = service.get_preview(project_id)
    if preview is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    return preview
