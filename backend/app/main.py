from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.core.logging import setup_logging, logger
from app.core.errors import HackMateException, SecurityViolationError, InvalidStateTransitionError, RunnerUnavailableError
from app.db.session import init_database
from app.services.orchestrator import orchestration_service
from app.api.router import api_v2_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    logger.info("Starting HackMate Core Application Gateway...")
    
    # 1. Initialize DB tables
    await init_database()
    logger.info("Database schema initialized successfully.")

    # 2. Recover any dangling projects from previous interrupted runs
    recovered = await orchestration_service.recover_interrupted_projects()
    if recovered > 0:
        logger.info(f"Recovered {recovered} dangling projects from prior interrupted runs.")

    # 3. Ensure workspace directory exists
    workspace_path = settings.resolved_workspace_path
    logger.info(f"Workspace root verified at: {workspace_path}")

    yield

    # Shutdown
    logger.info("Shutting down HackMate Core Application Gateway...")


def create_app() -> FastAPI:
    app = FastAPI(
        title="HackMate Core API",
        version="2.0.0",
        description="Autonomous AI-Powered Website Generation Platform Engine",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.parsed_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception Handlers
    @app.exception_handler(HackMateException)
    async def handle_hackmate_exception(request: Request, exc: HackMateException):
        logger.warning(f"Domain exception on {request.url.path}: {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.__class__.__name__, "message": exc.message}
        )

    # Mount API Router
    app.include_router(api_v2_router, prefix=settings.API_V2_PREFIX)

    return app


app = create_app()
