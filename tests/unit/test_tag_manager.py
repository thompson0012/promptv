"""
Unit tests for TagManager.
"""
import pytest
import json
from pathlib import Path
from datetime import datetime
from promptv.tag_manager import TagManager
from promptv.models import Tag, TagRegistry
from promptv.exceptions import PromptNotFoundError, TagNotFoundError, TagAlreadyExistsError


@pytest.fixture
def temp_prompts_dir(tmp_path):
    """Create a temporary prompts directory."""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    return prompts_dir


@pytest.fixture
def tag_manager(temp_prompts_dir):
    """Create a TagManager instance."""
    return TagManager(temp_prompts_dir)


@pytest.fixture
def sample_prompt(temp_prompts_dir):
    """Create a sample prompt directory."""
    prompt_dir = temp_prompts_dir / "test-prompt"
    prompt_dir.mkdir()
    
    # Create some version files
    (prompt_dir / "v1.md").write_text("Version 1 content")
    (prompt_dir / "v2.md").write_text("Version 2 content")
    (prompt_dir / "v3.md").write_text("Version 3 content")
    
    return "test-prompt"


@pytest.fixture
def sample_project_prompt(temp_prompts_dir):
    """Create a sample prompt directory with project."""
    project_dir = temp_prompts_dir / "my-app"
    project_dir.mkdir()
    prompt_dir = project_dir / "test-prompt"
    prompt_dir.mkdir()
    
    # Create some version files
    (prompt_dir / "v1.md").write_text("Version 1 content")
    (prompt_dir / "v2.md").write_text("Version 2 content")
    (prompt_dir / "v3.md").write_text("Version 3 content")
    
    return "test-prompt", "my-app"


class TestTagManagerInit:
    """Test TagManager initialization."""
    
    def test_init(self, temp_prompts_dir):
        """Test TagManager initialization."""
        manager = TagManager(temp_prompts_dir)
        assert manager.prompts_dir == temp_prompts_dir


class TestCreateTag:
    """Test tag creation."""
    
    def test_create_tag_new(self, tag_manager, sample_prompt):
        """Test creating a new tag."""
        tag = tag_manager.create_tag(
            prompt_name=sample_prompt,
            tag_name="prod",
            version=2,
            description="Production release"
        )
        
        assert tag.name == "prod"
        assert tag.version == 2
        assert tag.description == "Production release"
        assert isinstance(tag.created_at, datetime)
        assert isinstance(tag.updated_at, datetime)
        assert tag.created_at == tag.updated_at
    
    def test_create_tag_without_description(self, tag_manager, sample_prompt):
        """Test creating a tag without description."""
        tag = tag_manager.create_tag(
            prompt_name=sample_prompt,
            tag_name="staging",
            version=1
        )
        
        assert tag.name == "staging"
        assert tag.version == 1
        assert tag.description is None
    
    def test_create_tag_prompt_not_found(self, tag_manager):
        """Test creating a tag for non-existent prompt."""
        with pytest.raises(PromptNotFoundError) as exc_info:
            tag_manager.create_tag(
                prompt_name="nonexistent",
                tag_name="prod",
                version=1
            )
        assert "nonexistent" in str(exc_info.value)
    
    def test_create_tag_duplicate_fails(self, tag_manager, sample_prompt):
        """Test creating duplicate tag fails without allow_update."""
        # Create initial tag
        tag_manager.create_tag(
            prompt_name=sample_prompt,
            tag_name="prod",
            version=1
        )
        
        # Try to create again
        with pytest.raises(TagAlreadyExistsError) as exc_info:
            tag_manager.create_tag(
                prompt_name=sample_prompt,
                tag_name="prod",
                version=2
            )
        assert "prod" in str(exc_info.value)
        assert sample_prompt in str(exc_info.value)
    
    def test_create_tag_duplicate_with_update(self, tag_manager, sample_prompt):
        """Test updating existing tag with allow_update=True."""
        # Create initial tag
        tag1 = tag_manager.create_tag(
            prompt_name=sample_prompt,
            tag_name="prod",
            version=1,
            description="Initial"
        )
        
        # Update tag
        tag2 = tag_manager.create_tag(
            prompt_name=sample_prompt,
            tag_name="prod",
            version=3,
            description="Updated",
            allow_update=True
        )
        
        assert tag2.name == "prod"
        assert tag2.version == 3
        assert tag2.description == "Updated"
        assert tag2.created_at == tag1.created_at
        assert tag2.updated_at > tag1.updated_at
    
    def test_create_tag_persistence(self, tag_manager, sample_prompt, temp_prompts_dir):
        """Test that tags are persisted to disk."""
        tag_manager.create_tag(
            prompt_name=sample_prompt,
            tag_name="prod",
            version=2
        )
        
        # Check file exists
        tags_file = temp_prompts_dir / sample_prompt / "tags.json"
        assert tags_file.exists()
        
        # Check file content
        with open(tags_file, 'r') as f:
            data = json.load(f)
        
        assert data["prompt_name"] == sample_prompt
        assert "prod" in data["tags"]
        assert data["tags"]["prod"]["version"] == 2


class TestGetTag:
    """Test tag retrieval."""
    
    def test_get_existing_tag(self, tag_manager, sample_prompt):
        """Test retrieving an existing tag."""
        # Create a tag
        created_tag = tag_manager.create_tag(
            prompt_name=sample_prompt,
            tag_name="prod",
            version=2,
            description="Production"
        )
        
        # Retrieve it
        retrieved_tag = tag_manager.get_tag(sample_prompt, "prod")
        
        assert retrieved_tag is not None
        assert retrieved_tag.name == created_tag.name
        assert retrieved_tag.version == created_tag.version
        assert retrieved_tag.description == created_tag.description
    
    def test_get_nonexistent_tag(self, tag_manager, sample_prompt):
        """Test retrieving a tag that doesn't exist."""
        tag = tag_manager.get_tag(sample_prompt, "nonexistent")
        assert tag is None
    
    def test_get_tag_from_nonexistent_prompt(self, tag_manager):
        """Test retrieving a tag from a prompt that doesn't exist."""
        tag = tag_manager.get_tag("nonexistent-prompt", "prod")
        assert tag is None


class TestListTags:
    """Test listing tags."""
    
    def test_list_tags_empty(self, tag_manager, sample_prompt):
        """Test listing tags when none exist."""
        tags = tag_manager.list_tags(sample_prompt)
        assert tags == {}
    
    def test_list_single_tag(self, tag_manager, sample_prompt):
        """Test listing a single tag."""
        tag_manager.create_tag(sample_prompt, "prod", 2)
        
        tags = tag_manager.list_tags(sample_prompt)
        assert len(tags) == 1
        assert "prod" in tags
        assert tags["prod"].version == 2
    
    def test_list_multiple_tags(self, tag_manager, sample_prompt):
        """Test listing multiple tags."""
        tag_manager.create_tag(sample_prompt, "prod", 2, "Production")
        tag_manager.create_tag(sample_prompt, "staging", 3, "Staging")
        tag_manager.create_tag(sample_prompt, "dev", 3, "Development")
        
        tags = tag_manager.list_tags(sample_prompt)
        assert len(tags) == 3
        assert "prod" in tags
        assert "staging" in tags
        assert "dev" in tags
        assert tags["prod"].version == 2
        assert tags["staging"].version == 3
    
    def test_list_tags_nonexistent_prompt(self, tag_manager):
        """Test listing tags for a prompt that doesn't exist."""
        tags = tag_manager.list_tags("nonexistent")
        assert tags == {}


class TestDeleteTag:
    """Test tag deletion."""
    
    def test_delete_existing_tag(self, tag_manager, sample_prompt):
        """Test deleting an existing tag."""
        tag_manager.create_tag(sample_prompt, "prod", 2)
        
        # Delete it
        result = tag_manager.delete_tag(sample_prompt, "prod")
        assert result is True
        
        # Verify it's gone
        tags = tag_manager.list_tags(sample_prompt)
        assert "prod" not in tags
    
    def test_delete_nonexistent_tag(self, tag_manager, sample_prompt):
        """Test deleting a tag that doesn't exist."""
        with pytest.raises(TagNotFoundError) as exc_info:
            tag_manager.delete_tag(sample_prompt, "nonexistent")
        assert "nonexistent" in str(exc_info.value)
    
    def test_delete_one_of_many_tags(self, tag_manager, sample_prompt):
        """Test deleting one tag while others remain."""
        tag_manager.create_tag(sample_prompt, "prod", 1)
        tag_manager.create_tag(sample_prompt, "staging", 2)
        tag_manager.create_tag(sample_prompt, "dev", 3)
        
        # Delete staging
        tag_manager.delete_tag(sample_prompt, "staging")
        
        # Check remaining tags
        tags = tag_manager.list_tags(sample_prompt)
        assert len(tags) == 2
        assert "prod" in tags
        assert "dev" in tags
        assert "staging" not in tags
    
    def test_delete_tag_persistence(self, tag_manager, sample_prompt, temp_prompts_dir):
        """Test that tag deletion is persisted."""
        tag_manager.create_tag(sample_prompt, "prod", 1)
        tag_manager.create_tag(sample_prompt, "staging", 2)
        
        # Delete one
        tag_manager.delete_tag(sample_prompt, "prod")
        
        # Check file content
        tags_file = temp_prompts_dir / sample_prompt / "tags.json"
        with open(tags_file, 'r') as f:
            data = json.load(f)
        
        assert "prod" not in data["tags"]
        assert "staging" in data["tags"]


class TestResolveVersion:
    """Test version resolution."""
    
    def test_resolve_latest(self, tag_manager, sample_prompt):
        """Test resolving 'latest' to max version."""
        version = tag_manager.resolve_version(sample_prompt, "latest", max_version=5)
        assert version == 5
    
    def test_resolve_version_number(self, tag_manager, sample_prompt):
        """Test resolving a direct version number."""
        version = tag_manager.resolve_version(sample_prompt, "3", max_version=5)
        assert version == 3
    
    def test_resolve_version_number_as_int(self, tag_manager, sample_prompt):
        """Test resolving an integer version number."""
        version = tag_manager.resolve_version(sample_prompt, "2", max_version=5)
        assert version == 2
    
    def test_resolve_tag_name(self, tag_manager, sample_prompt):
        """Test resolving a tag name to version."""
        # Create a tag
        tag_manager.create_tag(sample_prompt, "prod", 3)
        
        # Resolve it
        version = tag_manager.resolve_version(sample_prompt, "prod", max_version=5)
        assert version == 3
    
    def test_resolve_version_out_of_range(self, tag_manager, sample_prompt):
        """Test resolving version number out of range."""
        with pytest.raises(ValueError) as exc_info:
            tag_manager.resolve_version(sample_prompt, "10", max_version=5)
        assert "out of range" in str(exc_info.value)
    
    def test_resolve_nonexistent_tag(self, tag_manager, sample_prompt):
        """Test resolving a tag that doesn't exist."""
        with pytest.raises(TagNotFoundError) as exc_info:
            tag_manager.resolve_version(sample_prompt, "nonexistent", max_version=5)
        assert "nonexistent" in str(exc_info.value)
    
    def test_resolve_zero_version(self, tag_manager, sample_prompt):
        """Test resolving version 0 (invalid)."""
        with pytest.raises(ValueError) as exc_info:
            tag_manager.resolve_version(sample_prompt, "0", max_version=5)
        assert "out of range" in str(exc_info.value)


class TestTagsPersistence:
    """Test tags file persistence and loading."""
    
    def test_load_empty_tags(self, tag_manager, sample_prompt):
        """Test loading tags when no tags.json exists."""
        registry = tag_manager._load_tags(sample_prompt)
        assert registry.prompt_name == sample_prompt
        assert registry.tags == {}
    
    def test_save_and_load_tags(self, tag_manager, sample_prompt):
        """Test saving and loading tags."""
        # Create tags
        tag_manager.create_tag(sample_prompt, "prod", 2, "Production")
        tag_manager.create_tag(sample_prompt, "staging", 3, "Staging")
        
        # Load tags
        registry = tag_manager._load_tags(sample_prompt)
        assert len(registry.tags) == 2
        assert "prod" in registry.tags
        assert "staging" in registry.tags
        assert registry.tags["prod"].version == 2
        assert registry.tags["staging"].version == 3
    
    def test_tags_file_format(self, tag_manager, sample_prompt, temp_prompts_dir):
        """Test that tags.json has correct format."""
        tag_manager.create_tag(sample_prompt, "prod", 2, "Production")
        
        tags_file = temp_prompts_dir / sample_prompt / "tags.json"
        with open(tags_file, 'r') as f:
            data = json.load(f)
        
        assert "prompt_name" in data
        assert "tags" in data
        assert data["prompt_name"] == sample_prompt
        assert isinstance(data["tags"], dict)
        
        prod_tag = data["tags"]["prod"]
        assert prod_tag["name"] == "prod"
        assert prod_tag["version"] == 2
        assert prod_tag["description"] == "Production"
        assert "created_at" in prod_tag
        assert "updated_at" in prod_tag
    
    def test_datetime_serialization(self, tag_manager, sample_prompt, temp_prompts_dir):
        """Test that datetime objects are properly serialized."""
        tag_manager.create_tag(sample_prompt, "prod", 2)
        
        tags_file = temp_prompts_dir / sample_prompt / "tags.json"
        with open(tags_file, 'r') as f:
            data = json.load(f)
        
        prod_tag = data["tags"]["prod"]
        # Timestamps should be ISO format strings in JSON
        assert isinstance(prod_tag["created_at"], str)
        assert isinstance(prod_tag["updated_at"], str)
        
        # Should be valid ISO format
        datetime.fromisoformat(prod_tag["created_at"])
        datetime.fromisoformat(prod_tag["updated_at"])
    
    def test_reload_from_disk(self, tag_manager, sample_prompt, temp_prompts_dir):
        """Test reloading tags from disk in a new TagManager instance."""
        # Create tags
        tag_manager.create_tag(sample_prompt, "prod", 2)
        
        # Create new TagManager instance
        new_manager = TagManager(temp_prompts_dir)
        
        # Load tags with new manager
        tag = new_manager.get_tag(sample_prompt, "prod")
        assert tag is not None
        assert tag.version == 2


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_create_tag_with_special_characters(self, tag_manager, sample_prompt):
        """Test creating tags with various valid names."""
        valid_names = ["v1.0.0", "staging-v2", "prod_release", "beta-1"]
        
        for i, name in enumerate(valid_names, start=1):
            tag = tag_manager.create_tag(sample_prompt, name, i)
            assert tag.name == name
    
    def test_multiple_tags_same_version(self, tag_manager, sample_prompt):
        """Test creating multiple tags pointing to the same version."""
        tag_manager.create_tag(sample_prompt, "prod", 2)
        tag_manager.create_tag(sample_prompt, "stable", 2)
        tag_manager.create_tag(sample_prompt, "release-1.0", 2)
        
        tags = tag_manager.list_tags(sample_prompt)
        assert len(tags) == 3
        assert all(tag.version == 2 for tag in tags.values())
    
    def test_update_tag_description_only(self, tag_manager, sample_prompt):
        """Test updating just the description of a tag."""
        tag_manager.create_tag(sample_prompt, "prod", 2, "Initial")
        
        # Update with same version but new description
        tag = tag_manager.create_tag(
            sample_prompt,
            "prod",
            2,
            "Updated description",
            allow_update=True
        )
        
        assert tag.version == 2
        assert tag.description == "Updated description"
    
    def test_empty_prompt_name(self, tag_manager, temp_prompts_dir):
        """Test handling empty prompt name."""
        # Create an empty prompt directory
        (temp_prompts_dir / "").mkdir(exist_ok=True)
        
        # Empty prompt name should be handled gracefully
        # The directory "" will exist but it's not a valid prompt
        # This test ensures we don't crash on edge cases
        tags = tag_manager.list_tags("")
        assert tags == {}


class TestProjectBasedTags:
    """Test project-based tag functionality."""
    
    def test_create_tag_with_project(self, tag_manager, sample_project_prompt):
        """Test creating a tag with project parameter."""
        prompt_name, project = sample_project_prompt
        
        tag = tag_manager.create_tag(
            prompt_name=prompt_name,
            tag_name="prod",
            version=2,
            description="Production release",
            project=project
        )
        
        assert tag.name == "prod"
        assert tag.version == 2
        assert tag.description == "Production release"
    
    def test_list_tags_with_project(self, tag_manager, sample_project_prompt):
        """Test listing tags with project parameter."""
        prompt_name, project = sample_project_prompt
        
        # Create tags
        tag_manager.create_tag(prompt_name, "prod", 2, project=project)
        tag_manager.create_tag(prompt_name, "staging", 1, project=project)
        
        # List tags
        tags = tag_manager.list_tags(prompt_name, project=project)
        assert len(tags) == 2
        assert "prod" in tags
        assert "staging" in tags
    
    def test_get_tag_with_project(self, tag_manager, sample_project_prompt):
        """Test getting a tag with project parameter."""
        prompt_name, project = sample_project_prompt
        
        # Create tag
        tag_manager.create_tag(prompt_name, "prod", 2, project=project)
        
        # Get tag
        tag = tag_manager.get_tag(prompt_name, "prod", project=project)
        assert tag is not None
        assert tag.version == 2
    
    def test_delete_tag_with_project(self, tag_manager, sample_project_prompt):
        """Test deleting a tag with project parameter."""
        prompt_name, project = sample_project_prompt
        
        # Create tag
        tag_manager.create_tag(prompt_name, "prod", 2, project=project)
        
        # Delete tag
        result = tag_manager.delete_tag(prompt_name, "prod", project=project)
        assert result is True
        
        # Verify deleted
        tag = tag_manager.get_tag(prompt_name, "prod", project=project)
        assert tag is None
    
    def test_resolve_version_with_project(self, tag_manager, sample_project_prompt):
        """Test resolving version with project parameter."""
        prompt_name, project = sample_project_prompt
        
        # Create tag
        tag_manager.create_tag(prompt_name, "prod", 2, project=project)
        
        # Resolve version
        version = tag_manager.resolve_version(prompt_name, "prod", 3, project=project)
        assert version == 2
    
    def test_project_and_non_project_tags_separate(self, tag_manager, sample_prompt, sample_project_prompt):
        """Test that project-based and non-project tags are separate."""
        prompt_name, project = sample_project_prompt
        
        # Create tag without project
        tag_manager.create_tag(sample_prompt, "prod", 1)
        
        # Create tag with project (same prompt name)
        tag_manager.create_tag(prompt_name, "prod", 2, project=project)
        
        # Verify they're separate
        tag_no_project = tag_manager.get_tag(sample_prompt, "prod")
        tag_with_project = tag_manager.get_tag(prompt_name, "prod", project=project)
        
        assert tag_no_project.version == 1
        assert tag_with_project.version == 2