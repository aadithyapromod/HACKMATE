from typing import List, Optional
from app.schemas.project import Project, ProjectStatus
from app.schemas.task import Task
from app.schemas.files import GeneratedFile, BuildResult
from app.storage.repository import BaseRepository, get_repository


class ProjectService:
    def __init__(
        self,
        repository: Optional[BaseRepository] = None,
    ):
        self.repo = repository or get_repository()

    def create_project(self, idea: str) -> Project:
        return self.repo.create_project(idea)

    def get_project(self, project_id: str) -> Optional[Project]:
        return self.repo.get_project(project_id)

    def set_status_planning(self, project_id: str) -> Optional[Project]:
        """Transition project to PLANNING status. Pipeline is scheduled by the endpoint."""
        project = self.repo.get_project(project_id)
        if not project:
            return None
        updated = self.repo.update_project_status(project_id, ProjectStatus.PLANNING)
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
