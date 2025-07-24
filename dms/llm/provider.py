"""OpenRouter LLM Provider for DMS"""

import requests
import time
from typing import List, Dict, Any, Optional
from requests.exceptions import RequestException, Timeout, HTTPError
from dms.config import OpenRouterConfig
from dms.errors import (
    LLMAPIError, TransientAPIError, handle_api_errors, retry_on_failure
)
from dms.logging_setup import get_logger, log_performance


class ModelNotAvailableError(LLMAPIError):
    """Exception raised when a model is not available"""
    
    def __init__(self, model: str):
        super().__init__(
            f"Model '{model}' is not available",
            model=model,
            recovery_suggestion="Try a different model or check OpenRouter model availability."
        )


class LLMProvider:
    """OpenRouter API client for LLM interactions"""
    
    def __init__(self, config: OpenRouterConfig):
        """Initialize LLM provider with configuration
        
        Args:
            config: OpenRouter configuration
            
        Raises:
            LLMAPIError: If API key is missing or invalid
        """
        if not config.api_key:
            raise LLMAPIError(
                "OpenRouter API key is required",
                recovery_suggestion="Set your API key in configuration or OPENROUTER_API_KEY environment variable."
            )
        
        self.config = config
        self.logger = get_logger(f"{__name__}.LLMProvider")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/rmoriz/dms",
            "X-Title": "DMS - Document Management System"
        })
        
        self.logger.debug(f"Initialized LLM provider with default model: {config.default_model}")
    
    @retry_on_failure(max_retries=2, delay=1.0, exceptions=(TransientAPIError,))
    def chat_completion(self, messages: List[Dict[str, str]], model: Optional[str] = None) -> str:
        """Generate chat completion using specified model with fallback
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model to use (defaults to config default_model)
            
        Returns:
            Generated response text
            
        Raises:
            LLMAPIError: If all models fail or other API errors occur
        """
        if model is None:
            model = self.config.default_model
        
        # Try primary model first, then fallbacks
        models_to_try = [model] + self._get_fallback_models(model)
        
        self.logger.debug(f"Attempting chat completion with models: {models_to_try}")
        
        last_error = None
        for i, current_model in enumerate(models_to_try):
            try:
                with log_performance(f"Chat completion with {current_model}", self.logger):
                    response = self._make_chat_request(messages, current_model)
                    if i > 0:  # Used fallback model
                        self.logger.info(f"Successfully used fallback model: {current_model}")
                    return response
            except (ModelNotAvailableError, TransientAPIError) as e:
                last_error = e
                self.logger.warning(f"Model {current_model} failed: {e}")
                continue
            except LLMAPIError as e:
                # Non-retryable API error, don't try other models
                self.logger.error(f"Non-retryable API error with {current_model}: {e}")
                raise e
        
        # All models failed
        self.logger.error(f"All {len(models_to_try)} models failed")
        raise LLMAPIError(
            f"All models failed. Last error: {last_error}",
            recovery_suggestion="Check your API key, internet connection, and try again later."
        )
    
    @handle_api_errors
    def _make_chat_request(self, messages: List[Dict[str, str]], model: str) -> str:
        """Make a single chat completion request
        
        Args:
            messages: List of message dictionaries
            model: Model identifier
            
        Returns:
            Generated response text
            
        Raises:
            ModelNotAvailableError: If model is not available
            TransientAPIError: For retryable API errors
            LLMAPIError: For other API errors
        """
        url = f"{self.config.base_url}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        self.logger.debug(f"Making chat request to {model} with {len(messages)} messages")
        
        response = self.session.post(
            url, 
            json=payload, 
            timeout=self.config.timeout
        )
        
        # Handle specific status codes
        if response.status_code == 404:
            raise ModelNotAvailableError(model)
        elif response.status_code == 429:
            raise TransientAPIError(
                "Rate limit exceeded",
                model=model,
                status_code=429
            )
        elif response.status_code in [502, 503, 504]:
            raise TransientAPIError(
                f"Service temporarily unavailable (HTTP {response.status_code})",
                model=model,
                status_code=response.status_code
            )
        elif response.status_code >= 400:
            error_msg = "Unknown error"
            try:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", error_msg)
            except:
                pass
            raise LLMAPIError(
                f"API error: {error_msg}",
                model=model,
                status_code=response.status_code
            )
        
        response.raise_for_status()
        data = response.json()
        
        if "choices" not in data or not data["choices"]:
            raise LLMAPIError(
                "Invalid response format: no choices",
                model=model,
                recovery_suggestion="This may be a temporary API issue. Try again."
            )
        
        content = data["choices"][0]["message"]["content"]
        self.logger.debug(f"Received response: {len(content)} characters")
        
        return content
    
    @handle_api_errors
    @retry_on_failure(max_retries=2, delay=1.0, exceptions=(TransientAPIError,))
    def list_available_models(self) -> List[str]:
        """Get list of available models from OpenRouter
        
        Returns:
            List of model identifiers
            
        Raises:
            LLMAPIError: If API request fails
        """
        url = f"{self.config.base_url}/models"
        
        self.logger.debug("Fetching available models from OpenRouter")
        
        response = self.session.get(url, timeout=self.config.timeout)
        response.raise_for_status()
        data = response.json()
        
        models = [model["id"] for model in data.get("data", [])]
        self.logger.debug(f"Found {len(models)} available models")
        
        return models
    
    @handle_api_errors
    @retry_on_failure(max_retries=2, delay=1.0, exceptions=(TransientAPIError,))
    def get_model_info(self, model: str) -> Dict[str, Any]:
        """Get detailed information about a specific model
        
        Args:
            model: Model identifier
            
        Returns:
            Dictionary with model information
            
        Raises:
            ModelNotAvailableError: If model is not found
            LLMAPIError: If API request fails
        """
        url = f"{self.config.base_url}/models"
        
        self.logger.debug(f"Fetching info for model: {model}")
        
        response = self.session.get(url, timeout=self.config.timeout)
        response.raise_for_status()
        data = response.json()
        
        for model_info in data.get("data", []):
            if model_info["id"] == model:
                self.logger.debug(f"Found model info for {model}")
                return model_info
        
        raise ModelNotAvailableError(model)
    
    def _get_fallback_models(self, primary_model: str) -> List[str]:
        """Get fallback model chain excluding the primary model
        
        Args:
            primary_model: The primary model that failed
            
        Returns:
            List of fallback models to try
        """
        all_models = [self.config.default_model] + self.config.fallback_models
        
        # Remove primary model and duplicates while preserving order
        fallbacks = []
        for model in all_models:
            if model != primary_model and model not in fallbacks:
                fallbacks.append(model)
        
        return fallbacks
    
    def test_connectivity(self) -> bool:
        """Test connectivity to OpenRouter API
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.logger.debug("Testing OpenRouter API connectivity")
            test_messages = [{"role": "user", "content": "Hello"}]
            self._make_chat_request(test_messages, self.config.default_model)
            self.logger.debug("Connectivity test successful")
            return True
        except Exception as e:
            self.logger.warning(f"Connectivity test failed: {e}")
            return False