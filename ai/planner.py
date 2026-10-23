import os
from ai.models import PlanOutput, PlanTask


def create_plan(idea: str) -> PlanOutput:
    """Decomposes a user hackathon idea into a structured execution plan.

    Args:
        idea: Raw user hackathon idea text.

    Returns:
        PlanOutput containing summary, framework ('react-vite'), and task list.
    """
    clean_idea = idea.strip()
    summary = f"Autonomous generation plan for: {clean_idea[:75]}..."

    tasks = [
        PlanTask(
            id="task-1",
            title="Design System & Dependencies",
            description="Configure Vite build toolchain, Tailwind utility styling, and icon sets.",
            status="completed"
        ),
        PlanTask(
            id="task-2",
            title="Core State & Layout Synthesis",
            description="Generate responsive navigation shell and application state management.",
            status="completed"
        ),
        PlanTask(
            id="task-3",
            title="Feature View Implementation",
            description=f"Synthesize custom domain components tailored for: '{clean_idea[:60]}'.",
            status="pending"
        ),
        PlanTask(
            id="task-4",
            title="Assembly & Integration Verification",
            description="Assemble all generated modules into src/App.jsx and verify imports.",
            status="pending"
        )
    ]

    return PlanOutput(
        summary=summary,
        framework="react-vite",
        tasks=tasks
    )
