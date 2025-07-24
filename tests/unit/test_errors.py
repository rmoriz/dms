"""Unit tests for error handling system"""

import pytest
import time
import logging
import requests.exceptions
from unittest.mock import Mock, patch, MagicMock
from dms.errors import (
    DMSError, ConfigurationError, PDFProcessingError, CorruptedPDFError,
    OCRError, LLMAPIError, VectorStoreError, DatabaseError,
    RetryableError, TransientAPIError, TransientNetworkError,
    retry_on_failure, handle_pdf_errors, handle_api_errors,
    ErrorHandler, setup_error_recovery_suggestions
)


class TestDMSError:
    """Test base DMSError functionality"""
    
    def test_basic_error(self):
        """Test basic error creation"""
        error = DMSError("Test error message")
        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.recovery_suggestion is None
        assert error.original_error is None
    
    def test_error_with_suggestion(self):
        """Test error with recovery suggestion"""
        error = DMSError("Test error", "Try this fix")
        expected = "Test error\n💡 Suggestion: Try this fix"
        assert str(error) == expected
        assert error.recovery_suggestion == "Try this fix"
    
    def test_error_with_original_error(self):
        """Test error with original exception"""
        original = ValueError("Original error")
        error = DMSError("Wrapped error", original_error=original)
        assert error.original_error == original


class TestSpecificErrors:
    """Test specific error types"""
    
    def test_corrupted_pdf_error(self):
        """Test CorruptedPDFError"""
        error = CorruptedPDFError("/path/to/file.pdf")
        assert "corrupted or unreadable" in str(error)
        assert "password-protected" in str(error)
        assert error.file_path == "/path/to/file.pdf"
    
    def test_ocr_error(self):
        """Test OCRError"""
        error = OCRError("/path/to/file.pdf")
        assert "OCR processing failed" in str(error)
        assert "Tesseract" in str(error)
        assert error.file_path == "/path/to/file.pdf"
    
    def test_llm_api_error_with_status_codes(self):
        """Test LLMAPIError with different status codes"""
        # Test 401 Unauthorized
        error = LLMAPIError("Unauthorized", status_code=401)
        assert "API key" in str(error)
        
        # Test 429 Rate Limit
        error = LLMAPIError("Rate limited", status_code=429)
        assert "Rate limit" in str(error)
        
        # Test 503 Service Unavailable
        error = LLMAPIError("Service unavailable", status_code=503)
        assert "temporarily unavailable" in str(error)
        
        # Test 500 Server Error
        error = LLMAPIError("Server error", status_code=500)
        assert "Server error" in str(error)
        
        # Test unknown status code
        error = LLMAPIError("Unknown error", status_code=418)
        assert "internet connection" in str(error)


class TestRetryDecorator:
    """Test retry_on_failure decorator"""
    
    def test_successful_call_no_retry(self):
        """Test successful function call without retries"""
        @retry_on_failure(max_retries=3)
        def successful_function():
            return "success"
        
        result = successful_function()
        assert result == "success"
    
    def test_retry_on_retryable_error(self):
        """Test retry on retryable errors"""
        call_count = 0
        
        @retry_on_failure(max_retries=2, delay=0.01)
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TransientAPIError("Temporary failure")
            return "success"
        
        result = failing_function()
        assert result == "success"
        assert call_count == 3
    
    def test_retry_exhausted(self):
        """Test when all retries are exhausted"""
        @retry_on_failure(max_retries=2, delay=0.01)
        def always_failing_function():
            raise TransientAPIError("Always fails")
        
        with pytest.raises(TransientAPIError):
            always_failing_function()
    
    def test_non_retryable_error_no_retry(self):
        """Test that non-retryable errors are not retried"""
        call_count = 0
        
        @retry_on_failure(max_retries=3, delay=0.01)
        def non_retryable_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Non-retryable error")
        
        with pytest.raises(ValueError):
            non_retryable_error()
        
        assert call_count == 1  # Should not retry
    
    def test_retry_with_backoff(self):
        """Test retry with exponential backoff"""
        call_times = []
        
        @retry_on_failure(max_retries=2, delay=0.01, backoff_factor=2.0)
        def timing_function():
            call_times.append(time.time())
            raise TransientAPIError("Timing test")
        
        with pytest.raises(TransientAPIError):
            timing_function()
        
        assert len(call_times) == 3  # Initial + 2 retries
        
        # Check that delays increase (allowing for some timing variance)
        if len(call_times) >= 3:
            delay1 = call_times[1] - call_times[0]
            delay2 = call_times[2] - call_times[1]
            assert delay2 > delay1 * 1.5  # Should be roughly 2x with some tolerance
    
    def test_retry_with_logger(self):
        """Test retry with logging"""
        mock_logger = Mock()
        
        @retry_on_failure(max_retries=1, delay=0.01, logger=mock_logger)
        def logged_function():
            raise TransientAPIError("Logged failure")
        
        with pytest.raises(TransientAPIError):
            logged_function()
        
        # Should have warning and error log calls
        assert mock_logger.warning.called
        assert mock_logger.error.called


class TestPDFErrorHandler:
    """Test handle_pdf_errors decorator"""
    
    def test_successful_pdf_processing(self):
        """Test successful PDF processing"""
        @handle_pdf_errors
        def successful_pdf_function(file_path):
            return f"Processed {file_path}"
        
        result = successful_pdf_function("/path/to/file.pdf")
        assert result == "Processed /path/to/file.pdf"
    
    def test_corrupted_pdf_detection(self):
        """Test detection of corrupted PDF errors"""
        @handle_pdf_errors
        def corrupted_pdf_function(file_path):
            raise Exception("PDF is corrupted and cannot be read")
        
        with pytest.raises(CorruptedPDFError) as exc_info:
            corrupted_pdf_function("/path/to/file.pdf")
        
        assert exc_info.value.file_path == "/path/to/file.pdf"
    
    def test_ocr_error_detection(self):
        """Test detection of OCR errors"""
        @handle_pdf_errors
        def ocr_function(pdf_path):
            raise Exception("Tesseract OCR failed to process image")
        
        with pytest.raises(OCRError) as exc_info:
            ocr_function("/path/to/file.pdf")
        
        assert exc_info.value.file_path == "/path/to/file.pdf"
    
    def test_permission_error_detection(self):
        """Test detection of permission errors"""
        @handle_pdf_errors
        def permission_function(file_path):
            raise Exception("Permission denied accessing file")
        
        with pytest.raises(PDFProcessingError) as exc_info:
            permission_function("/path/to/file.pdf")
        
        assert "Cannot access file" in str(exc_info.value)
        assert "permissions" in str(exc_info.value)
    
    def test_generic_pdf_error(self):
        """Test generic PDF processing error"""
        @handle_pdf_errors
        def generic_error_function(file_path):
            raise Exception("Some other PDF error")
        
        with pytest.raises(PDFProcessingError) as exc_info:
            generic_error_function("/path/to/file.pdf")
        
        assert "Failed to process PDF" in str(exc_info.value)


class TestAPIErrorHandler:
    """Test handle_api_errors decorator"""
    
    def test_successful_api_call(self):
        """Test successful API call"""
        @handle_api_errors
        def successful_api_function():
            return "API success"
        
        result = successful_api_function()
        assert result == "API success"
    
    def test_timeout_error(self):
        """Test API timeout error handling"""
        @handle_api_errors
        def timeout_function():
            raise requests.exceptions.Timeout("Request timed out")
        
        with pytest.raises(TransientAPIError) as exc_info:
            timeout_function()
        
        assert "timed out" in str(exc_info.value)
    
    def test_connection_error(self):
        """Test API connection error handling"""
        @handle_api_errors
        def connection_function():
            raise requests.exceptions.ConnectionError("Connection failed")
        
        with pytest.raises(TransientNetworkError) as exc_info:
            connection_function()
        
        assert "Network connection failed" in str(exc_info.value)
    
    def test_http_error_retryable(self):
        """Test retryable HTTP errors"""
        mock_response = Mock()
        mock_response.status_code = 503
        
        @handle_api_errors
        def http_error_function():
            error = requests.exceptions.HTTPError("Service unavailable")
            error.response = mock_response
            raise error
        
        with pytest.raises(TransientAPIError) as exc_info:
            http_error_function()
        
        assert exc_info.value.status_code == 503
    
    def test_http_error_non_retryable(self):
        """Test non-retryable HTTP errors"""
        mock_response = Mock()
        mock_response.status_code = 400
        
        @handle_api_errors
        def http_error_function():
            error = requests.exceptions.HTTPError("Bad request")
            error.response = mock_response
            raise error
        
        with pytest.raises(LLMAPIError) as exc_info:
            http_error_function()
        
        assert exc_info.value.status_code == 400
    
    def test_non_api_error_passthrough(self):
        """Test that non-API errors are passed through"""
        @handle_api_errors
        def non_api_error_function():
            raise ValueError("Not an API error")
        
        with pytest.raises(ValueError):
            non_api_error_function()


class TestErrorHandler:
    """Test ErrorHandler class"""
    
    def test_handle_dms_error(self):
        """Test handling of DMS errors"""
        mock_logger = Mock()
        handler = ErrorHandler(mock_logger)
        
        error = DMSError("Test error", "Test suggestion")
        handler.handle_error(error, "Test context")
        
        mock_logger.error.assert_called_once()
        mock_logger.info.assert_called_once()
        assert "Test error" in mock_logger.error.call_args[0][0]
        assert "Test suggestion" in mock_logger.info.call_args[0][0]
    
    def test_handle_generic_error(self):
        """Test handling of generic errors"""
        mock_logger = Mock()
        handler = ErrorHandler(mock_logger)
        
        error = ValueError("Generic error")
        handler.handle_error(error, "Test context")
        
        mock_logger.error.assert_called_once()
        assert "Unexpected error" in mock_logger.error.call_args[0][0]
    
    def test_handle_warning(self):
        """Test warning handling"""
        mock_logger = Mock()
        handler = ErrorHandler(mock_logger)
        
        handler.handle_warning("Test warning", "Test context")
        
        mock_logger.warning.assert_called_once()
        assert "Test warning" in mock_logger.warning.call_args[0][0]
    
    def test_handle_info(self):
        """Test info handling"""
        mock_logger = Mock()
        handler = ErrorHandler(mock_logger)
        
        handler.handle_info("Test info", "Test context")
        
        mock_logger.info.assert_called_once()
        assert "Test info" in mock_logger.info.call_args[0][0]


class TestErrorRecoverySuggestions:
    """Test error recovery suggestions"""
    
    def test_setup_error_recovery_suggestions(self):
        """Test setup of error recovery suggestions"""
        suggestions = setup_error_recovery_suggestions()
        
        assert isinstance(suggestions, dict)
        assert "corrupted_pdf" in suggestions
        assert "ocr_failure" in suggestions
        assert "api_failure" in suggestions
        assert "database_error" in suggestions
        assert "vector_store_error" in suggestions
        
        # Check that suggestions are lists of strings
        for key, suggestion_list in suggestions.items():
            assert isinstance(suggestion_list, list)
            assert all(isinstance(s, str) for s in suggestion_list)
            assert len(suggestion_list) > 0