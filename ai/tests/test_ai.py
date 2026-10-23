"""
ai/tests/test_ai.py — Comprehensive tests for the HackMate AI module.

Test coverage:
  - Fallback plan parsing and structure validation
  - Fallback file generation — all required files present
  - _validate_plan: valid input, missing summary, bad framework, empty tasks
  - _validate_files: valid input, missing required paths, unsafe paths, duplicates
  - _sanitise_path: safe paths, traversal attacks, absolute paths
  - create_plan: provider success, provider error → PlannerError, empty JSON, bad schema
  - generate_files: provider success, provider error → GeneratorError, missing files
  - Provider routing: Gemini key set → GeminiProvider, no key → FallbackProvider

All LLM calls are mocked so tests run without any API key or network access.
To test against a real Gemini key, set GEMINI_API_KEY in your .env and run:
    pytest ai/tests/test_ai.py -k live --live
(live tests are skipped by default)
"""

import json
import os
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from ai.models import PlanOutput, PlanTask, FileListOutput, GeneratedFileModel
from ai.planner import (
    create_plan,
    _validate_plan,
    _fallback_plan,
    _strip_json_fences,
    PlannerError,
)
from ai.generator import (
    generate_files,
    _validate_files,
    _sanitise_path,
    _fallback_files,
    GeneratorError,
)
from ai.provider import FallbackProvider, GeminiProvider, get_provider, ProviderError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_IDEA = "Build a student hackathon matching website"

VALID_PLAN_DICT = {
    "summary": "Plan for a hackathon matching platform",
    "framework": "react-vite",
    "tasks": [
        {"id": "task-1", "title": "Design System", "description": "Set up Vite.", "status": "pending"},
        {"id": "task-2", "title": "Core Layout", "description": "Build shell.", "status": "pending"},
    ],
}

VALID_FILES_LIST = [
    {"path": "package.json", "content": '{"name":"test"}'},
    {"path": "index.html", "content": "<!doctype html><html></html>"},
    {"path": "vite.config.js", "content": "export default {}"},
    {"path": "src/main.jsx", "content": "import React from 'react'"},
    {"path": "src/App.jsx", "content": "export default function App() { return null; }"},
    {"path": "src/index.css", "content": "body { margin: 0; }"},
]


# ---------------------------------------------------------------------------
# _strip_json_fences
# ---------------------------------------------------------------------------

def test_strip_json_fences_no_fences():
    assert _strip_json_fences('{"a": 1}') == '{"a": 1}'


def test_strip_json_fences_with_json_fence():
    text = "```json\n{\"a\": 1}\n```"
    assert _strip_json_fences(text) == '{"a": 1}'


def test_strip_json_fences_with_plain_fence():
    text = "```\n{\"a\": 1}\n```"
    assert _strip_json_fences(text) == '{"a": 1}'


# ---------------------------------------------------------------------------
# _validate_plan
# ---------------------------------------------------------------------------

def test_validate_plan_valid():
    result = _validate_plan(VALID_PLAN_DICT)
    assert isinstance(result, PlanOutput)
    assert result.framework == "react-vite"
    assert len(result.tasks) == 2
    assert result.tasks[0].title == "Design System"


def test_validate_plan_missing_summary():
    data = {**VALID_PLAN_DICT, "summary": ""}
    with pytest.raises(ValueError, match="missing 'summary'"):
        _validate_plan(data)


def test_validate_plan_wrong_framework():
    data = {**VALID_PLAN_DICT, "framework": "next-js"}
    with pytest.raises(ValueError, match="framework"):
        _validate_plan(data)


def test_validate_plan_empty_tasks():
    data = {**VALID_PLAN_DICT, "tasks": []}
    with pytest.raises(ValueError, match="at least one task"):
        _validate_plan(data)


def test_validate_plan_task_missing_title():
    data = {
        **VALID_PLAN_DICT,
        "tasks": [{"id": "t1", "title": "", "description": "desc", "status": "pending"}],
    }
    with pytest.raises(ValueError, match="missing 'title'"):
        _validate_plan(data)


def test_validate_plan_non_dict():
    with pytest.raises(ValueError, match="object"):
        _validate_plan([])  # type: ignore


# ---------------------------------------------------------------------------
# _sanitise_path
# ---------------------------------------------------------------------------

def test_sanitise_path_normal():
    assert _sanitise_path("src/App.jsx") == "src/App.jsx"


def test_sanitise_path_leading_slash():
    # Leading absolute slash is considered unsafe — reject it rather than silently strip
    with pytest.raises(ValueError, match="Unsafe"):
        _sanitise_path("/src/App.jsx")


def test_sanitise_path_traversal():
    with pytest.raises(ValueError, match="Unsafe"):
        _sanitise_path("../etc/passwd")


def test_sanitise_path_absolute_windows():
    with pytest.raises(ValueError, match="Unsafe"):
        _sanitise_path("C:\\Windows\\System32\\evil.exe")


def test_sanitise_path_empty():
    with pytest.raises(ValueError):
        _sanitise_path("")


def test_sanitise_path_nested():
    assert _sanitise_path("src/components/Header.jsx") == "src/components/Header.jsx"


# ---------------------------------------------------------------------------
# _validate_files
# ---------------------------------------------------------------------------

def test_validate_files_valid():
    result = _validate_files(VALID_FILES_LIST)
    assert len(result) == 6
    paths = [f.path for f in result]
    assert "package.json" in paths
    assert "src/App.jsx" in paths


def test_validate_files_missing_required():
    incomplete = [f for f in VALID_FILES_LIST if f["path"] != "src/App.jsx"]
    with pytest.raises(ValueError, match="missing required"):
        _validate_files(incomplete)


def test_validate_files_unsafe_path_in_list():
    bad = VALID_FILES_LIST + [{"path": "../secret.txt", "content": "oops"}]
    # Should still validate the good ones but reject the bad path
    # Since _validate_files calls _sanitise_path which raises, it propagates
    with pytest.raises((ValueError, GeneratorError)):
        _validate_files(bad)


def test_validate_files_empty_list():
    with pytest.raises(ValueError, match="non-empty"):
        _validate_files([])


def test_validate_files_duplicate_paths():
    duped = VALID_FILES_LIST + [{"path": "package.json", "content": "dupe"}]
    # Duplicates are skipped (warning logged), so result should still be valid
    result = _validate_files(duped)
    pkg_count = sum(1 for f in result if f.path == "package.json")
    assert pkg_count == 1


# ---------------------------------------------------------------------------
# _fallback_plan
# ---------------------------------------------------------------------------

def test_fallback_plan_structure():
    plan = _fallback_plan(SAMPLE_IDEA)
    assert isinstance(plan, PlanOutput)
    assert plan.framework == "react-vite"
    assert len(plan.tasks) >= 3
    assert "[FALLBACK]" in plan.summary


# ---------------------------------------------------------------------------
# _fallback_files
# ---------------------------------------------------------------------------

def test_fallback_files_structure():
    output = _fallback_files(SAMPLE_IDEA)
    assert isinstance(output, FileListOutput)
    paths = [f.path for f in output.files]
    for required in ["package.json", "index.html", "vite.config.js",
                     "src/main.jsx", "src/App.jsx", "src/index.css"]:
        assert required in paths, f"Missing required file: {required}"


def test_fallback_files_idea_injected():
    output = _fallback_files("My special hackathon idea")
    app_jsx = next(f for f in output.files if f.path == "src/App.jsx")
    assert "My special hackathon idea" in app_jsx.content


# ---------------------------------------------------------------------------
# create_plan — mocked provider
# ---------------------------------------------------------------------------

VALID_PLAN_JSON = json.dumps(VALID_PLAN_DICT)


@pytest.mark.asyncio
async def test_create_plan_uses_fallback_when_no_key():
    """When no GEMINI_API_KEY is set, must use deterministic fallback."""
    with patch.dict(os.environ, {"GEMINI_API_KEY": "", "AI_MODEL": ""}, clear=False):
        result = await create_plan(SAMPLE_IDEA)
    assert isinstance(result, PlanOutput)
    assert "[FALLBACK]" in result.summary


@pytest.mark.asyncio
async def test_create_plan_success_with_mock_provider():
    """Provider returns valid JSON → PlanOutput returned."""
    mock_provider = MagicMock()
    mock_provider.complete = AsyncMock(return_value=VALID_PLAN_JSON)
    mock_provider.__class__ = MagicMock  # not FallbackProvider

    with patch("ai.planner.get_provider", return_value=mock_provider):
        result = await create_plan(SAMPLE_IDEA)

    assert isinstance(result, PlanOutput)
    assert result.summary == "Plan for a hackathon matching platform"
    assert len(result.tasks) == 2


@pytest.mark.asyncio
async def test_create_plan_provider_error_raises_planner_error():
    """Provider raises ProviderError → PlannerError propagated."""
    mock_provider = MagicMock()
    mock_provider.complete = AsyncMock(side_effect=ProviderError("quota exceeded"))
    mock_provider.__class__ = MagicMock

    with patch("ai.planner.get_provider", return_value=mock_provider):
        with pytest.raises(PlannerError, match="quota exceeded"):
            await create_plan(SAMPLE_IDEA)


@pytest.mark.asyncio
async def test_create_plan_invalid_json_raises_planner_error():
    """Provider returns garbage → PlannerError raised."""
    mock_provider = MagicMock()
    mock_provider.complete = AsyncMock(return_value="not json at all !!!")
    mock_provider.__class__ = MagicMock

    with patch("ai.planner.get_provider", return_value=mock_provider):
        with pytest.raises(PlannerError, match="invalid JSON"):
            await create_plan(SAMPLE_IDEA)


@pytest.mark.asyncio
async def test_create_plan_schema_violation_raises_planner_error():
    """Provider returns valid JSON but wrong schema → PlannerError."""
    bad_plan = json.dumps({"summary": "ok", "framework": "vue", "tasks": []})
    mock_provider = MagicMock()
    mock_provider.complete = AsyncMock(return_value=bad_plan)
    mock_provider.__class__ = MagicMock

    with patch("ai.planner.get_provider", return_value=mock_provider):
        with pytest.raises(PlannerError):
            await create_plan(SAMPLE_IDEA)


@pytest.mark.asyncio
async def test_create_plan_empty_idea_raises():
    with pytest.raises(PlannerError, match="empty"):
        await create_plan("")


# ---------------------------------------------------------------------------
# generate_files — mocked provider
# ---------------------------------------------------------------------------

VALID_FILES_JSON = json.dumps(VALID_FILES_LIST)


@pytest.mark.asyncio
async def test_generate_files_uses_fallback_when_no_key():
    """When no key is set, must return deterministic fallback files."""
    with patch.dict(os.environ, {"GEMINI_API_KEY": "", "AI_MODEL": ""}, clear=False):
        result = await generate_files(SAMPLE_IDEA, VALID_PLAN_DICT)
    assert isinstance(result, FileListOutput)
    paths = [f.path for f in result.files]
    assert "src/App.jsx" in paths


@pytest.mark.asyncio
async def test_generate_files_success_with_mock_provider():
    """Provider returns valid JSON file array → FileListOutput returned."""
    mock_provider = MagicMock()
    mock_provider.complete = AsyncMock(return_value=VALID_FILES_JSON)
    mock_provider.__class__ = MagicMock

    with patch("ai.generator.get_provider", return_value=mock_provider):
        result = await generate_files(SAMPLE_IDEA, VALID_PLAN_DICT)

    assert isinstance(result, FileListOutput)
    assert len(result.files) == 6
    paths = [f.path for f in result.files]
    assert "package.json" in paths
    assert "src/App.jsx" in paths


@pytest.mark.asyncio
async def test_generate_files_provider_error_raises_generator_error():
    """Provider raises ProviderError → GeneratorError propagated."""
    mock_provider = MagicMock()
    mock_provider.complete = AsyncMock(side_effect=ProviderError("timeout"))
    mock_provider.__class__ = MagicMock

    with patch("ai.generator.get_provider", return_value=mock_provider):
        with pytest.raises(GeneratorError, match="timeout"):
            await generate_files(SAMPLE_IDEA, VALID_PLAN_DICT)


@pytest.mark.asyncio
async def test_generate_files_invalid_json_raises_generator_error():
    """Provider returns non-JSON → GeneratorError."""
    mock_provider = MagicMock()
    mock_provider.complete = AsyncMock(return_value="here are your files: ...")
    mock_provider.__class__ = MagicMock

    with patch("ai.generator.get_provider", return_value=mock_provider):
        with pytest.raises(GeneratorError, match="invalid JSON"):
            await generate_files(SAMPLE_IDEA, VALID_PLAN_DICT)


@pytest.mark.asyncio
async def test_generate_files_missing_required_file_raises_generator_error():
    """Provider omits required file → GeneratorError."""
    incomplete = [f for f in VALID_FILES_LIST if f["path"] != "src/App.jsx"]
    mock_provider = MagicMock()
    mock_provider.complete = AsyncMock(return_value=json.dumps(incomplete))
    mock_provider.__class__ = MagicMock

    with patch("ai.generator.get_provider", return_value=mock_provider):
        with pytest.raises(GeneratorError, match="missing required"):
            await generate_files(SAMPLE_IDEA, VALID_PLAN_DICT)


@pytest.mark.asyncio
async def test_generate_files_accepts_plan_output_object():
    """generate_files accepts PlanOutput in addition to dict."""
    plan = PlanOutput(
        summary="Test plan", framework="react-vite",
        tasks=[PlanTask(id="t1", title="T", description="D", status="pending")]
    )
    with patch.dict(os.environ, {"GEMINI_API_KEY": "", "AI_MODEL": ""}, clear=False):
        result = await generate_files(SAMPLE_IDEA, plan)
    assert isinstance(result, FileListOutput)


@pytest.mark.asyncio
async def test_generate_files_empty_idea_raises():
    with pytest.raises(GeneratorError, match="empty"):
        await generate_files("", VALID_PLAN_DICT)


# ---------------------------------------------------------------------------
# Provider routing
# ---------------------------------------------------------------------------

def test_get_provider_no_key_returns_fallback():
    with patch.dict(os.environ, {"GEMINI_API_KEY": "", "AI_MODEL": ""}, clear=False):
        provider = get_provider()
    assert isinstance(provider, FallbackProvider)


def test_get_provider_mock_mode_returns_fallback():
    with patch.dict(os.environ, {"GEMINI_API_KEY": "any-key", "AI_MODEL": "mock"}, clear=False):
        provider = get_provider()
    assert isinstance(provider, FallbackProvider)


def test_get_provider_gemini_key_returns_gemini():
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key-123", "AI_MODEL": ""}, clear=False):
        with patch("google.genai.Client"):
            provider = get_provider()
    assert isinstance(provider, GeminiProvider)
