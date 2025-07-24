"""Logging setup and configuration for DMS"""

import logging
import logging.handlers
import sys
import time
from pathlib import Path
from typing import Optional
from dms.config import DMSConfig, LoggingConfig


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record):
        # Add color to levelname
        if record.levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
            )
        
        return super().format(record)


def setup_logging(config: Optional[DMSConfig] = None) -> logging.Logger:
    """
    Setup logging configuration based on DMS config
    
    Args:
        config: DMS configuration object. If None, loads default config.
    
    Returns:
        Configured logger instance
    """
    if config is None:
        config = DMSConfig.load()
    
    logging_config = config.logging
    
    # Create root logger
    logger = logging.getLogger('dms')
    logger.setLevel(getattr(logging, logging_config.level.upper()))
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Setup file logging if enabled
    if logging_config.file_enabled:
        _setup_file_logging(logger, config, logging_config)
    
    # Setup console logging if enabled
    if logging_config.console_enabled:
        _setup_console_logging(logger, logging_config)
    
    # Prevent propagation to root logger to avoid duplicate messages
    logger.propagate = False
    
    return logger


def _setup_file_logging(logger: logging.Logger, config: DMSConfig, logging_config: LoggingConfig):
    """Setup file logging with rotation"""
    # Ensure logs directory exists
    logs_dir = config.logs_path
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Main log file
    log_file = logs_dir / "dms.log"
    
    # Create rotating file handler
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=logging_config.max_file_size,
        backupCount=logging_config.backup_count,
        encoding='utf-8'
    )
    
    # Set formatter for file output (no colors)
    file_formatter = logging.Formatter(logging_config.format)
    file_handler.setFormatter(file_formatter)
    
    # Set level for file handler
    file_handler.setLevel(getattr(logging, logging_config.level.upper()))
    
    logger.addHandler(file_handler)
    
    # Create separate error log file
    error_log_file = logs_dir / "dms_errors.log"
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_file,
        maxBytes=logging_config.max_file_size,
        backupCount=logging_config.backup_count,
        encoding='utf-8'
    )
    
    error_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    )
    error_handler.setFormatter(error_formatter)
    error_handler.setLevel(logging.ERROR)
    
    logger.addHandler(error_handler)


def _setup_console_logging(logger: logging.Logger, logging_config: LoggingConfig):
    """Setup console logging with colors"""
    console_handler = logging.StreamHandler(sys.stdout)
    
    # Use colored formatter for console
    console_formatter = ColoredFormatter(
        "%(levelname)s - %(message)s"
    )
    console_handler.setFormatter(console_formatter)
    
    # Set level for console handler
    console_handler.setLevel(getattr(logging, logging_config.level.upper()))
    
    logger.addHandler(console_handler)


def get_logger(name: str = 'dms') -> logging.Logger:
    """Get a logger instance with the specified name"""
    return logging.getLogger(name)


class LoggingContext:
    """Context manager for temporary logging level changes"""
    
    def __init__(self, logger: logging.Logger, level: str):
        self.logger = logger
        self.new_level = getattr(logging, level.upper())
        self.old_level = None
    
    def __enter__(self):
        self.old_level = self.logger.level
        self.logger.setLevel(self.new_level)
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.setLevel(self.old_level)


def log_function_call(logger: Optional[logging.Logger] = None):
    """Decorator to log function calls with parameters and execution time"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            nonlocal logger
            if logger is None:
                logger = get_logger()
            
            # Log function entry
            func_name = f"{func.__module__}.{func.__name__}"
            logger.debug(f"Entering {func_name}")
            
            import time
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.debug(f"Completed {func_name} in {execution_time:.3f}s")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"Failed {func_name} after {execution_time:.3f}s: {e}")
                raise
        
        return wrapper
    return decorator


def log_performance(operation: str, logger: Optional[logging.Logger] = None):
    """Context manager to log performance of operations"""
    class PerformanceLogger:
        def __init__(self, operation: str, logger: logging.Logger):
            self.operation = operation
            self.logger = logger
            self.start_time = None
        
        def __enter__(self):
            self.start_time = time.time()
            self.logger.debug(f"Starting {self.operation}")
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            import time
            execution_time = time.time() - self.start_time
            if exc_type is None:
                self.logger.info(f"Completed {self.operation} in {execution_time:.3f}s")
            else:
                self.logger.error(f"Failed {self.operation} after {execution_time:.3f}s")
    
    if logger is None:
        logger = get_logger()
    
    return PerformanceLogger(operation, logger)


def setup_cli_logging(verbose: bool = False) -> logging.Logger:
    """Setup logging specifically for CLI usage"""
    # Load config
    try:
        config = DMSConfig.load()
    except Exception:
        # Fallback to basic logging if config fails
        logging.basicConfig(
            level=logging.DEBUG if verbose else logging.INFO,
            format="%(levelname)s - %(message)s"
        )
        return logging.getLogger('dms')
    
    # Override console level based on verbose flag
    if verbose:
        config.logging.level = "DEBUG"
        config.logging.console_enabled = True
    
    return setup_logging(config)


def log_system_info(logger: logging.Logger):
    """Log system information for debugging"""
    import platform
    import sys
    from pathlib import Path
    
    logger.info("=== DMS System Information ===")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Platform: {platform.platform()}")
    logger.info(f"Architecture: {platform.architecture()}")
    logger.info(f"Working directory: {Path.cwd()}")
    logger.info(f"DMS version: {_get_dms_version()}")
    logger.info("=" * 30)


def _get_dms_version() -> str:
    """Get DMS version from setup.py or package info"""
    try:
        # Try to get version from installed package
        import pkg_resources
        return pkg_resources.get_distribution('dms').version
    except:
        # Fallback to reading setup.py
        try:
            setup_py = Path(__file__).parent.parent / "setup.py"
            if setup_py.exists():
                content = setup_py.read_text()
                import re
                match = re.search(r'version=["\']([^"\']+)["\']', content)
                if match:
                    return match.group(1)
        except:
            pass
        
        return "unknown"