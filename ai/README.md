# HackMate AI Engine

Module responsible for decomposing hackathon ideas into actionable architectures and synthesizing full React + Vite applications.

---

## Architecture & Interfaces

The AI module exposes two core public interfaces:

1. **`create_plan(idea: str) -> PlanOutput`**
   - Inputs: User prompt / idea string.
   - Outputs: Pydantic validated plan with `summary`, `framework: "react-vite"`, and an ordered list of tasks.

2. **`generate_files(idea: str, plan: PlanOutput | dict) -> FileListOutput`**
   - Inputs: Original idea and validated plan.
   - Outputs: Collection of `{ "path": str, "content": str }` models composing a functional React + Vite app.

---

## Security & Secrets

API keys (OpenAI, Gemini, Anthropic) are accessed strictly via environment variables (`OPENAI_API_KEY`, `GEMINI_API_KEY`) and are never hard-coded or logged.

When no LLM keys are supplied, the module falls back to deterministic mock generators for offline hackathon testing.

---

## Local Development & Testing

```powershell
cd ai
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest
```
