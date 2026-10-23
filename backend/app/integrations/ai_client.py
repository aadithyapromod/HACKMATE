"""
backend/app/integrations/ai_client.py

Bridge between the FastAPI orchestrator (pipeline.py) and the ai/ module.

The ai/ module owns all LLM logic. This client:
  - Calls ai.create_plan() and ai.generate_files() (both async).
  - Converts ai.PlanOutput → dict  (what pipeline.py expects for plan).
  - Converts ai.FileListOutput → List[GeneratedFile]  (what repo.set_files expects).
  - Propagates errors as RuntimeError so the pipeline can catch them cleanly.
"""

import logging
from typing import Any, Dict, List

from app.schemas.files import GeneratedFile

logger = logging.getLogger(__name__)


class AIClient:
    """Thin async wrapper that delegates to the ai/ module."""

    async def create_plan(self, idea: str) -> Dict[str, Any]:
        """Return a plan dict compatible with pipeline.py.

        Returns:
            {
                "summary": str,
                "framework": "react-vite",
                "tasks": [{"id", "title", "description", "status"}, ...]
            }
        """
        try:
            from ai.planner import create_plan as _create_plan, PlannerError
        except ImportError as exc:
            raise RuntimeError(
                "ai/ module not importable. Ensure PYTHONPATH includes the repo root."
            ) from exc

        try:
            plan_output = await _create_plan(idea)
        except PlannerError as exc:
            raise RuntimeError(f"AI planning failed: {exc}") from exc

        return {
            "summary": plan_output.summary,
            "framework": plan_output.framework,
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "description": t.description,
                    "status": t.status,
                }
                for t in plan_output.tasks
            ],
        }

    async def generate_files(
        self, idea: str, plan: Dict[str, Any]
    ) -> List[GeneratedFile]:
        """Return generated files as a list of backend GeneratedFile models.

        Args:
            idea: Original hackathon idea text.
            plan: Dict returned by create_plan() (contains 'summary', 'tasks', etc.)

        Returns:
            List[GeneratedFile] — each has .path and .content attributes.
        """
        try:
            from ai.generator import generate_files as _generate_files, GeneratorError
        except ImportError as exc:
            raise RuntimeError(
                "ai/ module not importable. Ensure PYTHONPATH includes the repo root."
            ) from exc

        try:
            file_list_output = await _generate_files(idea, plan)
        except GeneratorError as exc:
            raise RuntimeError(f"AI file generation failed: {exc}") from exc

        return [
            GeneratedFile(path=f.path, content=f.content)
            for f in file_list_output.files
        ]


_ai_client = AIClient()


def get_ai_client() -> AIClient:
    return _ai_client
