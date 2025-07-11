"""
Logging configuration for the web scraper project.
"""
import logging
import logging.config
import os
from typing import Dict, Any


def setup_logging(log_level: str = "INFO", log_file: str = None) -> None:
    """
    Set up logging configuration for the application.
    
    Args:
        log_level: The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file. If None, logs only to console
    """
    config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "simple": {
                "format": "%(levelname)s - %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "simple",
                "stream": "ext://sys.stdout"
            }
        },
        "loggers": {
            "scraper": {
                "level": log_level,
                "handlers": ["console"],
                "propagate": False
            }
        },
        "root": {
            "level": log_level,
            "handlers": ["console"]
        }
    }
    
    # Add file handler if log_file is specified
    if log_file:
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        config["handlers"]["file"] = {
            "class": "logging.FileHandler",
            "level": log_level,
            "formatter": "detailed",
            "filename": log_file,
            "mode": "a"
        }
        config["loggers"]["scraper"]["handlers"].append("file")
        config["root"]["handlers"].append("file")
    
    logging.config.dictConfig(config)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the given name.
    
    Args:
        name: The name of the logger (usually __name__)
        
    Returns:
        A configured logger instance
    """
    return logging.getLogger(f"scraper.{name}")
