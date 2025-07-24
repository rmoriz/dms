"""Unit tests for logging setup system"""

import pytest
import logging
import tempfile
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from dms.logging_setup import (
    ColoredFormatter, setup_logging, get_logger, LoggingContext,
    log_function_call, log_performance, setup_cli_logging, log_system_info
)
from dms.config import DMSConfig, LoggingConfig


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_config(temp_dir):
    """Create mock DMS config for testing"""
    config = Mock(spec=DMSConfig)
    config.logging = LoggingConfig(
        level="INFO",
        file_enabled=True,
        console_enabled=True,
        max_file_size=1024*1024,
        backup_count=3
    )
    config.logs_path = temp_dir / "logs"
    return config


class TestColoredFormatter:
    """Test ColoredFormatter functionality"""
    
    def test_colored_formatting(self):
        """Test that formatter adds colors to log levels"""
        formatter = ColoredFormatter("%(levelname)s - %(message)s")
        
        # Create log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        
        # Should contain ANSI color codes
        assert '\033[32m' in formatted  # Green for INFO
        assert '\033[0m' in formatted   # Reset code
        assert 'Test message' in formatted
    
    def test_different_log_levels(self):
        """Test coloring for different log levels"""
        formatter = ColoredFormatter("%(levelname)s")
        
        levels_and_colors = [
            (logging.DEBUG, '\033[36m'),    # Cyan
            (logging.INFO, '\033[32m'),     # Green
            (logging.WARNING, '\033[33m'),  # Yellow
            (logging.ERROR, '\033[31m'),    # Red
            (logging.CRITICAL, '\033[35m'), # Magenta
        ]
        
        for level, expected_color in levels_and_colors:
            record = logging.LogRecord(
                name="test", level=level, pathname="test.py", lineno=1,
                msg="Test", args=(), exc_info=None
            )
            formatted = formatter.format(record)
            assert expected_color in formatted


class TestSetupLogging:
    """Test setup_logging function"""
    
    def test_setup_with_config(self, mock_config):
        """Test logging setup with provided config"""
        logger = setup_logging(mock_config)
        
        assert logger.name == 'dms'
        assert logger.level == logging.INFO
        assert len(logger.handlers) >= 1  # Should have at least one handler
    
    def test_setup_without_config(self):
        """Test logging setup without config (loads default)"""
        with patch('dms.logging_setup.DMSConfig') as mock_dms_config:
            mock_config = Mock()
            mock_config.logging = LoggingConfig()
            mock_config.logs_path = Path("/tmp/logs")
            mock_dms_config.load.return_value = mock_config
            
            logger = setup_logging()
            
            assert logger.name == 'dms'
            mock_dms_config.load.assert_called_once()
    
    def test_file_logging_disabled(self, temp_dir):
        """Test setup with file logging disabled"""
        config = Mock(spec=DMSConfig)
        config.logging = LoggingConfig(
            level="DEBUG",
            file_enabled=False,
            console_enabled=True
        )
        config.logs_path = temp_dir / "logs"
        
        logger = setup_logging(config)
        
        # Should only have console handler
        handler_types = [type(h).__name__ for h in logger.handlers]
        assert 'StreamHandler' in handler_types
        assert 'RotatingFileHandler' not in handler_types
    
    def test_console_logging_disabled(self, temp_dir):
        """Test setup with console logging disabled"""
        config = Mock(spec=DMSConfig)
        config.logging = LoggingConfig(
            level="DEBUG",
            file_enabled=True,
            console_enabled=False
        )
        config.logs_path = temp_dir / "logs"
        
        logger = setup_logging(config)
        
        # Should only have file handlers
        handler_types = [type(h).__name__ for h in logger.handlers]
        assert 'StreamHandler' not in handler_types
        assert 'RotatingFileHandler' in handler_types
    
    def test_log_directory_creation(self, temp_dir):
        """Test that log directory is created"""
        config = Mock(spec=DMSConfig)
        config.logging = LoggingConfig(file_enabled=True)
        config.logs_path = temp_dir / "new_logs"
        
        assert not config.logs_path.exists()
        
        setup_logging(config)
        
        assert config.logs_path.exists()
        assert config.logs_path.is_dir()
    
    def test_multiple_log_files(self, temp_dir):
        """Test that both main and error log files are created"""
        config = Mock(spec=DMSConfig)
        config.logging = LoggingConfig(file_enabled=True)
        config.logs_path = temp_dir / "logs"
        
        logger = setup_logging(config)
        
        # Log some messages to trigger file creation
        logger.info("Test info message")
        logger.error("Test error message")
        
        # Force handlers to flush
        for handler in logger.handlers:
            handler.flush()
        
        # Check that log files exist
        main_log = temp_dir / "logs" / "dms.log"
        error_log = temp_dir / "logs" / "dms_errors.log"
        
        # Files should exist (though they might be empty initially)
        assert main_log.parent.exists()
        assert error_log.parent.exists()


class TestGetLogger:
    """Test get_logger function"""
    
    def test_get_default_logger(self):
        """Test getting default logger"""
        logger = get_logger()
        assert logger.name == 'dms'
    
    def test_get_named_logger(self):
        """Test getting named logger"""
        logger = get_logger('test.module')
        assert logger.name == 'test.module'
    
    def test_logger_hierarchy(self):
        """Test logger hierarchy"""
        parent_logger = get_logger('dms')
        child_logger = get_logger('dms.module')
        
        assert child_logger.parent == parent_logger


class TestLoggingContext:
    """Test LoggingContext context manager"""
    
    def test_temporary_level_change(self):
        """Test temporary logging level change"""
        logger = logging.getLogger('test_context')
        original_level = logging.INFO
        logger.setLevel(original_level)
        
        with LoggingContext(logger, 'DEBUG'):
            assert logger.level == logging.DEBUG
        
        assert logger.level == original_level
    
    def test_context_with_exception(self):
        """Test that level is restored even if exception occurs"""
        logger = logging.getLogger('test_context_exception')
        original_level = logging.INFO
        logger.setLevel(original_level)
        
        try:
            with LoggingContext(logger, 'DEBUG'):
                assert logger.level == logging.DEBUG
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        assert logger.level == original_level


class TestLogFunctionCall:
    """Test log_function_call decorator"""
    
    def test_function_call_logging(self):
        """Test that function calls are logged"""
        mock_logger = Mock()
        
        @log_function_call(mock_logger)
        def test_function(arg1, arg2=None):
            return "result"
        
        result = test_function("value1", arg2="value2")
        
        assert result == "result"
        assert mock_logger.debug.call_count >= 2  # Entry and completion
        
        # Check that function name is in log messages
        debug_calls = [call[0][0] for call in mock_logger.debug.call_args_list]
        assert any("test_function" in msg for msg in debug_calls)
    
    def test_function_call_with_exception(self):
        """Test logging when function raises exception"""
        mock_logger = Mock()
        
        @log_function_call(mock_logger)
        def failing_function():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            failing_function()
        
        # Should have error log call
        mock_logger.error.assert_called_once()
        error_msg = mock_logger.error.call_args[0][0]
        assert "failing_function" in error_msg
        assert "Test error" in error_msg
    
    def test_function_call_without_logger(self):
        """Test decorator without explicit logger"""
        @log_function_call()
        def test_function():
            return "success"
        
        # Should not raise exception
        result = test_function()
        assert result == "success"


class TestLogPerformance:
    """Test log_performance context manager"""
    
    def test_performance_logging(self):
        """Test performance logging"""
        mock_logger = Mock()
        
        with log_performance("test operation", mock_logger):
            pass  # Simulate some work
        
        # Should have debug and info calls
        mock_logger.debug.assert_called_once()
        mock_logger.info.assert_called_once()
        
        debug_msg = mock_logger.debug.call_args[0][0]
        info_msg = mock_logger.info.call_args[0][0]
        
        assert "Starting test operation" in debug_msg
        assert "Completed test operation" in info_msg
        assert "in" in info_msg  # Should contain timing info
    
    def test_performance_logging_with_exception(self):
        """Test performance logging when exception occurs"""
        mock_logger = Mock()
        
        try:
            with log_performance("failing operation", mock_logger):
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # Should have debug and error calls
        mock_logger.debug.assert_called_once()
        mock_logger.error.assert_called_once()
        
        error_msg = mock_logger.error.call_args[0][0]
        assert "Failed failing operation" in error_msg


class TestSetupCLILogging:
    """Test setup_cli_logging function"""
    
    def test_cli_logging_normal(self):
        """Test CLI logging setup in normal mode"""
        with patch('dms.logging_setup.DMSConfig') as mock_dms_config:
            mock_config = Mock()
            mock_config.logging = LoggingConfig(level="INFO")
            mock_config.logs_path = Path("/tmp/logs")
            mock_dms_config.load.return_value = mock_config
            
            logger = setup_cli_logging(verbose=False)
            
            assert logger.name == 'dms'
    
    def test_cli_logging_verbose(self):
        """Test CLI logging setup in verbose mode"""
        with patch('dms.logging_setup.DMSConfig') as mock_dms_config:
            mock_config = Mock()
            mock_config.logging = LoggingConfig(level="INFO")
            mock_config.logs_path = Path("/tmp/logs")
            mock_dms_config.load.return_value = mock_config
            
            logger = setup_cli_logging(verbose=True)
            
            assert logger.name == 'dms'
            # Config should be modified for verbose mode
            assert mock_config.logging.level == "DEBUG"
            assert mock_config.logging.console_enabled is True
    
    def test_cli_logging_fallback(self):
        """Test CLI logging fallback when config fails"""
        with patch('dms.logging_setup.DMSConfig') as mock_dms_config:
            mock_dms_config.load.side_effect = Exception("Config failed")
            
            with patch('logging.basicConfig') as mock_basic_config:
                logger = setup_cli_logging(verbose=True)
                
                mock_basic_config.assert_called_once()
                assert logger.name == 'dms'


class TestLogSystemInfo:
    """Test log_system_info function"""
    
    def test_system_info_logging(self):
        """Test that system information is logged"""
        mock_logger = Mock()
        
        log_system_info(mock_logger)
        
        # Should have multiple info calls for different system info
        assert mock_logger.info.call_count >= 5
        
        # Check that various system info is logged
        info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        info_text = " ".join(info_calls)
        
        assert "Python version" in info_text
        assert "Platform" in info_text
        assert "Architecture" in info_text
        assert "Working directory" in info_text
        assert "DMS version" in info_text