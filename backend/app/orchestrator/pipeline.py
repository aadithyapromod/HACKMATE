import asyncio
from typing import Optional

from app.schemas.project import ProjectStatus
from app.schemas.task import Task, TaskStatus
from app.schemas.events import EventType
from app.storage.repository import BaseRepository, get_repository
from app.services.event_service import EventService, get_event_service
from app.integrations.ai_client import AIClient, get_ai_client
from app.integrations.runner_client import RunnerClient, get_runner_client


class ProjectPipeline:
    def __init__(
        self,
        repository: Optional[BaseRepository] = None,
        event_service: Optional[EventService] = None,
        ai_client: Optional[AIClient] = None,
        runner_client: Optional[RunnerClient] = None,
    ):
        self.repo = repository or get_repository()
        self.events = event_service or get_event_service()
        self.ai = ai_client or get_ai_client()
        self.runner = runner_client or get_runner_client()

    async def run(self, project_id: str) -> None:
        """Executes the pipeline stages: planning -> generating -> building -> completed."""
        project = self.repo.get_project(project_id)
        if not project:
            return

        try:
            # 1. Planning Stage
            self.repo.update_project_status(project_id, ProjectStatus.PLANNING)
            await self.events.publish(
                project_id,
                EventType.PROJECT_STATUS,
                {"status": ProjectStatus.PLANNING.value, "message": "Planning project architecture..."}
            )
            await self.events.publish(
                project_id,
                EventType.AGENT_STATUS,
                {"agent": "Planner", "status": "running", "message": "Analyzing prompt & creating plan."}
            )

            plan = await self.ai.create_plan(project.idea)
            raw_tasks = plan.get("tasks", [])
            tasks = [
                Task(
                    id=t["id"],
                    title=t["title"],
                    description=t["description"],
                    status=TaskStatus(t["status"])
                )
                for t in raw_tasks
            ]
            self.repo.set_tasks(project_id, tasks)

            for task in tasks:
                await self.events.publish(
                    project_id,
                    EventType.TASK_UPDATED,
                    {"task_id": task.id, "title": task.title, "status": task.status.value}
                )

            # 2. Generating Stage
            self.repo.update_project_status(project_id, ProjectStatus.GENERATING)
            await self.events.publish(
                project_id,
                EventType.PROJECT_STATUS,
                {"status": ProjectStatus.GENERATING.value, "message": "Synthesizing React + Vite application files..."}
            )
            await self.events.publish(
                project_id,
                EventType.AGENT_STATUS,
                {"agent": "Developer", "status": "running", "message": "Writing project files."}
            )

            files = await self.ai.generate_files(project.idea, plan)
            self.repo.set_files(project_id, files)

            # 3. Building Stage
            self.repo.update_project_status(project_id, ProjectStatus.BUILDING)
            await self.events.publish(
                project_id,
                EventType.PROJECT_STATUS,
                {"status": ProjectStatus.BUILDING.value, "message": "Building project in runner container..."}
            )

            build_result = await self.runner.build_project(project_id, f"./generated/{project_id}")
            self.repo.set_preview(project_id, build_result)

            await self.events.publish(
                project_id,
                EventType.BUILD_LOG,
                {"logs": build_result.logs}
            )
            await self.events.publish(
                project_id,
                EventType.BUILD_COMPLETED,
                {"success": build_result.success, "exit_code": build_result.exit_code}
            )

            # 4. Completion
            self.repo.update_project_status(project_id, ProjectStatus.COMPLETED)
            await self.events.publish(
                project_id,
                EventType.PROJECT_STATUS,
                {"status": ProjectStatus.COMPLETED.value, "message": "Project generation completed."}
            )
            await self.events.publish(
                project_id,
                EventType.PROJECT_COMPLETED,
                {"project_id": project_id, "preview_url": build_result.preview_url}
            )

        except Exception as e:
            self.repo.update_project_status(project_id, ProjectStatus.FAILED)
            await self.events.publish(
                project_id,
                EventType.PROJECT_FAILED,
                {"project_id": project_id, "error": str(e)}
            )


_pipeline = ProjectPipeline()


def get_pipeline() -> ProjectPipeline:
    return _pipeline
