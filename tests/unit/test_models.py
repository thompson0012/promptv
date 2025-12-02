"""
Unit tests for promptv Pydantic models.
"""
import pytest
from datetime import datetime
from promptv.models import (
    VersionMetadata,
    PromptMetadata,
    Tag,
    TagRegistry,
    CostEstimate,
    CacheConfig,
    CostEstimationConfig,
    Config,
)


class TestVersionMetadata:
    """Tests for VersionMetadata model."""
    
    def test_version_metadata_creation(self):
        """Test creating a VersionMetadata instance."""
        now = datetime.now()
        metadata = VersionMetadata(
            version=1,
            timestamp=now,
            file_path="/path/to/file.md"
        )
        
        assert metadata.version == 1
        assert metadata.timestamp == now
        assert metadata.file_path == "/path/to/file.md"
        assert metadata.source_file is None
        assert metadata.author is None
        assert metadata.message is None
        assert metadata.variables == []
        assert metadata.token_count is None
    
    def test_version_metadata_with_all_fields(self):
        """Test VersionMetadata with all fields populated."""
        now = datetime.now()
        metadata = VersionMetadata(
            version=2,
            timestamp=now,
            source_file="/src/prompt.txt",
            file_path="/path/to/file.md",
            author="John Doe",
            message="Added new features",
            variables=["user_name", "topic"],
            token_count=150
        )
        
        assert metadata.version == 2
        assert metadata.author == "John Doe"
        assert metadata.message == "Added new features"
        assert metadata.variables == ["user_name", "topic"]
        assert metadata.token_count == 150
    
    def test_version_metadata_serialization(self):
        """Test VersionMetadata JSON serialization."""
        now = datetime.now()
        metadata = VersionMetadata(
            version=1,
            timestamp=now,
            file_path="/path/to/file.md"
        )
        
        data = metadata.model_dump()
        assert data["version"] == 1
        assert isinstance(data["timestamp"], datetime)
        assert data["file_path"] == "/path/to/file.md"


class TestPromptMetadata:
    """Tests for PromptMetadata model."""
    
    def test_prompt_metadata_creation(self):
        """Test creating a PromptMetadata instance."""
        now = datetime.now()
        version = VersionMetadata(
            version=1,
            timestamp=now,
            file_path="/path/to/file.md"
        )
        
        metadata = PromptMetadata(
            name="test-prompt",
            versions=[version],
            current_version=1,
            created_at=now,
            updated_at=now
        )
        
        assert metadata.name == "test-prompt"
        assert len(metadata.versions) == 1
        assert metadata.current_version == 1
        assert metadata.description is None
    
    def test_prompt_metadata_multiple_versions(self):
        """Test PromptMetadata with multiple versions."""
        now = datetime.now()
        versions = [
            VersionMetadata(version=i, timestamp=now, file_path=f"/path/v{i}.md")
            for i in range(1, 4)
        ]
        
        metadata = PromptMetadata(
            name="test-prompt",
            versions=versions,
            current_version=3,
            created_at=now,
            updated_at=now,
            description="Test prompt description"
        )
        
        assert len(metadata.versions) == 3
        assert metadata.current_version == 3
        assert metadata.description == "Test prompt description"


class TestTag:
    """Tests for Tag model."""
    
    def test_tag_creation(self):
        """Test creating a Tag instance."""
        now = datetime.now()
        tag = Tag(
            name="prod",
            version=5,
            created_at=now,
            updated_at=now
        )
        
        assert tag.name == "prod"
        assert tag.version == 5
        assert tag.description is None
    
    def test_tag_with_description(self):
        """Test Tag with description."""
        now = datetime.now()
        tag = Tag(
            name="v1.0.0",
            version=10,
            created_at=now,
            updated_at=now,
            description="First stable release"
        )
        
        assert tag.description == "First stable release"


class TestTagRegistry:
    """Tests for TagRegistry model."""
    
    def test_tag_registry_creation(self):
        """Test creating a TagRegistry instance."""
        registry = TagRegistry(prompt_name="test-prompt")
        
        assert registry.prompt_name == "test-prompt"
        assert registry.tags == {}
    
    def test_tag_registry_with_tags(self):
        """Test TagRegistry with tags."""
        now = datetime.now()
        tag1 = Tag(name="prod", version=5, created_at=now, updated_at=now)
        tag2 = Tag(name="staging", version=6, created_at=now, updated_at=now)
        
        registry = TagRegistry(
            prompt_name="test-prompt",
            tags={"prod": tag1, "staging": tag2}
        )
        
        assert len(registry.tags) == 2
        assert registry.tags["prod"].version == 5
        assert registry.tags["staging"].version == 6


class TestCostEstimate:
    """Tests for CostEstimate model."""
    
    def test_cost_estimate_creation(self):
        """Test creating a CostEstimate instance."""
        estimate = CostEstimate(
            input_tokens=100,
            estimated_output_tokens=500,
            total_tokens=600,
            input_cost=0.003,
            estimated_output_cost=0.015,
            total_cost=0.018,
            model="gpt-4",
            provider="openai"
        )
        
        assert estimate.input_tokens == 100
        assert estimate.estimated_output_tokens == 500
        assert estimate.total_tokens == 600
        assert estimate.total_cost == 0.018
        assert estimate.model == "gpt-4"
        assert estimate.provider == "openai"


class TestConfig:
    """Tests for configuration models."""
    
    def test_cache_config_defaults(self):
        """Test CacheConfig default values."""
        config = CacheConfig()
        
        assert config.enabled is True
        assert config.ttl_seconds == 300
        assert config.max_entries == 100
    
    def test_cost_estimation_config_defaults(self):
        """Test CostEstimationConfig default values."""
        config = CostEstimationConfig()
        
        assert config.confirm_threshold == 0.10
        assert config.default_output_tokens == 500
        assert config.default_model == "gpt-4"
        assert config.default_provider == "openai"
    
    def test_main_config_creation(self):
        """Test main Config with defaults."""
        config = Config()
        
        assert config.cache.enabled is True
        assert config.cost_estimation.default_model == "gpt-4"
    
    def test_main_config_customization(self):
        """Test main Config with custom values."""
        config = Config(
            cache=CacheConfig(enabled=False, ttl_seconds=600),
            cost_estimation=CostEstimationConfig(default_model="gpt-3.5-turbo")
        )
        
        assert config.cache.enabled is False
        assert config.cache.ttl_seconds == 600
        assert config.cost_estimation.default_model == "gpt-3.5-turbo"