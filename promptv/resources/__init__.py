"""
Resources module for loading static data files.
"""
from pathlib import Path
import yaml
from typing import Dict, Any


def load_pricing_data() -> Dict[str, Any]:
    """
    Load pricing data from pricing.yaml.
    
    Returns:
        Dictionary with pricing data for all providers and models.
    """
    resources_dir = Path(__file__).parent
    pricing_file = resources_dir / "pricing.yaml"
    
    if not pricing_file.exists():
        raise FileNotFoundError(f"Pricing data not found at {pricing_file}")
    
    with open(pricing_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


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
