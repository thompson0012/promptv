"""
PromptClient SDK - Programmatic access to prompts with caching.

This module provides a Python SDK for accessing and rendering prompts
programmatically with built-in caching support.
"""

from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime, timedelta
import hashlib
import logging

from pydantic import BaseModel
from ..manager import PromptManager
from ..tag_manager import TagManager
from ..variable_engine import VariableEngine
from ..secrets_manager import SecretsManager
from ..models import VersionMetadata, PromptMetadata, CostEstimate
from ..exceptions import PromptNotFoundError, TagNotFoundError
from ..cost_estimator import CostEstimator

logger = logging.getLogger(__name__)


class CachedPrompt(BaseModel):
    """Cached prompt with TTL support."""
    content: str
    cached_at: datetime
    ttl_seconds: int = 300
    
    def is_expired(self) -> bool:
        """Check if the cached prompt has expired."""
        return datetime.now() > self.cached_at + timedelta(seconds=self.ttl_seconds)


class PromptClient:
    """
    SDK client for programmatic prompt access.
    
    This client provides a simple API for retrieving and rendering prompts
    programmatically with built-in caching, variable interpolation, and 
    secrets management.
    
    Examples:
        >>> client = PromptClient()
        
        # Prompt management
        >>> prompt = client.get_prompt('onboarding-email', label='prod')
        >>> 
        >>> # With variables
        >>> prompt = client.get_prompt(
        ...     'onboarding-email',
        ...     label='prod',
        ...     variables={'name': 'Alice', 'product': 'promptv'}
        ... )
        >>> 
        >>> # Secrets management
        >>> client.set_api_key("openai", "sk-...")
        >>> client.set_secret("DATABASE_URL", "postgres://...", project="my-app")
        >>> db_url = client.get_secret("DATABASE_URL", project="my-app")
        >>> 
        >>> # With context manager
        >>> with PromptClient() as client:
        ...     prompt = client.get_prompt('my-prompt')
    """
    
    def __init__(self, base_dir: Optional[Path] = None, cache_ttl: int = 300):
        """
        Initialize the PromptClient.
        
        Args:
            base_dir: Optional custom base directory (default: ~/.promptv)
            cache_ttl: Cache TTL in seconds (default: 300)
        """
        self.base_dir = base_dir or Path.home() / ".promptv"
        self.cache_ttl = cache_ttl
        self.manager = PromptManager()
        if base_dir:
            self.manager.base_dir = base_dir
            self.manager.prompts_dir = base_dir / "prompts"
            self.manager.config_dir = base_dir / ".config"
        self.tag_manager = TagManager(self.manager.prompts_dir)
        self.variable_engine = VariableEngine()
        self.cache: Dict[str, CachedPrompt] = {}
        
        # Initialize SecretsManager for secrets management
        secrets_dir = self.base_dir / ".secrets" if base_dir else None
        self.secrets_manager = SecretsManager(secrets_dir=secrets_dir)
        
        logger.debug(f"Initialized PromptClient with base_dir={self.base_dir}, cache_ttl={cache_ttl}")
    
    def get_prompt(
        self,
        name: str,
        label: Optional[str] = None,
        version: Optional[int] = None,
        variables: Optional[Dict[str, Any]] = None,
        use_cache: bool = True
    ) -> str:
        """
        Get a prompt and optionally render with variables.
        
        Args:
            name: Prompt name
            label: Tag/label to retrieve (e.g., 'prod', 'staging')
            version: Specific version number to retrieve
            variables: Variables for template rendering
            use_cache: Whether to use cache (default: True)
        
        Returns:
            Rendered prompt content
        
        Raises:
            PromptNotFoundError: If prompt doesn't exist
            TagNotFoundError: If label doesn't exist
            ValueError: If both label and version are specified
        
        Examples:
            >>> client = PromptClient()
            >>> # Get latest version
            >>> prompt = client.get_prompt('my-prompt')
            >>> 
            >>> # Get specific label
            >>> prompt = client.get_prompt('my-prompt', label='prod')
            >>> 
            >>> # Get specific version
            >>> prompt = client.get_prompt('my-prompt', version=2)
            >>> 
            >>> # With variables
            >>> prompt = client.get_prompt(
            ...     'onboarding-email',
            ...     label='prod',
            ...     variables={'user_name': 'Alice', 'product': 'promptv'}
            ... )
        """
        if label and version:
            raise ValueError("Cannot specify both 'label' and 'version'")
        
        # Generate cache key
        cache_key = self._cache_key(name, label, version, variables)
        
        # Check cache
        if use_cache and cache_key in self.cache:
            cached = self.cache[cache_key]
            if not cached.is_expired():
                logger.debug(f"Cache hit for prompt '{name}'")
                return cached.content
            else:
                logger.debug(f"Cache expired for prompt '{name}'")
                del self.cache[cache_key]
        
        # Resolve version from tag/label
        version_ref = "latest"
        if label:
            metadata = self.manager._load_metadata(name)
            if not metadata.versions:
                raise PromptNotFoundError(name)
            max_version = metadata.current_version
            version_num = self.tag_manager.resolve_version(name, label, max_version)
            version_ref = str(version_num)
        elif version is not None:
            version_ref = str(version)
        
        # Get prompt content
        content = self.manager.get_prompt(name, version_ref)
        if content is None:
            raise PromptNotFoundError(name)
        
        logger.debug(f"Retrieved prompt '{name}' version {version_ref}")
        
        # Render with variables if provided
        if variables:
            content = self.variable_engine.render(content, variables)
            logger.debug(f"Rendered prompt '{name}' with {len(variables)} variables")
        
        # Cache result
        if use_cache:
            self.cache[cache_key] = CachedPrompt(
                content=content,
                cached_at=datetime.now(),
                ttl_seconds=self.cache_ttl
            )
            logger.debug(f"Cached prompt '{name}' with TTL {self.cache_ttl}s")
        
        return content
    
    def get_prompt_with_metadata(
        self,
        name: str,
        label: Optional[str] = None,
        version: Optional[int] = None
    ) -> Tuple[str, VersionMetadata]:
        """
        Get prompt content along with its metadata.
        
        Args:
            name: Prompt name
            label: Tag/label to retrieve
            version: Specific version number to retrieve
        
        Returns:
            Tuple of (content, metadata)
        
        Raises:
            PromptNotFoundError: If prompt doesn't exist
            TagNotFoundError: If label doesn't exist
        
        Examples:
            >>> client = PromptClient()
            >>> content, meta = client.get_prompt_with_metadata('my-prompt', label='prod')
            >>> print(f"Version: {meta.version}, Author: {meta.author}")
        """
        if label and version:
            raise ValueError("Cannot specify both 'label' and 'version'")
        
        # Resolve version
        version_ref = "latest"
        if label:
            metadata = self.manager._load_metadata(name)
            if not metadata.versions:
                raise PromptNotFoundError(name)
            max_version = metadata.current_version
            version_num = self.tag_manager.resolve_version(name, label, max_version)
            version_ref = str(version_num)
        elif version is not None:
            version_ref = str(version)
        
        # Get prompt and metadata
        prompt_metadata = self.manager._load_metadata(name)
        
        # Find version metadata
        version_num = int(version_ref) if version_ref != "latest" else prompt_metadata.current_version
        version_meta = None
        for v in prompt_metadata.versions:
            if v.version == version_num:
                version_meta = v
                break
        
        if version_meta is None:
            raise PromptNotFoundError(f"{name} (version {version_num})")
        
        # Get content
        content = self.manager.get_prompt(name, str(version_num))
        if content is None:
            raise PromptNotFoundError(name)
        
        return content, version_meta
    
    def list_prompts(self) -> List[str]:
        """
        List all available prompts.
        
        Returns:
            List of prompt names
        
        Examples:
            >>> client = PromptClient()
            >>> prompts = client.list_prompts()
            >>> print(f"Available prompts: {', '.join(prompts)}")
        """
        prompts_dir = self.manager.prompts_dir
        if not prompts_dir.exists():
            return []
        
        prompt_names = []
        for item in prompts_dir.iterdir():
            if item.is_dir():
                metadata_file = item / "metadata.json"
                if metadata_file.exists():
                    prompt_names.append(item.name)
        
        return sorted(prompt_names)
    
    def get_versions(self, name: str) -> List[VersionMetadata]:
        """
        Get all versions for a prompt.
        
        Args:
            name: Prompt name
        
        Returns:
            List of version metadata
        
        Raises:
            PromptNotFoundError: If prompt doesn't exist
        
        Examples:
            >>> client = PromptClient()
            >>> versions = client.get_versions('my-prompt')
            >>> for v in versions:
            ...     print(f"v{v.version}: {v.message or 'No message'}")
        """
        metadata = self.manager._load_metadata(name)
        if not metadata.versions:
            raise PromptNotFoundError(name)
        
        return metadata.versions
    
    def get_tags(self, name: str) -> Dict[str, int]:
        """
        Get all tags for a prompt.
        
        Args:
            name: Prompt name
        
        Returns:
            Dictionary mapping tag names to version numbers
        
        Examples:
            >>> client = PromptClient()
            >>> tags = client.get_tags('my-prompt')
            >>> for tag_name, version in tags.items():
            ...     print(f"{tag_name} → v{version}")
        """
        tags_dict = self.tag_manager.list_tags(name)
        # tags_dict is Dict[str, Tag], convert to Dict[str, int]
        return {tag_name: tag.version for tag_name, tag in tags_dict.items()}
    
    def _cache_key(
        self,
        name: str,
        label: Optional[str],
        version: Optional[int],
        variables: Optional[Dict[str, Any]]
    ) -> str:
        """
        Generate cache key from parameters.
        
        Args:
            name: Prompt name
            label: Tag/label
            version: Version number
            variables: Variables dict
        
        Returns:
            SHA256 hash of the parameters
        """
        label_str = label or ""
        version_str = str(version) if version is not None else ""
        var_str = str(sorted(variables.items())) if variables else ""
        key_input = f"{name}:{label_str}:{version_str}:{var_str}"
        return hashlib.sha256(key_input.encode()).hexdigest()
    
    def clear_cache(self) -> None:
        """
        Clear all cached prompts.
        
        Examples:
            >>> client = PromptClient()
            >>> client.clear_cache()
        """
        cache_count = len(self.cache)
        self.cache.clear()
        logger.debug(f"Cleared {cache_count} cached prompts")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        
        Examples:
            >>> client = PromptClient()
            >>> stats = client.get_cache_stats()
            >>> print(f"Cached: {stats['cached_count']}, Expired: {stats['expired_count']}")
        """
        expired_count = sum(1 for cached in self.cache.values() if cached.is_expired())
        return {
            "cached_count": len(self.cache),
            "expired_count": expired_count,
            "active_count": len(self.cache) - expired_count,
            "ttl_seconds": self.cache_ttl
        }
    
    def estimate_cost(
        self,
        name: str,
        label: Optional[str] = None,
        version: Optional[int] = None,
        variables: Optional[Dict[str, Any]] = None,
        model: str = "gpt-4",
        provider: str = "openai",
        estimated_output_tokens: int = 500
    ) -> CostEstimate:
        """
        Estimate the cost of using a prompt with a specific model.
        
        Args:
            name: Prompt name
            label: Tag/label to retrieve (e.g., 'prod', 'staging')
            version: Specific version number to retrieve
            variables: Variables for template rendering
            model: Model name (default: 'gpt-4')
            provider: Provider name (default: 'openai')
            estimated_output_tokens: Estimated output tokens (default: 500)
        
        Returns:
            CostEstimate object with detailed cost breakdown
        
        Raises:
            PromptNotFoundError: If prompt doesn't exist
            TagNotFoundError: If label doesn't exist
            UnknownModelError: If model/provider not found in pricing data
        
        Examples:
            >>> client = PromptClient()
            >>> cost = client.estimate_cost(
            ...     'my-prompt',
            ...     label='prod',
            ...     model='gpt-4',
            ...     provider='openai',
            ...     estimated_output_tokens=200
            ... )
            >>> print(f"Total cost: ${cost.total_cost:.6f}")
            >>> 
            >>> # With variables
            >>> cost = client.estimate_cost(
            ...     'onboarding-email',
            ...     variables={'name': 'Alice'},
            ...     model='gpt-3.5-turbo'
            ... )
        """
        # Get prompt content (don't use cache for cost estimation)
        content = self.get_prompt(
            name=name,
            label=label,
            version=version,
            variables=variables,
            use_cache=False
        )
        
        # Estimate cost
        estimator = CostEstimator()
        return estimator.estimate_cost(
            text=content,
            model=model,
            provider=provider,
            estimated_output_tokens=estimated_output_tokens
        )
    
    def count_tokens(
        self,
        name: str,
        label: Optional[str] = None,
        version: Optional[int] = None,
        variables: Optional[Dict[str, Any]] = None,
        model: str = "gpt-4",
        provider: str = "openai"
    ) -> int:
        """
        Count tokens in a prompt.
        
        Args:
            name: Prompt name
            label: Tag/label to retrieve
            version: Specific version number to retrieve
            variables: Variables for template rendering
            model: Model name (default: 'gpt-4')
            provider: Provider name (default: 'openai')
        
        Returns:
            Number of tokens
        
        Raises:
            PromptNotFoundError: If prompt doesn't exist
            TagNotFoundError: If label doesn't exist
        
        Examples:
            >>> client = PromptClient()
            >>> tokens = client.count_tokens('my-prompt', label='prod')
            >>> print(f"Token count: {tokens}")
        """
        # Get prompt content
        content = self.get_prompt(
            name=name,
            label=label,
            version=version,
            variables=variables,
            use_cache=False
        )
        
        # Count tokens
        estimator = CostEstimator()
        return estimator.count_tokens(content, model, provider)
    
    def compare_costs(
        self,
        name: str,
        models: List[Tuple[str, str]],
        label: Optional[str] = None,
        version: Optional[int] = None,
        variables: Optional[Dict[str, Any]] = None,
        estimated_output_tokens: int = 500
    ) -> Dict[str, CostEstimate]:
        """
        Compare costs across multiple models for a prompt.
        
        Args:
            name: Prompt name
            models: List of (provider, model) tuples to compare
            label: Tag/label to retrieve
            version: Specific version number to retrieve
            variables: Variables for template rendering
            estimated_output_tokens: Estimated output tokens (default: 500)
        
        Returns:
            Dictionary mapping "provider/model" to CostEstimate (or None if failed)
        
        Examples:
            >>> client = PromptClient()
            >>> comparisons = client.compare_costs(
            ...     'my-prompt',
            ...     models=[
            ...         ('openai', 'gpt-4'),
            ...         ('openai', 'gpt-3.5-turbo'),
            ...         ('anthropic', 'claude-3-sonnet-20240229')
            ...     ],
            ...     label='prod'
            ... )
            >>> for key, cost in comparisons.items():
            ...     if cost:
            ...         print(f"{key}: ${cost.total_cost:.6f}")
        """
        # Get prompt content
        content = self.get_prompt(
            name=name,
            label=label,
            version=version,
            variables=variables,
            use_cache=False
        )
        
        # Compare costs
        estimator = CostEstimator()
        return estimator.compare_costs(content, models, estimated_output_tokens)
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup cache."""
        self.clear_cache()
        return False
    
    # Secrets Management Methods - Provider API Keys
    
    def set_api_key(self, provider: str, api_key: str) -> None:
        """
        Store an API key for a provider.
        
        Args:
            provider: Provider name (e.g., "openai", "anthropic")
            api_key: API key to store
            
        Raises:
            ValueError: If provider is not supported
            
        Examples:
            >>> client = PromptClient()
            >>> client.set_api_key("openai", "sk-...")
        """
        self.secrets_manager.set_api_key(provider, api_key)
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """
        Retrieve an API key for a provider.
        
        Args:
            provider: Provider name (e.g., "openai", "anthropic")
            
        Returns:
            API key if found, None otherwise
            
        Examples:
            >>> client = PromptClient()
            >>> api_key = client.get_api_key("openai")
            >>> if api_key:
            ...     print("OpenAI key configured")
        """
        return self.secrets_manager.get_api_key(provider)
    
    def has_api_key(self, provider: str) -> bool:
        """
        Check if an API key exists for a provider.
        
        Args:
            provider: Provider name (e.g., "openai", "anthropic")
            
        Returns:
            True if API key exists, False otherwise
            
        Examples:
            >>> client = PromptClient()
            >>> if client.has_api_key("openai"):
            ...     print("OpenAI configured")
        """
        return self.secrets_manager.has_api_key(provider)
    
    def delete_api_key(self, provider: str) -> None:
        """
        Delete an API key for a provider.
        
        Args:
            provider: Provider name (e.g., "openai", "anthropic")
            
        Examples:
            >>> client = PromptClient()
            >>> client.delete_api_key("openai")
        """
        self.secrets_manager.delete_api_key(provider)
    
    # Secrets Management Methods - Generic Secrets
    
    def set_secret(self, key_name: str, value: str, project: Optional[str] = None) -> None:
        """
        Store a generic secret (non-provider API key).
        
        Args:
            key_name: Name of the secret
            value: Secret value
            project: Optional project name for scoping (default: None)
        
        Examples:
            >>> client = PromptClient()
            >>> client.set_secret("DATABASE_URL", "postgres://...")
            >>> client.set_secret("API_KEY", "abc123", project="my-app")
        """
        self.secrets_manager.set_secret(key_name, value, project=project)
    
    def get_secret(self, key_name: str, project: Optional[str] = None) -> Optional[str]:
        """
        Retrieve a generic secret.
        
        Args:
            key_name: Name of the secret
            project: Optional project name for scoping
        
        Returns:
            Secret value if found, None otherwise
        
        Examples:
            >>> client = PromptClient()
            >>> db_url = client.get_secret("DATABASE_URL")
            >>> api_key = client.get_secret("API_KEY", project="my-app")
        """
        return self.secrets_manager.get_secret(key_name, project=project)
    
    def delete_secret(self, key_name: str, project: Optional[str] = None) -> None:
        """
        Delete a generic secret.
        
        Args:
            key_name: Name of the secret
            project: Optional project name for scoping
        
        Examples:
            >>> client = PromptClient()
            >>> client.delete_secret("DATABASE_URL")
            >>> client.delete_secret("API_KEY", project="my-app")
        """
        self.secrets_manager.delete_secret(key_name, project=project)
    
    def test_prompt_interactive(
        self,
        name: str,
        provider: str,
        model: str,
        version: Optional[int] = None,
        label: Optional[str] = None,
        project: str = 'default',
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        api_key: Optional[str] = None,
        custom_endpoint: Optional[str] = None
    ) -> None:
        """
        Interactively test a prompt with an LLM provider.
        
        This method loads a saved prompt, extracts variables, prompts the user for values,
        and starts an interactive chat session with the selected LLM provider.
        
        Args:
            name: Prompt name to test
            provider: LLM provider to use ('openai', 'anthropic', 'openrouter')
            model: Model name to use (e.g., 'gpt-4', 'claude-3-5-sonnet-20241022')
            version: Specific version number to test (optional)
            label: Label/tag to test (optional)
            project: Project name (default: 'default')
            temperature: Sampling temperature (0.0-2.0, optional)
            max_tokens: Maximum tokens in response (optional)
            api_key: Direct API key (overrides secrets management - USE WITH CAUTION) (optional)
            custom_endpoint: Custom API endpoint URL (overrides provider defaults) (optional)
        
        Raises:
            PromptNotFoundError: If prompt doesn't exist
            ValueError: If both version and label are specified
        
        Examples:
            >>> client = PromptClient()
            >>> client.test_prompt_interactive(
            ...     name='greeting-prompt',
            ...     provider='openai',
            ...     model='gpt-4'
            ... )
            
            >>> # With specific version and temperature
            >>> client.test_prompt_interactive(
            ...     name='creative-prompt',
            ...     provider='anthropic',
            ...     model='claude-3-5-sonnet-20241022',
            ...     version=2,
            ...     temperature=0.7
            ... )
            
            >>> # With custom endpoint and API key
            >>> client.test_prompt_interactive(
            ...     name='custom-prompt',
            ...     provider='openai',
            ...     model='my-model',
            ...     custom_endpoint='https://api.example.com/v1/chat',
            ...     api_key='sk-12345'
            ... )
        """
        # Validate inputs
        if version is not None and label is not None:
            raise ValueError("Cannot specify both version and label")
        
        # Resolve prompt version (from version or label)
        if version is not None:
            prompt_content = self.manager.get_prompt(name, version=version, project=project)
        elif label is not None:
            prompt_content = self.manager.get_prompt(name, label=label, project=project)
        else:
            prompt_content = self.manager.get_prompt(name, project=project)
        
        # Extract and prompt for variables
        variables = self.manager.extract_variables(prompt_content)
        variable_values = {}
        
        if variables:
            print("Detected variables in prompt:")
            for var in variables:
                value = input(f"Enter value for '{var}': ")
                variable_values[var] = value
        
        # Render prompt with variables
        if variable_values:
            rendered_prompt = self.variable_engine.render(prompt_content, variable_values)
        else:
            rendered_prompt = prompt_content
        
        # Get API key - precedence: api_key parameter > secrets > None
        if api_key:
            # Use directly provided API key
            effective_api_key = api_key
        else:
            # Get from secrets
            effective_api_key = self.secrets_manager.get_api_key(provider)
            
            if not effective_api_key:
                raise ValueError(
                    f"API key not found for provider '{provider}'. "
                    f"Set your API key with: client.set_api_key('{provider}', 'your-api-key') "
                    f"or provide it directly with the api_key parameter."
                )
        
        # Create provider using factory function - handle custom endpoint
        from ..llm_providers import create_provider
        if custom_endpoint:
            provider_instance = create_provider(provider, model, effective_api_key, custom_endpoint)
        else:
            provider_instance = create_provider(provider, model, effective_api_key)
        
        # Create InteractiveTester instance
        from ..interactive_tester import InteractiveTester
        tester = InteractiveTester(
            provider=provider_instance,
            initial_prompt=rendered_prompt,
            show_costs=True,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Start interactive session
        tester.start_session()

    def list_secrets(self, project: Optional[str] = None) -> Dict[str, Any]:
        """
        List all secrets grouped by type and project.
        
        Args:
            project: Optional project filter
        
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
            >>> client = PromptClient()
            >>> all_secrets = client.list_secrets()
            >>> print(f"Providers: {all_secrets['providers']}")
            >>> for proj, keys in all_secrets['secrets'].items():
            ...     print(f"{proj}: {keys}")
            
            >>> # Filter by project
            >>> app_secrets = client.list_secrets(project="my-app")
        """
        return self.secrets_manager.list_all_secrets(project=project)