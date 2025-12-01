"""
Jinja2-powered variable engine for template interpolation.
"""
from jinja2 import Environment, Template, meta, UndefinedError, StrictUndefined
from typing import List, Dict, Any, Tuple


class VariableEngine:
    """Engine for extracting and rendering Jinja2 template variables."""
    
    def __init__(self):
        """Initialize the variable engine with Jinja2 environment."""
        self.env = Environment(undefined=StrictUndefined)
    
    def extract_variables(self, template_str: str) -> List[str]:
        """
        Extract all variable names from a Jinja2 template.
        
        Args:
            template_str: The template string to parse
            
        Returns:
            Sorted list of unique variable names found in the template
            
        Example:
            >>> engine = VariableEngine()
            >>> engine.extract_variables("Hello {{name}}, you have {{count}} messages")
            ['count', 'name']
        """
        try:
            ast = self.env.parse(template_str)
            variables = meta.find_undeclared_variables(ast)
            return sorted(variables)
        except Exception:
            # If parsing fails, return empty list
            return []
    
    def render(self, template_str: str, variables: Dict[str, Any]) -> str:
        """
        Render a template with provided variables.
        
        Args:
            template_str: The template string to render
            variables: Dictionary of variable names to values
            
        Returns:
            Rendered template string
            
        Raises:
            UndefinedError: If a required variable is not provided
            
        Example:
            >>> engine = VariableEngine()
            >>> engine.render("Hello {{name}}!", {"name": "World"})
            'Hello World!'
        """
        template = self.env.from_string(template_str)
        return template.render(**variables)
    
    def validate_variables(self, template_str: str, variables: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Check if all required variables are provided.
        
        Args:
            template_str: The template string to validate
            variables: Dictionary of variable names to values
            
        Returns:
            Tuple of (is_valid, missing_variables)
            - is_valid: True if all required variables are provided
            - missing_variables: List of missing variable names
            
        Example:
            >>> engine = VariableEngine()
            >>> template = "Hello {{name}}, you have {{count}} messages"
            >>> engine.validate_variables(template, {"name": "Alice"})
            (False, ['count'])
            >>> engine.validate_variables(template, {"name": "Alice", "count": 5})
            (True, [])
        """
        required = self.extract_variables(template_str)
        missing = [v for v in required if v not in variables]
        return len(missing) == 0, missing