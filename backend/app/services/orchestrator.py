import asyncio
from typing import Dict, Optional, List, Any
from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import AsyncSessionLocal
from app.db.base import utc_now
from app.models.project import Project, ProjectStatus
from app.models.task import Task, TaskStatus
from app.models.file import GeneratedFile
from app.models.build import BuildRun, BuildLogChunk, BuildStatus, BuildTrigger
from app.services.workspace import workspace_service
from app.services.sse_manager import sse_manager
from app.services.runner_service import runner_service
from app.services.ai_service import ai_service, GeneratedFileSchema
from app.services.integrations.firecrawl_service import firecrawl_service
from app.services.integrations.n8n_service import n8n_service
from app.core.errors import InvalidStateTransitionError, ProjectNotFoundError
from app.core.logging import logger
from app.config import settings


def _status_str(status_val: Any) -> str:
    return status_val.value if hasattr(status_val, "value") else str(status_val)


class OrchestrationService:
    def __init__(self):
        # Maps project_id -> asyncio.Task
        self._running_tasks: Dict[str, asyncio.Task] = {}
        # Maps project_id -> asyncio.Event
        self._cancel_events: Dict[str, asyncio.Event] = {}

    def is_project_running(self, project_id: str) -> bool:
        task = self._running_tasks.get(project_id)
        return bool(task and not task.done())

    async def start_pipeline(self, project_id: str) -> None:
        """Starts the autonomous generation pipeline as an async background task."""
        if self.is_project_running(project_id):
            raise InvalidStateTransitionError(
                current_status="IN_PROGRESS",
                target_status="START"
            )

        cancel_event = asyncio.Event()
        self._cancel_events[project_id] = cancel_event

        task = asyncio.create_task(
            self._execute_pipeline(project_id, cancel_event)
        )
        self._running_tasks[project_id] = task

        # Add done callback to clean up registry
        def _cleanup(t):
            self._running_tasks.pop(project_id, None)
            self._cancel_events.pop(project_id, None)

        task.add_done_callback(_cleanup)

    async def cancel_pipeline(self, project_id: str) -> bool:
        """Signals cancellation to an active background job."""
        cancel_event = self._cancel_events.get(project_id)
        task = self._running_tasks.get(project_id)

        if not cancel_event or not task or task.done():
            return False

        logger.info(f"Triggering cancellation for project {project_id}")
        cancel_event.set()
        task.cancel()

        # Update database state to CANCELLED
        async with AsyncSessionLocal() as session:
            project = await session.get(Project, project_id)
            if project:
                prev = _status_str(project.status)
                project.status = ProjectStatus.CANCELLED
                project.error_message = "Generation was cancelled by the user."
                project.updated_at = utc_now()
                await session.commit()
                await sse_manager.emit_status(
                    project_id, prev, ProjectStatus.CANCELLED.value, "Cancelled by user"
                )

        return True

    async def recover_interrupted_projects(self) -> int:
        """
        On server startup, scans for projects stuck in non-terminal states
        from an unexpected server termination and marks them FAILED.
        """
        active_states = [
            ProjectStatus.ANALYZING,
            ProjectStatus.PLANNING,
            ProjectStatus.GENERATING,
            ProjectStatus.WRITING_FILES,
            ProjectStatus.BUILDING,
            ProjectStatus.REPAIRING,
        ]

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Project).where(Project.status.in_(active_states))
            )
            interrupted = result.scalars().all()
            for p in interrupted:
                logger.warning(f"Recovering interrupted project {p.id} from state {p.status}")
                p.status = ProjectStatus.FAILED
                p.error_message = "Generation was interrupted by a server restart. You can re-trigger the build."
                p.updated_at = utc_now()

            if interrupted:
                await session.commit()
            return len(interrupted)

    async def _execute_pipeline(self, project_id: str, cancel_event: asyncio.Event):
        """The complete core generation and build orchestration state machine."""
        logger.info(f"Initiating pipeline for project {project_id}")
        try:
            # 1. Verification & STAGE 1: ANALYZING State
            async with AsyncSessionLocal() as session:
                project = await session.get(Project, project_id)
                if not project:
                    raise ProjectNotFoundError(project_id)

                prev_status = _status_str(project.status)
                project.status = ProjectStatus.ANALYZING
                project.updated_at = utc_now()
                await session.commit()
                await sse_manager.emit_status(project_id, prev_status, ProjectStatus.ANALYZING.value)

            if cancel_event.is_set():
                return

            # Optional Firecrawl reference scraping with SSRF guard
            reference_guidance = None
            if project.reference_url:
                try:
                    reference_guidance = await firecrawl_service.scrape_reference_design(project.reference_url)
                except Exception as e:
                    logger.warning(f"Optional Firecrawl scraping failed, proceeding with prompt only: {e}")

            analysis = await ai_service.analyze_requirements(
                prompt=project.prompt,
                reference_url=project.reference_url,
                reference_guidance=reference_guidance
            )

            # 2. STAGE 2: PLANNING State
            async with AsyncSessionLocal() as session:
                project = await session.get(Project, project_id)
                project.status = ProjectStatus.PLANNING
                project.updated_at = utc_now()
                await session.commit()
                await sse_manager.emit_status(project_id, ProjectStatus.ANALYZING.value, ProjectStatus.PLANNING.value)

            plan = await ai_service.generate_plan(project.prompt, analysis)

            # Persist tasks to DB and emit SSE
            async with AsyncSessionLocal() as session:
                for t in plan.tasks:
                    db_task = Task(
                        project_id=project_id,
                        sequence_order=t.sequence_order,
                        title=t.title,
                        description=t.description,
                        status=TaskStatus.PENDING,
                    )
                    session.add(db_task)
                    await sse_manager.emit_task_updated(
                        project_id=project_id,
                        task_id=t.id,
                        title=t.title,
                        status=TaskStatus.PENDING.value,
                        order=t.sequence_order
                    )
                await session.commit()

            if cancel_event.is_set():
                return

            # 3. STAGE 3: GENERATING State
            async with AsyncSessionLocal() as session:
                project = await session.get(Project, project_id)
                project.status = ProjectStatus.GENERATING
                project.updated_at = utc_now()
                await session.commit()
                await sse_manager.emit_status(project_id, ProjectStatus.PLANNING.value, ProjectStatus.GENERATING.value)

            generated_files = await ai_service.generate_codebase(project.prompt, plan)

            if cancel_event.is_set():
                return

            # 4. WRITING_FILES State
            async with AsyncSessionLocal() as session:
                project = await session.get(Project, project_id)
                project.status = ProjectStatus.WRITING_FILES
                project.updated_at = utc_now()
                await session.commit()
                await sse_manager.emit_status(project_id, ProjectStatus.GENERATING.value, ProjectStatus.WRITING_FILES.value)

                # Write files to disk and DB
                total_files = len(generated_files)
                for idx, gf in enumerate(generated_files):
                    file_size = workspace_service.write_file(project_id, gf.file_path, gf.content)
                    db_file = GeneratedFile(
                        project_id=project_id,
                        file_path=gf.file_path,
                        content=gf.content,
                        language=gf.language,
                        file_size_bytes=file_size,
                    )
                    session.add(db_file)
                    await sse_manager.emit_file_written(
                        project_id=project_id,
                        file_path=gf.file_path,
                        file_size=file_size,
                        index=idx + 1,
                        total=total_files
                    )

                await session.commit()

            if cancel_event.is_set():
                return

            # 5. BUILDING & BOUNDED REPAIR LOOP
            project_dir = workspace_service.get_project_dir(project_id)
            build_success = False
            attempt = 0

            while attempt <= settings.MAX_REPAIR_ATTEMPTS and not build_success:
                attempt += 1
                trigger = BuildTrigger.INITIAL_BUILD if attempt == 1 else BuildTrigger.REPAIR_ATTEMPT

                # Update state
                target_status = ProjectStatus.BUILDING if attempt == 1 else ProjectStatus.REPAIRING
                async with AsyncSessionLocal() as session:
                    project = await session.get(Project, project_id)
                    current_status_str = _status_str(project.status)
                    project.status = target_status
                    project.current_repair_iteration = attempt - 1
                    project.updated_at = utc_now()

                    build_run = BuildRun(
                        project_id=project_id,
                        attempt_number=attempt,
                        trigger_type=trigger,
                        status=BuildStatus.RUNNING,
                    )
                    session.add(build_run)
                    await session.commit()
                    await session.refresh(build_run)
                    build_run_id = build_run.id

                    await sse_manager.emit_status(project_id, current_status_str, target_status.value)

                # Callback for streaming build logs chunk-by-chunk
                async def handle_log_chunk(stream: str, chunk: str):
                    await sse_manager.emit_build_log(project_id, build_run_id, stream, chunk)
                    async with AsyncSessionLocal() as log_session:
                        log_entry = BuildLogChunk(
                            build_run_id=build_run_id,
                            stream=stream,
                            message=chunk,
                        )
                        log_session.add(log_entry)
                        await log_session.commit()

                # Execute sandbox build
                success, exit_code, error_summary = await runner_service.execute_build(
                    project_id=project_id,
                    workspace_path=project_dir,
                    on_log_chunk=handle_log_chunk,
                    cancellation_token=cancel_event,
                )

                # Update build run in DB
                async with AsyncSessionLocal() as session:
                    db_build = await session.get(BuildRun, build_run_id)
                    if db_build:
                        db_build.status = BuildStatus.SUCCESS if success else BuildStatus.FAILED
                        db_build.exit_code = exit_code
                        db_build.error_summary = error_summary
                        db_build.completed_at = utc_now()
                        await session.commit()

                if success:
                    build_success = True
                    break

                if attempt <= settings.MAX_REPAIR_ATTEMPTS:
                    logger.info(f"Build failed for {project_id}, running repair attempt {attempt} of {settings.MAX_REPAIR_ATTEMPTS}...")
                    await sse_manager.emit_repair_attempt(
                        project_id=project_id,
                        iteration=attempt,
                        max_iterations=settings.MAX_REPAIR_ATTEMPTS,
                        reason=error_summary[:200]
                    )

                    repaired_files = await ai_service.repair_codebase(
                        project.prompt, generated_files, error_summary, attempt
                    )
                    # Revalidate all repaired files
                    validated_repaired = ai_service.validate_codebase(repaired_files)
                    for rf in validated_repaired:
                        workspace_service.write_file(project_id, rf.file_path, rf.content)
                    generated_files = validated_repaired

            # 6. Final State Evaluation & SSE Completion
            async with AsyncSessionLocal() as session:
                project = await session.get(Project, project_id)
                final_prev_str = _status_str(project.status)
                if build_success:
                    project.status = ProjectStatus.READY
                    project.preview_url = f"/api/v2/projects/{project_id}/preview/index.html"
                    project.error_message = None
                    await session.execute(
                        update(Task)
                        .where(Task.project_id == project_id)
                        .values(status=TaskStatus.COMPLETED, completed_at=utc_now())
                    )
                else:
                    project.status = ProjectStatus.FAILED
                    project.error_message = f"Build failed after {attempt} attempts. Check build logs for details."

                project.updated_at = utc_now()
                await session.commit()
                await sse_manager.emit_status(project_id, final_prev_str, _status_str(project.status))
                await sse_manager.emit_build_completed(
                    project_id=project_id,
                    success=build_success,
                    preview_url=project.preview_url,
                    error=project.error_message
                )

                # Optional n8n workflow notification
                try:
                    await n8n_service.send_event(
                        event_type="project.completed",
                        project_id=project_id,
                        data={
                            "title": project.title,
                            "status": _status_str(project.status),
                            "preview_url": project.preview_url,
                            "error": project.error_message,
                            "repair_iterations": project.current_repair_iteration,
                        }
                    )
                except Exception as e:
                    logger.warning(f"Optional n8n webhook notification failed: {e}")

        except asyncio.CancelledError:
            logger.info(f"Pipeline task for {project_id} was cancelled.")
        except Exception as e:
            logger.error(f"Error in pipeline execution for {project_id}: {str(e)}", exc_info=True)
            async with AsyncSessionLocal() as session:
                project = await session.get(Project, project_id)
                if project:
                    project.status = ProjectStatus.FAILED
                    project.error_message = str(e)
                    project.updated_at = utc_now()
                    await session.commit()
                    await sse_manager.emit_status(project_id, "ERROR", ProjectStatus.FAILED.value, str(e))
                    await sse_manager.emit_build_completed(
                        project_id=project_id,
                        success=False,
                        error=str(e)
                    )


orchestration_service = OrchestrationService()
