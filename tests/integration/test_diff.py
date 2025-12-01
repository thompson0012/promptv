"""
Integration tests for diff CLI command.

Tests diff command with various formats and version references.
"""

import pytest
from click.testing import CliRunner
from pathlib import Path

from promptv.cli import cli
from promptv.manager import PromptManager


@pytest.fixture
def runner():
    """Create CLI runner."""
    return CliRunner()


@pytest.fixture
def isolated_promptv(tmp_path, monkeypatch):
    """Create an isolated promptv environment."""
    # Override home directory for testing
    test_home = tmp_path / "home"
    test_home.mkdir()
    monkeypatch.setenv("HOME", str(test_home))
    
    # Initialize PromptManager to create directories
    manager = PromptManager()
    
    yield manager


class TestDiffIntegration:
    """Integration tests for diff command."""
    
    def test_diff_by_version_numbers(self, runner, isolated_promptv, tmp_path):
        """Test diff between two version numbers."""
        # Create first version
        prompt_file = tmp_path / "prompt_v1.md"
        prompt_file.write_text("Hello {{name}}!\nThis is version 1.")
        
        result = runner.invoke(cli, ['commit', '--source', str(prompt_file), '--name', 'test-prompt'])
        assert result.exit_code == 0, f"Commit failed: {result.output}"
        
        # Create second version
        prompt_file2 = tmp_path / "prompt_v2.md"
        prompt_file2.write_text("Hello {{name}}!\nThis is version 2.\nWith a new line.")
        
        result = runner.invoke(cli, ['set', 'test-prompt', '-f', str(prompt_file2)])
        assert result.exit_code == 0, f"Set failed: {result.output}"
        
        # Test diff
        result = runner.invoke(cli, ['diff', 'test-prompt', '1', '2'])
        
        if result.exit_code != 0:
            print(f"Diff output: {result.output}")
        assert result.exit_code == 0
        assert len(result.output) > 0
    
    def test_diff_by_tags(self, runner, isolated_promptv, tmp_path):
        """Test diff between two tags."""
        # Create first version with tag
        prompt_file = tmp_path / "prompt_v1.md"
        prompt_file.write_text("Hello world!\nVersion 1.")
        
        result = runner.invoke(cli, ['commit', '--source', str(prompt_file), '--name', 'test-prompt'])
        assert result.exit_code == 0
        
        result = runner.invoke(cli, ['tag', 'create', 'test-prompt', 'v1', '--version', '1'])
        assert result.exit_code == 0
        
        # Create second version with tag
        prompt_file2 = tmp_path / "prompt_v2.md"
        prompt_file2.write_text("Hello universe!\nVersion 2.")
        
        result = runner.invoke(cli, ['set', 'test-prompt', '-f', str(prompt_file2)])
        assert result.exit_code == 0
        
        result = runner.invoke(cli, ['tag', 'create', 'test-prompt', 'v2', '--version', '2'])
        assert result.exit_code == 0
        
        # Test diff
        result = runner.invoke(cli, ['diff', 'test-prompt', 'v1', 'v2'])
        
        assert result.exit_code == 0
        assert len(result.output) > 0
    
    def test_diff_with_latest(self, runner, isolated_promptv, tmp_path):
        """Test diff with 'latest' keyword."""
        # Create multiple versions
        prompt_file = tmp_path / "prompt.md"
        prompt_file.write_text("Version 1")
        
        result = runner.invoke(cli, ['commit', '--source', str(prompt_file), '--name', 'test-prompt'])
        assert result.exit_code == 0
        
        prompt_file.write_text("Version 2")
        result = runner.invoke(cli, ['set', 'test-prompt', '-f', str(prompt_file)])
        assert result.exit_code == 0
        
        # Diff with latest
        result = runner.invoke(cli, ['diff', 'test-prompt', '1', 'latest'])
        
        assert result.exit_code == 0
    
    def test_diff_unified_format(self, runner, isolated_promptv, tmp_path):
        """Test unified diff format."""
        # Create two versions
        prompt_file = tmp_path / "prompt.md"
        prompt_file.write_text("Line 1\nLine 2\nLine 3")
        
        result = runner.invoke(cli, ['commit', '--source', str(prompt_file), '--name', 'test-prompt'])
        assert result.exit_code == 0
        
        prompt_file.write_text("Line 1\nModified Line 2\nLine 3")
        result = runner.invoke(cli, ['set', 'test-prompt', '-f', str(prompt_file)])
        assert result.exit_code == 0
        
        # Test unified format
        result = runner.invoke(cli, ['diff', 'test-prompt', '1', '2', '--format', 'unified'])
        
        assert result.exit_code == 0
        assert len(result.output) > 0
    
    def test_diff_json_format(self, runner, isolated_promptv, tmp_path):
        """Test JSON diff format."""
        # Create two versions
        prompt_file = tmp_path / "prompt.md"
        prompt_file.write_text("Content A")
        
        result = runner.invoke(cli, ['commit', '--source', str(prompt_file), '--name', 'test-prompt'])
        assert result.exit_code == 0
        
        prompt_file.write_text("Content B")
        result = runner.invoke(cli, ['set', 'test-prompt', '-f', str(prompt_file)])
        assert result.exit_code == 0
        
        # Test JSON format
        result = runner.invoke(cli, ['diff', 'test-prompt', '1', '2', '--format', 'json'])
        
        assert result.exit_code == 0
        assert '"label_a"' in result.output
        assert '"label_b"' in result.output
        assert '"changes"' in result.output
    
    def test_diff_nonexistent_prompt(self, runner, isolated_promptv):
        """Test diff with non-existent prompt."""
        result = runner.invoke(cli, ['diff', 'nonexistent', '1', '2'])
        
        assert result.exit_code != 0
        assert 'Error' in result.output or 'not found' in result.output.lower()
    
    def test_diff_invalid_version(self, runner, isolated_promptv, tmp_path):
        """Test diff with invalid version number."""
        # Create one version
        prompt_file = tmp_path / "prompt.md"
        prompt_file.write_text("Content")
        
        result = runner.invoke(cli, ['commit', '--source', str(prompt_file), '--name', 'test-prompt'])
        assert result.exit_code == 0
        
        # Try to diff with non-existent version
        result = runner.invoke(cli, ['diff', 'test-prompt', '999', '1'])
        
        assert result.exit_code != 0
    
    def test_diff_same_version(self, runner, isolated_promptv, tmp_path):
        """Test diff comparing same version."""
        # Create one version
        prompt_file = tmp_path / "prompt.md"
        prompt_file.write_text("Same content")
        
        result = runner.invoke(cli, ['commit', '--source', str(prompt_file), '--name', 'test-prompt'])
        assert result.exit_code == 0
        
        # Diff same version
        result = runner.invoke(cli, ['diff', 'test-prompt', '1', '1'])
        
        assert result.exit_code == 0
        # Should show no differences or minimal output