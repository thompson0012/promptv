"""
Unit tests for LLM providers.
"""

import unittest
from unittest.mock import patch, MagicMock

from promptv.llm_providers import (
    LLMProvider, OpenAIProvider, AnthropicProvider, OpenRouterProvider, 
    create_provider, LLMProviderError, APIKeyError, APIError, NetworkError
)


class TestLLMProviders(unittest.TestCase):
    """Test suite for LLM provider implementations."""

    def test_llm_provider_abstract_class(self):
        """Test that LLMProvider is abstract and cannot be instantiated."""
        with self.assertRaises(TypeError):
            LLMProvider()

    @patch('promptv.llm_providers.OpenAI')
    def test_openai_provider_initialization(self, mock_openai):
        """Test OpenAIProvider initialization."""
        provider = OpenAIProvider(api_key="test-key", model="gpt-4")
        self.assertIsInstance(provider, LLMProvider)
        mock_openai.assert_called_once_with(api_key="test-key")

    @patch('promptv.llm_providers.OpenAI')
    def test_openai_provider_with_custom_base_url(self, mock_openai):
        """Test OpenAIProvider with custom base URL."""
        provider = OpenAIProvider(
            api_key="test-key", 
            model="gpt-4", 
            base_url="https://custom-api.com/v1"
        )
        mock_openai.assert_called_once_with(
            api_key="test-key",
            base_url="https://custom-api.com/v1"
        )

    @patch('promptv.llm_providers.Anthropic')
    def test_anthropic_provider_initialization(self, mock_anthropic):
        """Test AnthropicProvider initialization."""
        provider = AnthropicProvider(api_key="test-key", model="claude-3-5-sonnet-20241022")
        self.assertIsInstance(provider, LLMProvider)
        mock_anthropic.assert_called_once_with(api_key="test-key")

    @patch('promptv.llm_providers.Anthropic')
    def test_anthropic_provider_with_custom_base_url(self, mock_anthropic):
        """Test AnthropicProvider with custom base URL."""
        provider = AnthropicProvider(
            api_key="test-key", 
            model="claude-3-5-sonnet-20241022",
            base_url="https://custom-anthropic.com/v1"
        )
        mock_anthropic.assert_called_once_with(
            api_key="test-key",
            base_url="https://custom-anthropic.com/v1"
        )

    @patch('promptv.llm_providers.OpenAI')
    def test_openrouter_provider_initialization(self, mock_openai):
        """Test OpenRouterProvider initialization."""
        provider = OpenRouterProvider(api_key="test-key", model="openai/gpt-4-turbo")
        self.assertIsInstance(provider, LLMProvider)
        mock_openai.assert_called_once_with(
            api_key="test-key",
            base_url="https://openrouter.ai/api/v1"
        )

    @patch('promptv.llm_providers.OpenAI')
    def test_openrouter_provider_with_custom_base_url(self, mock_openai):
        """Test OpenRouterProvider with custom base URL."""
        provider = OpenRouterProvider(
            api_key="test-key", 
            model="openai/gpt-4-turbo",
            base_url="https://custom-openrouter.com/v1"
        )
        mock_openai.assert_called_once_with(
            api_key="test-key",
            base_url="https://custom-openrouter.com/v1"
        )

    def test_create_provider_openai(self):
        """Test create_provider factory for OpenAI."""
        with patch('promptv.llm_providers.OpenAIProvider') as mock_provider:
            provider = create_provider("openai", "gpt-4", "test-key")
            mock_provider.assert_called_once_with(api_key="test-key", model="gpt-4")

    def test_create_provider_anthropic(self):
        """Test create_provider factory for Anthropic."""
        with patch('promptv.llm_providers.AnthropicProvider') as mock_provider:
            provider = create_provider("anthropic", "claude-3-5-sonnet-20241022", "test-key")
            mock_provider.assert_called_once_with(api_key="test-key", model="claude-3-5-sonnet-20241022")

    def test_create_provider_anthropic_with_custom_endpoint(self):
        """Test create_provider factory for Anthropic with custom endpoint."""
        with patch('promptv.llm_providers.AnthropicProvider') as mock_provider:
            provider = create_provider("anthropic", "claude-3-5-sonnet-20241022", "test-key", "https://custom-anthropic.com/v1")
            mock_provider.assert_called_once_with(
                api_key="test-key", 
                model="claude-3-5-sonnet-20241022",
                base_url="https://custom-anthropic.com/v1"
            )

    def test_create_provider_openrouter(self):
        """Test create_provider factory for OpenRouter."""
        with patch('promptv.llm_providers.OpenRouterProvider') as mock_provider:
            provider = create_provider("openrouter", "openai/gpt-4-turbo", "test-key")
            mock_provider.assert_called_once_with(api_key="test-key", model="openai/gpt-4-turbo")

    def test_create_provider_openrouter_with_custom_endpoint(self):
        """Test create_provider factory for OpenRouter with custom endpoint."""
        with patch('promptv.llm_providers.OpenRouterProvider') as mock_provider:
            provider = create_provider("openrouter", "openai/gpt-4-turbo", "test-key", "https://custom-openrouter.com/v1")
            mock_provider.assert_called_once_with(
                api_key="test-key", 
                model="openai/gpt-4-turbo",
                base_url="https://custom-openrouter.com/v1"
            )

    def test_create_provider_custom(self):
        """Test create_provider factory for custom endpoint."""
        with patch('promptv.llm_providers.OpenAIProvider') as mock_provider:
            provider = create_provider("custom", "my-model", "test-key", "http://localhost:8000/v1")
            mock_provider.assert_called_once_with(
                api_key="test-key", 
                model="my-model", 
                base_url="http://localhost:8000/v1"
            )

    def test_create_provider_unknown(self):
        """Test create_provider with unknown provider."""
        with self.assertRaises(ValueError) as context:
            create_provider("unknown", "model", "key")
        self.assertIn("Unknown provider", str(context.exception))

    def test_create_provider_custom_without_endpoint(self):
        """Test create_provider custom without endpoint raises error."""
        with self.assertRaises(ValueError) as context:
            create_provider("custom", "model", "key")
        self.assertIn("Custom provider requires an endpoint", str(context.exception))


if __name__ == '__main__':
    unittest.main()