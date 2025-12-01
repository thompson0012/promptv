"""
Integration tests for PromptClient SDK.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from promptv.sdk.client import PromptClient
from promptv.manager import PromptManager
from promptv.tag_manager import TagManager
from promptv.exceptions import PromptNotFoundError


class TestSDKIntegration:
    """Integration tests for SDK with real components."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path)
    
    @pytest.fixture
    def setup_prompts(self, temp_dir):
        """Set up a complete prompt environment."""
        manager = PromptManager()
        manager.base_dir = temp_dir
        manager.prompts_dir = temp_dir / "prompts"
        manager.config_dir = temp_dir / ".config"
        manager._initialize_directories()
        
        # Create multiple prompts with versions
        manager.set_prompt("onboarding-email", "Hello {{user_name}},\n\nWelcome to {{product}}!")
        manager.set_prompt("onboarding-email", "Hi {{user_name}},\n\nWelcome to {{product}}!\n\nBest regards")
        manager.set_prompt("reminder", "Don't forget: {{task}}")
        
        # Create tags
        tag_manager = TagManager(manager.prompts_dir)
        tag_manager.create_tag("onboarding-email", "prod", 1)
        tag_manager.create_tag("onboarding-email", "staging", 2)
        tag_manager.create_tag("reminder", "latest", 1)
        
        return manager
    
    def test_end_to_end_get_prompt(self, temp_dir, setup_prompts):
        """Test end-to-end prompt retrieval."""
        client = PromptClient(base_dir=temp_dir)
        
        # Get latest version
        content = client.get_prompt("onboarding-email")
        assert "Hi {{user_name}}" in content
        assert "Best regards" in content
    
    def test_end_to_end_get_with_label(self, temp_dir, setup_prompts):
        """Test end-to-end prompt retrieval with label."""
        client = PromptClient(base_dir=temp_dir)
        
        # Get prod version
        content = client.get_prompt("onboarding-email", label="prod")
        assert "Hello {{user_name}}" in content
        assert "Best regards" not in content
        
        # Get staging version
        content = client.get_prompt("onboarding-email", label="staging")
        assert "Hi {{user_name}}" in content
        assert "Best regards" in content
    
    def test_end_to_end_with_variables(self, temp_dir, setup_prompts):
        """Test end-to-end with variable rendering."""
        client = PromptClient(base_dir=temp_dir)
        
        content = client.get_prompt(
            "onboarding-email",
            label="prod",
            variables={
                "user_name": "Alice",
                "product": "PromptV"
            }
        )
        
        assert content == "Hello Alice,\n\nWelcome to PromptV!"
    
    def test_end_to_end_caching_behavior(self, temp_dir, setup_prompts):
        """Test end-to-end caching behavior."""
        client = PromptClient(base_dir=temp_dir, cache_ttl=300)
        
        # First retrieval - should cache
        content1 = client.get_prompt("onboarding-email", label="prod")
        cache_stats1 = client.get_cache_stats()
        assert cache_stats1["cached_count"] == 1
        
        # Second retrieval - should use cache
        content2 = client.get_prompt("onboarding-email", label="prod")
        assert content1 == content2
        cache_stats2 = client.get_cache_stats()
        assert cache_stats2["cached_count"] == 1  # Same cache entry
        
        # Different label - should create new cache entry
        content3 = client.get_prompt("onboarding-email", label="staging")
        cache_stats3 = client.get_cache_stats()
        assert cache_stats3["cached_count"] == 2
    
    def test_end_to_end_list_operations(self, temp_dir, setup_prompts):
        """Test end-to-end listing operations."""
        client = PromptClient(base_dir=temp_dir)
        
        # List all prompts
        prompts = client.list_prompts()
        assert "onboarding-email" in prompts
        assert "reminder" in prompts
        assert len(prompts) == 2
        
        # Get versions
        versions = client.get_versions("onboarding-email")
        assert len(versions) == 2
        assert versions[0].version == 1
        assert versions[1].version == 2
        
        # Get tags
        tags = client.get_tags("onboarding-email")
        assert "prod" in tags
        assert "staging" in tags
        assert tags["prod"] == 1
        assert tags["staging"] == 2
    
    def test_end_to_end_with_metadata(self, temp_dir, setup_prompts):
        """Test end-to-end metadata retrieval."""
        client = PromptClient(base_dir=temp_dir)
        
        content, metadata = client.get_prompt_with_metadata(
            "onboarding-email",
            label="prod"
        )
        
        assert "Hello {{user_name}}" in content
        assert metadata.version == 1
    
    def test_context_manager_workflow(self, temp_dir, setup_prompts):
        """Test full workflow with context manager."""
        with PromptClient(base_dir=temp_dir) as client:
            # List prompts
            prompts = client.list_prompts()
            assert len(prompts) == 2
            
            # Get prompt with variables
            content = client.get_prompt(
                "reminder",
                variables={"task": "Review PR"}
            )
            assert content == "Don't forget: Review PR"
            
            # Check cache was used
            stats = client.get_cache_stats()
            assert stats["cached_count"] == 1
    
    def test_multiple_versions_workflow(self, temp_dir, setup_prompts):
        """Test workflow with multiple versions."""
        client = PromptClient(base_dir=temp_dir)
        
        # Get specific versions
        v1 = client.get_prompt("onboarding-email", version=1)
        v2 = client.get_prompt("onboarding-email", version=2)
        
        assert v1 != v2
        assert "Hello" in v1
        assert "Hi" in v2
        
        # Both should be cached separately
        stats = client.get_cache_stats()
        assert stats["cached_count"] == 2
    
    def test_error_handling_workflow(self, temp_dir, setup_prompts):
        """Test error handling in real workflow."""
        client = PromptClient(base_dir=temp_dir)
        
        # Non-existent prompt
        with pytest.raises(PromptNotFoundError):
            client.get_prompt("non-existent")
        
        # Non-existent label
        from promptv.exceptions import TagNotFoundError
        with pytest.raises(TagNotFoundError):
            client.get_prompt("onboarding-email", label="non-existent")
        
        # Both label and version
        with pytest.raises(ValueError):
            client.get_prompt("onboarding-email", label="prod", version=1)
    
    def test_cache_invalidation_workflow(self, temp_dir, setup_prompts):
        """Test cache invalidation workflow."""
        client = PromptClient(base_dir=temp_dir)
        
        # Cache multiple prompts
        client.get_prompt("onboarding-email")
        client.get_prompt("reminder")
        assert client.get_cache_stats()["cached_count"] == 2
        
        # Clear cache
        client.clear_cache()
        assert client.get_cache_stats()["cached_count"] == 0
        
        # Retrieve again - should cache again
        client.get_prompt("onboarding-email")
        assert client.get_cache_stats()["cached_count"] == 1
    
    def test_complex_variable_rendering(self, temp_dir, setup_prompts):
        """Test complex variable rendering scenarios."""
        # Create a prompt with multiple variables
        manager = PromptManager()
        manager.base_dir = temp_dir
        manager.prompts_dir = temp_dir / "prompts"
        manager.config_dir = temp_dir / ".config"
        
        manager.set_prompt(
            "complex",
            "Name: {{name}}\nAge: {{age}}\nCity: {{city}}"
        )
        
        client = PromptClient(base_dir=temp_dir)
        content = client.get_prompt(
            "complex",
            variables={
                "name": "Alice",
                "age": 30,
                "city": "San Francisco"
            }
        )
        
        assert "Name: Alice" in content
        assert "Age: 30" in content
        assert "City: San Francisco" in content
    
    def test_tag_manager_integration(self, temp_dir, setup_prompts):
        """Test integration with TagManager."""
        client = PromptClient(base_dir=temp_dir)
        
        # Verify tag resolution works correctly
        prod_content = client.get_prompt("onboarding-email", label="prod")
        staging_content = client.get_prompt("onboarding-email", label="staging")
        
        assert prod_content != staging_content
        
        # Verify tags are correctly mapped
        tags = client.get_tags("onboarding-email")
        assert tags["prod"] == 1
        assert tags["staging"] == 2
