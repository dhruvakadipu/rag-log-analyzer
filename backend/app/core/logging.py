import logging
from logging.handlers import RotatingFileHandler
from app.core.config import settings

def setup_logging():
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            RotatingFileHandler(
                "backend.log", 
                maxBytes=settings.max_log_size_mb * 1024 * 1024, 
                backupCount=settings.log_backup_count
            )
        ]
    )
    return logging.getLogger("log-copilot")

logger = setup_logging()
