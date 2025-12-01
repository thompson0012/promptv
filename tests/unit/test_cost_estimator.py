"""
Unit tests for CostEstimator.
"""
import pytest
from pathlib import Path
from promptv.cost_estimator import CostEstimator, UnknownModelError, TokenizationError
from promptv.models import CostEstimate


# Mock pricing data for testing
MOCK_PRICING = {
    'openai': {
        'gpt-4': {
            'input': 0.00003,
            'output': 0.00006,
            'encoding': 'cl100k_base'
        },
        'gpt-3.5-turbo': {
            'input': 0.0000005,
            'output': 0.0000015,
            'encoding': 'cl100k_base'
        }
    },
    'anthropic': {
        'claude-3-opus': {
            'input': 0.000015,
            'output': 0.000075,
            'encoding': 'cl100k_base'
        }
    },
    'aliases': {
        'gpt4': 'gpt-4',
        'gpt35': 'gpt-3.5-turbo'
    }
}


@pytest.fixture
def estimator():
    """Create a CostEstimator with mock pricing data."""
    return CostEstimator(pricing_data=MOCK_PRICING)


class TestCostEstimator:
    """Test suite for CostEstimator class."""
    
    def test_init_with_custom_pricing(self, estimator):
        """Test initialization with custom pricing data."""
        assert estimator.pricing == MOCK_PRICING
        assert estimator._encoders == {}
    
    def test_init_with_default_pricing(self):
        """Test initialization with default pricing.yaml."""
        # This should load from pricing.yaml
        estimator = CostEstimator()
        assert 'openai' in estimator.pricing
        assert 'anthropic' in estimator.pricing
    
    def test_count_tokens_simple(self, estimator):
        """Test token counting for simple text."""
        text = "Hello, world!"
        count = estimator.count_tokens(text, model="gpt-4", provider="openai")
        
        # "Hello, world!" should be ~4 tokens with cl100k_base
        assert count > 0
        assert count < 10  # Sanity check
    
    def test_count_tokens_long_text(self, estimator):
        """Test token counting for longer text."""
        text = "This is a longer piece of text that should result in more tokens. " * 10
        count = estimator.count_tokens(text, model="gpt-4", provider="openai")
        
        assert count > 50  # Should be much more than 50 tokens
    
    def test_count_tokens_empty_string(self, estimator):
        """Test token counting for empty string."""
        count = estimator.count_tokens("", model="gpt-4", provider="openai")
        assert count == 0
    
    def test_count_tokens_encoder_caching(self, estimator):
        """Test that encoders are cached after first use."""
        text = "Test text"
        
        # First call should create encoder
        estimator.count_tokens(text, model="gpt-4", provider="openai")
        assert 'cl100k_base' in estimator._encoders
        
        # Second call should reuse cached encoder
        encoder_before = estimator._encoders['cl100k_base']
        estimator.count_tokens(text, model="gpt-4", provider="openai")
        encoder_after = estimator._encoders['cl100k_base']
        
        assert encoder_before is encoder_after  # Same object
    
    def test_count_tokens_unknown_model(self, estimator):
        """Test token counting with unknown model."""
        with pytest.raises(UnknownModelError):
            estimator.count_tokens("Test", model="unknown-model", provider="openai")
    
    def test_count_tokens_unknown_provider(self, estimator):
        """Test token counting with unknown provider."""
        with pytest.raises(UnknownModelError):
            estimator.count_tokens("Test", model="gpt-4", provider="unknown-provider")
    
    def test_estimate_cost_basic(self, estimator):
        """Test basic cost estimation."""
        text = "Hello, world!"
        cost = estimator.estimate_cost(
            text=text,
            model="gpt-4",
            provider="openai",
            estimated_output_tokens=100
        )
        
        # Verify CostEstimate structure
        assert isinstance(cost, CostEstimate)
        assert cost.input_tokens > 0
        assert cost.estimated_output_tokens == 100
        assert cost.total_tokens == cost.input_tokens + 100
        assert cost.model == "gpt-4"
        assert cost.provider == "openai"
        
        # Verify cost calculations
        assert cost.input_cost > 0
        assert cost.estimated_output_cost > 0
        assert cost.total_cost == cost.input_cost + cost.estimated_output_cost
        
        # Verify pricing matches expected rates
        expected_input_cost = cost.input_tokens * 0.00003
        expected_output_cost = 100 * 0.00006
        assert abs(cost.input_cost - expected_input_cost) < 1e-9
        assert abs(cost.estimated_output_cost - expected_output_cost) < 1e-9
    
    def test_estimate_cost_different_models(self, estimator):
        """Test cost estimation for different models."""
        text = "Test prompt"
        
        # GPT-4 should be more expensive than GPT-3.5
        cost_gpt4 = estimator.estimate_cost(text, "gpt-4", "openai", 100)
        cost_gpt35 = estimator.estimate_cost(text, "gpt-3.5-turbo", "openai", 100)
        
        assert cost_gpt4.total_cost > cost_gpt35.total_cost
    
    def test_estimate_cost_zero_output_tokens(self, estimator):
        """Test cost estimation with zero output tokens."""
        text = "Test prompt"
        cost = estimator.estimate_cost(text, "gpt-4", "openai", estimated_output_tokens=0)
        
        assert cost.estimated_output_tokens == 0
        assert cost.estimated_output_cost == 0
        assert cost.total_cost == cost.input_cost
    
    def test_estimate_cost_large_output(self, estimator):
        """Test cost estimation with large output token estimate."""
        text = "Short prompt"
        cost = estimator.estimate_cost(text, "gpt-4", "openai", estimated_output_tokens=4000)
        
        assert cost.estimated_output_tokens == 4000
        # Output cost should dominate for large outputs
        assert cost.estimated_output_cost > cost.input_cost
    
    def test_estimate_cost_unknown_model(self, estimator):
        """Test cost estimation with unknown model."""
        with pytest.raises(UnknownModelError):
            estimator.estimate_cost("Test", "unknown-model", "openai", 100)
    
    def test_compare_costs(self, estimator):
        """Test cost comparison across multiple models."""
        text = "Test prompt for comparison"
        models = [
            ("openai", "gpt-4"),
            ("openai", "gpt-3.5-turbo"),
            ("anthropic", "claude-3-opus")
        ]
        
        results = estimator.compare_costs(text, models, estimated_output_tokens=100)
        
        # Check all models are in results
        assert "openai/gpt-4" in results
        assert "openai/gpt-3.5-turbo" in results
        assert "anthropic/claude-3-opus" in results
        
        # Check all results are CostEstimate objects
        for key, cost in results.items():
            assert isinstance(cost, CostEstimate)
            assert cost.input_tokens > 0
            assert cost.estimated_output_tokens == 100
    
    def test_compare_costs_with_unknown_model(self, estimator):
        """Test cost comparison including an unknown model."""
        text = "Test prompt"
        models = [
            ("openai", "gpt-4"),
            ("unknown-provider", "unknown-model"),
            ("openai", "gpt-3.5-turbo")
        ]
        
        results = estimator.compare_costs(text, models, estimated_output_tokens=100)
        
        # Valid models should have results
        assert isinstance(results["openai/gpt-4"], CostEstimate)
        assert isinstance(results["openai/gpt-3.5-turbo"], CostEstimate)
        
        # Unknown model should be None
        assert results["unknown-provider/unknown-model"] is None
    
    def test_compare_costs_ordering(self, estimator):
        """Test that cost comparison shows correct price ordering."""
        text = "Test prompt"
        models = [
            ("openai", "gpt-4"),
            ("openai", "gpt-3.5-turbo")
        ]
        
        results = estimator.compare_costs(text, models, estimated_output_tokens=100)
        
        # GPT-4 should be more expensive than GPT-3.5
        assert results["openai/gpt-4"].total_cost > results["openai/gpt-3.5-turbo"].total_cost
    
    def test_cost_estimate_serialization(self, estimator):
        """Test that CostEstimate can be serialized to dict/JSON."""
        text = "Test prompt"
        cost = estimator.estimate_cost(text, "gpt-4", "openai", 100)
        
        # Pydantic models should have model_dump method
        cost_dict = cost.model_dump()
        
        assert cost_dict['model'] == 'gpt-4'
        assert cost_dict['provider'] == 'openai'
        assert cost_dict['input_tokens'] > 0
        assert cost_dict['total_cost'] > 0
    
    def test_encoder_reuse_across_models(self, estimator):
        """Test that encoder is reused for models with same encoding."""
        text = "Test text"
        
        # Both models use cl100k_base
        estimator.count_tokens(text, "gpt-4", "openai")
        estimator.count_tokens(text, "gpt-3.5-turbo", "openai")
        
        # Should only have one encoder cached
        assert len(estimator._encoders) == 1
        assert 'cl100k_base' in estimator._encoders
