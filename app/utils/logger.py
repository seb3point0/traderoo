"""
Logging configuration using loguru
"""
import sys
from pathlib import Path
from loguru import logger
from app.config import get_settings

settings = get_settings()


def setup_logger():
    """Configure logger with file and console output"""
    
    # Remove default handler
    logger.remove()
    
    # Create logs directory
    log_dir = Path(settings.log_file).parent
    log_dir.mkdir(exist_ok=True)
    
    # Console handler with color
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=settings.log_level,
        colorize=True,
    )
    
    # File handler with rotation
    logger.add(
        settings.log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=settings.log_level,
        rotation="100 MB",
        retention="30 days",
        compression="zip",
    )
    
    return logger


# Initialize logger
log = setup_logger()

