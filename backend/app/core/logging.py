import logging
import sys
from app.config import settings


def setup_logging():
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    # Quiet overly chatty loggers in dev
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)


logger = logging.getLogger("hackmate.core")
