"""
Integration tests for promptv secrets CLI commands.
"""

import pytest
import tempfile
import shutil
import json
from pathlib import Path
from click.testing import CliRunner
from promptv.cli import cli
from promptv.secrets_manager import SecretsManager


@pytest.fixture
def temp_promptv_dir():
    """Create a temporary .promptv directory for testing."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def runner():
    """Create a Click CLI runner."""
    return CliRunner()


class TestSecretsActivateCommand:
    """Test suite for `promptv secrets activate` command."""
    
    def test_activate_default_project_shell_format(self, runner, temp_promptv_dir, monkeypatch):
        """Test activating default project with shell format."""
        secrets_dir = temp_promptv_dir / ".secrets"
        monkeypatch.setenv("HOME", str(temp_promptv_dir.parent))
        
        manager = SecretsManager(secrets_dir=secrets_dir)
        manager.set_api_key("openai", "sk-test-key")
        manager.set_secret("DATABASE_URL", "postgres://localhost/db")
        manager.set_secret("API_KEY", "abc123")
        
        result = runner.invoke(cli, ['secrets', 'activate'])
        
        assert result.exit_code == 0
        assert 'export OPENAI_API_KEY="sk-test-key"' in result.output
        assert 'export DATABASE_URL="postgres://localhost/db"' in result.output
        assert 'export API_KEY="abc123"' in result.output
        assert "Activated 3 secret(s) from project 'default'" in result.output
    
    def test_activate_specific_project(self, runner, temp_promptv_dir, monkeypatch):
        """Test activating specific project."""
        secrets_dir = temp_promptv_dir / ".secrets"
        monkeypatch.setenv("HOME", str(temp_promptv_dir.parent))
        
        manager = SecretsManager(secrets_dir=secrets_dir)
        manager.set_api_key("openai", "sk-test-key")
        manager.set_secret("DATABASE_URL", "postgres://app1", project="app1")
        manager.set_secret("REDIS_URL", "redis://localhost", project="app1")
        manager.set_secret("OTHER_KEY", "other", project="app2")
        
        result = runner.invoke(cli, ['secrets', 'activate', '--project', 'app1'])
        
        assert result.exit_code == 0
        assert 'export OPENAI_API_KEY="sk-test-key"' in result.output
        assert 'export DATABASE_URL="postgres://app1"' in result.output
        assert 'export REDIS_URL="redis://localhost"' in result.output
        assert 'OTHER_KEY' not in result.output
        assert "Activated 3 secret(s) from project 'app1'" in result.output
    
    def test_activate_export_format(self, runner, temp_promptv_dir, monkeypatch):
        """Test activating with export format (no comments)."""
        secrets_dir = temp_promptv_dir / ".secrets"
        monkeypatch.setenv("HOME", str(temp_promptv_dir.parent))
        
        manager = SecretsManager(secrets_dir=secrets_dir)
        manager.set_secret("DATABASE_URL", "postgres://localhost/db")
        manager.set_secret("API_KEY", "abc123")
        
        result = runner.invoke(cli, ['secrets', 'activate', '--format', 'export'])
        
        assert result.exit_code == 0
        assert 'export DATABASE_URL="postgres://localhost/db"' in result.output
        assert 'export API_KEY="abc123"' in result.output
        assert "Activated" not in result.output
        assert "#" not in result.output
    
    def test_activate_json_format(self, runner, temp_promptv_dir, monkeypatch):
        """Test activating with JSON format."""
        secrets_dir = temp_promptv_dir / ".secrets"
        monkeypatch.setenv("HOME", str(temp_promptv_dir.parent))
        
        manager = SecretsManager(secrets_dir=secrets_dir)
        manager.set_secret("DATABASE_URL", "postgres://localhost/db")
        manager.set_secret("API_KEY", "abc123")
        
        result = runner.invoke(cli, ['secrets', 'activate', '--format', 'json'])
        
        assert result.exit_code == 0
        
        output_data = json.loads(result.output)
        assert output_data["DATABASE_URL"] == "postgres://localhost/db"
        assert output_data["API_KEY"] == "abc123"
    
    def test_activate_no_include_providers(self, runner, temp_promptv_dir, monkeypatch):
        """Test activating without provider API keys."""
        secrets_dir = temp_promptv_dir / ".secrets"
        monkeypatch.setenv("HOME", str(temp_promptv_dir.parent))
        
        manager = SecretsManager(secrets_dir=secrets_dir)
        manager.set_api_key("openai", "sk-test-key")
        manager.set_api_key("anthropic", "sk-ant-key")
        manager.set_secret("DATABASE_URL", "postgres://localhost/db")
        
        result = runner.invoke(cli, [
            'secrets', 'activate', 
            '--no-include-providers'
        ])
        
        assert result.exit_code == 0
        assert 'OPENAI_API_KEY' not in result.output
        assert 'ANTHROPIC_API_KEY' not in result.output
        assert 'export DATABASE_URL="postgres://localhost/db"' in result.output
        assert "Activated 1 secret(s) from project 'default'" in result.output
    
    def test_activate_empty_project(self, runner, temp_promptv_dir, monkeypatch):
        """Test activating project with no secrets."""
        secrets_dir = temp_promptv_dir / ".secrets"
        monkeypatch.setenv("HOME", str(temp_promptv_dir.parent))
        
        manager = SecretsManager(secrets_dir=secrets_dir)
        manager.set_secret("DATABASE_URL", "postgres://db", project="app1")
        
        result = runner.invoke(cli, [
            'secrets', 'activate', 
            '--project', 'app2',
            '--no-include-providers'
        ])
        
        assert result.exit_code == 0
        assert "No secrets found for project 'app2'" in result.output
    
    def test_activate_provider_key_format(self, runner, temp_promptv_dir, monkeypatch):
        """Test that provider keys are formatted as ENV_VAR_NAME."""
        secrets_dir = temp_promptv_dir / ".secrets"
        monkeypatch.setenv("HOME", str(temp_promptv_dir.parent))
        
        manager = SecretsManager(secrets_dir=secrets_dir)
        manager.set_api_key("openai", "sk-openai")
        manager.set_api_key("anthropic", "sk-ant")
        manager.set_api_key("google", "google-key")
        
        result = runner.invoke(cli, ['secrets', 'activate'])
        
        assert result.exit_code == 0
        assert 'export OPENAI_API_KEY="sk-openai"' in result.output
        assert 'export ANTHROPIC_API_KEY="sk-ant"' in result.output
        assert 'export GOOGLE_API_KEY="google-key"' in result.output
    
    def test_activate_multiple_projects(self, runner, temp_promptv_dir, monkeypatch):
        """Test activating secrets from multiple projects (only activates specified)."""
        secrets_dir = temp_promptv_dir / ".secrets"
        monkeypatch.setenv("HOME", str(temp_promptv_dir.parent))
        
        manager = SecretsManager(secrets_dir=secrets_dir)
        manager.set_secret("DB_URL_1", "postgres://db1", project="app1")
        manager.set_secret("DB_URL_2", "postgres://db2", project="app2")
        manager.set_secret("REDIS_URL", "redis://localhost", project="app1")
        
        result = runner.invoke(cli, [
            'secrets', 'activate', 
            '--project', 'app1',
            '--no-include-providers'
        ])
        
        assert result.exit_code == 0
        assert 'export DB_URL_1="postgres://db1"' in result.output
        assert 'export REDIS_URL="redis://localhost"' in result.output
        assert 'DB_URL_2' not in result.output
        assert "Activated 2 secret(s) from project 'app1'" in result.output
    
    def test_activate_sorted_output(self, runner, temp_promptv_dir, monkeypatch):
        """Test that secrets are output in sorted order."""
        secrets_dir = temp_promptv_dir / ".secrets"
        monkeypatch.setenv("HOME", str(temp_promptv_dir.parent))
        
        manager = SecretsManager(secrets_dir=secrets_dir)
        manager.set_secret("ZEBRA", "z")
        manager.set_secret("APPLE", "a")
        manager.set_secret("MONGO", "m")
        
        result = runner.invoke(cli, ['secrets', 'activate', '--format', 'export'])
        
        assert result.exit_code == 0
        
        lines = [line for line in result.output.split('\n') if line.startswith('export')]
        assert lines[0].startswith('export APPLE=')
        assert lines[1].startswith('export MONGO=')
        assert lines[2].startswith('export ZEBRA=')
