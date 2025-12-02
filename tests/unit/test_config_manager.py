"""
Unit tests for ConfigManager.
"""
import pytest
import tempfile
import shutil
from pathlib import Path
import yaml

from promptv.config_manager import ConfigManager, ConfigManagerError
from promptv.models import Config


class TestConfigManager:
    """Test suite for ConfigManager class."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary directory for config files."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def config_manager(self, temp_config_dir):
        """Create a ConfigManager with a temporary config path."""
        config_path = temp_config_dir / "config.yaml"
        return ConfigManager(config_path=config_path)
    
    def test_init_creates_default_config(self, temp_config_dir):
        """Test that initialization creates default config file."""
        config_path = temp_config_dir / "config.yaml"
        assert not config_path.exists()
        
        manager = ConfigManager(config_path=config_path)
        
        assert config_path.exists()
        assert manager.config_path == config_path
    
    def test_init_with_existing_config(self, config_manager):
        """Test initialization with existing config file."""
        # First init creates the file
        assert config_manager.config_path.exists()
        
        # Second init should not recreate
        manager2 = ConfigManager(config_path=config_manager.config_path)
        assert manager2.config_path.exists()
    
    def test_get_config_default(self, config_manager):
        """Test getting default configuration."""
        config = config_manager.get_config()
        
        assert isinstance(config, Config)
        assert config.cache.enabled is True
        assert config.cache.ttl_seconds == 300
        assert config.cache.max_entries == 100
        assert config.cost_estimation.confirm_threshold == 0.10
        assert config.cost_estimation.default_model == "gpt-4"
        assert config.cost_estimation.default_provider == "openai"
    
    def test_save_config(self, config_manager):
        """Test saving configuration."""
        config = config_manager.get_config()
        config.cache.ttl_seconds = 600
        config.cost_estimation.default_model = "gpt-3.5-turbo"
        
        config_manager.save_config(config)
        
        # Reload and verify
        reloaded = config_manager.get_config()
        assert reloaded.cache.ttl_seconds == 600
        assert reloaded.cost_estimation.default_model == "gpt-3.5-turbo"
    
    def test_save_config_creates_directory(self, temp_config_dir):
        """Test that saving config creates directory if needed."""
        nested_path = temp_config_dir / "nested" / "config.yaml"
        manager = ConfigManager(config_path=nested_path)
        
        config = manager.get_config()
        manager.save_config(config)
        
        assert nested_path.exists()
    
    def test_reset_to_defaults(self, config_manager):
        """Test resetting configuration to defaults."""
        # Modify config
        config = config_manager.get_config()
        config.cache.ttl_seconds = 999
        config_manager.save_config(config)
        
        # Reset
        default_config = config_manager.reset_to_defaults()
        
        assert default_config.cache.ttl_seconds == 300
        
        # Verify it's persisted
        reloaded = config_manager.get_config()
        assert reloaded.cache.ttl_seconds == 300
    
    def test_update_cache_settings(self, config_manager):
        """Test updating cache settings."""
        updated = config_manager.update_cache_settings(
            enabled=False,
            ttl_seconds=600,
            max_entries=50
        )
        
        assert updated.cache.enabled is False
        assert updated.cache.ttl_seconds == 600
        assert updated.cache.max_entries == 50
        
        # Verify persistence
        reloaded = config_manager.get_config()
        assert reloaded.cache.enabled is False
        assert reloaded.cache.ttl_seconds == 600
    
    def test_update_cache_settings_partial(self, config_manager):
        """Test updating only some cache settings."""
        # Update only ttl_seconds
        updated = config_manager.update_cache_settings(ttl_seconds=1200)
        
        assert updated.cache.enabled is True  # Unchanged
        assert updated.cache.ttl_seconds == 1200  # Changed
        assert updated.cache.max_entries == 100  # Unchanged
    
    def test_update_cost_settings(self, config_manager):
        """Test updating cost estimation settings."""
        updated = config_manager.update_cost_settings(
            confirm_threshold=0.50,
            default_output_tokens=1000,
            default_model="claude-3-sonnet",
            default_provider="anthropic"
        )
        
        assert updated.cost_estimation.confirm_threshold == 0.50
        assert updated.cost_estimation.default_output_tokens == 1000
        assert updated.cost_estimation.default_model == "claude-3-sonnet"
        assert updated.cost_estimation.default_provider == "anthropic"
        
        # Verify persistence
        reloaded = config_manager.get_config()
        assert reloaded.cost_estimation.confirm_threshold == 0.50
    
    def test_update_cost_settings_partial(self, config_manager):
        """Test updating only some cost settings."""
        updated = config_manager.update_cost_settings(default_model="gpt-3.5-turbo")
        
        assert updated.cost_estimation.default_model == "gpt-3.5-turbo"
        assert updated.cost_estimation.confirm_threshold == 0.10  # Unchanged
        assert updated.cost_estimation.default_provider == "openai"  # Unchanged
    
    def test_invalid_config_file(self, temp_config_dir):
        """Test handling of invalid config file."""
        config_path = temp_config_dir / "config.yaml"
        
        # Write invalid YAML
        with open(config_path, 'w') as f:
            f.write("invalid: yaml: content: [")
        
        manager = ConfigManager(config_path=config_path)
        
        with pytest.raises(ConfigManagerError) as exc_info:
            manager.get_config()
        
        assert "Failed to parse config file" in str(exc_info.value)
    
    def test_empty_config_file(self, temp_config_dir):
        """Test handling of empty config file."""
        config_path = temp_config_dir / "config.yaml"
        
        # Write empty file
        config_path.touch()
        
        manager = ConfigManager(config_path=config_path)
        config = manager.get_config()
        
        # Should return default config
        assert isinstance(config, Config)
        assert config.cache.ttl_seconds == 300
    
    def test_config_with_missing_fields(self, temp_config_dir):
        """Test config file with some missing fields uses defaults."""
        config_path = temp_config_dir / "config.yaml"
        
        # Write partial config
        with open(config_path, 'w') as f:
            yaml.safe_dump({"cache": {"ttl_seconds": 600}}, f)
        
        manager = ConfigManager(config_path=config_path)
        config = manager.get_config()
        
        # Custom value
        assert config.cache.ttl_seconds == 600
        # Default values
        assert config.cache.enabled is True
        assert config.cost_estimation.default_model == "gpt-4"
    
    def test_default_config_format(self, config_manager):
        """Test that default config file has proper format."""
        content = config_manager.config_path.read_text()
        
        # Should have comments
        assert "# promptv configuration file" in content
        
        # Should be valid YAML
        data = yaml.safe_load(content)
        assert "cache" in data
        assert "cost_estimation" in data
    
    def test_config_persistence_across_instances(self, temp_config_dir):
        """Test that config changes persist across manager instances."""
        config_path = temp_config_dir / "config.yaml"
        
        # First instance
        manager1 = ConfigManager(config_path=config_path)
        manager1.update_cache_settings(ttl_seconds=999)
        
        # Second instance
        manager2 = ConfigManager(config_path=config_path)
        config = manager2.get_config()
        
        assert config.cache.ttl_seconds == 999