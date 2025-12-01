"""
Unit tests for PromptClient SDK.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from promptv.sdk.client import PromptClient, CachedPrompt
from promptv.manager import PromptManager
from promptv.tag_manager import TagManager
from promptv.exceptions import PromptNotFoundError, TagNotFoundError


class TestCachedPrompt:
    """Test suite for CachedPrompt model."""
    
    def test_is_expired_false(self):
        """Test that fresh cache is not expired."""
        cached = CachedPrompt(
            content="test content",
            cached_at=datetime.now(),
            ttl_seconds=300
        )
        assert cached.is_expired() is False
    
    def test_is_expired_true(self):
        """Test that old cache is expired."""
        cached = CachedPrompt(
            content="test content",
            cached_at=datetime.now() - timedelta(seconds=400),
            ttl_seconds=300
        )
        assert cached.is_expired() is True
    
    def test_custom_ttl(self):
        """Test custom TTL value."""
        cached = CachedPrompt(
            content="test content",
            cached_at=datetime.now(),
            ttl_seconds=60
        )
        assert cached.ttl_seconds == 60


class TestPromptClient:
    """Test suite for PromptClient class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path)
    
    @pytest.fixture
    def client(self, temp_dir):
        """Create PromptClient with temporary directory."""
        return PromptClient(base_dir=temp_dir, cache_ttl=300)
    
    @pytest.fixture
    def sample_prompt(self, temp_dir):
        """Create a sample prompt for testing."""
        manager = PromptManager()
        manager.base_dir = temp_dir
        manager.prompts_dir = temp_dir / "prompts"
        manager.config_dir = temp_dir / ".config"
        manager._initialize_directories()
        
        # Create a prompt
        result = manager.set_prompt("test-prompt", "Hello {{name}}!")
        
        # Create a tag
        tag_manager = TagManager(manager.prompts_dir)
        tag_manager.create_tag("test-prompt", "prod", result['version'])
        
        return manager
    
    def test_init_default_dir(self):
        """Test initialization with default directory."""
        client = PromptClient()
        assert client.base_dir == Path.home() / ".promptv"
        assert client.cache_ttl == 300
    
    def test_init_custom_dir(self, temp_dir):
        """Test initialization with custom directory."""
        client = PromptClient(base_dir=temp_dir, cache_ttl=600)
        assert client.base_dir == temp_dir
        assert client.cache_ttl == 600
    
    def test_get_prompt_latest(self, client, sample_prompt):
        """Test getting latest version of prompt."""
        content = client.get_prompt("test-prompt")
        assert content == "Hello {{name}}!"
    
    def test_get_prompt_with_label(self, client, sample_prompt):
        """Test getting prompt by label."""
        content = client.get_prompt("test-prompt", label="prod")
        assert content == "Hello {{name}}!"
    
    def test_get_prompt_with_version(self, client, sample_prompt):
        """Test getting prompt by version number."""
        content = client.get_prompt("test-prompt", version=1)
        assert content == "Hello {{name}}!"
    
    def test_get_prompt_with_variables(self, client, sample_prompt):
        """Test getting prompt with variable rendering."""
        content = client.get_prompt(
            "test-prompt",
            variables={"name": "Alice"}
        )
        assert content == "Hello Alice!"
    
    def test_get_prompt_not_found(self, client):
        """Test getting non-existent prompt."""
        with pytest.raises(PromptNotFoundError):
            client.get_prompt("non-existent")
    
    def test_get_prompt_label_not_found(self, client, sample_prompt):
        """Test getting prompt with non-existent label."""
        with pytest.raises(TagNotFoundError):
            client.get_prompt("test-prompt", label="non-existent")
    
    def test_get_prompt_both_label_and_version(self, client, sample_prompt):
        """Test error when both label and version specified."""
        with pytest.raises(ValueError) as exc_info:
            client.get_prompt("test-prompt", label="prod", version=1)
        assert "Cannot specify both" in str(exc_info.value)
    
    def test_caching_enabled(self, client, sample_prompt):
        """Test that caching works."""
        # First call - should cache
        content1 = client.get_prompt("test-prompt", use_cache=True)
        assert len(client.cache) == 1
        
        # Second call - should use cache
        content2 = client.get_prompt("test-prompt", use_cache=True)
        assert content1 == content2
        assert len(client.cache) == 1
    
    def test_caching_disabled(self, client, sample_prompt):
        """Test that caching can be disabled."""
        content = client.get_prompt("test-prompt", use_cache=False)
        assert len(client.cache) == 0
    
    def test_cache_expiration(self, client, sample_prompt):
        """Test that expired cache is not used."""
        # Set very short TTL
        client.cache_ttl = 0
        
        # First call
        content1 = client.get_prompt("test-prompt", use_cache=True)
        assert len(client.cache) == 1
        
        # Wait a bit for expiration
        import time
        time.sleep(0.1)
        
        # Second call - cache should be expired
        content2 = client.get_prompt("test-prompt", use_cache=True)
        assert content1 == content2
    
    def test_get_prompt_with_metadata(self, client, sample_prompt):
        """Test getting prompt with metadata."""
        content, metadata = client.get_prompt_with_metadata("test-prompt")
        assert content == "Hello {{name}}!"
        assert metadata.version == 1
    
    def test_get_prompt_with_metadata_label(self, client, sample_prompt):
        """Test getting prompt with metadata by label."""
        content, metadata = client.get_prompt_with_metadata("test-prompt", label="prod")
        assert content == "Hello {{name}}!"
        assert metadata.version == 1
    
    def test_get_prompt_with_metadata_version(self, client, sample_prompt):
        """Test getting prompt with metadata by version."""
        content, metadata = client.get_prompt_with_metadata("test-prompt", version=1)
        assert content == "Hello {{name}}!"
        assert metadata.version == 1
    
    def test_list_prompts_empty(self, client):
        """Test listing prompts when none exist."""
        prompts = client.list_prompts()
        assert prompts == []
    
    def test_list_prompts(self, client, sample_prompt):
        """Test listing prompts."""
        prompts = client.list_prompts()
        assert "test-prompt" in prompts
    
    def test_get_versions(self, client, sample_prompt):
        """Test getting all versions."""
        versions = client.get_versions("test-prompt")
        assert len(versions) == 1
        assert versions[0].version == 1
    
    def test_get_versions_not_found(self, client):
        """Test getting versions for non-existent prompt."""
        with pytest.raises(PromptNotFoundError):
            client.get_versions("non-existent")
    
    def test_get_tags(self, client, sample_prompt):
        """Test getting all tags."""
        tags = client.get_tags("test-prompt")
        assert "prod" in tags
        assert tags["prod"] == 1
    
    def test_get_tags_empty(self, client, temp_dir):
        """Test getting tags when none exist."""
        # Create prompt without tags
        manager = PromptManager()
        manager.base_dir = temp_dir
        manager.prompts_dir = temp_dir / "prompts"
        manager.config_dir = temp_dir / ".config"
        manager.set_prompt("no-tags", "Content")
        
        tags = client.get_tags("no-tags")
        assert tags == {}
    
    def test_clear_cache(self, client, sample_prompt):
        """Test clearing cache."""
        # Add to cache
        client.get_prompt("test-prompt", use_cache=True)
        assert len(client.cache) > 0
        
        # Clear cache
        client.clear_cache()
        assert len(client.cache) == 0
    
    def test_get_cache_stats(self, client, sample_prompt):
        """Test getting cache statistics."""
        # Empty cache
        stats = client.get_cache_stats()
        assert stats["cached_count"] == 0
        assert stats["active_count"] == 0
        assert stats["ttl_seconds"] == 300
        
        # Add to cache
        client.get_prompt("test-prompt", use_cache=True)
        stats = client.get_cache_stats()
        assert stats["cached_count"] == 1
        assert stats["active_count"] == 1
    
    def test_get_cache_stats_with_expired(self, client, sample_prompt):
        """Test cache stats with expired entries."""
        # Set short TTL and cache a prompt
        client.cache_ttl = 0
        client.get_prompt("test-prompt", use_cache=True)
        
        # Wait for expiration
        import time
        time.sleep(0.1)
        
        stats = client.get_cache_stats()
        assert stats["cached_count"] == 1
        assert stats["expired_count"] == 1
        assert stats["active_count"] == 0
    
    def test_context_manager(self, client, sample_prompt):
        """Test context manager usage."""
        with PromptClient(base_dir=client.base_dir) as ctx_client:
            content = ctx_client.get_prompt("test-prompt", use_cache=True)
            assert content == "Hello {{name}}!"
            assert len(ctx_client.cache) == 1
        
        # Cache should be cleared after context exit
        # We can't check ctx_client.cache here as it's out of scope,
        # but the __exit__ should have been called
    
    def test_cache_key_generation(self, client):
        """Test cache key generation."""
        key1 = client._cache_key("test", None, None, None)
        key2 = client._cache_key("test", None, None, None)
        assert key1 == key2
        
        key3 = client._cache_key("test", "prod", None, None)
        assert key1 != key3
        
        key4 = client._cache_key("test", None, 1, None)
        assert key1 != key4
        
        key5 = client._cache_key("test", None, None, {"name": "Alice"})
        assert key1 != key5
    
    def test_cache_key_with_different_variables(self, client):
        """Test that different variables produce different cache keys."""
        key1 = client._cache_key("test", None, None, {"name": "Alice"})
        key2 = client._cache_key("test", None, None, {"name": "Bob"})
        assert key1 != key2
        
        key3 = client._cache_key("test", None, None, {"name": "Alice", "age": 30})
        assert key1 != key3
    
    def test_multiple_prompts_caching(self, client, temp_dir):
        """Test caching with multiple prompts."""
        # Create multiple prompts
        manager = PromptManager()
        manager.base_dir = temp_dir
        manager.prompts_dir = temp_dir / "prompts"
        manager.config_dir = temp_dir / ".config"
        manager._initialize_directories()
        
        manager.set_prompt("prompt1", "Content 1")
        manager.set_prompt("prompt2", "Content 2")
        
        # Get both prompts
        client.get_prompt("prompt1", use_cache=True)
        client.get_prompt("prompt2", use_cache=True)
        
        assert len(client.cache) == 2
    
    def test_get_prompt_with_label_and_variables(self, client, sample_prompt):
        """Test getting prompt with both label and variables."""
        content = client.get_prompt(
            "test-prompt",
            label="prod",
            variables={"name": "Bob"}
        )
        assert content == "Hello Bob!"
    
    def test_estimate_cost_basic(self, client, sample_prompt):
        """Test basic cost estimation."""
        cost = client.estimate_cost(
            "test-prompt",
            label="prod",
            model="gpt-4",
            provider="openai",
            estimated_output_tokens=100
        )
        
        assert cost.input_tokens > 0
        assert cost.estimated_output_tokens == 100
        assert cost.total_cost > 0
        assert cost.model == "gpt-4"
        assert cost.provider == "openai"
    
    def test_estimate_cost_with_variables(self, client, sample_prompt):
        """Test cost estimation with variables."""
        cost = client.estimate_cost(
            "test-prompt",
            variables={"name": "Alice"},
            model="gpt-4",
            provider="openai",
            estimated_output_tokens=100
        )
        
        # Should have rendered the variable
        assert cost.input_tokens > 0
        assert cost.total_cost > 0
    
    def test_estimate_cost_different_models(self, client, sample_prompt):
        """Test cost estimation for different models."""
        cost_gpt4 = client.estimate_cost(
            "test-prompt",
            model="gpt-4",
            provider="openai"
        )
        
        cost_gpt35 = client.estimate_cost(
            "test-prompt",
            model="gpt-3.5-turbo",
            provider="openai"
        )
        
        # GPT-4 should be more expensive
        assert cost_gpt4.total_cost > cost_gpt35.total_cost
    
    def test_count_tokens_basic(self, client, sample_prompt):
        """Test basic token counting."""
        tokens = client.count_tokens(
            "test-prompt",
            label="prod",
            model="gpt-4",
            provider="openai"
        )
        
        assert tokens > 0
        assert isinstance(tokens, int)
    
    def test_count_tokens_with_variables(self, client, sample_prompt):
        """Test token counting with variables."""
        tokens_with_var = client.count_tokens(
            "test-prompt",
            variables={"name": "Alice"},
            model="gpt-4",
            provider="openai"
        )
        
        # Should count tokens of rendered content
        assert tokens_with_var > 0
    
    def test_compare_costs_basic(self, client, sample_prompt):
        """Test cost comparison across models."""
        models = [
            ("openai", "gpt-4"),
            ("openai", "gpt-3.5-turbo")
        ]
        
        comparisons = client.compare_costs(
            "test-prompt",
            models=models,
            label="prod",
            estimated_output_tokens=100
        )
        
        assert "openai/gpt-4" in comparisons
        assert "openai/gpt-3.5-turbo" in comparisons
        assert comparisons["openai/gpt-4"] is not None
        assert comparisons["openai/gpt-3.5-turbo"] is not None
        
        # GPT-4 should be more expensive
        assert comparisons["openai/gpt-4"].total_cost > comparisons["openai/gpt-3.5-turbo"].total_cost
    
    def test_compare_costs_with_variables(self, client, sample_prompt):
        """Test cost comparison with variables."""
        models = [
            ("openai", "gpt-4"),
            ("openai", "gpt-3.5-turbo")
        ]
        
        comparisons = client.compare_costs(
            "test-prompt",
            models=models,
            variables={"name": "Bob"},
            estimated_output_tokens=100
        )
        
        # Both should have results
        assert comparisons["openai/gpt-4"] is not None
        assert comparisons["openai/gpt-3.5-turbo"] is not None