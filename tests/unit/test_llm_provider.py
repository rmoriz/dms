"""Tests for LLMProvider class"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from requests.exceptions import RequestException, HTTPError, Timeout
from dms.llm.provider import LLMProvider, LLMError, ModelNotAvailableError
from dms.config import OpenRouterConfig


class TestLLMProvider:
    """Test cases for LLMProvider"""
    
    @pytest.fixture
    def config(self):
        """Create test configuration"""
        return OpenRouterConfig(
            api_key="test-api-key",
            default_model="anthropic/claude-3-sonnet",
            fallback_models=["openai/gpt-4", "meta-llama/llama-2-70b-chat"],
            base_url="https://openrouter.ai/api/v1"
        )
    
    @pytest.fixture
    def provider(self, config):
        """Create LLMProvider instance"""
        return LLMProvider(config)
    
    def test_init_with_config(self, config):
        """Test LLMProvider initialization with config"""
        provider = LLMProvider(config)
        assert provider.config == config
        assert provider.session is not None
        assert provider.session.headers["Authorization"] == "Bearer test-api-key"
        assert provider.session.headers["HTTP-Referer"] == "https://github.com/rmoriz/dms"
    
    def test_init_with_missing_api_key(self):
        """Test initialization fails with missing API key"""
        config = OpenRouterConfig(api_key="")
        with pytest.raises(ValueError, match="OpenRouter API key is required"):
            LLMProvider(config)
    
    @patch('requests.Session.post')
    def test_chat_completion_success(self, mock_post, provider):
        """Test successful chat completion"""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "This is a test response"
                }
            }]
        }
        mock_post.return_value = mock_response
        
        messages = [{"role": "user", "content": "Test question"}]
        result = provider.chat_completion(messages, "anthropic/claude-3-sonnet")
        
        assert result == "This is a test response"
        mock_post.assert_called_once()
        
        # Verify request payload
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://openrouter.ai/api/v1/chat/completions"
        payload = call_args[1]["json"]
        assert payload["model"] == "anthropic/claude-3-sonnet"
        assert payload["messages"] == messages
    
    @patch('requests.Session.post')
    def test_chat_completion_with_fallback(self, mock_post, provider):
        """Test chat completion with fallback on model failure"""
        # First call fails with 404 (model not available)
        mock_response_404 = Mock()
        mock_response_404.status_code = 404
        mock_response_404.json.return_value = {"error": {"message": "Model not found"}}
        
        # Second call succeeds
        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {
            "choices": [{
                "message": {
                    "content": "Fallback response"
                }
            }]
        }
        
        mock_post.side_effect = [mock_response_404, mock_response_200]
        
        messages = [{"role": "user", "content": "Test question"}]
        result = provider.chat_completion(messages, "invalid-model")
        
        assert result == "Fallback response"
        assert mock_post.call_count == 2
    
    @patch('requests.Session.post')
    def test_chat_completion_all_models_fail(self, mock_post, provider):
        """Test chat completion when all models fail"""
        # All calls fail
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": {"message": "Server error"}}
        mock_post.return_value = mock_response
        
        messages = [{"role": "user", "content": "Test question"}]
        
        with pytest.raises(LLMError, match="All models failed"):
            provider.chat_completion(messages, "invalid-model")
    
    @patch('requests.Session.post')
    def test_chat_completion_timeout(self, mock_post, provider):
        """Test chat completion with timeout"""
        mock_post.side_effect = Timeout("Request timed out")
        
        messages = [{"role": "user", "content": "Test question"}]
        
        with pytest.raises(LLMError, match="Request timed out"):
            provider.chat_completion(messages, "anthropic/claude-3-sonnet")
    
    @patch('requests.Session.get')
    def test_list_available_models_success(self, mock_get, provider):
        """Test successful model listing"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"id": "anthropic/claude-3-sonnet", "name": "Claude 3 Sonnet"},
                {"id": "openai/gpt-4", "name": "GPT-4"},
                {"id": "meta-llama/llama-2-70b-chat", "name": "Llama 2 70B"}
            ]
        }
        mock_get.return_value = mock_response
        
        models = provider.list_available_models()
        
        assert len(models) == 3
        assert "anthropic/claude-3-sonnet" in models
        assert "openai/gpt-4" in models
        assert "meta-llama/llama-2-70b-chat" in models
    
    @patch('requests.Session.get')
    def test_list_available_models_failure(self, mock_get, provider):
        """Test model listing failure"""
        mock_get.side_effect = RequestException("Network error")
        
        with pytest.raises(LLMError, match="Failed to fetch available models"):
            provider.list_available_models()
    
    @patch('requests.Session.get')
    def test_get_model_info_success(self, mock_get, provider):
        """Test successful model info retrieval"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "anthropic/claude-3-sonnet",
                    "name": "Claude 3 Sonnet",
                    "description": "Anthropic's Claude 3 Sonnet model",
                    "pricing": {"prompt": "0.003", "completion": "0.015"},
                    "context_length": 200000
                }
            ]
        }
        mock_get.return_value = mock_response
        
        info = provider.get_model_info("anthropic/claude-3-sonnet")
        
        assert info["id"] == "anthropic/claude-3-sonnet"
        assert info["name"] == "Claude 3 Sonnet"
        assert "pricing" in info
        assert "context_length" in info
    
    @patch('requests.Session.get')
    def test_get_model_info_not_found(self, mock_get, provider):
        """Test model info for non-existent model"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response
        
        with pytest.raises(ModelNotAvailableError, match="Model 'invalid-model' not found"):
            provider.get_model_info("invalid-model")
    
    def test_get_fallback_models(self, provider):
        """Test fallback model chain generation"""
        # Test with model in fallback list
        fallbacks = provider._get_fallback_models("openai/gpt-4")
        expected = ["anthropic/claude-3-sonnet", "meta-llama/llama-2-70b-chat"]
        assert fallbacks == expected
        
        # Test with model not in fallback list
        fallbacks = provider._get_fallback_models("some-other-model")
        expected = ["anthropic/claude-3-sonnet", "openai/gpt-4", "meta-llama/llama-2-70b-chat"]
        assert fallbacks == expected
        
        # Test with default model
        fallbacks = provider._get_fallback_models("anthropic/claude-3-sonnet")
        expected = ["openai/gpt-4", "meta-llama/llama-2-70b-chat"]
        assert fallbacks == expected
    
    @patch('requests.Session.post')
    def test_test_connectivity_success(self, mock_post, provider):
        """Test successful connectivity test"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "Hello!"
                }
            }]
        }
        mock_post.return_value = mock_response
        
        result = provider.test_connectivity()
        assert result is True
    
    @patch('requests.Session.post')
    def test_test_connectivity_failure(self, mock_post, provider):
        """Test connectivity test failure"""
        mock_post.side_effect = RequestException("Network error")
        
        result = provider.test_connectivity()
        assert result is False