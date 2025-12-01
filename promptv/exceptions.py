"""
Custom exception hierarchy for promptv.
"""
from typing import List, Optional


class PromptVError(Exception):
    """Base exception for all promptv errors."""
    
    def __init__(self, message: str, suggestion: Optional[str] = None):
        self.message = message
        self.suggestion = suggestion
        super().__init__(self.format_message())
    
    def format_message(self) -> str:
        """Format the error message with suggestion if available."""
        if self.suggestion:
            return f"{self.message}\n💡 Suggestion: {self.suggestion}"
        return self.message


class PromptNotFoundError(PromptVError):
    """Prompt does not exist."""
    
    def __init__(self, prompt_name: str):
        message = f"Prompt '{prompt_name}' not found"
        suggestion = f"Run 'promptv list' to see available prompts or create it with 'promptv set {prompt_name}'"
        super().__init__(message, suggestion)
        self.prompt_name = prompt_name


class VersionNotFoundError(PromptVError):
    """Version does not exist for a prompt."""
    
    def __init__(self, prompt_name: str, version: str):
        message = f"Version '{version}' not found for prompt '{prompt_name}'"
        suggestion = f"Run 'promptv list {prompt_name}' to see available versions"
        super().__init__(message, suggestion)
        self.prompt_name = prompt_name
        self.version = version


class TagNotFoundError(PromptVError):
    """Tag does not exist."""
    
    def __init__(self, tag_name: str, prompt_name: str):
        message = f"Tag '{tag_name}' not found for prompt '{prompt_name}'"
        suggestion = f"Run 'promptv tag list {prompt_name}' to see available tags"
        super().__init__(message, suggestion)
        self.prompt_name = prompt_name
        self.tag_name = tag_name


class TagAlreadyExistsError(PromptVError):
    """Tag already exists."""
    
    def __init__(self, tag_name: str, prompt_name: str):
        message = f"Tag '{tag_name}' already exists for prompt '{prompt_name}'"
        suggestion = "Use --force to update the existing tag or choose a different tag name"
        super().__init__(message, suggestion)
        self.prompt_name = prompt_name
        self.tag_name = tag_name


class VariableMissingError(PromptVError):
    """Required variable not provided."""
    
    def __init__(self, missing_variables: List[str]):
        message = f"Missing required variables: {', '.join(missing_variables)}"
        suggestion = "Provide variables using --var or in SDK variables dict"
        super().__init__(message, suggestion)
        self.missing_variables = missing_variables


class CostThresholdError(PromptVError):
    """Estimated cost exceeds threshold."""
    
    def __init__(self, estimated_cost: float, threshold: float):
        message = f"Estimated cost ${estimated_cost:.4f} exceeds threshold ${threshold:.4f}"
        suggestion = "Use --force to proceed anyway or adjust your config threshold"
        super().__init__(message, suggestion)
        self.estimated_cost = estimated_cost
        self.threshold = threshold


class InvalidTagNameError(PromptVError):
    """Invalid tag name format."""
    
    def __init__(self, tag_name: str):
        message = f"Invalid tag name '{tag_name}'"
        suggestion = "Tag names must be alphanumeric with hyphens/underscores, e.g., 'prod', 'v1.0.0', 'staging-v2'"
        super().__init__(message, suggestion)
        self.tag_name = tag_name


class MetadataCorruptedError(PromptVError):
    """Metadata file is corrupted or invalid."""
    
    def __init__(self, prompt_name: str, details: str):
        message = f"Metadata corrupted for prompt '{prompt_name}': {details}"
        suggestion = "You may need to recreate this prompt or restore from backup"
        super().__init__(message, suggestion)
        self.prompt_name = prompt_name
        self.details = details