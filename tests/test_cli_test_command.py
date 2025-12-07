"""
Unit tests for CLI test command.
"""

import unittest
from unittest.mock import patch, MagicMock
import pytest
from click.testing import CliRunner

from promptv.cli import cli


class TestCLITestCommand(unittest.TestCase):
    """Test suite for CLI test command."""

    def setUp(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch('promptv.cli.PromptManager')
    @patch('promptv.cli.SecretsManager')
    def test_test_command_missing_required_args(self, mock_secrets, mock_manager):
        """Test test command with missing required arguments."""
        # Test missing --llm
        result = self.runner.invoke(cli, ['test', 'test-prompt'])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Missing option '--llm'", result.output)
        
        # Test missing both --provider and --endpoint
        result = self.runner.invoke(cli, ['test', 'test-prompt', '--llm', 'gpt-4'])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Either --provider or --endpoint must be specified", result.output)

    @patch('promptv.cli.PromptManager')
    @patch('promptv.cli.SecretsManager')
    def test_test_command_mutual_exclusive_args(self, mock_secrets, mock_manager):
        """Test test command with mutually exclusive arguments."""
        result = self.runner.invoke(cli, [
            'test', 'test-prompt', 
            '--llm', 'gpt-4',
            '--provider', 'openai',
            '--endpoint', 'http://localhost:8000/v1'
        ])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("--provider and --endpoint are mutually exclusive", result.output)

    @patch('promptv.cli.PromptManager')
    @patch('promptv.cli.SecretsManager')
    def test_test_command_invalid_temperature(self, mock_secrets, mock_manager):
        """Test test command with invalid temperature."""
        result = self.runner.invoke(cli, [
            'test', 'test-prompt',
            '--llm', 'gpt-4',
            '--provider', 'openai',
            '--temperature', '3.0'  # Too high
        ])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Temperature must be between 0.0 and 2.0", result.output)

    @patch('promptv.cli.PromptManager')
    @patch('promptv.cli.SecretsManager')
    def test_test_command_invalid_max_tokens(self, mock_secrets, mock_manager):
        """Test test command with invalid max tokens."""
        result = self.runner.invoke(cli, [
            'test', 'test-prompt',
            '--llm', 'gpt-4',
            '--provider', 'openai',
            '--max-tokens', '0'  # Not positive
        ])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Max tokens must be positive", result.output)

    @patch('promptv.cli.PromptManager')
    @patch('promptv.cli.SecretsManager')
    def test_test_command_prompt_not_found(self, mock_secrets, mock_manager):
        """Test test command when prompt is not found."""
        mock_manager_instance = MagicMock()
        mock_manager_instance.prompt_exists.return_value = False
        mock_manager.return_value = mock_manager_instance
        
        result = self.runner.invoke(cli, [
            'test', 'nonexistent-prompt',
            '--llm', 'gpt-4',
            '--provider', 'openai'
        ])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Prompt 'nonexistent-prompt' not found", result.output)

    @patch('promptv.cli.PromptManager')
    @patch('promptv.cli.SecretsManager')
    @patch('promptv.cli.create_provider')
    def test_test_command_api_key_not_found(self, mock_create_provider, mock_secrets, mock_manager):
        """Test test command when API key is not found."""
        # Setup mocks
        mock_manager_instance = MagicMock()
        mock_manager_instance.prompt_exists.return_value = True
        mock_manager_instance.get_prompt.return_value = "Test prompt content"
        mock_manager_instance.extract_variables.return_value = []
        mock_manager.return_value = mock_manager_instance
        
        mock_secrets_instance = MagicMock()
        mock_secrets_instance.get_api_key.return_value = None
        mock_secrets.return_value = mock_secrets_instance
        
        result = self.runner.invoke(cli, [
            'test', 'test-prompt',
            '--llm', 'gpt-4',
            '--provider', 'openai'
        ])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("API key not found for provider 'openai'", result.output)

    @patch('promptv.cli.PromptManager')
    @patch('promptv.cli.SecretsManager')
    @patch('promptv.cli.create_provider')
    @patch('promptv.cli.InteractiveTester')
    def test_test_command_success(self, mock_interactive_tester, mock_create_provider, mock_secrets, mock_manager):
        """Test successful test command execution."""
        # Setup mocks
        mock_manager_instance = MagicMock()
        mock_manager_instance.prompt_exists.return_value = True
        mock_manager_instance.get_prompt.return_value = "Test prompt content"
        mock_manager_instance.extract_variables.return_value = []
        mock_manager.return_value = mock_manager_instance
        
        mock_secrets_instance = MagicMock()
        mock_secrets_instance.get_api_key.return_value = "test-api-key"
        mock_secrets.return_value = mock_secrets_instance
        
        mock_provider_instance = MagicMock()
        mock_create_provider.return_value = mock_provider_instance
        
        mock_tester_instance = MagicMock()
        mock_interactive_tester.return_value = mock_tester_instance
        
        result = self.runner.invoke(cli, [
            'test', 'test-prompt',
            '--llm', 'gpt-4',
            '--provider', 'openai'
        ])
        
        # Should exit normally (we can't easily test the interactive session)
        # But we can verify the mocks were called correctly
        mock_manager_instance.prompt_exists.assert_called_once_with('test-prompt', project='default')
        mock_manager_instance.get_prompt.assert_called_once_with('test-prompt', project='default')
        mock_secrets_instance.get_api_key.assert_called_once_with('openai')
        mock_create_provider.assert_called_once_with('openai', 'gpt-4', 'test-api-key')
        mock_interactive_tester.assert_called_once()


if __name__ == '__main__':
    unittest.main()