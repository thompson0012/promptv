"""
Unit tests for SecretsManager (local file storage version).
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from promptv.secrets_manager import (
    SecretsManager,
    SecretsManagerError
)


class TestSecretsManager:
    """Test suite for SecretsManager class."""
    
    @pytest.fixture
    def temp_secrets_dir(self):
        """Create a temporary secrets directory for testing."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_init_success(self, temp_secrets_dir):
        """Test successful initialization."""
        manager = SecretsManager(secrets_dir=temp_secrets_dir)
        assert manager.SERVICE_NAME == "promptv"
        assert len(manager.SUPPORTED_PROVIDERS) > 0
        assert (temp_secrets_dir / "secrets.json").exists()
    
    def test_set_api_key_success(self, temp_secrets_dir):
        """Test setting an API key."""
        manager = SecretsManager(secrets_dir=temp_secrets_dir)
        manager.set_api_key("openai", "sk-test-key-123")
        
        # Verify key was stored
        key = manager.get_api_key("openai")
        assert key == "sk-test-key-123"
    
    def test_set_api_key_strips_whitespace(self, temp_secrets_dir):
        """Test that API keys are stripped of whitespace."""
        manager = SecretsManager(secrets_dir=temp_secrets_dir)
        manager.set_api_key("openai", "  sk-test-key-123  ")
        
        key = manager.get_api_key("openai")
        assert key == "sk-test-key-123"
    
    def test_set_api_key_unsupported_provider(self, temp_secrets_dir):
        """Test setting API key for unsupported provider."""
        manager = SecretsManager(secrets_dir=temp_secrets_dir)
        
        with pytest.raises(ValueError) as exc_info:
            manager.set_api_key("unsupported", "key123")
        
        assert "Unsupported provider" in str(exc_info.value)
    
    def test_set_api_key_empty_key(self, temp_secrets_dir):
        """Test setting empty API key."""
        manager = SecretsManager(secrets_dir=temp_secrets_dir)
        
        with pytest.raises(ValueError) as exc_info:
            manager.set_api_key("openai", "")
        
        assert "cannot be empty" in str(exc_info.value)
    
    def test_get_api_key_success(self, temp_secrets_dir):
        """Test retrieving an API key."""
        manager = SecretsManager(secrets_dir=temp_secrets_dir)
        manager.set_api_key("anthropic", "sk-ant-test")
        
        key = manager.get_api_key("anthropic")
        assert key == "sk-ant-test"
    
    def test_get_api_key_not_found(self, temp_secrets_dir):
        """Test retrieving non-existent API key."""
        manager = SecretsManager(secrets_dir=temp_secrets_dir)
        
        key = manager.get_api_key("openai")
        assert key is None
    
    def test_delete_api_key_success(self, temp_secrets_dir):
        """Test deleting an API key."""
        manager = SecretsManager(secrets_dir=temp_secrets_dir)
        manager.set_api_key("openai", "sk-test")
        
        manager.delete_api_key("openai")
        
        key = manager.get_api_key("openai")
        assert key is None
    
    def test_delete_api_key_not_found(self, temp_secrets_dir):
        """Test deleting non-existent API key (should not raise)."""
        manager = SecretsManager(secrets_dir=temp_secrets_dir)
        
        # Should not raise an exception
        manager.delete_api_key("openai")
    
    def test_list_configured_providers(self, temp_secrets_dir):
        """Test listing configured providers."""
        manager = SecretsManager(secrets_dir=temp_secrets_dir)
        manager.set_api_key("openai", "sk-test-1")
        manager.set_api_key("anthropic", "sk-test-2")
        
        providers = manager.list_configured_providers()
        assert "openai" in providers
        assert "anthropic" in providers
        assert len(providers) == 2
    
    def test_list_configured_providers_empty(self, temp_secrets_dir):
        """Test listing providers when none configured."""
        manager = SecretsManager(secrets_dir=temp_secrets_dir)
        
        providers = manager.list_configured_providers()
        assert len(providers) == 0
    
    def test_has_api_key_true(self, temp_secrets_dir):
        """Test has_api_key returns True when key exists."""
        manager = SecretsManager(secrets_dir=temp_secrets_dir)
        manager.set_api_key("openai", "sk-test")
        
        assert manager.has_api_key("openai") is True
    
    def test_has_api_key_false(self, temp_secrets_dir):
        """Test has_api_key returns False when key doesn't exist."""
        manager = SecretsManager(secrets_dir=temp_secrets_dir)
        
        assert manager.has_api_key("openai") is False
    
    def test_supported_providers_list(self, temp_secrets_dir):
        """Test that supported providers list is correct."""
        manager = SecretsManager(secrets_dir=temp_secrets_dir)
        
        expected_providers = [
            "openai", "anthropic", "cohere", "huggingface",
            "together", "google", "replicate", "custom"
        ]
        
        for provider in expected_providers:
            assert provider in manager.SUPPORTED_PROVIDERS
    
    def test_encoding_decoding(self, temp_secrets_dir):
        """Test that values are stored and retrieved correctly."""
        manager = SecretsManager(secrets_dir=temp_secrets_dir)
        test_key = "sk-test-key-with-special-chars-!@#$%"
        
        manager.set_api_key("openai", test_key)
        retrieved = manager.get_api_key("openai")
        
        assert retrieved == test_key
    
    def test_file_permissions(self, temp_secrets_dir):
        """Test that secrets file has restrictive permissions."""
        manager = SecretsManager(secrets_dir=temp_secrets_dir)
        manager.set_api_key("openai", "sk-test")
        
        mode = manager.secrets_file.stat().st_mode
        permissions = oct(mode)[-3:]
        assert permissions == "600"
    
    def test_get_project_secrets_with_values_default(self, temp_secrets_dir):
        """Test getting secrets for default project with values."""
        manager = SecretsManager(secrets_dir=temp_secrets_dir)
        
        manager.set_api_key("openai", "sk-openai-key")
        manager.set_secret("DATABASE_URL", "postgres://localhost/db")
        manager.set_secret("API_KEY", "abc123")
        
        secrets = manager.get_project_secrets_with_values(project="default")
        
        assert secrets["OPENAI_API_KEY"] == "sk-openai-key"
        assert secrets["DATABASE_URL"] == "postgres://localhost/db"
        assert secrets["API_KEY"] == "abc123"
        assert len(secrets) == 3
    
    def test_get_project_secrets_with_values_specific_project(self, temp_secrets_dir):
        """Test getting secrets for specific project with values."""
        manager = SecretsManager(secrets_dir=temp_secrets_dir)
        
        manager.set_api_key("openai", "sk-openai-key")
        manager.set_secret("DATABASE_URL", "postgres://db1", project="app1")
        manager.set_secret("REDIS_URL", "redis://localhost", project="app1")
        manager.set_secret("API_KEY", "xyz789", project="app2")
        
        secrets = manager.get_project_secrets_with_values(project="app1")
        
        assert secrets["OPENAI_API_KEY"] == "sk-openai-key"
        assert secrets["DATABASE_URL"] == "postgres://db1"
        assert secrets["REDIS_URL"] == "redis://localhost"
        assert "API_KEY" not in secrets
        assert len(secrets) == 3
    
    def test_get_project_secrets_with_values_no_providers(self, temp_secrets_dir):
        """Test getting secrets without provider API keys."""
        manager = SecretsManager(secrets_dir=temp_secrets_dir)
        
        manager.set_api_key("openai", "sk-openai-key")
        manager.set_api_key("anthropic", "sk-ant-key")
        manager.set_secret("DATABASE_URL", "postgres://localhost/db")
        
        secrets = manager.get_project_secrets_with_values(
            project="default", 
            include_providers=False
        )
        
        assert "OPENAI_API_KEY" not in secrets
        assert "ANTHROPIC_API_KEY" not in secrets
        assert secrets["DATABASE_URL"] == "postgres://localhost/db"
        assert len(secrets) == 1
    
    def test_get_project_secrets_with_values_empty_project(self, temp_secrets_dir):
        """Test getting secrets for project with no secrets."""
        manager = SecretsManager(secrets_dir=temp_secrets_dir)
        
        manager.set_secret("DATABASE_URL", "postgres://db", project="app1")
        
        secrets = manager.get_project_secrets_with_values(
            project="app2", 
            include_providers=False
        )
        
        assert len(secrets) == 0
    
    def test_get_project_secrets_with_values_provider_name_format(self, temp_secrets_dir):
        """Test that provider keys are formatted correctly as env vars."""
        manager = SecretsManager(secrets_dir=temp_secrets_dir)
        
        manager.set_api_key("openai", "sk-test")
        manager.set_api_key("anthropic", "sk-ant-test")
        manager.set_api_key("google", "google-key")
        
        secrets = manager.get_project_secrets_with_values(project="default")
        
        assert "OPENAI_API_KEY" in secrets
        assert "ANTHROPIC_API_KEY" in secrets
        assert "GOOGLE_API_KEY" in secrets
        assert secrets["OPENAI_API_KEY"] == "sk-test"
        assert secrets["ANTHROPIC_API_KEY"] == "sk-ant-test"
        assert secrets["GOOGLE_API_KEY"] == "google-key"