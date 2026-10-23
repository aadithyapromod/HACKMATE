import asyncio
from typing import List, Optional
from app.schemas.project import Project, ProjectStatus
from app.schemas.task import Task
from app.schemas.files import GeneratedFile, BuildResult
from app.storage.repository import BaseRepository, get_repository
from app.orchestrator.pipeline import ProjectPipeline, get_pipeline


class ProjectService:
    def __init__(
        self,
        repository: Optional[BaseRepository] = None,
        pipeline: Optional[ProjectPipeline] = None,
    ):
        self.repo = repository or get_repository()
        self.pipeline = pipeline or get_pipeline()

    def create_project(self, idea: str) -> Project:
        return self.repo.create_project(idea)

    def get_project(self, project_id: str) -> Optional[Project]:
        return self.repo.get_project(project_id)

    def start_project(self, project_id: str) -> Optional[Project]:
        project = self.repo.get_project(project_id)
        if not project:
            return None

        # Return truthful status: transition to planning and trigger async pipeline
        updated = self.repo.update_project_status(project_id, ProjectStatus.PLANNING)
        asyncio.create_task(self.pipeline.run(project_id))
        return updated or project

    def get_tasks(self, project_id: str) -> Optional[List[Task]]:
        if not self.repo.get_project(project_id):
            return None
        return self.repo.get_tasks(project_id)

    def get_files(self, project_id: str) -> Optional[List[GeneratedFile]]:
        if not self.repo.get_project(project_id):
            return None
        return self.repo.get_files(project_id)

    def get_preview(self, project_id: str) -> Optional[BuildResult]:
        if not self.repo.get_project(project_id):
            return None
        return self.repo.get_preview(project_id)


_project_service = ProjectService()


def get_project_service() -> ProjectService:
    return _project_service
