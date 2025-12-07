"""
Pydantic models for promptv data structures.
"""
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, Dict, List


class VersionMetadata(BaseModel):
    """Metadata for a single prompt version."""
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )
    
    version: int
    timestamp: datetime
    source_file: Optional[str] = None
    file_path: str
    author: Optional[str] = None  # Git-like attribution
    message: Optional[str] = None  # Commit message
    variables: List[str] = Field(default_factory=list)  # Extracted Jinja2 variables
    token_count: Optional[int] = None  # Cached token count


class PromptMetadata(BaseModel):
    """Enhanced metadata for a prompt."""
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )
    
    name: str
    versions: List[VersionMetadata]
    current_version: int  # Track latest version
    created_at: datetime
    updated_at: datetime
    description: Optional[str] = None  # Optional prompt description
    project: Optional[str] = None  # Project tag for organization


class Tag(BaseModel):
    """Tag/label pointing to a specific version."""
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )
    
    name: str
    version: int
    created_at: datetime
    updated_at: datetime
    description: Optional[str] = None


class TagRegistry(BaseModel):
    """Registry of all tags for a prompt."""
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )
    
    prompt_name: str
    tags: Dict[str, Tag] = Field(default_factory=dict)  # tag_name -> Tag


class CostEstimate(BaseModel):
    """Cost estimation result."""
    input_tokens: int
    estimated_output_tokens: int
    total_tokens: int
    input_cost: float
    estimated_output_cost: float
    total_cost: float
    model: str
    provider: str


class CacheConfig(BaseModel):
    """Cache configuration."""
    enabled: bool = True
    ttl_seconds: int = 300  # 5 minutes
    max_entries: int = 100


class CostEstimationConfig(BaseModel):
    """Cost estimation configuration."""
    confirm_threshold: float = 0.10  # Confirm if cost > $0.10
    default_output_tokens: int = 500
    default_model: str = "gpt-4"
    default_provider: str = "openai"


class LLMProviderConfig(BaseModel):
    """LLM provider API configuration."""
    api_base_url: str
    default_model: Optional[str] = None


class LLMProvidersConfig(BaseModel):
    """Configuration for all LLM providers."""
    openai: LLMProviderConfig = Field(
        default_factory=lambda: LLMProviderConfig(
            api_base_url="https://api.openai.com/v1",
            default_model="gpt-4"
        )
    )
    anthropic: LLMProviderConfig = Field(
        default_factory=lambda: LLMProviderConfig(
            api_base_url="https://api.anthropic.com/v1",
            default_model="claude-3-5-sonnet-20241022"
        )
    )
    openrouter: LLMProviderConfig = Field(
        default_factory=lambda: LLMProviderConfig(
            api_base_url="https://openrouter.ai/api/v1",
            default_model="openai/gpt-4-turbo"
        )
    )
    cohere: LLMProviderConfig = Field(
        default_factory=lambda: LLMProviderConfig(
            api_base_url="https://api.cohere.ai/v1",
            default_model="command-r-plus"
        )
    )
    google: LLMProviderConfig = Field(
        default_factory=lambda: LLMProviderConfig(
            api_base_url="https://generativelanguage.googleapis.com/v1",
            default_model="gemini-pro"
        )
    )
    together: LLMProviderConfig = Field(
        default_factory=lambda: LLMProviderConfig(
            api_base_url="https://api.together.xyz/v1",
            default_model="meta-llama/Llama-3-70b-chat-hf"
        )
    )
    custom: LLMProviderConfig = Field(
        default_factory=lambda: LLMProviderConfig(
            api_base_url="http://localhost:8000/v1",
            default_model="custom-model"
        )
    )


class CloudConfig(BaseModel):
    """Cloud storage configuration."""
    api_key: Optional[str] = None
    project_id: Optional[str] = None
    endpoint: str = "https://api.promptv.io"


class ExecutionMode(BaseModel):
    """Execution mode configuration."""
    mode: str = "local"  # "local" or "cloud"
    cloud: CloudConfig = Field(default_factory=CloudConfig)


class Config(BaseModel):
    """Main configuration."""
    execution: ExecutionMode = Field(default_factory=ExecutionMode)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    cost_estimation: CostEstimationConfig = Field(default_factory=CostEstimationConfig)
    llm_providers: LLMProvidersConfig = Field(default_factory=LLMProvidersConfig)