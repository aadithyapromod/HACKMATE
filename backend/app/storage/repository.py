from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime, timezone
import uuid

from app.schemas.project import Project, ProjectStatus
from app.schemas.task import Task
from app.schemas.files import GeneratedFile, BuildResult


class BaseRepository(ABC):
    @abstractmethod
    def create_project(self, idea: str) -> Project:
        pass

    @abstractmethod
    def get_project(self, project_id: str) -> Optional[Project]:
        pass

    @abstractmethod
    def update_project_status(self, project_id: str, status: ProjectStatus) -> Optional[Project]:
        pass

    @abstractmethod
    def get_tasks(self, project_id: str) -> List[Task]:
        pass

    @abstractmethod
    def set_tasks(self, project_id: str, tasks: List[Task]) -> List[Task]:
        pass

    @abstractmethod
    def get_files(self, project_id: str) -> List[GeneratedFile]:
        pass

    @abstractmethod
    def set_files(self, project_id: str, files: List[GeneratedFile]) -> List[GeneratedFile]:
        pass

    @abstractmethod
    def get_preview(self, project_id: str) -> BuildResult:
        pass

    @abstractmethod
    def set_preview(self, project_id: str, preview: BuildResult) -> BuildResult:
        pass


class InMemoryRepository(BaseRepository):
    def __init__(self):
        self._projects: Dict[str, Project] = {}
        self._tasks: Dict[str, List[Task]] = {}
        self._files: Dict[str, List[GeneratedFile]] = {}
        self._previews: Dict[str, BuildResult] = {}

    def create_project(self, idea: str) -> Project:
        project_id = f"project-{uuid.uuid4().hex[:8]}"
        project = Project(
            id=project_id,
            idea=idea,
            status=ProjectStatus.CREATED,
            created_at=datetime.now(timezone.utc).isoformat()
        )
        self._projects[project_id] = project
        self._tasks[project_id] = []
        self._files[project_id] = []
        self._previews[project_id] = BuildResult(
            success=False,
            exit_code=0,
            logs="Project created. Build not yet initiated.",
            preview_url=None
        )
        return project

    def get_project(self, project_id: str) -> Optional[Project]:
        return self._projects.get(project_id)

    def update_project_status(self, project_id: str, status: ProjectStatus) -> Optional[Project]:
        proj = self._projects.get(project_id)
        if proj:
            updated = proj.model_copy(update={"status": status})
            self._projects[project_id] = updated
            return updated
        return None

    def get_tasks(self, project_id: str) -> List[Task]:
        return self._tasks.get(project_id, [])

    def set_tasks(self, project_id: str, tasks: List[Task]) -> List[Task]:
        self._tasks[project_id] = tasks
        return tasks

    def get_files(self, project_id: str) -> List[GeneratedFile]:
        return self._files.get(project_id, [])

    def set_files(self, project_id: str, files: List[GeneratedFile]) -> List[GeneratedFile]:
        self._files[project_id] = files
        return files

    def get_preview(self, project_id: str) -> BuildResult:
        return self._previews.get(
            project_id,
            BuildResult(
                success=False,
                exit_code=0,
                logs="No build logs available for this project.",
                preview_url=None
            )
        )

    def set_preview(self, project_id: str, preview: BuildResult) -> BuildResult:
        self._previews[project_id] = preview
        return preview


# Global singleton repository instance
_repo_instance = InMemoryRepository()


def get_repository() -> BaseRepository:
    return _repo_instance
