"""
Unit tests for CLI test command.
"""

import unittest
from unittest.mock import patch, MagicMock
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
        
        # Test missing all provider options
        result = self.runner.invoke(cli, ['test', 'test-prompt', '--llm', 'gpt-4'])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Either --provider, --endpoint, or --custom-endpoint must be specified", result.output)

    @patch('promptv.cli.PromptManager')
    @patch('promptv.cli.SecretsManager')
    def test_test_command_mutual_exclusive_args(self, mock_secrets, mock_manager):
        """Test test command with mutually exclusive arguments."""
        # Test --provider and --endpoint together
        result = self.runner.invoke(cli, [
            'test', 'test-prompt', 
            '--llm', 'gpt-4',
            '--provider', 'openai',
            '--endpoint', 'http://localhost:8000/v1'
        ])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("--provider, --endpoint, and --custom-endpoint are mutually exclusive", result.output)
        
        # Test --provider and --custom-endpoint together
        result = self.runner.invoke(cli, [
            'test', 'test-prompt', 
            '--llm', 'gpt-4',
            '--provider', 'openai',
            '--custom-endpoint', 'https://api.example.com/v1/chat'
        ])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("--provider, --endpoint, and --custom-endpoint are mutually exclusive", result.output)
        
        # Test --endpoint and --custom-endpoint together
        result = self.runner.invoke(cli, [
            'test', 'test-prompt', 
            '--llm', 'gpt-4',
            '--endpoint', 'http://localhost:8000/v1',
            '--custom-endpoint', 'https://api.example.com/v1/chat'
        ])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("--provider, --endpoint, and --custom-endpoint are mutually exclusive", result.output)

    @patch('promptv.cli.PromptManager')
    @patch('promptv.cli.SecretsManager')
    def test_test_command_invalid_urls(self, mock_secrets, mock_manager):
        """Test test command with invalid URLs."""
        # Test invalid --endpoint URL
        result = self.runner.invoke(cli, [
            'test', 'test-prompt',
            '--llm', 'gpt-4',
            '--endpoint', 'invalid-url'
        ])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Invalid URL format for --endpoint", result.output)
        
        # Test invalid --custom-endpoint URL
        result = self.runner.invoke(cli, [
            'test', 'test-prompt',
            '--llm', 'gpt-4',
            '--custom-endpoint', 'invalid-url'
        ])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Invalid URL format for --custom-endpoint", result.output)

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
    def test_test_command_success_with_custom_endpoint_and_api_key(self, mock_interactive_tester, mock_create_provider, mock_secrets, mock_manager):
        """Test successful test command execution with custom endpoint and API key."""
        # Setup mocks
        mock_manager_instance = MagicMock()
        mock_manager_instance.prompt_exists.return_value = True
        mock_manager_instance.get_prompt.return_value = "Test prompt content"
        mock_manager_instance.extract_variables.return_value = []
        mock_manager.return_value = mock_manager_instance
        
        mock_secrets_instance = MagicMock()
        mock_secrets_instance.get_api_key.return_value = "secret-api-key"
        mock_secrets.return_value = mock_secrets_instance
        
        mock_provider_instance = MagicMock()
        mock_create_provider.return_value = mock_provider_instance
        
        mock_tester_instance = MagicMock()
        mock_interactive_tester.return_value = mock_tester_instance
        
        result = self.runner.invoke(cli, [
            'test', 'test-prompt',
            '--llm', 'my-model',
            '--custom-endpoint', 'https://api.example.com/v1/chat',
            '--api-key', 'direct-api-key'
        ])
        
        # Should exit normally (we can't easily test the interactive session)
        # But we can verify the mocks were called correctly
        mock_manager_instance.prompt_exists.assert_called_once_with('test-prompt', project='default')
        mock_manager_instance.get_prompt.assert_called_once_with('test-prompt', project='default')
        # Should not call secrets manager when api-key is provided directly
        mock_secrets_instance.get_api_key.assert_not_called()
        mock_create_provider.assert_called_once_with('custom', 'my-model', 'direct-api-key', 'https://api.example.com/v1/chat')
        mock_interactive_tester.assert_called_once()
        
        # Should show security warning
        self.assertIn("Warning: Using --api-key exposes your API key", result.output)

    @patch('promptv.cli.PromptManager')
    @patch('promptv.cli.SecretsManager')
    @patch('promptv.cli.create_provider')
    @patch('promptv.cli.InteractiveTester')
    def test_test_command_success_with_custom_endpoint_only(self, mock_interactive_tester, mock_create_provider, mock_secrets, mock_manager):
        """Test successful test command execution with custom endpoint only."""
        # Setup mocks
        mock_manager_instance = MagicMock()
        mock_manager_instance.prompt_exists.return_value = True
        mock_manager_instance.get_prompt.return_value = "Test prompt content"
        mock_manager_instance.extract_variables.return_value = []
        mock_manager.return_value = mock_manager_instance
        
        mock_secrets_instance = MagicMock()
        mock_secrets_instance.get_api_key.return_value = "secret-api-key"
        mock_secrets.return_value = mock_secrets_instance
        
        mock_provider_instance = MagicMock()
        mock_create_provider.return_value = mock_provider_instance
        
        mock_tester_instance = MagicMock()
        mock_interactive_tester.return_value = mock_tester_instance
        
        result = self.runner.invoke(cli, [
            'test', 'test-prompt',
            '--llm', 'my-model',
            '--custom-endpoint', 'https://api.example.com/v1/chat'
        ])
        
        # Should exit normally
        mock_manager_instance.prompt_exists.assert_called_once_with('test-prompt', project='default')
        mock_manager_instance.get_prompt.assert_called_once_with('test-prompt', project='default')
        # Should call secrets manager when no api-key is provided
        mock_secrets_instance.get_api_key.assert_called_once_with('custom')
        mock_create_provider.assert_called_once_with('custom', 'my-model', 'secret-api-key', 'https://api.example.com/v1/chat')
        mock_interactive_tester.assert_called_once()

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