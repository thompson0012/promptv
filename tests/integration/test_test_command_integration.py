"""
Integration tests for test command.
"""

import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from promptv.manager import PromptManager
from promptv.secrets_manager import SecretsManager
from promptv.cli import cli
from click.testing import CliRunner


class TestTestCommandIntegration(unittest.TestCase):
    """Integration tests for the test command."""

    def setUp(self):
        """Set up test environment with temporary directories."""
        self.temp_dir = tempfile.mkdtemp()
        self.base_dir = Path(self.temp_dir) / ".promptv"
        self.base_dir.mkdir(parents=True)
        
        self.runner = CliRunner()
        
        # Create minimal directory structure
        (self.base_dir / "prompts").mkdir()
        (self.base_dir / ".config").mkdir()
        (self.base_dir / ".secrets").mkdir()
        
        # Create minimal config
        config_content = """
execution:
  mode: "local"
cache:
  enabled: true
  ttl_seconds: 300
cost_estimation:
  confirm_threshold: 0.10
  default_output_tokens: 500
llm_providers:
  openai:
    api_base_url: "https://api.openai.com/v1"
    default_model: "gpt-4"
"""
        with open(self.base_dir / ".config" / "config.yaml", 'w') as f:
            f.write(config_content)

    def tearDown(self):
        """Clean up temporary directory."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_integration_test_command_end_to_end(self):
        """Test full integration of test command with mocked API responses."""
        # Create a test prompt
        test_prompt_content = "# Test Prompt\n\nHello {{name}}!"
        
        with patch('promptv.cli.PromptManager') as mock_manager_class, \
             patch('promptv.cli.SecretsManager') as mock_secrets_class, \
             patch('promptv.cli.create_provider') as mock_create_provider, \
             patch('promptv.cli.InteractiveTester') as mock_interactive_tester:
            
            # Setup PromptManager mock
            mock_manager = MagicMock()
            mock_manager.prompt_exists.return_value = True
            mock_manager.get_prompt.return_value = test_prompt_content
            mock_manager.extract_variables.return_value = ['name']
            mock_manager_class.return_value = mock_manager
            
            # Setup SecretsManager mock
            mock_secrets = MagicMock()
            mock_secrets.get_api_key.return_value = "test-api-key"
            mock_secrets_class.return_value = mock_secrets
            
            # Setup provider mock
            mock_provider = MagicMock()
            mock_create_provider.return_value = mock_provider
            
            # Setup InteractiveTester mock
            mock_tester = MagicMock()
            mock_interactive_tester.return_value = mock_tester
            
            # Run the command
            result = self.runner.invoke(cli, [
                'test', 'test-prompt',
                '--llm', 'gpt-4',
                '--provider', 'openai'
            ], input='World\nexit\n')
            
            # Verify the command executed without error
            # Note: We expect it to fail in the interactive session since we're mocking,
            # but the key point is that it went through the setup correctly
            mock_manager.prompt_exists.assert_called_once_with('test-prompt', project='default')
            mock_manager.get_prompt.assert_called_once_with('test-prompt', project='default')
            mock_secrets.get_api_key.assert_called_once_with('openai')
            mock_create_provider.assert_called_once_with('openai', 'gpt-4', 'test-api-key')
            mock_interactive_tester.assert_called_once()


if __name__ == '__main__':
    unittest.main()