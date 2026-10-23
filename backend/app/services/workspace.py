import io
import shutil
import zipfile
from pathlib import Path
from typing import Dict, List, Optional
from app.config import settings
from app.core.security import sanitize_relative_path, validate_workspace_path
from app.core.errors import SecurityViolationError
from app.core.logging import logger


class WorkspaceService:
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or settings.resolved_workspace_path

    def get_project_dir(self, project_id: str) -> Path:
        """Returns the project's root directory, verifying safe path containment."""
        target_dir = (self.base_dir / project_id).resolve()
        return validate_workspace_path(self.base_dir, target_dir)

    def init_project_workspace(self, project_id: str) -> Path:
        """Initializes an empty isolated workspace directory for a project."""
        project_dir = self.get_project_dir(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir

    def write_file(self, project_id: str, relative_path: str, content: str) -> int:
        """
        Safely writes a file to the project workspace.
        Returns the written file size in bytes.
        """
        clean_rel_path = sanitize_relative_path(relative_path)
        project_dir = self.init_project_workspace(project_id)
        target_file = (project_dir / clean_rel_path).resolve()
        
        # Enforce boundary check
        validate_workspace_path(project_dir, target_file)

        # Create parent directories
        target_file.parent.mkdir(parents=True, exist_ok=True)

        encoded = content.encode("utf-8")
        target_file.write_bytes(encoded)
        logger.debug(f"Wrote file {clean_rel_path} ({len(encoded)} bytes) for project {project_id}")
        return len(encoded)

    def read_file(self, project_id: str, relative_path: str) -> str:
        """Safely reads a file from the project workspace."""
        clean_rel_path = sanitize_relative_path(relative_path)
        project_dir = self.get_project_dir(project_id)
        target_file = (project_dir / clean_rel_path).resolve()
        
        validate_workspace_path(project_dir, target_file)

        if not target_file.exists() or not target_file.is_file():
            raise FileNotFoundError(f"File '{clean_rel_path}' does not exist in workspace.")

        return target_file.read_text(encoding="utf-8")

    def list_files(self, project_id: str) -> List[str]:
        """Lists all relative paths of files in the workspace (excluding node_modules/.git)."""
        project_dir = self.get_project_dir(project_id)
        if not project_dir.exists():
            return []

        rel_paths = []
        for p in project_dir.rglob("*"):
            if p.is_file():
                rel = p.relative_to(project_dir).as_posix()
                if not rel.startswith("node_modules/") and not rel.startswith(".git/"):
                    rel_paths.append(rel)
        return sorted(rel_paths)

    def create_zip_archive(self, project_id: str) -> io.BytesIO:
        """Generates an in-memory ZIP archive of the project workspace."""
        project_dir = self.get_project_dir(project_id)
        if not project_dir.exists():
            raise FileNotFoundError(f"Project workspace '{project_id}' does not exist.")

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in project_dir.rglob("*"):
                if p.is_file():
                    rel = p.relative_to(project_dir).as_posix()
                    # Skip heavy dependencies and build artifacts from zip
                    if rel.startswith("node_modules/") or rel.startswith("dist/"):
                        continue
                    zf.write(p, arcname=rel)

        buffer.seek(0)
        return buffer

    def delete_workspace(self, project_id: str):
        """Removes the project workspace from disk."""
        project_dir = self.get_project_dir(project_id)
        if project_dir.exists():
            shutil.rmtree(project_dir, ignore_errors=True)
            logger.info(f"Cleaned up workspace for project {project_id}")

    def cleanup_temp_artifacts(self, project_id: str):
        """Cleans up transient npm cache or temporary files inside project."""
        project_dir = self.get_project_dir(project_id)
        if not project_dir.exists():
            return
        for temp_name in [".npm", ".cache", "tmp"]:
            p = project_dir / temp_name
            if p.exists() and p.is_dir():
                shutil.rmtree(p, ignore_errors=True)

    def cleanup_expired_workspaces(self, max_age_seconds: int = 86400) -> int:
        """Removes workspaces that have not been modified within max_age_seconds."""
        import time
        now = time.time()
        removed_count = 0
        if not self.base_dir.exists():
            return 0

        for child in self.base_dir.iterdir():
            if child.is_dir():
                mtime = child.stat().st_mtime
                if now - mtime > max_age_seconds:
                    shutil.rmtree(child, ignore_errors=True)
                    removed_count += 1
                    logger.info(f"Cleaned up expired workspace: {child.name}")

        return removed_count


workspace_service = WorkspaceService()
