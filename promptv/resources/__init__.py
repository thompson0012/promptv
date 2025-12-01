"""
Resources module for loading static data files.
"""
from pathlib import Path
import yaml
from typing import Dict, Any
import re


def get_pricing_file_path() -> Path:
    """
    Get the pricing file path with fallback strategy.
    
    First checks user config directory (~/.promptv/.config/pricing.yaml),
    then falls back to package resource if not found.
    
    Returns:
        Path to pricing.yaml (user config or package resource)
    """
    # Check user config first
    user_pricing = Path.home() / ".promptv" / ".config" / "pricing.yaml"
    if user_pricing.exists():
        return user_pricing
    
    # Fallback to package resource
    resources_dir = Path(__file__).parent
    return resources_dir / "pricing.yaml"


def load_pricing_data() -> Dict[str, Any]:
    """
    Load pricing data from pricing.yaml.
    
    Uses get_pricing_file_path() to determine source (user config or package resource).
    Adds metadata about the source to the returned data.
    
    Returns:
        Dictionary with pricing data for all providers and models.
    """
    pricing_file = get_pricing_file_path()
    
    if not pricing_file.exists():
        raise FileNotFoundError(f"Pricing data not found at {pricing_file}")
    
    try:
        with open(pricing_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        # If user config is corrupted, try falling back to package resource
        if 'promptv/.config' in str(pricing_file):
            resources_dir = Path(__file__).parent
            fallback_file = resources_dir / "pricing.yaml"
            if fallback_file.exists():
                with open(fallback_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                pricing_file = fallback_file
            else:
                raise FileNotFoundError(
                    f"Failed to parse user pricing.yaml and package resource not found"
                ) from e
        else:
            raise
    
    # Add metadata about source
    data['_source'] = {
        'path': str(pricing_file),
        'is_user_config': '.promptv/.config' in str(pricing_file)
    }
    
    return data


def get_pricing_data_date() -> str:
    """
    Extract the last updated date from pricing.yaml comments.
    
    Looks for "# Last updated: <date>" comment in the first few lines.
    
    Returns:
        Date string if found, "Unknown" otherwise
    """
    try:
        pricing_file = get_pricing_file_path()
        
        if not pricing_file.exists():
            return "Unknown"
        
        with open(pricing_file, 'r', encoding='utf-8') as f:
            # Read first 10 lines to find the date comment
            for _ in range(10):
                line = f.readline()
                if not line:
                    break
                
                # Look for pattern: # Last updated: <date>
                match = re.search(r'#\s*Last updated:\s*(.+)', line, re.IGNORECASE)
                if match:
                    return match.group(1).strip()
        
        return "Unknown"
    except Exception:
        return "Unknown"


def get_model_pricing(provider: str, model: str) -> Dict[str, Any]:
    """
    Get pricing information for a specific provider and model.
    
    Args:
        provider: Provider name (e.g., 'openai', 'anthropic')
        model: Model name (e.g., 'gpt-4', 'claude-3-opus')
    
    Returns:
        Dictionary with 'input', 'output', and 'encoding' keys.
    
    Raises:
        ValueError: If provider or model not found in pricing data.
    """
    pricing_data = load_pricing_data()
    
    # Check for aliases first
    if 'aliases' in pricing_data and model in pricing_data['aliases']:
        model = pricing_data['aliases'][model]
    
    if provider not in pricing_data:
        available_providers = [k for k in pricing_data.keys() if k != 'aliases']
        raise ValueError(
            f"Provider '{provider}' not found in pricing data. "
            f"Available providers: {', '.join(available_providers)}"
        )
    
    if model not in pricing_data[provider]:
        available_models = list(pricing_data[provider].keys())
        raise ValueError(
            f"Model '{model}' not found for provider '{provider}'. "
            f"Available models: {', '.join(available_models)}"
        )
    
    return pricing_data[provider][model]


def list_available_models(provider: str = None) -> Dict[str, list]:
    """
    List all available models, optionally filtered by provider.
    
    Args:
        provider: Optional provider name to filter by.
    
    Returns:
        Dictionary mapping provider names to lists of model names.
    """
    pricing_data = load_pricing_data()
    
    if provider:
        if provider not in pricing_data:
            raise ValueError(f"Provider '{provider}' not found")
        return {provider: list(pricing_data[provider].keys())}
    
    # Return all providers and their models, excluding 'aliases'
    return {
        prov: list(models.keys())
        for prov, models in pricing_data.items()
        if prov != 'aliases'
    }