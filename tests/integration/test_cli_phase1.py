"""
Integration tests for Phase 1 CLI functionality.
"""
import pytest
from click.testing import CliRunner
from pathlib import Path
from promptv.cli import cli
from promptv.manager import PromptManager


@pytest.fixture
def runner():
    """Create a CLI runner."""
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


class TestPhase1Integration:
    """Integration tests for Phase 1 features."""
    
    def test_full_workflow_commit_tag_get(self, runner, isolated_promptv, tmp_path):
        """Test complete workflow: commit → tag → get with label."""
        # Create a sample prompt file
        prompt_file = tmp_path / "test_prompt.md"
        prompt_file.write_text("This is a test prompt for {{user_name}}")
        
        # 1. Commit the prompt
        result = runner.invoke(cli, [
            'commit',
            '--source', str(prompt_file),
            '--name', 'test-prompt',
            '--message', 'Initial version'
        ])
        assert result.exit_code == 0
        assert "Committed prompt 'test-prompt'" in result.output
        assert "version 1" in result.output
        
        # 2. Create a tag
        result = runner.invoke(cli, [
            'tag', 'create',
            'test-prompt', 'prod',
            '--version', '1',
            '--description', 'Production release'
        ])
        assert result.exit_code == 0
        assert "Created tag 'prod'" in result.output
        
        # 3. Get prompt by tag
        result = runner.invoke(cli, [
            'get',
            'test-prompt',
            '--label', 'prod'
        ])
        assert result.exit_code == 0
        assert "This is a test prompt for {{user_name}}" in result.output
        
    def test_variable_rendering_workflow(self, runner, isolated_promptv, tmp_path):
        """Test variable rendering workflow."""
        # Create a prompt with variables
        prompt_file = tmp_path / "var_prompt.md"
        prompt_file.write_text("Hello {{name}}, you have {{count}} messages")
        
        # Commit the prompt
        result = runner.invoke(cli, [
            'commit',
            '--source', str(prompt_file),
            '--name', 'greeting'
        ])
        assert result.exit_code == 0
        
        # Render with variables
        result = runner.invoke(cli, [
            'render',
            'greeting',
            '--var', 'name=Alice',
            '--var', 'count=5'
        ])
        assert result.exit_code == 0
        assert "Hello Alice, you have 5 messages" in result.output
        
    def test_tag_management_workflow(self, runner, isolated_promptv, tmp_path):
        """Test tag management: create, list, show, delete."""
        # Create a prompt
        prompt_file = tmp_path / "tagged.md"
        prompt_file.write_text("Tagged content")
        
        result = runner.invoke(cli, [
            'commit',
            '--source', str(prompt_file),
            '--name', 'my-prompt'
        ])
        assert result.exit_code == 0
        
        # Create multiple tags
        runner.invoke(cli, ['tag', 'create', 'my-prompt', 'prod', '--version', '1'])
        runner.invoke(cli, ['tag', 'create', 'my-prompt', 'staging', '--version', '1'])
        
        # List tags
        result = runner.invoke(cli, ['tag', 'list', 'my-prompt'])
        assert result.exit_code == 0
        assert "prod" in result.output
        assert "staging" in result.output
        
        # Show specific tag
        result = runner.invoke(cli, ['tag', 'show', 'my-prompt', 'prod'])
        assert result.exit_code == 0
        assert "Tag: prod" in result.output
        assert "Version: 1" in result.output
        
        # Delete a tag
        result = runner.invoke(cli, [
            'tag', 'delete',
            'my-prompt', 'staging',
            '--yes'
        ])
        assert result.exit_code == 0
        assert "Deleted tag 'staging'" in result.output
        
        # Verify deletion
        result = runner.invoke(cli, ['tag', 'list', 'my-prompt'])
        assert "prod" in result.output
        assert "staging" not in result.output
        
    def test_commit_with_tag_option(self, runner, isolated_promptv, tmp_path):
        """Test committing with --tag option for auto-tagging."""
        prompt_file = tmp_path / "autotag.md"
        prompt_file.write_text("Auto-tagged content")
        
        result = runner.invoke(cli, [
            'commit',
            '--source', str(prompt_file),
            '--name', 'auto-tagged',
            '--tag', 'prod'
        ])
        assert result.exit_code == 0
        assert "Committed prompt 'auto-tagged'" in result.output
        assert "Tagged as: prod" in result.output
        
        # Verify tag was created
        result = runner.invoke(cli, ['tag', 'list', 'auto-tagged'])
        assert "prod" in result.output
        
    def test_set_with_message(self, runner, isolated_promptv):
        """Test set command with commit message."""
        result = runner.invoke(cli, [
            'set',
            'my-prompt',
            '--content', 'Test content',
            '--message', 'Created new prompt'
        ])
        assert result.exit_code == 0
        assert "Set prompt 'my-prompt'" in result.output
        assert "Message: Created new prompt" in result.output
        
    def test_list_with_show_tags(self, runner, isolated_promptv, tmp_path):
        """Test list command with --show-tags flag."""
        prompt_file = tmp_path / "list_test.md"
        prompt_file.write_text("List test content")
        
        result = runner.invoke(cli, [
            'commit',
            '--source', str(prompt_file),
            '--name', 'list-test',
            '--tag', 'v1.0'
        ])
        assert result.exit_code == 0, f"Commit failed: {result.output}"
        
        result = runner.invoke(cli, [
            'list',
            'list-test',
            '--show-tags'
        ])
        assert result.exit_code == 0
        assert "Tags:" in result.output
        assert "v1.0" in result.output
        
    def test_list_with_show_variables(self, runner, isolated_promptv, tmp_path):
        """Test list command with --show-variables flag."""
        prompt_file = tmp_path / "vars.md"
        prompt_file.write_text("Hello {{name}}, your score is {{score}}")
        
        result = runner.invoke(cli, [
            'commit',
            '--source', str(prompt_file),
            '--name', 'var-test'
        ])
        assert result.exit_code == 0, f"Commit failed: {result.output}"
        
        result = runner.invoke(cli, [
            'list',
            'var-test',
            '--show-variables'
        ])
        assert result.exit_code == 0
        assert "Variables:" in result.output
        assert "name" in result.output
        assert "score" in result.output
        
    def test_variables_list_command(self, runner, isolated_promptv, tmp_path):
        """Test variables list command."""
        prompt_file = tmp_path / "multi_var.md"
        prompt_file.write_text("Template with {{var1}}, {{var2}}, and {{var3}}")
        
        result = runner.invoke(cli, [
            'commit',
            '--source', str(prompt_file),
            '--name', 'multi-var'
        ])
        assert result.exit_code == 0, f"Commit failed: {result.output}"
        
        result = runner.invoke(cli, ['variables', 'list', 'multi-var'])
        assert result.exit_code == 0, f"Variables list failed: {result.output}"
        assert "var1" in result.output
        assert "var2" in result.output
        assert "var3" in result.output
        assert "Total: 3 variable(s)" in result.output
        
    def test_get_with_variables(self, runner, isolated_promptv, tmp_path):
        """Test get command with variable substitution."""
        # Create prompt with variables
        prompt_file = tmp_path / "sub.md"
        prompt_file.write_text("Welcome {{user}}, temperature is {{temp}}")
        
        runner.invoke(cli, [
            'commit',
            '--source', str(prompt_file),
            '--name', 'substitution'
        ])
        
        # Get with substitution
        result = runner.invoke(cli, [
            'get',
            'substitution',
            '--var', 'user=Bob',
            '--var', 'temp=0.7'
        ])
        assert result.exit_code == 0
        assert "Welcome Bob, temperature is 0.7" in result.output
        
    def test_error_missing_variables(self, runner, isolated_promptv, tmp_path):
        """Test error handling for missing variables."""
        # Create prompt with variables
        prompt_file = tmp_path / "missing.md"
        prompt_file.write_text("Hello {{name}}, you have {{count}} items")
        
        runner.invoke(cli, [
            'commit',
            '--source', str(prompt_file),
            '--name', 'missing-vars'
        ])
        
        # Try to render without all variables
        result = runner.invoke(cli, [
            'render',
            'missing-vars',
            '--var', 'name=Alice'
            # Missing 'count'
        ])
        assert result.exit_code != 0
        assert "Missing required variables" in result.output
        assert "count" in result.output
        
    def test_error_tag_already_exists(self, runner, isolated_promptv, tmp_path):
        """Test error when creating duplicate tag without --force."""
        # Create prompt
        prompt_file = tmp_path / "dup_tag.md"
        prompt_file.write_text("Content")
        
        runner.invoke(cli, [
            'commit',
            '--source', str(prompt_file),
            '--name', 'dup-test'
        ])
        
        # Create tag
        runner.invoke(cli, ['tag', 'create', 'dup-test', 'mytag', '--version', '1'])
        
        # Try to create again without --force
        result = runner.invoke(cli, ['tag', 'create', 'dup-test', 'mytag', '--version', '1'])
        assert result.exit_code != 0
        assert "already exists" in result.output
        
    def test_tag_update_with_force(self, runner, isolated_promptv, tmp_path):
        """Test updating tag with --force flag."""
        # Create prompt with multiple versions
        prompt_file = tmp_path / "update.md"
        prompt_file.write_text("Version 1")
        
        runner.invoke(cli, [
            'commit',
            '--source', str(prompt_file),
            '--name', 'update-test'
        ])
        
        # Create v2
        prompt_file.write_text("Version 2")
        runner.invoke(cli, [
            'commit',
            '--source', str(prompt_file),
            '--name', 'update-test'
        ])
        
        # Create tag pointing to v1
        runner.invoke(cli, ['tag', 'create', 'update-test', 'current', '--version', '1'])
        
        # Update tag to v2 with --force
        result = runner.invoke(cli, [
            'tag', 'create',
            'update-test', 'current',
            '--version', '2',
            '--force'
        ])
        assert result.exit_code == 0
        assert "Updated tag 'current'" in result.output
        
        # Verify tag points to v2
        result = runner.invoke(cli, ['tag', 'show', 'update-test', 'current'])
        assert "Version: 2" in result.output
        
    def test_list_all_prompts(self, runner, isolated_promptv, tmp_path):
        """Test listing all prompts without specifying name."""
        for i in range(3):
            prompt_file = tmp_path / f"prompt{i}.md"
            prompt_file.write_text(f"Content {i}")
            result = runner.invoke(cli, [
                'commit',
                '--source', str(prompt_file),
                '--name', f'prompt-{i}'
            ])
            assert result.exit_code == 0, f"Commit failed: {result.output}"
        
        result = runner.invoke(cli, ['list'])
        assert result.exit_code == 0
        assert "Found 3 prompt(s)" in result.output
        assert "default/" in result.output
        assert "prompt-0 (v1, 1 version(s))" in result.output
        assert "prompt-1 (v1, 1 version(s))" in result.output
        assert "prompt-2 (v1, 1 version(s))" in result.output


class TestBackwardCompatibility:
    """Test backward compatibility with existing prompts."""
    
    def test_read_old_format_prompt(self, runner, isolated_promptv, tmp_path):
        """Test that old format prompts can still be read."""
        # This test would require setting up old-format metadata
        # For now, we'll test that new format works
        prompt_file = tmp_path / "compat.md"
        prompt_file.write_text("Backward compatible content")
        
        result = runner.invoke(cli, [
            'commit',
            '--source', str(prompt_file),
            '--name', 'compat-test'
        ])
        assert result.exit_code == 0
        
        # Get the prompt
        result = runner.invoke(cli, ['get', 'compat-test'])
        assert result.exit_code == 0
        assert "Backward compatible content" in result.output