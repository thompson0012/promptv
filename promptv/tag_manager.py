"""
Tag management for promptv - Git-like tag/label system.
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict
from promptv.models import Tag, TagRegistry
from promptv.exceptions import PromptNotFoundError, TagNotFoundError, TagAlreadyExistsError


class TagManager:
    """Manages tags/labels for prompt versions."""
    
    def __init__(self, prompts_dir: Path):
        """
        Initialize the TagManager.
        
        Args:
            prompts_dir: Path to the prompts directory
        """
        self.prompts_dir = prompts_dir
    
    def _get_tags_file(self, prompt_name: str, project: Optional[str] = None) -> Path:
        """Get the path to tags.json for a prompt."""
        if project:
            return self.prompts_dir / project / prompt_name / "tags.json"
        return self.prompts_dir / prompt_name / "tags.json"
    
    def _load_tags(self, prompt_name: str, project: Optional[str] = None) -> TagRegistry:
        """
        Load tags for a prompt.
        
        Args:
            prompt_name: Name of the prompt
            project: Optional project name
            
        Returns:
            TagRegistry object
        """
        tags_file = self._get_tags_file(prompt_name, project=project)
        
        if not tags_file.exists():
            # No tags yet - return empty registry
            return TagRegistry(prompt_name=prompt_name, tags={})
        
        try:
            with open(tags_file, 'r') as f:
                data = json.load(f)
            
            # Convert timestamp strings to datetime objects
            for tag_data in data.get("tags", {}).values():
                if isinstance(tag_data.get("created_at"), str):
                    tag_data["created_at"] = datetime.fromisoformat(tag_data["created_at"])
                if isinstance(tag_data.get("updated_at"), str):
                    tag_data["updated_at"] = datetime.fromisoformat(tag_data["updated_at"])
            
            return TagRegistry(**data)
            
        except Exception as e:
            # If there's an error, return empty registry
            return TagRegistry(prompt_name=prompt_name, tags={})
    
    def _save_tags(self, registry: TagRegistry, project: Optional[str] = None):
        """
        Save tags to disk.
        
        Args:
            registry: TagRegistry to save
            project: Optional project name
        """
        tags_file = self._get_tags_file(registry.prompt_name, project=project)
        tags_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dict
        data = registry.model_dump(mode='json')
        
        # Convert datetime objects to ISO format strings
        for tag_data in data.get("tags", {}).values():
            if "created_at" in tag_data:
                tag_data["created_at"] = tag_data["created_at"]
            if "updated_at" in tag_data:
                tag_data["updated_at"] = tag_data["updated_at"]
        
        with open(tags_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def create_tag(
        self,
        prompt_name: str,
        tag_name: str,
        version: int,
        description: Optional[str] = None,
        allow_update: bool = False,
        project: Optional[str] = None
    ) -> Tag:
        """
        Create or update a tag pointing to a specific version.
        
        Args:
            prompt_name: Name of the prompt
            tag_name: Name of the tag
            version: Version number to tag
            description: Optional description for the tag
            allow_update: If True, allow updating existing tags
            project: Optional project name
            
        Returns:
            The created/updated Tag object
            
        Raises:
            PromptNotFoundError: If the prompt doesn't exist
            TagAlreadyExistsError: If tag exists and allow_update is False
        """
        # Check if prompt exists
        prompt_dir = self.prompts_dir / prompt_name if not project else self.prompts_dir / project / prompt_name
        if not prompt_dir.exists():
            raise PromptNotFoundError(prompt_name)
        
        # Load existing tags
        registry = self._load_tags(prompt_name, project=project)
        
        # Check if tag already exists
        now = datetime.now()
        if tag_name in registry.tags:
            if not allow_update:
                raise TagAlreadyExistsError(tag_name, prompt_name)
            
            # Update existing tag
            tag = registry.tags[tag_name]
            tag.version = version
            tag.updated_at = now
            if description is not None:
                tag.description = description
        else:
            # Create new tag
            tag = Tag(
                name=tag_name,
                version=version,
                created_at=now,
                updated_at=now,
                description=description
            )
            registry.tags[tag_name] = tag
        
        # Save changes
        self._save_tags(registry, project=project)
        
        return tag
    
    def get_tag(self, prompt_name: str, tag_name: str, project: Optional[str] = None) -> Optional[Tag]:
        """
        Retrieve a specific tag.
        
        Args:
            prompt_name: Name of the prompt
            tag_name: Name of the tag
            project: Optional project name
            
        Returns:
            Tag object or None if not found
        """
        registry = self._load_tags(prompt_name, project=project)
        return registry.tags.get(tag_name)
    
    def list_tags(self, prompt_name: str, project: Optional[str] = None) -> Dict[str, Tag]:
        """
        List all tags for a prompt.
        
        Args:
            prompt_name: Name of the prompt
            project: Optional project name
            
        Returns:
            Dictionary of tag_name -> Tag
        """
        registry = self._load_tags(prompt_name, project=project)
        return registry.tags
    
    def delete_tag(self, prompt_name: str, tag_name: str, project: Optional[str] = None) -> bool:
        """
        Delete a tag.
        
        Args:
            prompt_name: Name of the prompt
            tag_name: Name of the tag to delete
            project: Optional project name
            
        Returns:
            True if tag was deleted, False if it didn't exist
            
        Raises:
            TagNotFoundError: If the tag doesn't exist
        """
        registry = self._load_tags(prompt_name, project=project)
        
        if tag_name not in registry.tags:
            raise TagNotFoundError(tag_name, prompt_name)
        
        # Remove the tag
        del registry.tags[tag_name]
        
        # Save changes
        self._save_tags(registry, project=project)
        
        return True
    
    def resolve_version(self, prompt_name: str, ref: str, max_version: int, project: Optional[str] = None) -> int:
        """
        Resolve a reference (tag name, 'latest', or version number) to a version number.
        
        Args:
            prompt_name: Name of the prompt
            ref: Reference to resolve ('latest', tag name, or version number)
            max_version: Maximum available version number
            project: Optional project name
            
        Returns:
            Resolved version number
            
        Raises:
            TagNotFoundError: If ref is a tag name that doesn't exist
            ValueError: If ref is not a valid reference
            
        Examples:
            >>> resolve_version("my-prompt", "latest", 5)
            5
            >>> resolve_version("my-prompt", "prod", 5)  # Assuming 'prod' tag points to v3
            3
            >>> resolve_version("my-prompt", "3", 5)
            3
        """
        # Handle 'latest'
        if ref == "latest":
            return max_version
        
        # Try to parse as integer (direct version number)
        is_number = False
        try:
            version = int(ref)
            is_number = True
            # Validate version is in range
            if 1 <= version <= max_version:
                return version
            else:
                raise ValueError(f"Version {version} is out of range (1-{max_version})")
        except ValueError as e:
            if is_number:
                # It was a number but out of range - re-raise ValueError
                raise
            # Not a number, try as tag
        
        # Try to resolve as tag
        tag = self.get_tag(prompt_name, ref, project=project)
        if tag:
            return tag.version
        
        # Not found
        raise TagNotFoundError(ref, prompt_name)