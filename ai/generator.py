"""
ai/generator.py — HackMate AI Code Generator

Public interface (called by backend via ai_client.py):
    async def generate_files(idea: str, plan: Union[PlanOutput, dict]) -> FileListOutput

Behaviour:
  - Calls the configured LLM provider (Gemini free-tier by default).
  - Parses and validates the structured JSON file array response.
  - Sanitises all file paths (rejects traversal, absolute paths, unsafe names).
  - Falls back to a minimal deterministic React+Vite template when no provider
    key is configured (clearly identified as fallback).
  - Raises GeneratorError on unrecoverable failures.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Union

from ai.models import FileListOutput, GeneratedFileModel, PlanOutput
from ai.prompts import FILES_SYSTEM, FILES_USER
from ai.provider import FallbackProvider, ProviderError, _FALLBACK_SENTINEL, get_provider

logger = logging.getLogger(__name__)

# Required files that must be present in every generated project
_REQUIRED_PATHS = {
    "package.json",
    "index.html",
    "vite.config.js",
    "src/main.jsx",
    "src/App.jsx",
    "src/index.css",
}

# Disallowed path patterns — catches traversal, absolute Unix, Windows drive roots
_UNSAFE_PATTERNS = re.compile(r"\.\.|^/|^[A-Za-z]:[/\\]")


class GeneratorError(Exception):
    """Raised when file generation fails and cannot be recovered."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _strip_json_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _sanitise_path(path: str) -> str:
    """Normalise and validate a file path from the LLM.

    Returns the cleaned path or raises ValueError if it is unsafe.
    Rejects: path traversal (..),  absolute Unix paths (/...),
             Windows drive paths (C:\... or C:/...), null bytes.
    """
    if not path or not path.strip():
        raise ValueError(f"Unsafe file path rejected: empty path")
    if "\x00" in path:
        raise ValueError(f"Unsafe file path rejected: null byte in path")

    # Check raw path for Windows drive roots BEFORE normalisation
    if _UNSAFE_PATTERNS.search(path):
        raise ValueError(f"Unsafe file path rejected: '{path}'")

    # Normalise separators to forward-slash and strip leading slashes
    p = path.strip().replace("\\", "/").lstrip("/")

    # Re-check after normalisation
    if _UNSAFE_PATTERNS.search(p):
        raise ValueError(f"Unsafe file path rejected: '{path}'")

    # Walk segments, rejecting any .. traversal
    parts = p.split("/")
    safe_parts = []
    for part in parts:
        if part in ("", "."):
            continue
        if part == "..":
            raise ValueError(f"Unsafe file path rejected: traversal in '{path}'")
        safe_parts.append(part)
    if not safe_parts:
        raise ValueError(f"Path resolves to empty after sanitisation: '{path}'")
    return "/".join(safe_parts)


def _validate_files(data: list) -> list[GeneratedFileModel]:
    """Validate parsed file array and return GeneratedFileModel list.

    Raises ValueError on schema violations.
    """
    if not isinstance(data, list) or len(data) == 0:
        raise ValueError("File list JSON root must be a non-empty array.")

    files: list[GeneratedFileModel] = []
    seen_paths: set[str] = set()

    for i, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"File entry {i} is not an object.")
        raw_path = item.get("path", "")
        content = item.get("content", "")
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise ValueError(f"File entry {i} has missing or empty 'path'.")
        if not isinstance(content, str):
            raise ValueError(f"File entry {i} has non-string 'content'.")
        safe_path = _sanitise_path(raw_path)
        if safe_path in seen_paths:
            logger.warning("Duplicate file path '%s' skipped.", safe_path)
            continue
        seen_paths.add(safe_path)
        files.append(GeneratedFileModel(path=safe_path, content=content))

    # Check required files are present
    present = {f.path for f in files}
    missing = _REQUIRED_PATHS - present
    if missing:
        raise ValueError(f"Generated files are missing required paths: {missing}")

    return files


def _fallback_files(idea: str) -> FileListOutput:
    """Deterministic fallback file set. Used only when no LLM key is set."""
    clean = idea.strip()

    package_json = """{
  "name": "hackmate-generated-app",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "lucide-react": "^0.453.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.2",
    "vite": "^5.4.9"
  }
}"""

    vite_config = """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true
  }
})"""

    index_html = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>HackMate App</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>"""

    main_jsx = """import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)"""

    index_css = """* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background-color: #090d16;
  color: #f1f5f9;
  min-height: 100vh;
}"""

    app_jsx = f"""import React, {{ useState }} from 'react';

// [FALLBACK] Deterministic template — no LLM key configured.
// Set GEMINI_API_KEY in .env to enable real AI code generation.
export default function App() {{
  const [count, setCount] = useState(0);
  return (
    <main style={{{{ padding: '3rem 1.5rem', maxWidth: '800px', margin: '0 auto', textAlign: 'center' }}}}>
      <div style={{{{ display: 'inline-block', background: 'rgba(139,92,246,0.1)', border: '1px solid #8b5cf6',
          padding: '0.3rem 0.9rem', borderRadius: '9999px', color: '#a78bfa', fontSize: '0.8rem',
          marginBottom: '1rem' }}}}>
        ⚡ HackMate Fallback Template
      </div>
      <h1 style={{{{ fontSize: '2rem', fontWeight: 800, marginBottom: '1rem',
          background: 'linear-gradient(to right, #fff, #a78bfa)',
          WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}}}>
        Autonomous Hackathon Prototype
      </h1>
      <section style={{{{ background: '#111827', border: '1px solid #1f2937', borderRadius: '1rem',
          padding: '1.5rem', marginBottom: '1.5rem', textAlign: 'left' }}}}>
        <p style={{{{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#9ca3af', marginBottom: '0.5rem' }}}}>
          Original Prompt
        </p>
        <p style={{{{ fontSize: '1.1rem', color: '#e5e7eb', lineHeight: 1.6 }}}}>"{clean}"</p>
      </section>
      <button
        onClick={{() => setCount(c => c + 1)}}
        style={{{{ backgroundColor: '#8b5cf6', color: '#fff', border: 'none',
            padding: '0.75rem 1.5rem', borderRadius: '0.5rem', fontSize: '1rem',
            fontWeight: 600, cursor: 'pointer' }}}}>
        Interactions: {{count}}
      </button>
    </main>
  );
}}"""

    return FileListOutput(
        files=[
            GeneratedFileModel(path="package.json", content=package_json),
            GeneratedFileModel(path="vite.config.js", content=vite_config),
            GeneratedFileModel(path="index.html", content=index_html),
            GeneratedFileModel(path="src/main.jsx", content=main_jsx),
            GeneratedFileModel(path="src/index.css", content=index_css),
            GeneratedFileModel(path="src/App.jsx", content=app_jsx),
        ]
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def generate_files(
    idea: str,
    plan: Union[PlanOutput, dict],
) -> FileListOutput:
    """Generate a runnable React + Vite file tree for the given idea and plan.

    Args:
        idea: Raw user idea text.
        plan: PlanOutput instance or dict with 'summary' key.

    Returns:
        FileListOutput — validated list of GeneratedFileModel (path + content).

    Raises:
        GeneratorError: If the provider fails and cannot be recovered.
    """
    if not idea or not idea.strip():
        raise GeneratorError("Idea must not be empty.")

    # Extract summary from plan (accepts both PlanOutput and raw dict)
    if isinstance(plan, PlanOutput):
        plan_summary = plan.summary
    elif isinstance(plan, dict):
        plan_summary = str(plan.get("summary", idea.strip()[:60]))
    else:
        plan_summary = idea.strip()[:60]

    provider = get_provider()
    logger.info("generate_files() using provider: %s", provider.name)

    # Fallback path
    if isinstance(provider, FallbackProvider):
        logger.info("Fallback provider active — returning deterministic file set.")
        return _fallback_files(idea)

    prompt = (
        f"{FILES_SYSTEM}\n\n"
        f"{FILES_USER.format(idea=idea.strip(), plan_summary=plan_summary)}"
    )

    try:
        raw = await provider.complete(prompt)
    except ProviderError as exc:
        raise GeneratorError(f"AI provider failed during file generation: {exc}") from exc

    if raw == _FALLBACK_SENTINEL:
        return _fallback_files(idea)

    cleaned = _strip_json_fences(raw)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error("Generator: invalid JSON from provider: %s\nRaw: %.500s", exc, cleaned)
        raise GeneratorError(f"Provider returned invalid JSON: {exc}") from exc

    try:
        validated = _validate_files(data)
    except ValueError as exc:
        logger.error("Generator: schema validation failed: %s", exc)
        raise GeneratorError(f"Provider files failed schema validation: {exc}") from exc

    return FileListOutput(files=validated)
