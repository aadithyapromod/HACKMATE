"""
ai/planner.py — HackMate AI Planner

Public interface (called by backend via ai_client.py):
    async def create_plan(idea: str) -> PlanOutput

Behaviour:
  - Calls the configured LLM provider (Gemini free-tier by default).
  - Parses and validates the structured JSON response.
  - Falls back to a deterministic template when no provider key is configured
    (clearly identified as fallback, never presented as real LLM output).
  - Raises PlannerError on unrecoverable failures.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Union

from ai.models import PlanOutput, PlanTask
from ai.prompts import PLAN_SYSTEM, PLAN_USER
from ai.provider import FallbackProvider, ProviderError, _FALLBACK_SENTINEL, get_provider

logger = logging.getLogger(__name__)


class PlannerError(Exception):
    """Raised when planning fails and cannot be recovered."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _strip_json_fences(text: str) -> str:
    """Remove markdown code fences that some models emit despite instructions."""
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ```
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _validate_plan(data: dict) -> PlanOutput:
    """Validate a parsed plan dict and return a PlanOutput.

    Raises ValueError on schema violations.
    """
    if not isinstance(data, dict):
        raise ValueError("Plan JSON root must be an object.")

    summary = str(data.get("summary", "")).strip()
    if not summary:
        raise ValueError("Plan is missing 'summary'.")

    framework = data.get("framework", "react-vite")
    if framework != "react-vite":
        raise ValueError(f"Unexpected framework '{framework}'; expected 'react-vite'.")

    raw_tasks = data.get("tasks", [])
    if not isinstance(raw_tasks, list) or len(raw_tasks) == 0:
        raise ValueError("Plan must contain at least one task.")

    tasks: list[PlanTask] = []
    for i, t in enumerate(raw_tasks, start=1):
        if not isinstance(t, dict):
            raise ValueError(f"Task {i} is not an object.")
        task_id = str(t.get("id", f"task-{i}")).strip()
        title = str(t.get("title", "")).strip()
        description = str(t.get("description", "")).strip()
        status = str(t.get("status", "pending")).strip()
        if not title:
            raise ValueError(f"Task {i} is missing 'title'.")
        if status not in {"pending", "running", "completed", "failed"}:
            status = "pending"
        tasks.append(PlanTask(id=task_id, title=title, description=description, status=status))

    return PlanOutput(summary=summary, framework="react-vite", tasks=tasks)


def _fallback_plan(idea: str) -> PlanOutput:
    """Deterministic fallback plan. Used only when no LLM key is set."""
    clean = idea.strip()
    return PlanOutput(
        summary=f"[FALLBACK] Deterministic plan for: {clean[:80]}",
        framework="react-vite",
        tasks=[
            PlanTask(
                id="task-1",
                title="Design System & Dependencies",
                description="Configure Vite build toolchain and core React component structure.",
                status="pending",
            ),
            PlanTask(
                id="task-2",
                title="Core Layout & Navigation",
                description="Generate responsive shell and application state management.",
                status="pending",
            ),
            PlanTask(
                id="task-3",
                title="Feature View Implementation",
                description=f"Build primary feature components for: '{clean[:60]}'.",
                status="pending",
            ),
            PlanTask(
                id="task-4",
                title="Assembly & Integration",
                description="Assemble all generated modules into src/App.jsx and verify imports.",
                status="pending",
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def create_plan(idea: str) -> PlanOutput:
    """Decompose a hackathon idea into a structured execution plan.

    Args:
        idea: Raw user idea text (10-2000 characters).

    Returns:
        PlanOutput — validated plan with summary, framework, and task list.

    Raises:
        PlannerError: If the provider fails and cannot be recovered.
    """
    if not idea or not idea.strip():
        raise PlannerError("Idea must not be empty.")

    provider = get_provider()
    logger.info("create_plan() using provider: %s", provider.name)

    # Fallback path — skip LLM call entirely
    if isinstance(provider, FallbackProvider):
        logger.info("Fallback provider active — returning deterministic plan.")
        return _fallback_plan(idea)

    prompt = f"{PLAN_SYSTEM}\n\n{PLAN_USER.format(idea=idea.strip())}"

    try:
        raw = await provider.complete(prompt)
    except ProviderError as exc:
        raise PlannerError(f"AI provider failed during planning: {exc}") from exc

    # Detect sentinel (shouldn't happen for non-fallback providers, but guard anyway)
    if raw == _FALLBACK_SENTINEL:
        return _fallback_plan(idea)

    cleaned = _strip_json_fences(raw)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error("Planner: invalid JSON from provider: %s\nRaw: %.500s", exc, cleaned)
        raise PlannerError(f"Provider returned invalid JSON: {exc}") from exc

    try:
        return _validate_plan(data)
    except ValueError as exc:
        logger.error("Planner: schema validation failed: %s\nData: %s", exc, data)
        raise PlannerError(f"Provider plan failed schema validation: {exc}") from exc
