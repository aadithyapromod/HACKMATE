import asyncio
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.project import Project
from app.services.sse_manager import sse_manager
from app.schemas.events import SSEMessage, SSEEventType
from app.core.logging import logger

router = APIRouter(prefix="/projects/{project_id}", tags=["Events"])


@router.get("/events")
async def project_events_stream(
    project_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Real-time Server-Sent Events (SSE) stream for tracking pipeline progress,
    task updates, and sandbox build logs.
    """
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found."
        )

    queue = await sse_manager.subscribe(project_id)

    async def event_generator():
        try:
            # Send initial connection frame
            initial = SSEMessage(
                event=SSEEventType.HEARTBEAT,
                data={"status": "connected", "project_id": project_id}
            )
            yield initial.format_sse()

            while True:
                # Check for client disconnect
                if await request.is_disconnected():
                    logger.debug(f"SSE client disconnected from project {project_id}")
                    break

                try:
                    # Wait for next event with a 15-second heartbeat timeout
                    message = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield message
                except asyncio.TimeoutError:
                    # Send periodic keep-alive frame
                    heartbeat = SSEMessage(
                        event=SSEEventType.HEARTBEAT,
                        data={"timestamp": "keep-alive"}
                    )
                    yield heartbeat.format_sse()

        finally:
            await sse_manager.unsubscribe(project_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
