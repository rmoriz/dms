"""Comprehensive error handling for DMS"""

import logging
import time
import functools
from typing import Optional, Callable, Any, Type, Union, List
from pathlib import Path


class DMSError(Exception):
    """Base exception for DMS-related errors"""
    
    def __init__(self, message: str, recovery_suggestion: Optional[str] = None, 
                 original_error: Optional[Exception] = None):
        super().__init__(message)
        self.message = message
        self.recovery_suggestion = recovery_suggestion
        self.original_error = original_error
    
    def __str__(self) -> str:
        result = self.message
        if self.recovery_suggestion:
            result += f"\n💡 Suggestion: {self.recovery_suggestion}"
        return result


class ConfigurationError(DMSError):
    """Configuration-related errors"""
    pass


class PDFProcessingError(DMSError):
    """PDF processing-related errors"""
    pass


class CorruptedPDFError(PDFProcessingError):
    """Corrupted or unreadable PDF file"""
    
    def __init__(self, file_path: str, original_error: Optional[Exception] = None):
        message = f"PDF file is corrupted or unreadable: {file_path}"
        recovery_suggestion = (
            "Try opening the PDF in a PDF viewer to verify it's not corrupted. "
            "If the file is password-protected, remove the password first."
        )
        super().__init__(message, recovery_suggestion, original_error)
        self.file_path = file_path


class OCRError(PDFProcessingError):
    """OCR processing errors"""
    
    def __init__(self, file_path: str, original_error: Optional[Exception] = None):
        message = f"OCR processing failed for: {file_path}"
        recovery_suggestion = (
            "Ensure Tesseract is installed and configured correctly. "
            "Check if the PDF contains readable text or images."
        )
        super().__init__(message, recovery_suggestion, original_error)
        self.file_path = file_path


class LLMAPIError(DMSError):
    """LLM API-related errors"""
    
    def __init__(self, message: str, model: Optional[str] = None, 
                 status_code: Optional[int] = None, original_error: Optional[Exception] = None):
        recovery_suggestion = self._get_recovery_suggestion(status_code)
        super().__init__(message, recovery_suggestion, original_error)
        self.model = model
        self.status_code = status_code
    
    def _get_recovery_suggestion(self, status_code: Optional[int]) -> str:
        if status_code == 401:
            return "Check your OpenRouter API key in the configuration."
        elif status_code == 429:
            return "Rate limit exceeded. Wait a moment and try again."
        elif status_code == 503:
            return "Service temporarily unavailable. Try again later or use a different model."
        elif status_code and 500 <= status_code < 600:
            return "Server error. Try again later or use a different model."
        else:
            return "Check your internet connection and API configuration."


class VectorStoreError(DMSError):
    """Vector store-related errors"""
    pass


class DatabaseError(DMSError):
    """Database-related errors"""
    pass


class RetryableError(DMSError):
    """Base class for errors that can be retried"""
    pass


class TransientAPIError(RetryableError, LLMAPIError):
    """Transient API errors that can be retried"""
    pass


class TransientNetworkError(RetryableError):
    """Transient network errors that can be retried"""
    pass


def retry_on_failure(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (TransientAPIError, TransientNetworkError),
    logger: Optional[logging.Logger] = None
):
    """
    Decorator to retry function calls on specific exceptions
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff_factor: Factor to multiply delay by after each retry
        exceptions: Tuple of exception types to retry on
        logger: Logger instance for retry messages
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        break
                    
                    if logger:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}. "
                            f"Retrying in {current_delay:.1f}s..."
                        )
                    
                    time.sleep(current_delay)
                    current_delay *= backoff_factor
                except Exception as e:
                    # Non-retryable exception, re-raise immediately
                    raise e
            
            # All retries exhausted
            if logger:
                logger.error(f"All {max_retries + 1} attempts failed for {func.__name__}")
            raise last_exception
        
        return wrapper
    return decorator


def handle_pdf_errors(func: Callable) -> Callable:
    """Decorator to handle common PDF processing errors"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Try to extract file path from args/kwargs
            file_path = None
            if args and isinstance(args[0], (str, Path)):
                file_path = str(args[0])
            elif 'file_path' in kwargs:
                file_path = str(kwargs['file_path'])
            elif 'pdf_path' in kwargs:
                file_path = str(kwargs['pdf_path'])
            
            # Convert common exceptions to DMS exceptions
            error_message = str(e).lower()
            
            if any(keyword in error_message for keyword in [
                'corrupted', 'damaged', 'invalid pdf', 'not a pdf', 'encrypted'
            ]):
                raise CorruptedPDFError(file_path or "unknown", e)
            elif any(keyword in error_message for keyword in [
                'tesseract', 'ocr', 'image processing'
            ]):
                raise OCRError(file_path or "unknown", e)
            elif any(keyword in error_message for keyword in [
                'permission denied', 'access denied', 'file not found'
            ]):
                raise PDFProcessingError(
                    f"Cannot access file: {file_path or 'unknown'}",
                    "Check file permissions and ensure the file exists.",
                    e
                )
            else:
                # Generic PDF processing error
                raise PDFProcessingError(
                    f"Failed to process PDF: {file_path or 'unknown'}",
                    "Ensure the file is a valid PDF and not corrupted.",
                    e
                )
    
    return wrapper


def handle_api_errors(func: Callable) -> Callable:
    """Decorator to handle API-related errors"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            import requests
            
            if isinstance(e, requests.exceptions.RequestException):
                if isinstance(e, requests.exceptions.Timeout):
                    raise TransientAPIError(
                        "API request timed out",
                        original_error=e
                    )
                elif isinstance(e, requests.exceptions.ConnectionError):
                    raise TransientNetworkError(
                        "Network connection failed",
                        "Check your internet connection and try again.",
                        e
                    )
                elif hasattr(e, 'response') and e.response is not None:
                    status_code = e.response.status_code
                    if status_code in [429, 502, 503, 504]:
                        raise TransientAPIError(
                            f"API temporarily unavailable (HTTP {status_code})",
                            status_code=status_code,
                            original_error=e
                        )
                    else:
                        raise LLMAPIError(
                            f"API request failed (HTTP {status_code})",
                            status_code=status_code,
                            original_error=e
                        )
                else:
                    raise LLMAPIError(
                        f"API request failed: {str(e)}",
                        original_error=e
                    )
            else:
                # Re-raise non-API exceptions
                raise e
    
    return wrapper


class ErrorHandler:
    """Centralized error handling and logging"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
    
    def handle_error(self, error: Exception, context: str = "") -> None:
        """Handle and log errors with appropriate level and formatting"""
        if isinstance(error, DMSError):
            self.logger.error(f"{context}: {error.message}")
            if error.recovery_suggestion:
                self.logger.info(f"Recovery suggestion: {error.recovery_suggestion}")
            if error.original_error:
                self.logger.debug(f"Original error: {error.original_error}", exc_info=True)
        else:
            self.logger.error(f"{context}: Unexpected error: {error}", exc_info=True)
    
    def handle_warning(self, message: str, context: str = "") -> None:
        """Handle and log warnings"""
        self.logger.warning(f"{context}: {message}")
    
    def handle_info(self, message: str, context: str = "") -> None:
        """Handle and log info messages"""
        self.logger.info(f"{context}: {message}")


def setup_error_recovery_suggestions() -> dict:
    """Setup common error recovery suggestions"""
    return {
        "corrupted_pdf": [
            "Try opening the PDF in a PDF viewer to verify it's readable",
            "If password-protected, remove the password first",
            "Re-download the file if it may have been corrupted during transfer"
        ],
        "ocr_failure": [
            "Ensure Tesseract is installed: brew install tesseract (macOS) or apt-get install tesseract-ocr (Ubuntu)",
            "Install German language pack: brew install tesseract-lang (macOS)",
            "Check if the PDF contains readable images or is just text-based"
        ],
        "api_failure": [
            "Check your OpenRouter API key in configuration",
            "Verify your internet connection",
            "Try a different model if the current one is unavailable",
            "Check OpenRouter service status at https://status.openrouter.ai/"
        ],
        "database_error": [
            "Check disk space in your data directory",
            "Ensure you have write permissions to the data directory",
            "Try reinitializing the database with 'dms init'"
        ],
        "vector_store_error": [
            "Check available memory (vector operations can be memory-intensive)",
            "Try reducing chunk size in configuration",
            "Clear and rebuild the vector store if corrupted"
        ]
    }