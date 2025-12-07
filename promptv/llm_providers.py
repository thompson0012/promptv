"""
LLM Provider implementations for testing prompts.

This module provides a unified interface for interacting with different
LLM providers (OpenAI, Anthropic, OpenRouter) and custom endpoints.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class LLMProviderError(Exception):
    """Base exception for LLM provider errors."""
    pass


class APIKeyError(LLMProviderError):
    """Raised when API key is invalid or missing."""
    pass


class APIError(LLMProviderError):
    """Raised when API returns an error."""
    pass


class NetworkError(LLMProviderError):
    """Raised when network connection fails."""
    pass


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    Provides a unified interface for sending messages to different LLM APIs
    and receiving responses with token usage and cost information.
    """
    
    @abstractmethod
    def send_message(
        self,
        messages: List[Dict[str, str]],
        stream: bool = True,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Tuple[str, int, int, float]:
        """
        Send a message to the LLM and receive a response.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
                     Format: [{"role": "user", "content": "Hello"}]
            stream: Whether to stream the response (default: True)
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens in response
        
        Returns:
            Tuple of (response_text, prompt_tokens, completion_tokens, cost)
        
        Raises:
            APIKeyError: If API key is invalid or missing
            APIError: If API returns an error
            NetworkError: If network connection fails
        """
        pass


class OpenAIProvider(LLMProvider):
    """
    OpenAI API provider implementation.
    
    Supports OpenAI models like GPT-4, GPT-3.5-turbo, etc.
    
    Example:
        >>> provider = OpenAIProvider(api_key="sk-...", model="gpt-4")
        >>> messages = [{"role": "user", "content": "Hello!"}]
        >>> response, prompt_tokens, completion_tokens, cost = provider.send_message(messages)
    """
    
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: Optional[str] = None
    ):
        """
        Initialize OpenAI provider.
        
        Args:
            api_key: OpenAI API key
            model: Model name (e.g., "gpt-4", "gpt-3.5-turbo")
            base_url: Optional custom base URL (default: OpenAI's API)
        """
        try:
            from openai import OpenAI
        except ImportError as e:
            raise LLMProviderError(
                "OpenAI library not installed. Install with: pip install openai>=1.0.0"
            ) from e
        
        self.model = model
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        
        self.client = OpenAI(**kwargs)
        
        # Import cost estimator
        from promptv.cost_estimator import CostEstimator
        self.cost_estimator = CostEstimator()
    
    def send_message(
        self,
        messages: List[Dict[str, str]],
        stream: bool = True,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Tuple[str, int, int, float]:
        """
        Send a message to OpenAI API.
        
        Args:
            messages: List of message dicts
            stream: Whether to stream the response
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
        
        Returns:
            Tuple of (response_text, prompt_tokens, completion_tokens, cost)
        """
        try:
            # Build API kwargs
            kwargs = {
                "model": self.model,
                "messages": messages,
                "stream": stream,
            }
            
            if temperature is not None:
                kwargs["temperature"] = temperature
            if max_tokens is not None:
                kwargs["max_tokens"] = max_tokens
            
            # Make API call
            if stream:
                response_text = ""
                prompt_tokens = 0
                completion_tokens = 0
                
                stream_response = self.client.chat.completions.create(**kwargs)
                
                for chunk in stream_response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        response_text += content
                        # Print content as it streams
                        print(content, end="", flush=True)
                    
                    # Get usage from final chunk
                    if hasattr(chunk, 'usage') and chunk.usage:
                        prompt_tokens = chunk.usage.prompt_tokens
                        completion_tokens = chunk.usage.completion_tokens
                
                print()  # Newline after streaming
                
                # If usage not available in stream, estimate tokens
                if completion_tokens == 0:
                    completion_tokens = self.cost_estimator.count_tokens(
                        response_text, self.model, "openai"
                    )
                    # Estimate prompt tokens from messages
                    prompt_text = "\n".join([m.get('content', '') for m in messages])
                    prompt_tokens = self.cost_estimator.count_tokens(
                        prompt_text, self.model, "openai"
                    )
            else:
                response = self.client.chat.completions.create(**kwargs)
                response_text = response.choices[0].message.content
                prompt_tokens = response.usage.prompt_tokens
                completion_tokens = response.usage.completion_tokens
            
            # Calculate cost
            from promptv.resources import get_model_pricing
            try:
                pricing = get_model_pricing("openai", self.model)
                cost = (prompt_tokens * pricing['input']) + (completion_tokens * pricing['output'])
            except ValueError:
                # Model not in pricing database, cost is 0
                cost = 0.0
            
            return response_text, prompt_tokens, completion_tokens, cost
        
        except Exception as e:
            error_msg = str(e).lower()
            
            if "api key" in error_msg or "unauthorized" in error_msg or "401" in error_msg:
                raise APIKeyError(f"Invalid API key: {e}") from e
            elif "rate limit" in error_msg or "429" in error_msg:
                raise APIError(f"Rate limit exceeded: {e}") from e
            elif "quota" in error_msg or "insufficient" in error_msg:
                raise APIError(f"Quota exceeded: {e}") from e
            elif "network" in error_msg or "connection" in error_msg:
                raise NetworkError(f"Network error: {e}") from e
            else:
                raise APIError(f"API error: {e}") from e


class AnthropicProvider(LLMProvider):
    """
    Anthropic API provider implementation.
    
    Supports Claude models (Claude 3 Opus, Sonnet, Haiku).
    
    Example:
        >>> provider = AnthropicProvider(api_key="sk-ant-...", model="claude-3-5-sonnet-20241022")
        >>> messages = [{"role": "user", "content": "Hello!"}]
        >>> response, prompt_tokens, completion_tokens, cost = provider.send_message(messages)
    """
    
    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None):
        """
        Initialize Anthropic provider.
        
        Args:
            api_key: Anthropic API key
            model: Model name (e.g., "claude-3-5-sonnet-20241022")
            base_url: Optional custom base URL (default: Anthropic's API)
        """
        try:
            from anthropic import Anthropic
        except ImportError as e:
            raise LLMProviderError(
                "Anthropic library not installed. Install with: pip install anthropic>=0.18.0"
            ) from e
        
        self.model = model
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = Anthropic(**kwargs)
        
        # Import cost estimator
        from promptv.cost_estimator import CostEstimator
        self.cost_estimator = CostEstimator()
    
    def send_message(
        self,
        messages: List[Dict[str, str]],
        stream: bool = True,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Tuple[str, int, int, float]:
        """
        Send a message to Anthropic API.
        
        Args:
            messages: List of message dicts
            stream: Whether to stream the response
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response (default: 1024)
        
        Returns:
            Tuple of (response_text, prompt_tokens, completion_tokens, cost)
        """
        try:
            # Anthropic requires system messages to be separate
            system_message = None
            conversation_messages = []
            
            for msg in messages:
                if msg.get('role') == 'system':
                    system_message = msg.get('content', '')
                else:
                    conversation_messages.append({
                        'role': msg.get('role'),
                        'content': msg.get('content', '')
                    })
            
            # Build API kwargs
            kwargs = {
                "model": self.model,
                "messages": conversation_messages,
                "max_tokens": max_tokens if max_tokens else 1024,  # Required by Anthropic
                "stream": stream,
            }
            
            if system_message:
                kwargs["system"] = system_message
            if temperature is not None:
                kwargs["temperature"] = temperature
            
            # Make API call
            if stream:
                response_text = ""
                prompt_tokens = 0
                completion_tokens = 0
                
                with self.client.messages.stream(**kwargs) as stream_response:
                    for text in stream_response.text_stream:
                        response_text += text
                        print(text, end="", flush=True)
                    
                    # Get final message with usage
                    message = stream_response.get_final_message()
                    prompt_tokens = message.usage.input_tokens
                    completion_tokens = message.usage.output_tokens
                
                print()  # Newline after streaming
            else:
                response = self.client.messages.create(**kwargs)
                # Extract text from content blocks
                response_text = ""
                for block in response.content:
                    if hasattr(block, 'text'):
                        response_text += block.text
                
                prompt_tokens = response.usage.input_tokens
                completion_tokens = response.usage.output_tokens
            
            # Calculate cost
            from promptv.resources import get_model_pricing
            try:
                pricing = get_model_pricing("anthropic", self.model)
                cost = (prompt_tokens * pricing['input']) + (completion_tokens * pricing['output'])
            except ValueError:
                # Model not in pricing database, cost is 0
                cost = 0.0
            
            return response_text, prompt_tokens, completion_tokens, cost
        
        except Exception as e:
            error_msg = str(e).lower()
            
            if "api key" in error_msg or "unauthorized" in error_msg or "401" in error_msg:
                raise APIKeyError(f"Invalid API key: {e}") from e
            elif "rate limit" in error_msg or "429" in error_msg:
                raise APIError(f"Rate limit exceeded: {e}") from e
            elif "quota" in error_msg or "credit" in error_msg:
                raise APIError(f"Quota exceeded: {e}") from e
            elif "network" in error_msg or "connection" in error_msg:
                raise NetworkError(f"Network error: {e}") from e
            else:
                raise APIError(f"API error: {e}") from e


class OpenRouterProvider(LLMProvider):
    """
    OpenRouter API provider implementation.
    
    OpenRouter is OpenAI-compatible, so we use the OpenAI client with
    a different base URL.
    
    Example:
        >>> provider = OpenRouterProvider(api_key="sk-or-...", model="openai/gpt-4-turbo")
        >>> messages = [{"role": "user", "content": "Hello!"}]
        >>> response, prompt_tokens, completion_tokens, cost = provider.send_message(messages)
    """
    
    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None):
        """
        Initialize OpenRouter provider.
        
        Args:
            api_key: OpenRouter API key
            model: Model name (e.g., "openai/gpt-4-turbo", "anthropic/claude-3-opus")
            base_url: Optional custom base URL (default: OpenRouter's API)
        """
        try:
            from openai import OpenAI
        except ImportError as e:
            raise LLMProviderError(
                "OpenAI library not installed. Install with: pip install openai>=1.0.0"
            ) from e
        
        self.model = model
        kwargs = {
            "api_key": api_key,
            "base_url": base_url if base_url else "https://openrouter.ai/api/v1"
        }
        self.client = OpenAI(**kwargs)
        
        # Import cost estimator
        from promptv.cost_estimator import CostEstimator
        self.cost_estimator = CostEstimator()
    
    def send_message(
        self,
        messages: List[Dict[str, str]],
        stream: bool = True,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Tuple[str, int, int, float]:
        """
        Send a message to OpenRouter API.
        
        Args:
            messages: List of message dicts
            stream: Whether to stream the response
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
        
        Returns:
            Tuple of (response_text, prompt_tokens, completion_tokens, cost)
        """
        try:
            # Build API kwargs (same as OpenAI)
            kwargs = {
                "model": self.model,
                "messages": messages,
                "stream": stream,
            }
            
            if temperature is not None:
                kwargs["temperature"] = temperature
            if max_tokens is not None:
                kwargs["max_tokens"] = max_tokens
            
            # Make API call
            if stream:
                response_text = ""
                prompt_tokens = 0
                completion_tokens = 0
                
                stream_response = self.client.chat.completions.create(**kwargs)
                
                for chunk in stream_response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        response_text += content
                        print(content, end="", flush=True)
                    
                    # Get usage from final chunk
                    if hasattr(chunk, 'usage') and chunk.usage:
                        prompt_tokens = chunk.usage.prompt_tokens
                        completion_tokens = chunk.usage.completion_tokens
                
                print()  # Newline after streaming
                
                # If usage not available in stream, estimate tokens
                if completion_tokens == 0:
                    # Use OpenAI encoding for estimation
                    completion_tokens = self.cost_estimator.count_tokens(
                        response_text, "gpt-4", "openai"
                    )
                    prompt_text = "\n".join([m.get('content', '') for m in messages])
                    prompt_tokens = self.cost_estimator.count_tokens(
                        prompt_text, "gpt-4", "openai"
                    )
            else:
                response = self.client.chat.completions.create(**kwargs)
                response_text = response.choices[0].message.content
                prompt_tokens = response.usage.prompt_tokens
                completion_tokens = response.usage.completion_tokens
            
            # Cost calculation for OpenRouter
            # Note: OpenRouter returns cost in response headers, but for now we'll estimate
            # or set to 0 if model not in our pricing database
            cost = 0.0
            
            return response_text, prompt_tokens, completion_tokens, cost
        
        except Exception as e:
            error_msg = str(e).lower()
            
            if "api key" in error_msg or "unauthorized" in error_msg or "401" in error_msg:
                raise APIKeyError(f"Invalid API key: {e}") from e
            elif "rate limit" in error_msg or "429" in error_msg:
                raise APIError(f"Rate limit exceeded: {e}") from e
            elif "quota" in error_msg or "insufficient" in error_msg:
                raise APIError(f"Quota exceeded: {e}") from e
            elif "network" in error_msg or "connection" in error_msg:
                raise NetworkError(f"Network error: {e}") from e
            else:
                raise APIError(f"API error: {e}") from e


def create_provider(
    provider_name: str,
    model: str,
    api_key: str,
    endpoint: Optional[str] = None
) -> LLMProvider:
    """
    Factory function to create the appropriate LLM provider.
    
    Args:
        provider_name: Name of the provider ("openai", "anthropic", "openrouter", "custom")
        model: Model name to use
        api_key: API key for the provider
        endpoint: Optional custom endpoint URL (only used for "custom" provider)
    
    Returns:
        LLMProvider instance
    
    Raises:
        ValueError: If provider_name is unknown
        LLMProviderError: If provider initialization fails
    
    Examples:
        >>> # OpenAI provider
        >>> provider = create_provider("openai", "gpt-4", "sk-...")
        
        >>> # Anthropic provider
        >>> provider = create_provider("anthropic", "claude-3-5-sonnet-20241022", "sk-ant-...")
        
        >>> # OpenRouter provider
        >>> provider = create_provider("openrouter", "openai/gpt-4-turbo", "sk-or-...")
        
        >>> # Custom endpoint
        >>> provider = create_provider("custom", "my-model", "key", "http://localhost:8000/v1")
    """
    provider_name = provider_name.lower()
    
    if provider_name == "openai":
        return OpenAIProvider(api_key=api_key, model=model)
    
    elif provider_name == "anthropic":
        # For Anthropic, we can pass a custom endpoint if provided
        if endpoint:
            return AnthropicProvider(api_key=api_key, model=model, base_url=endpoint)
        else:
            return AnthropicProvider(api_key=api_key, model=model)
    
    elif provider_name == "openrouter":
        # For OpenRouter, we can pass a custom endpoint if provided
        if endpoint:
            return OpenRouterProvider(api_key=api_key, model=model, base_url=endpoint)
        else:
            return OpenRouterProvider(api_key=api_key, model=model)
    
    elif provider_name == "custom":
        if not endpoint:
            raise ValueError("Custom provider requires an endpoint URL")
        return OpenAIProvider(api_key=api_key, model=model, base_url=endpoint)
    
    else:
        raise ValueError(
            f"Unknown provider: {provider_name}. "
            f"Supported providers: openai, anthropic, openrouter, custom"
        )