"""
Secrets Manager for secure API key storage using local file storage.

This module provides storage and retrieval of API keys for various
LLM providers using encrypted local file storage in ~/.promptv/.secrets
"""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

from .exceptions import PromptVError

logger = logging.getLogger(__name__)


class SecretsManagerError(PromptVError):
    """Exception raised for secrets management errors."""
    pass


class SecretsManager:
    """
    Manages storage of API keys using local file storage.
    
    This class provides an interface for storing, retrieving, and managing
    API keys for various LLM providers, as well as generic project-scoped secrets.
    Keys are stored in plaintext JSON in ~/.promptv/.secrets/secrets.json 
    with restrictive file permissions.
    
    Examples:
        >>> manager = SecretsManager()
        
        # Provider API keys
        >>> manager.set_api_key("openai", "sk-...")
        >>> api_key = manager.get_api_key("openai")
        >>> providers = manager.list_configured_providers()
        >>> manager.delete_api_key("openai")
        
        # Generic secrets with project scoping
        >>> manager.set_secret("DATABASE_URL", "postgres://...", project="my-app")
        >>> db_url = manager.get_secret("DATABASE_URL", project="my-app")
        >>> all_secrets = manager.list_all_secrets()
        >>> manager.delete_secret("DATABASE_URL", project="my-app")
    """
    
    SERVICE_NAME = "promptv"
    
    SUPPORTED_PROVIDERS = [
        "openai",
        "anthropic",
        "openrouter",
        "cohere",
        "huggingface",
        "together",
        "google",
        "replicate",
        "custom"
    ]
    
    def __init__(self, secrets_dir: Optional[Path] = None):
        """
        Initialize the SecretsManager with local file storage.
        
        Args:
            secrets_dir: Optional custom secrets directory (default: ~/.promptv/.secrets)
        """
        if secrets_dir:
            self.secrets_dir = Path(secrets_dir)
        else:
            self.secrets_dir = Path.home() / ".promptv" / ".secrets"
        
        self.secrets_file = self.secrets_dir / "secrets.json"
        self.project = None  # Current project context
        
        # Initialize secrets directory and file
        self._initialize_storage()
    
    def _initialize_storage(self) -> None:
        """Initialize the secrets storage directory and file."""
        try:
            # Create directory if it doesn't exist
            self.secrets_dir.mkdir(parents=True, exist_ok=True)
            
            # Set restrictive permissions (owner read/write only)
            self.secrets_dir.chmod(0o700)
            
            # Create secrets file if it doesn't exist
            if not self.secrets_file.exists():
                self._save_secrets({})
                self.secrets_file.chmod(0o600)
            
            logger.debug(f"Secrets storage initialized at {self.secrets_file}")
            
        except Exception as e:
            raise SecretsManagerError(
                f"Failed to initialize secrets storage: {str(e)}"
            ) from e
    
    def _load_secrets(self) -> dict:
        """
        Load secrets from the JSON file.
        
        Returns:
            Dictionary of secrets
        """
        try:
            if not self.secrets_file.exists():
                return {}
            
            with open(self.secrets_file, 'r') as f:
                data = json.load(f)
            
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse secrets file: {e}")
            return {}
        except Exception as e:
            raise SecretsManagerError(
                f"Failed to load secrets: {str(e)}"
            ) from e
    
    def _save_secrets(self, secrets: dict) -> None:
        """
        Save secrets to the JSON file.
        
        Args:
            secrets: Dictionary of secrets to save
        """
        try:
            with open(self.secrets_file, 'w') as f:
                json.dump(secrets, f, indent=2)
            
            # Ensure file has restrictive permissions
            self.secrets_file.chmod(0o600)
            
        except Exception as e:
            raise SecretsManagerError(
                f"Failed to save secrets: {str(e)}"
            ) from e
    
    def set_project(self, project: str) -> None:
        """
        Set current project context for scoped secrets.
        
        Args:
            project: Project name
        
        Examples:
            >>> manager = SecretsManager()
            >>> manager.set_project("my-app")
            >>> manager.set_secret("db_password", "secret123")
        """
        self.project = project
    
    def _get_key_name(self, key_name: str, provider: Optional[str] = None) -> str:
        """
        Get fully qualified key name with optional project scoping.
        
        Args:
            key_name: Base key name
            provider: Optional provider name
        
        Returns:
            Fully qualified key name
        """
        if provider:
            # Provider API keys are global (not project-scoped)
            return provider
        
        # Generic secrets can be project-scoped
        if self.project:
            return f"{self.project}::{key_name}"
        return key_name
    
    def set_api_key(self, provider: str, api_key: str) -> None:
        """
        Store an API key for a provider.
        
        Args:
            provider: Provider name (e.g., "openai", "anthropic")
            api_key: API key to store
            
        Raises:
            ValueError: If provider is not supported
            SecretsManagerError: If storing the key fails
            
        Examples:
            >>> manager = SecretsManager()
            >>> manager.set_api_key("openai", "sk-proj-...")
        """
        if provider not in self.SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Unsupported provider: {provider}\n"
                f"Supported providers: {', '.join(self.SUPPORTED_PROVIDERS)}"
            )
        
        if not api_key or not api_key.strip():
            raise ValueError("API key cannot be empty")
        
        try:
            secrets = self._load_secrets()
            secrets[provider] = api_key.strip()
            self._save_secrets(secrets)
            logger.info(f"API key for provider '{provider}' stored securely")
        except Exception as e:
            raise SecretsManagerError(
                f"Failed to store API key for provider '{provider}': {str(e)}"
            ) from e
    
    def set_secret(self, key_name: str, value: str, project: Optional[str] = None) -> None:
        """
        Store a generic secret (non-provider API key).
        
        Args:
            key_name: Name of the secret
            value: Secret value
            project: Optional project name for scoping
        
        Examples:
            >>> manager = SecretsManager()
            >>> manager.set_secret("db_password", "secret123", project="my-app")
        """
        if not key_name or not key_name.strip():
            raise ValueError("Secret key name cannot be empty")
        
        if not value or not value.strip():
            raise ValueError("Secret value cannot be empty")
        
        # Temporarily override project if specified
        old_project = self.project
        if project:
            self.project = project
        
        try:
            qualified_name = self._get_key_name(key_name)
            secrets = self._load_secrets()
            secrets[qualified_name] = value.strip()
            self._save_secrets(secrets)
            logger.info(f"Secret '{qualified_name}' stored securely")
        except Exception as e:
            raise SecretsManagerError(
                f"Failed to store secret '{key_name}': {str(e)}"
            ) from e
        finally:
            self.project = old_project
    
    def get_secret(self, key_name: str, project: Optional[str] = None) -> Optional[str]:
        """
        Retrieve a generic secret.
        
        Args:
            key_name: Name of the secret
            project: Optional project name for scoping
        
        Returns:
            Secret value if found, None otherwise
        
        Examples:
            >>> manager = SecretsManager()
            >>> password = manager.get_secret("db_password", project="my-app")
        """
        # Temporarily override project if specified
        old_project = self.project
        if project:
            self.project = project
        
        try:
            qualified_name = self._get_key_name(key_name)
            secrets = self._load_secrets()
            secret = secrets.get(qualified_name)
            if secret:
                logger.debug(f"Retrieved secret '{qualified_name}'")
                return secret
            return None
        except Exception as e:
            raise SecretsManagerError(
                f"Failed to retrieve secret '{key_name}': {str(e)}"
            ) from e
        finally:
            self.project = old_project
    
    def delete_secret(self, key_name: str, project: Optional[str] = None) -> None:
        """
        Delete a generic secret.
        
        Args:
            key_name: Name of the secret
            project: Optional project name for scoping
        
        Examples:
            >>> manager = SecretsManager()
            >>> manager.delete_secret("db_password", project="my-app")
        """
        # Temporarily override project if specified
        old_project = self.project
        if project:
            self.project = project
        
        try:
            qualified_name = self._get_key_name(key_name)
            secrets = self._load_secrets()
            
            if qualified_name not in secrets:
                logger.warning(f"No secret found: '{qualified_name}'")
                return
            
            del secrets[qualified_name]
            self._save_secrets(secrets)
            logger.info(f"Secret '{qualified_name}' deleted")
        except Exception as e:
            raise SecretsManagerError(
                f"Failed to delete secret '{key_name}': {str(e)}"
            ) from e
        finally:
            self.project = old_project
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """
        Retrieve an API key for a provider.
        
        Args:
            provider: Provider name (e.g., "openai", "anthropic")
            
        Returns:
            API key if found, None otherwise
            
        Raises:
            SecretsManagerError: If retrieving the key fails
            
        Examples:
            >>> manager = SecretsManager()
            >>> api_key = manager.get_api_key("openai")
            >>> if api_key:
            ...     print("Key found!")
        """
        try:
            secrets = self._load_secrets()
            api_key = secrets.get(provider)
            if api_key:
                logger.debug(f"Retrieved API key for provider '{provider}'")
                return api_key
            return None
        except Exception as e:
            raise SecretsManagerError(
                f"Failed to retrieve API key for provider '{provider}': {str(e)}"
            ) from e
    
    def delete_api_key(self, provider: str) -> None:
        """
        Delete an API key for a provider.
        
        Args:
            provider: Provider name (e.g., "openai", "anthropic")
            
        Raises:
            SecretsManagerError: If deleting the key fails
            
        Examples:
            >>> manager = SecretsManager()
            >>> manager.delete_api_key("openai")
        """
        try:
            secrets = self._load_secrets()
            
            if provider not in secrets:
                logger.warning(f"No API key found for provider '{provider}'")
                return
            
            del secrets[provider]
            self._save_secrets(secrets)
            logger.info(f"API key for provider '{provider}' deleted")
        except Exception as e:
            raise SecretsManagerError(
                f"Failed to delete API key for provider '{provider}': {str(e)}"
            ) from e
    
    def list_configured_providers(self) -> List[str]:
        """
        List all providers with stored API keys.
        
        Returns:
            List of provider names with configured keys
            
        Examples:
            >>> manager = SecretsManager()
            >>> providers = manager.list_configured_providers()
            >>> print(f"Configured: {', '.join(providers)}")
        """
        configured = []
        secrets = self._load_secrets()
        
        for provider in self.SUPPORTED_PROVIDERS:
            if provider in secrets:
                configured.append(provider)
        
        return configured
    
    def has_api_key(self, provider: str) -> bool:
        """
        Check if an API key exists for a provider.
        
        Args:
            provider: Provider name (e.g., "openai", "anthropic")
            
        Returns:
            True if API key exists, False otherwise
            
        Examples:
            >>> manager = SecretsManager()
            >>> if manager.has_api_key("openai"):
            ...     print("OpenAI key is configured")
        """
        try:
            return self.get_api_key(provider) is not None
        except SecretsManagerError:
            return False
    
    def is_provider_key(self, key_name: str) -> bool:
        """
        Check if a key name matches a supported provider.
        
        Args:
            key_name: The key name to check
            
        Returns:
            True if the key name is a supported provider, False otherwise
            
        Examples:
            >>> manager = SecretsManager()
            >>> manager.is_provider_key("openai")
            True
            >>> manager.is_provider_key("MY_API_KEY")
            False
        """
        return key_name in self.SUPPORTED_PROVIDERS
    
    def list_all_secrets(self, project: Optional[str] = None) -> Dict[str, Any]:
        """
        List all secrets grouped by type and project.
        
        Args:
            project: Optional project filter to show only secrets for that project
            
        Returns:
            Dictionary with the format:
            {
                "providers": ["openai", "anthropic"],
                "secrets": {
                    "default": ["DATABASE_URL", "API_KEY"],
                    "my-app": ["DB_PASSWORD", "REDIS_URL"]
                }
            }
            
        Examples:
            >>> manager = SecretsManager()
            >>> all_secrets = manager.list_all_secrets()
            >>> print(f"Providers: {all_secrets['providers']}")
            >>> for proj, keys in all_secrets['secrets'].items():
            ...     print(f"{proj}: {keys}")
            
            >>> # Filter by project
            >>> app_secrets = manager.list_all_secrets(project="my-app")
            >>> print(app_secrets['secrets']['my-app'])
        """
        secrets = self._load_secrets()
        providers = []
        project_secrets: Dict[str, List[str]] = {}
        
        for key, value in secrets.items():
            if self.is_provider_key(key):
                # This is a provider API key
                providers.append(key)
            elif "::" in key:
                # This is a project-scoped secret
                proj_name, secret_name = key.split("::", 1)
                
                # Apply project filter if specified
                if project and proj_name != project:
                    continue
                
                if proj_name not in project_secrets:
                    project_secrets[proj_name] = []
                project_secrets[proj_name].append(secret_name)
            else:
                # This is a non-scoped secret (treat as "default" project)
                proj_name = "default"
                
                # Apply project filter if specified
                if project and proj_name != project:
                    continue
                
                if proj_name not in project_secrets:
                    project_secrets[proj_name] = []
                project_secrets[proj_name].append(key)
        
        return {
            "providers": sorted(providers),
            "secrets": {k: sorted(v) for k, v in sorted(project_secrets.items())}
        }
    
    def get_project_secrets_with_values(
        self, 
        project: Optional[str] = None, 
        include_providers: bool = True
    ) -> Dict[str, str]:
        """
        Get all secrets for a project with their actual values.
        
        This is useful for exporting secrets to environment variables.
        
        Args:
            project: Project name to filter (default: "default")
            include_providers: Whether to include provider API keys (default: True)
            
        Returns:
            Dictionary mapping environment variable names to their values
            
        Examples:
            >>> manager = SecretsManager()
            >>> secrets = manager.get_project_secrets_with_values(project="moonshoot")
            >>> for key, value in secrets.items():
            ...     print(f"export {key}={value}")
        """
        if project is None:
            project = "default"
        
        secrets = self._load_secrets()
        result = {}
        
        for key, value in secrets.items():
            if self.is_provider_key(key):
                if include_providers:
                    # Convert provider key to env var format (e.g., openai -> OPENAI_API_KEY)
                    env_var_name = f"{key.upper()}_API_KEY"
                    result[env_var_name] = value
            elif "::" in key:
                # Project-scoped secret
                proj_name, secret_name = key.split("::", 1)
                if proj_name == project:
                    result[secret_name] = value
            else:
                # Non-scoped secret (belongs to "default" project)
                if project == "default":
                    result[key] = value
        
        return result