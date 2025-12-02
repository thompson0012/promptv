import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Tuple
from promptv.models import PromptMetadata, VersionMetadata
from promptv.variable_engine import VariableEngine
from promptv.exceptions import PromptNotFoundError, VersionNotFoundError, MetadataCorruptedError
from promptv.config_manager import ConfigManager


# Lazy import to avoid circular dependency
def _get_cost_estimator():
    """Lazy import of CostEstimator to avoid circular dependencies."""
    from promptv.cost_estimator import CostEstimator
    return CostEstimator()


class PromptManager:
    """Manages prompt storage, versioning, and metadata."""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.config = self.config_manager.get_config()
        
        self.home_dir = Path.home()
        
        # Determine base directory based on execution mode
        if self.config.execution.mode == "cloud":
            # Cloud mode - still use local cache but mark for cloud sync
            self.base_dir = self.home_dir / ".promptv"
            self.is_cloud_mode = True
        else:
            # Local mode
            self.base_dir = self.home_dir / ".promptv"
            self.is_cloud_mode = False
        
        self.config_dir = self.base_dir / ".config"
        self.prompts_dir = self.base_dir / "prompts"
        self.variable_engine = VariableEngine()
        self._initialize_directories()
    
    def _initialize_directories(self):
        """Create necessary directories if they don't exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.prompts_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_prompt_dir(self, name: str, project: Optional[str] = None) -> Path:
        """Get the directory for a specific prompt name."""
        if project:
            return self.prompts_dir / project / name
        return self.prompts_dir / name
    
    def _get_metadata_file(self, name: str, project: Optional[str] = None) -> Path:
        """Get the metadata file path for a prompt."""
        return self._get_prompt_dir(name, project=project) / "metadata.json"
    
    def _load_metadata(self, name: str, project: Optional[str] = None) -> PromptMetadata:
        """
        Load metadata for a prompt.
        
        Handles both old and new metadata formats for backward compatibility.
        """
        metadata_file = self._get_metadata_file(name, project=project)
        
        if not metadata_file.exists():
            # New prompt - create initial metadata
            now = datetime.now()
            return PromptMetadata(
                name=name,
                versions=[],
                current_version=0,
                created_at=now,
                updated_at=now
            )
        
        try:
            with open(metadata_file, 'r') as f:
                data = json.load(f)
            
            # Check if this is old format (just versions list)
            if "versions" in data and "current_version" not in data:
                # Migrate old format to new format
                return self._migrate_metadata(name, data)
            
            # Parse as new format
            # Convert timestamp strings back to datetime objects
            if isinstance(data.get("created_at"), str):
                data["created_at"] = datetime.fromisoformat(data["created_at"])
            if isinstance(data.get("updated_at"), str):
                data["updated_at"] = datetime.fromisoformat(data["updated_at"])
            
            # Convert version timestamps
            for version_data in data.get("versions", []):
                if isinstance(version_data.get("timestamp"), str):
                    version_data["timestamp"] = datetime.fromisoformat(version_data["timestamp"])
            
            return PromptMetadata(**data)
            
        except Exception as e:
            raise MetadataCorruptedError(name, str(e))
    
    def _migrate_metadata(self, name: str, old_data: Dict) -> PromptMetadata:
        """Migrate old metadata format to new format."""
        versions = []
        now = datetime.now()
        
        for version_data in old_data.get("versions", []):
            # Convert timestamp string to datetime
            timestamp = version_data.get("timestamp")
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            
            # Create VersionMetadata from old format
            version_meta = VersionMetadata(
                version=version_data["version"],
                timestamp=timestamp,
                source_file=version_data.get("source_file"),
                file_path=version_data["file_path"],
                author=None,  # Old format didn't have author
                message=None,  # Old format didn't have message
                variables=[],  # Extract variables from file if exists
                token_count=None  # Will be computed later if needed
            )
            
            # Try to extract variables from existing file
            try:
                file_path = Path(version_meta.file_path)
                if file_path.exists():
                    with open(file_path, 'r') as f:
                        content = f.read()
                    version_meta.variables = self.extract_variables(content)
            except Exception:
                pass  # Skip variable extraction on error
            
            versions.append(version_meta)
        
        current_version = max((v.version for v in versions), default=0)
        created_at = versions[0].timestamp if versions else now
        
        return PromptMetadata(
            name=name,
            versions=versions,
            current_version=current_version,
            created_at=created_at,
            updated_at=now,
            description=None
        )
    
    def _save_metadata(self, metadata: PromptMetadata, project: Optional[str] = None):
        """Save metadata for a prompt."""
        metadata_file = self._get_metadata_file(metadata.name, project=project)
        metadata_file.parent.mkdir(parents=True, exist_ok=True)
        
        data = metadata.model_dump(mode='json')
        
        data["created_at"] = metadata.created_at.isoformat()
        data["updated_at"] = metadata.updated_at.isoformat()
        
        for version_data in data["versions"]:
            if "timestamp" in version_data:
                version_data["timestamp"] = version_data["timestamp"]
        
        with open(metadata_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _convert_to_markdown(self, content: str, source_path: Optional[str] = None) -> str:
        """Convert content to markdown format if needed."""
        # If source file has extension and it's not .md, we might need conversion
        # For now, we'll just ensure the content is treated as markdown
        return content
    
    def extract_variables(self, content: str) -> List[str]:
        """Extract Jinja2 variables from prompt content."""
        return self.variable_engine.extract_variables(content)
    
    def count_tokens(self, content: str, model: str = "gpt-4", provider: str = "openai") -> int:
        """
        Count tokens in content using tiktoken.
        
        Args:
            content: Text content to count tokens for
            model: Model name (default: "gpt-4")
            provider: Provider name (default: "openai")
        
        Returns:
            Number of tokens
        
        Example:
            >>> manager = PromptManager()
            >>> tokens = manager.count_tokens("Hello, world!", model="gpt-4")
        """
        try:
            estimator = _get_cost_estimator()
            return estimator.count_tokens(content, model, provider)
        except Exception:
            # Fallback to simple word-based estimate if tiktoken fails
            words = content.split()
            return int(len(words) * 1.3)
    
    def get_prompt_with_metadata(self, name: str, version: str = "latest", project: Optional[str] = None) -> Tuple[str, VersionMetadata]:
        """
        Get prompt content along with its metadata.
        
        Args:
            name: Name of the prompt
            version: Version to retrieve (default: "latest")
            project: Optional project name
            
        Returns:
            Tuple of (content, version_metadata)
            
        Raises:
            PromptNotFoundError: If prompt doesn't exist
            VersionNotFoundError: If version doesn't exist
        """
        metadata = self._load_metadata(name, project=project)
        
        if not metadata.versions:
            raise PromptNotFoundError(name)
        
        if version == "latest":
            version_meta = metadata.versions[-1]
        else:
            try:
                version_num = int(version)
                version_meta = next((v for v in metadata.versions if v.version == version_num), None)
                if not version_meta:
                    raise VersionNotFoundError(name, version)
            except ValueError:
                raise VersionNotFoundError(name, version)
        
        prompt_file = Path(version_meta.file_path)
        if prompt_file.exists():
            with open(prompt_file, 'r') as f:
                content = f.read()
            return content, version_meta
        
        raise VersionNotFoundError(name, version)
    
    def commit_prompt(self, source_file: str, name: str, message: Optional[str] = None, project: Optional[str] = None) -> Dict:
        """
        Save a prompt file with a specific name.
        
        Args:
            source_file: Path to the source file
            name: Name to save the prompt as
            message: Optional commit message
            project: Optional project name
            
        Returns:
            Dictionary with commit information
        """
        source_path = Path(source_file)
        
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_file}")
        
        # Read the source file
        with open(source_path, 'r') as f:
            content = f.read()
        
        # Convert to markdown if needed
        content = self._convert_to_markdown(content, str(source_path))
        
        # Load existing metadata
        metadata = self._load_metadata(name, project=project)
        
        # Get next version number
        version = metadata.current_version + 1
        
        # Create prompt directory
        prompt_dir = self._get_prompt_dir(name, project=project)
        prompt_dir.mkdir(parents=True, exist_ok=True)
        
        # Save the prompt file
        prompt_file = prompt_dir / f"v{version}.md"
        with open(prompt_file, 'w') as f:
            f.write(content)
        
        variables = self.extract_variables(content)
        
        token_count = self.count_tokens(content)
        
        now = datetime.now()
        version_info = VersionMetadata(
            version=version,
            timestamp=now,
            source_file=str(source_path),
            file_path=str(prompt_file),
            message=message,
            variables=variables,
            token_count=token_count
        )
        
        metadata.versions.append(version_info)
        metadata.current_version = version
        metadata.updated_at = now
        if not metadata.versions or version == 1:
            metadata.created_at = now
        
        self._save_metadata(metadata, project=project)
        
        return {
            "name": name,
            "version": version,
            "file_path": str(prompt_file)
        }
    
    def set_prompt(self, name: str, content: str, message: Optional[str] = None, project: Optional[str] = None) -> Dict:
        """
        Set/update a prompt with the given name.
        
        Args:
            name: Name of the prompt
            content: Content of the prompt
            message: Optional commit message
            project: Optional project name
            
        Returns:
            Dictionary with set information
        """
        # Load existing metadata
        metadata = self._load_metadata(name, project=project)
        
        # Get next version number
        version = metadata.current_version + 1
        
        # Create prompt directory
        prompt_dir = self._get_prompt_dir(name, project=project)
        prompt_dir.mkdir(parents=True, exist_ok=True)
        
        # Convert to markdown
        content = self._convert_to_markdown(content)
        
        # Save the prompt file
        prompt_file = prompt_dir / f"v{version}.md"
        with open(prompt_file, 'w') as f:
            f.write(content)
        
        # Extract variables
        variables = self.extract_variables(content)
        
        # Count tokens
        token_count = self.count_tokens(content)
        
        now = datetime.now()
        version_info = VersionMetadata(
            version=version,
            timestamp=now,
            source_file=None,
            file_path=str(prompt_file),
            message=message,
            variables=variables,
            token_count=token_count
        )
        
        metadata.versions.append(version_info)
        metadata.current_version = version
        metadata.updated_at = now
        if not metadata.versions or version == 1:
            metadata.created_at = now
        
        self._save_metadata(metadata, project=project)
        
        return {
            "name": name,
            "version": version,
            "file_path": str(prompt_file)
        }
    
    def get_prompt(self, name: str, version: str = "latest", project: Optional[str] = None) -> Optional[str]:
        """
        Retrieve a specific version of a prompt.
        
        Args:
            name: Name of the prompt
            version: Version to retrieve (default: "latest")
            project: Optional project name
            
        Returns:
            Content of the prompt or None if not found
        """
        try:
            content, _ = self.get_prompt_with_metadata(name, version, project=project)
            return content
        except (PromptNotFoundError, VersionNotFoundError):
            return None
    
    def list_versions(self, name: str, project: Optional[str] = None) -> Optional[Dict]:
        """
        List all versions and metadata for a specific prompt name.
        
        Args:
            name: Name of the prompt
            project: Optional project name
            
        Returns:
            Dictionary with prompt metadata or None if not found
        """
        prompt_dir = self._get_prompt_dir(name, project=project)
        if not prompt_dir.exists():
            return None
        
        try:
            metadata = self._load_metadata(name, project=project)
            
            # Convert to dict for backward compatibility
            result = {
                "name": metadata.name,
                "versions": []
            }
            
            for version_meta in metadata.versions:
                version_dict = {
                    "version": version_meta.version,
                    "timestamp": version_meta.timestamp.isoformat(),
                    "file_path": version_meta.file_path,
                }
                if version_meta.source_file:
                    version_dict["source_file"] = version_meta.source_file
                if version_meta.message:
                    version_dict["message"] = version_meta.message
                if version_meta.variables:
                    version_dict["variables"] = version_meta.variables
                
                result["versions"].append(version_dict)
            
            return result
        except Exception:
            return None
    
    def remove_prompts(self, names: List[str], project: Optional[str] = None) -> Dict[str, bool]:
        """
        Remove one or more prompts by name.
        
        Args:
            names: List of prompt names to remove
            project: Optional project name
            
        Returns:
            Dictionary mapping names to success status
        """
        results = {}
        for name in names:
            prompt_dir = self._get_prompt_dir(name, project=project)
            if prompt_dir.exists():
                shutil.rmtree(prompt_dir)
                results[name] = True
            else:
                results[name] = False
        return results
    
    def prompt_exists(self, name: str, project: Optional[str] = None) -> bool:
        """Check if a prompt exists."""
        return self._get_prompt_dir(name, project=project).exists()