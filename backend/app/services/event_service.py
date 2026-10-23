import asyncio
import json
from typing import AsyncGenerator, Dict, List
from datetime import datetime, timezone

from app.schemas.events import EventType, AgentEvent


class EventService:
    def __init__(self):
        # Maps project_id -> list of asyncio.Queue for connected SSE clients
        self._listeners: Dict[str, List[asyncio.Queue]] = {}

    def format_sse_message(self, event_type: str, data: dict) -> str:
        """Format payload into standard SSE framing: event: ... \n data: ... \n\n"""
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

    async def publish(self, project_id: str, event_type: EventType | str, data: dict) -> None:
        """Publish an event to all subscribers of a project."""
        str_event_type = event_type.value if isinstance(event_type, EventType) else str(event_type)
        payload = {
            "project_id": project_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **data
        }
        message = self.format_sse_message(str_event_type, payload)

        listeners = self._listeners.get(project_id, [])
        for queue in listeners:
            await queue.put(message)

    async def subscribe(self, project_id: str, initial_status: str) -> AsyncGenerator[str, None]:
        """Subscribe to SSE events for a specific project. Yields initial snapshot then stream."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        if project_id not in self._listeners:
            self._listeners[project_id] = []
        self._listeners[project_id].append(queue)

        try:
            # Yield initial snapshot event
            initial_msg = self.format_sse_message(
                EventType.PROJECT_STATUS.value,
                {
                    "project_id": project_id,
                    "status": initial_status,
                    "message": "Connected to HackMate project event stream."
                }
            )
            yield initial_msg

            while True:
                # Wait for queued messages or yield keep-alive comment
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield message
                except asyncio.TimeoutError:
                    # Heartbeat comment to keep SSE connection alive
                    yield ": ping\n\n"
        finally:
            if project_id in self._listeners and queue in self._listeners[project_id]:
                self._listeners[project_id].remove(queue)
                if not self._listeners[project_id]:
                    del self._listeners[project_id]


_event_service = EventService()


def get_event_service() -> EventService:
    return _event_service
