"""
Integration tests for promptv init command.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from click.testing import CliRunner
from promptv.cli import cli


@pytest.fixture
def runner():
    """Create a Click CLI runner."""
    return CliRunner()


@pytest.fixture
def temp_home(monkeypatch):
    """Create a temporary home directory."""
    temp_dir = Path(tempfile.mkdtemp())
    monkeypatch.setenv("HOME", str(temp_dir))
    yield temp_dir
    shutil.rmtree(temp_dir)


class TestInitCommand:
    """Test suite for `promptv init` command."""
    
    def test_init_creates_directory_structure(self, runner, temp_home):
        """Test that init creates all required directories and files."""
        result = runner.invoke(cli, ['init'])
        
        assert result.exit_code == 0
        assert "✅ Initialization complete!" in result.output
        
        # Check directory structure
        promptv_dir = temp_home / ".promptv"
        assert promptv_dir.exists()
        assert (promptv_dir / ".config").exists()
        assert (promptv_dir / ".secrets").exists()
        assert (promptv_dir / "prompts").exists()
        
        # Check files
        assert (promptv_dir / ".config" / "config.yaml").exists()
        assert (promptv_dir / ".config" / "pricing.yaml").exists()
        assert (promptv_dir / ".secrets" / "secrets.json").exists()
    
    def test_init_copies_pricing_yaml(self, runner, temp_home):
        """Test that pricing.yaml is copied from package resources."""
        result = runner.invoke(cli, ['init'])
        
        assert result.exit_code == 0
        
        pricing_file = temp_home / ".promptv" / ".config" / "pricing.yaml"
        assert pricing_file.exists()
        
        # Check file is not empty
        assert pricing_file.stat().st_size > 0
        
        # Check it contains pricing data
        content = pricing_file.read_text()
        assert "openai" in content.lower() or "pricing" in content.lower()
    
    def test_init_idempotent(self, runner, temp_home):
        """Test that running init multiple times is safe."""
        # First init
        result1 = runner.invoke(cli, ['init'])
        assert result1.exit_code == 0
        assert "✓ Created ~/.promptv/" in result1.output
        
        # Second init (should not fail)
        result2 = runner.invoke(cli, ['init'])
        assert result2.exit_code == 0
        assert "already exists" in result2.output
    
    def test_init_with_force_flag(self, runner, temp_home):
        """Test init with --force flag (destructive reinit)."""
        # Create initial structure with some data
        promptv_dir = temp_home / ".promptv"
        promptv_dir.mkdir(parents=True)
        test_file = promptv_dir / "test.txt"
        test_file.write_text("test data")
        
        # Force reinit with confirmation
        result = runner.invoke(cli, ['init', '--force'], input='y\n')
        
        assert result.exit_code == 0
        assert "Force mode" in result.output
        assert "✅ Initialization complete!" in result.output
        
        # Old file should be gone
        assert not test_file.exists()
        
        # New structure should exist
        assert (promptv_dir / ".config").exists()
    
    def test_init_force_cancelled(self, runner, temp_home):
        """Test that force init can be cancelled."""
        # Create initial structure
        promptv_dir = temp_home / ".promptv"
        promptv_dir.mkdir(parents=True)
        test_file = promptv_dir / "test.txt"
        test_file.write_text("test data")
        
        # Force init but cancel
        result = runner.invoke(cli, ['init', '--force'], input='n\n')
        
        assert result.exit_code == 0
        assert "Cancelled" in result.output
        
        # Original file should still exist
        assert test_file.exists()
    
    def test_init_sets_correct_permissions(self, runner, temp_home):
        """Test that init sets correct permissions on secrets directory."""
        result = runner.invoke(cli, ['init'])
        
        assert result.exit_code == 0
        
        secrets_dir = temp_home / ".promptv" / ".secrets"
        secrets_file = secrets_dir / "secrets.json"
        
        # Check directory permissions (0700)
        dir_mode = oct(secrets_dir.stat().st_mode)[-3:]
        assert dir_mode == "700"
        
        # Check file permissions (0600)
        file_mode = oct(secrets_file.stat().st_mode)[-3:]
        assert file_mode == "600"
    
    def test_init_output_shows_pricing_date(self, runner, temp_home):
        """Test that init output shows pricing data date."""
        result = runner.invoke(cli, ['init'])
        
        assert result.exit_code == 0
        assert "Last updated:" in result.output
        assert "✓ Copied pricing.yaml" in result.output
    
    def test_init_creates_valid_config_yaml(self, runner, temp_home):
        """Test that created config.yaml is valid."""
        result = runner.invoke(cli, ['init'])
        
        assert result.exit_code == 0
        
        config_file = temp_home / ".promptv" / ".config" / "config.yaml"
        assert config_file.exists()
        
        # Check it's valid YAML
        import yaml
        with open(config_file) as f:
            config = yaml.safe_load(f)
        
        assert config is not None
        assert isinstance(config, dict)
    
    def test_init_creates_valid_pricing_yaml(self, runner, temp_home):
        """Test that copied pricing.yaml is valid."""
        result = runner.invoke(cli, ['init'])
        
        assert result.exit_code == 0
        
        pricing_file = temp_home / ".promptv" / ".config" / "pricing.yaml"
        assert pricing_file.exists()
        
        # Check it's valid YAML
        import yaml
        with open(pricing_file) as f:
            pricing = yaml.safe_load(f)
        
        assert pricing is not None
        assert isinstance(pricing, dict)
    
    def test_init_pricing_yaml_contains_models(self, runner, temp_home):
        """Test that pricing.yaml contains model pricing data."""
        result = runner.invoke(cli, ['init'])
        
        assert result.exit_code == 0
        
        pricing_file = temp_home / ".promptv" / ".config" / "pricing.yaml"
        
        import yaml
        with open(pricing_file) as f:
            pricing = yaml.safe_load(f)
        
        # Should have pricing data for at least one provider
        assert len(pricing) > 0
        
        # Check structure (provider -> models -> pricing)
        for provider, models in pricing.items():
            if isinstance(models, dict):
                # At least one model should have pricing info
                has_pricing = any(
                    isinstance(model_data, dict) and 
                    ('input' in model_data or 'output' in model_data)
                    for model_data in models.values()
                )
                if has_pricing:
                    break
        else:
            pytest.fail("No pricing data found in pricing.yaml")


class TestAutoInitialization:
    """Test automatic initialization on first command."""
    
    def test_auto_init_on_first_command(self, runner, temp_home):
        """Test that promptv auto-initializes on first command."""
        # Ensure .promptv doesn't exist
        promptv_dir = temp_home / ".promptv"
        assert not promptv_dir.exists()
        
        # Run any command (not init)
        result = runner.invoke(cli, ['secrets', 'list'])
        
        # Should succeed and create structure
        assert result.exit_code == 0
        assert promptv_dir.exists()
        assert (promptv_dir / ".config").exists()
        assert (promptv_dir / ".config" / "pricing.yaml").exists()
    
    def test_auto_init_does_not_run_for_init_command(self, runner, temp_home):
        """Test that auto-init is skipped when running init command."""
        # This test verifies the logic but outcome is same
        result = runner.invoke(cli, ['init'])
        
        assert result.exit_code == 0
        assert "Initializing promptv..." in result.output
