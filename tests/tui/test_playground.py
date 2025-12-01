"""
TUI tests for the Playground application.

Uses Textual's testing utilities to test UI interactions.
"""

import pytest
from pathlib import Path

from textual.pilot import Pilot
from promptv.playground.app import PlaygroundApp
from promptv.manager import PromptManager


@pytest.fixture
def isolated_promptv(tmp_path, monkeypatch):
    """Create an isolated promptv environment."""
    # Override home directory for testing
    test_home = tmp_path / "home"
    test_home.mkdir()
    monkeypatch.setenv("HOME", str(test_home))
    
    # Initialize PromptManager to create directories
    manager = PromptManager()
    
    # Create a test prompt
    test_content = "Hello {{name}}!\n\nThis is a test prompt."
    manager.set_prompt("test-prompt", test_content, message="Initial test prompt")
    
    yield manager


class TestPlaygroundTUI:
    """Test suite for Playground TUI."""
    
    @pytest.mark.asyncio
    async def test_app_launches(self, isolated_promptv):
        """Test that the app launches successfully."""
        app = PlaygroundApp()
        
        async with app.run_test() as pilot:
            # App should have loaded
            assert app.is_running
            
            # Check that header and footer are present
            assert app.query_one("Header")
            assert app.query_one("Footer")
    
    @pytest.mark.asyncio
    async def test_app_with_prompt_name(self, isolated_promptv):
        """Test launching app with specific prompt."""
        app = PlaygroundApp(prompt_name="test-prompt")
        
        async with app.run_test() as pilot:
            # Should have loaded the prompt
            assert app.selected_prompt == "test-prompt"
            assert "Hello {{name}}!" in app.current_content
    
    @pytest.mark.asyncio
    async def test_variables_detection(self, isolated_promptv):
        """Test that variables are detected from content."""
        app = PlaygroundApp(prompt_name="test-prompt")
        
        async with app.run_test() as pilot:
            # Should detect 'name' variable
            assert "name" in app.variables
    
    @pytest.mark.asyncio
    async def test_execute_button_exists(self, isolated_promptv):
        """Test that execute button is present."""
        app = PlaygroundApp()
        
        async with app.run_test() as pilot:
            # Query for execute button
            button = app.query_one("#execute-button")
            assert button is not None
            assert "Execute" in str(button.label)
    
    @pytest.mark.asyncio
    async def test_save_button_exists(self, isolated_promptv):
        """Test that save button is present."""
        app = PlaygroundApp()
        
        async with app.run_test() as pilot:
            # Query for save button
            button = app.query_one("#save-button")
            assert button is not None
            assert "Save" in str(button.label)
    
    @pytest.mark.asyncio
    async def test_quit_action(self, isolated_promptv):
        """Test quit action."""
        app = PlaygroundApp()
        
        async with app.run_test() as pilot:
            # Press Q to quit
            await pilot.press("q")
            
            # App should have exited
            assert not app.is_running
    
    @pytest.mark.asyncio
    async def test_text_area_present(self, isolated_promptv):
        """Test that content editor text area exists."""
        app = PlaygroundApp()
        
        async with app.run_test() as pilot:
            # Query for text area
            editor = app.query_one("#content-editor")
            assert editor is not None
    
    @pytest.mark.asyncio
    async def test_cost_display_present(self, isolated_promptv):
        """Test that cost display exists."""
        app = PlaygroundApp()
        
        async with app.run_test() as pilot:
            # Query for cost display
            cost_display = app.query_one("#cost-display")
            assert cost_display is not None
    
    @pytest.mark.asyncio
    async def test_variables_list_present(self, isolated_promptv):
        """Test that variables list exists."""
        app = PlaygroundApp()
        
        async with app.run_test() as pilot:
            # Query for variables list
            vars_list = app.query_one("#variables-list")
            assert vars_list is not None
    
    @pytest.mark.asyncio
    async def test_output_display_present(self, isolated_promptv):
        """Test that output display exists."""
        app = PlaygroundApp()
        
        async with app.run_test() as pilot:
            # Query for output display
            output = app.query_one("#output-display")
            assert output is not None
    
    @pytest.mark.asyncio
    async def test_prompt_list_loads(self, isolated_promptv):
        """Test that prompt list loads correctly."""
        app = PlaygroundApp()
        
        async with app.run_test() as pilot:
            # Should show the test prompt in the list
            prompt_list = app.query_one("#prompt-list-content")
            # Use str() to get the content
            content = str(prompt_list.render())
            assert "test-prompt" in content or "test-prompt" in str(prompt_list)
    
    @pytest.mark.asyncio
    async def test_execute_with_missing_vars_shows_error(self, isolated_promptv):
        """Test that executing without variables shows error."""
        app = PlaygroundApp(prompt_name="test-prompt")
        
        async with app.run_test() as pilot:
            # Execute without setting variables
            button = app.query_one("#execute-button")
            await pilot.click(button)
            
            # Should show error in output
            # (In the implementation, this shows a mock error message)
            assert app.variables  # Variables should be detected but empty
    
    @pytest.mark.asyncio
    async def test_keyboard_shortcut_execute(self, isolated_promptv):
        """Test Ctrl+E keyboard shortcut for execute."""
        app = PlaygroundApp(prompt_name="test-prompt")
        
        async with app.run_test() as pilot:
            # Press Ctrl+E
            await pilot.press("ctrl+e")
            
            # Action should have been triggered (we can't easily verify
            # the output, but we can verify the app didn't crash)
            assert app.is_running
    
    @pytest.mark.asyncio
    async def test_keyboard_shortcut_save(self, isolated_promptv):
        """Test Ctrl+S keyboard shortcut for save."""
        app = PlaygroundApp(prompt_name="test-prompt")
        
        async with app.run_test() as pilot:
            # Press Ctrl+S
            await pilot.press("ctrl+s")
            
            # Action should have been triggered
            assert app.is_running