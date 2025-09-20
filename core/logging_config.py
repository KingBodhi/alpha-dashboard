"""
Alpha Protocol Network - Logging Configuration
Structured logging setup with proper formatters and handlers.
"""
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime

def setup_logging(log_level: str = "INFO", log_dir: Path = None) -> logging.Logger:
    """
    Setup structured logging for APN with file rotation and console output.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_dir: Directory for log files (default: ~/.apn/logs)
    
    Returns:
        Configured logger instance
    """
    if log_dir is None:
        log_dir = Path.home() / ".apn" / "logs"
    
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    log_file = log_dir / f"apn_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    
    # Create APN-specific logger
    apn_logger = logging.getLogger("apn")
    apn_logger.info(f"Logging initialized - Level: {log_level}, Dir: {log_dir}")
    
    return apn_logger

def get_logger(name: str) -> logging.Logger:
    """Get a logger with APN prefix"""
    return logging.getLogger(f"apn.{name}")
