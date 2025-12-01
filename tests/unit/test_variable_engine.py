"""
Unit tests for VariableEngine.
"""
import pytest
from promptv.variable_engine import VariableEngine
from jinja2 import UndefinedError


class TestVariableEngine:
    """Tests for VariableEngine class."""
    
    @pytest.fixture
    def engine(self):
        """Create a VariableEngine instance for testing."""
        return VariableEngine()
    
    def test_extract_variables_simple(self, engine):
        """Test extracting variables from simple template."""
        template = "Hello {{name}}!"
        variables = engine.extract_variables(template)
        
        assert variables == ["name"]
    
    def test_extract_variables_multiple(self, engine):
        """Test extracting multiple variables."""
        template = "Hello {{user_name}}, you have {{count}} messages about {{topic}}"
        variables = engine.extract_variables(template)
        
        assert variables == ["count", "topic", "user_name"]
    
    def test_extract_variables_none(self, engine):
        """Test template with no variables."""
        template = "This is a static template with no variables"
        variables = engine.extract_variables(template)
        
        assert variables == []
    
    def test_extract_variables_duplicate(self, engine):
        """Test that duplicate variables are only listed once."""
        template = "{{name}} said hello. {{name}} waved goodbye."
        variables = engine.extract_variables(template)
        
        assert variables == ["name"]
    
    def test_extract_variables_with_filters(self, engine):
        """Test extracting variables that use filters."""
        template = "{{name|upper}} has {{count|default(0)}} items"
        variables = engine.extract_variables(template)
        
        assert "name" in variables
        assert "count" in variables
    
    def test_extract_variables_multiline(self, engine):
        """Test extracting variables from multiline template."""
        template = """Hello {{name}},
        
You have {{count}} new messages.

Best regards,
{{sender}}"""
        variables = engine.extract_variables(template)
        
        assert variables == ["count", "name", "sender"]
    
    def test_render_simple(self, engine):
        """Test rendering simple template."""
        template = "Hello {{name}}!"
        result = engine.render(template, {"name": "World"})
        
        assert result == "Hello World!"
    
    def test_render_multiple_variables(self, engine):
        """Test rendering template with multiple variables."""
        template = "Hello {{user_name}}, you have {{count}} messages"
        result = engine.render(template, {"user_name": "Alice", "count": 5})
        
        assert result == "Hello Alice, you have 5 messages"
    
    def test_render_missing_variable(self, engine):
        """Test that rendering fails when variable is missing."""
        template = "Hello {{name}}!"
        
        with pytest.raises(UndefinedError):
            engine.render(template, {})
    
    def test_render_with_filter(self, engine):
        """Test rendering with Jinja2 filters."""
        template = "Hello {{name|upper}}!"
        result = engine.render(template, {"name": "world"})
        
        assert result == "Hello WORLD!"
    
    def test_render_multiline(self, engine):
        """Test rendering multiline template."""
        template = """Hello {{name}},

You have {{count}} new messages.

Best regards,
{{sender}}"""
        result = engine.render(template, {
            "name": "Alice",
            "count": 3,
            "sender": "Bob"
        })
        
        expected = """Hello Alice,

You have 3 new messages.

Best regards,
Bob"""
        assert result == expected
    
    def test_validate_variables_all_provided(self, engine):
        """Test validation when all variables are provided."""
        template = "Hello {{name}}, you have {{count}} messages"
        is_valid, missing = engine.validate_variables(
            template,
            {"name": "Alice", "count": 5}
        )
        
        assert is_valid is True
        assert missing == []
    
    def test_validate_variables_some_missing(self, engine):
        """Test validation when some variables are missing."""
        template = "Hello {{name}}, you have {{count}} messages about {{topic}}"
        is_valid, missing = engine.validate_variables(
            template,
            {"name": "Alice"}
        )
        
        assert is_valid is False
        assert set(missing) == {"count", "topic"}
    
    def test_validate_variables_all_missing(self, engine):
        """Test validation when all variables are missing."""
        template = "Hello {{name}}!"
        is_valid, missing = engine.validate_variables(template, {})
        
        assert is_valid is False
        assert missing == ["name"]
    
    def test_validate_variables_none_required(self, engine):
        """Test validation when no variables are required."""
        template = "This is a static template"
        is_valid, missing = engine.validate_variables(template, {})
        
        assert is_valid is True
        assert missing == []
    
    def test_validate_variables_extra_provided(self, engine):
        """Test validation when extra variables are provided."""
        template = "Hello {{name}}!"
        is_valid, missing = engine.validate_variables(
            template,
            {"name": "Alice", "extra": "value"}
        )
        
        # Should still be valid, extra variables are ignored
        assert is_valid is True
        assert missing == []
