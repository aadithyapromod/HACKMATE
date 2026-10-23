import pytest
import asyncio
from httpx import AsyncClient
from app.services.sse_manager import sse_manager
from app.schemas.events import SSEMessage, SSEEventType


@pytest.mark.asyncio
async def test_sse_manager_subscription():
    project_id = "test-sse-proj"
    queue = await sse_manager.subscribe(project_id)
    assert queue is not None

    msg = SSEMessage(
        event=SSEEventType.STATUS_CHANGED,
        data={"project_id": project_id, "from_status": "QUEUED", "to_status": "ANALYZING"}
    )
    await sse_manager.broadcast(project_id, msg)

    received_raw = await asyncio.wait_for(queue.get(), timeout=2.0)
    assert "event: status_changed" in received_raw
    assert "ANALYZING" in received_raw

    await sse_manager.unsubscribe(project_id, queue)
