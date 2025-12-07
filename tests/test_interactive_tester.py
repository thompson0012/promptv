"""
Unit tests for InteractiveTester.
"""

import unittest
from unittest.mock import patch, MagicMock
import pytest
from io import StringIO
import sys

from promptv.interactive_tester import InteractiveTester
from promptv.llm_providers import LLMProvider


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing."""
    
    def send_message(self, messages, stream=True, temperature=None, max_tokens=None):
        """Mock send_message that returns predefined responses."""
        # Simple echo response for testing
        last_message = messages[-1]['content'] if messages else ""
        response_text = f"Echo: {last_message}"
        return response_text, 10, 5, 0.001


class TestInteractiveTester(unittest.TestCase):
    """Test suite for InteractiveTester."""

    def setUp(self):
        """Set up test fixtures."""
        self.provider = MockLLMProvider()
        self.initial_prompt = "You are a helpful assistant."
        self.tester = InteractiveTester(
            provider=self.provider,
            initial_prompt=self.initial_prompt,
            show_costs=True
        )

    def test_interactive_tester_initialization(self):
        """Test InteractiveTester initialization."""
        self.assertEqual(self.tester.initial_prompt, self.initial_prompt)
        self.assertTrue(self.tester.show_costs)
        self.assertEqual(len(self.tester.conversation_history), 0)
        self.assertEqual(self.tester.total_prompt_tokens, 0)
        self.assertEqual(self.tester.total_completion_tokens, 0)
        self.assertEqual(self.tester.total_cost, 0.0)

    @patch('builtins.input', side_effect=['Hello', 'exit'])
    @patch('sys.stdout', new_callable=StringIO)
    def test_handle_user_input_normal(self, mock_stdout, mock_input):
        """Test normal user input handling."""
        result = self.tester._handle_user_input()
        self.assertEqual(result, 'Hello')

    @patch('builtins.input', side_effect=['', 'Hello again'])
    @patch('sys.stdout', new_callable=StringIO)
    def test_handle_user_input_empty_then_valid(self, mock_stdout, mock_input):
        """Test handling of empty input followed by valid input."""
        result = self.tester._handle_user_input()
        self.assertEqual(result, 'Hello again')

    @patch('builtins.input', side_effect=[EOFError()])
    @patch('sys.stdout', new_callable=StringIO)
    def test_handle_user_input_eof(self, mock_stdout, mock_input):
        """Test handling of EOF (Ctrl+D)."""
        result = self.tester._handle_user_input()
        self.assertIsNone(result)

    def test_send_and_display(self):
        """Test sending and displaying messages."""
        with patch('sys.stdout', new_callable=StringIO):
            self.tester._send_and_display("Test message")
            
            # Check that conversation history was updated
            self.assertEqual(len(self.tester.conversation_history), 2)
            self.assertEqual(self.tester.conversation_history[0]['role'], 'system')
            self.assertEqual(self.tester.conversation_history[1]['role'], 'assistant')
            
            # Check that token counts were updated
            self.assertEqual(self.tester.total_prompt_tokens, 10)
            self.assertEqual(self.tester.total_completion_tokens, 5)
            self.assertEqual(self.tester.total_cost, 0.001)

    def test_display_message_stats(self):
        """Test displaying message statistics."""
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            self.tester._display_message_stats(10, 5, 0.001)
            output = mock_stdout.getvalue()
            self.assertIn("Tokens: 15", output)
            self.assertIn("input: 10", output)
            self.assertIn("output: 5", output)
            self.assertIn("Cost: $0.001000", output)

    def test_display_session_summary(self):
        """Test displaying session summary."""
        # Add some test data
        self.tester.message_count = 3
        self.tester.total_prompt_tokens = 30
        self.tester.total_completion_tokens = 15
        self.tester.total_cost = 0.003
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            self.tester._display_session_summary()
            output = mock_stdout.getvalue()
            self.assertIn("Session Summary", output)
            self.assertIn("Messages Sent", output)
            self.assertIn("Total Tokens", output)
            self.assertIn("Total Cost", output)


if __name__ == '__main__':
    unittest.main()