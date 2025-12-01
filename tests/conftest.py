"""
Shared test fixtures and configuration for promptv tests.
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from promptv.manager import PromptManager


@pytest.fixture
def temp_home(monkeypatch):
    """Create a temporary home directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir)
        monkeypatch.setenv("HOME", str(temp_path))
        # Also patch Path.home() to return our temp directory
        monkeypatch.setattr(Path, "home", lambda: temp_path)
        yield temp_path


@pytest.fixture
def prompt_manager(temp_home):
    """Create a PromptManager instance with temporary home directory."""
    return PromptManager()


@pytest.fixture
def sample_prompt_content():
    """Sample prompt content for testing."""
    return "This is a sample prompt for testing."


@pytest.fixture
def sample_prompt_with_variables():
    """Sample prompt content with Jinja2 variables."""
    return """Hello {{user_name}},

Please help me with {{topic}}.

Additional context: {{context}}"""


@pytest.fixture
def sample_prompts(prompt_manager, sample_prompt_content):
    """Create some sample prompts for testing."""
    prompts = {}
    
    # Create first prompt with 2 versions
    result1 = prompt_manager.set_prompt("test-prompt-1", sample_prompt_content)
    result2 = prompt_manager.set_prompt("test-prompt-1", sample_prompt_content + "\nVersion 2")
    prompts["test-prompt-1"] = [result1, result2]
    
    # Create second prompt with 1 version
    result3 = prompt_manager.set_prompt("test-prompt-2", "Another prompt")
    prompts["test-prompt-2"] = [result3]
    
    return prompts
