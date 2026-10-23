import asyncio
from typing import Dict, Set, Optional
from app.schemas.events import SSEMessage, SSEEventType
from app.core.logging import logger


class SSEManager:
    """Manages Server-Sent Events subscribers per project."""
    def __init__(self):
        # Maps project_id -> set of asyncio.Queue
        self._subscribers: Dict[str, Set[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, project_id: str) -> asyncio.Queue:
        async with self._lock:
            if project_id not in self._subscribers:
                self._subscribers[project_id] = set()
            queue = asyncio.Queue(maxsize=100)
            self._subscribers[project_id].add(queue)
            logger.debug(f"Client subscribed to SSE for project {project_id}. Total: {len(self._subscribers[project_id])}")
            return queue

    async def unsubscribe(self, project_id: str, queue: asyncio.Queue):
        async with self._lock:
            if project_id in self._subscribers:
                self._subscribers[project_id].discard(queue)
                if not self._subscribers[project_id]:
                    del self._subscribers[project_id]
            logger.debug(f"Client unsubscribed from SSE for project {project_id}")

    async def broadcast(self, project_id: str, message: SSEMessage):
        """Sends an SSE event to all connected listeners for a project."""
        async with self._lock:
            subscribers = list(self._subscribers.get(project_id, []))

        formatted = message.format_sse()
        for q in subscribers:
            try:
                q.put_nowait(formatted)
            except asyncio.QueueFull:
                logger.warning(f"SSE queue full for subscriber on project {project_id}, dropping frame.")

    async def emit_status(self, project_id: str, from_status: str, to_status: str, message: str = ""):
        msg = SSEMessage(
            event=SSEEventType.STATUS_CHANGED,
            data={
                "project_id": project_id,
                "from_status": from_status,
                "to_status": to_status,
                "message": message,
            }
        )
        await self.broadcast(project_id, msg)

    async def emit_task_updated(self, project_id: str, task_id: str, title: str, status: str, order: int):
        msg = SSEMessage(
            event=SSEEventType.TASK_UPDATED,
            data={
                "project_id": project_id,
                "task_id": task_id,
                "title": title,
                "status": status,
                "order": order,
            }
        )
        await self.broadcast(project_id, msg)

    async def emit_file_written(self, project_id: str, file_path: str, file_size: int, index: int, total: int):
        msg = SSEMessage(
            event=SSEEventType.FILE_WRITTEN,
            data={
                "project_id": project_id,
                "path": file_path,
                "size": file_size,
                "index": index,
                "total": total,
            }
        )
        await self.broadcast(project_id, msg)

    async def emit_build_log(self, project_id: str, build_run_id: str, stream: str, chunk: str):
        msg = SSEMessage(
            event=SSEEventType.BUILD_LOG,
            data={
                "project_id": project_id,
                "build_run_id": build_run_id,
                "stream": stream,
                "chunk": chunk,
            }
        )
        await self.broadcast(project_id, msg)

    async def emit_repair_attempt(self, project_id: str, iteration: int, max_iterations: int, reason: str):
        msg = SSEMessage(
            event=SSEEventType.REPAIR_ATTEMPT,
            data={
                "project_id": project_id,
                "iteration": iteration,
                "max_iterations": max_iterations,
                "reason": reason,
            }
        )
        await self.broadcast(project_id, msg)

    async def emit_build_completed(self, project_id: str, success: bool, preview_url: Optional[str] = None, error: Optional[str] = None):
        msg = SSEMessage(
            event=SSEEventType.BUILD_COMPLETED,
            data={
                "project_id": project_id,
                "success": success,
                "preview_url": preview_url,
                "error": error,
            }
        )
        await self.broadcast(project_id, msg)


sse_manager = SSEManager()
