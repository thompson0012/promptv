"""
Cost estimation using tiktoken for token counting.
"""
import tiktoken
from typing import Dict, Optional
from pathlib import Path

from promptv.models import CostEstimate
from promptv.resources import load_pricing_data, get_model_pricing
from promptv.exceptions import PromptVError


class CostEstimatorError(PromptVError):
    """Base exception for cost estimator errors."""
    pass


class UnknownModelError(CostEstimatorError):
    """Raised when model/provider is not found in pricing data."""
    pass


class TokenizationError(CostEstimatorError):
    """Raised when tokenization fails."""
    pass


class CostEstimator:
    """
    Cost estimator for LLM API calls using tiktoken.
    
    Features:
    - Accurate token counting using tiktoken
    - Support for major LLM providers (OpenAI, Anthropic, Google, etc.)
    - Maintainable pricing database
    - Token encoder caching for performance
    
    Example:
        >>> estimator = CostEstimator()
        >>> cost = estimator.estimate_cost(
        ...     text="Hello, world!",
        ...     model="gpt-4",
        ...     provider="openai",
        ...     estimated_output_tokens=100
        ... )
        >>> print(f"Total cost: ${cost.total_cost:.4f}")
    """
    
    def __init__(self, pricing_data: Optional[Dict] = None):
        """
        Initialize cost estimator.
        
        Args:
            pricing_data: Optional custom pricing data. If None, loads from pricing.yaml.
        """
        self.pricing = pricing_data if pricing_data else load_pricing_data()
        self._encoders: Dict[str, tiktoken.Encoding] = {}  # Cache for tokenizers
    
    def count_tokens(self, text: str, model: str = "gpt-4", provider: str = "openai") -> int:
        """
        Count tokens in text using tiktoken.
        
        Args:
            text: Text to tokenize
            model: Model name (default: "gpt-4")
            provider: Provider name (default: "openai")
        
        Returns:
            Number of tokens
        
        Raises:
            TokenizationError: If tokenization fails
            UnknownModelError: If model pricing not found
        """
        try:
            # Get encoding name for the model
            model_pricing = get_model_pricing(provider, model)
            encoding_name = model_pricing.get('encoding', 'cl100k_base')
            
            # Get or create encoder (with caching)
            if encoding_name not in self._encoders:
                self._encoders[encoding_name] = tiktoken.get_encoding(encoding_name)
            
            encoder = self._encoders[encoding_name]
            
            # Count tokens
            tokens = encoder.encode(text)
            return len(tokens)
            
        except ValueError as e:
            if "not found" in str(e).lower():
                raise UnknownModelError(str(e)) from e
            raise TokenizationError(f"Failed to tokenize text: {e}") from e
        except Exception as e:
            raise TokenizationError(f"Failed to tokenize text: {e}") from e
    
    def estimate_cost(
        self,
        text: str,
        model: str,
        provider: str,
        estimated_output_tokens: int = 500
    ) -> CostEstimate:
        """
        Estimate cost for a prompt.
        
        Args:
            text: Prompt text to estimate cost for
            model: Model name (e.g., 'gpt-4', 'claude-3-opus')
            provider: Provider name (e.g., 'openai', 'anthropic')
            estimated_output_tokens: Estimated number of output tokens (default: 500)
        
        Returns:
            CostEstimate object with detailed cost breakdown
        
        Raises:
            UnknownModelError: If model/provider not found in pricing data
            TokenizationError: If token counting fails
        
        Example:
            >>> estimator = CostEstimator()
            >>> cost = estimator.estimate_cost(
            ...     text="Summarize this article...",
            ...     model="gpt-4",
            ...     provider="openai",
            ...     estimated_output_tokens=200
            ... )
            >>> print(f"Input tokens: {cost.input_tokens}")
            >>> print(f"Total cost: ${cost.total_cost:.4f}")
        """
        # Count input tokens
        input_tokens = self.count_tokens(text, model, provider)
        
        # Get pricing information
        try:
            model_pricing = get_model_pricing(provider, model)
        except ValueError as e:
            raise UnknownModelError(str(e)) from e
        
        # Calculate costs (pricing is per token)
        input_cost = input_tokens * model_pricing['input']
        output_cost = estimated_output_tokens * model_pricing['output']
        total_cost = input_cost + output_cost
        total_tokens = input_tokens + estimated_output_tokens
        
        return CostEstimate(
            input_tokens=input_tokens,
            estimated_output_tokens=estimated_output_tokens,
            total_tokens=total_tokens,
            input_cost=input_cost,
            estimated_output_cost=output_cost,
            total_cost=total_cost,
            model=model,
            provider=provider
        )
    
    def compare_costs(
        self,
        text: str,
        models: list[tuple[str, str]],
        estimated_output_tokens: int = 500
    ) -> Dict[str, CostEstimate]:
        """
        Compare costs across multiple models.
        
        Args:
            text: Prompt text to estimate cost for
            models: List of (provider, model) tuples to compare
            estimated_output_tokens: Estimated number of output tokens
        
        Returns:
            Dictionary mapping "provider/model" to CostEstimate
        
        Example:
            >>> estimator = CostEstimator()
            >>> comparisons = estimator.compare_costs(
            ...     text="Hello, world!",
            ...     models=[
            ...         ("openai", "gpt-4"),
            ...         ("openai", "gpt-3.5-turbo"),
            ...         ("anthropic", "claude-3-sonnet")
            ...     ]
            ... )
            >>> for key, cost in comparisons.items():
            ...     print(f"{key}: ${cost.total_cost:.4f}")
        """
        results = {}
        
        for provider, model in models:
            try:
                cost = self.estimate_cost(
                    text=text,
                    model=model,
                    provider=provider,
                    estimated_output_tokens=estimated_output_tokens
                )
                results[f"{provider}/{model}"] = cost
            except (UnknownModelError, TokenizationError) as e:
                # Skip models that fail, but continue with others
                results[f"{provider}/{model}"] = None
        
        return results
