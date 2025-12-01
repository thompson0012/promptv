"""
Playground TUI application for interactive prompt testing.

A text-based user interface for browsing, editing, and testing prompts
with real-time cost estimation and mock LLM execution.
"""

from pathlib import Path
from typing import Dict, List, Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Button,
    Header,
    Footer,
    Static,
    Input,
    Select,
    TextArea,
    Label,
)
from textual.binding import Binding

from promptv.manager import PromptManager
from promptv.variable_engine import VariableEngine
from promptv.cost_estimator import CostEstimator
from promptv.exceptions import PromptNotFoundError


class PlaygroundApp(App):
    """
    Interactive playground for testing and editing prompts.
    
    Features:
    - Browse and select prompts
    - View and edit prompt content
    - Input variables dynamically
    - Real-time cost estimation
    - Mock LLM execution
    - Save new versions
    """
    
    CSS = """
    Screen {
        background: $surface;
    }
    
    #header {
        dock: top;
        height: 3;
        background: $primary;
        color: $text;
        padding: 1;
    }
    
    #main-container {
        layout: horizontal;
        height: 100%;
    }
    
    #prompt-list {
        width: 30;
        border: solid $primary;
        padding: 1;
    }
    
    #content-area {
        width: 1fr;
        padding: 1;
        border: solid $primary;
    }
    
    #variables-panel {
        width: 40;
        border: solid $primary;
        padding: 1;
    }
    
    #output-panel {
        height: 20;
        border: solid $accent;
        padding: 1;
        margin-top: 1;
    }
    
    TextArea {
        height: 1fr;
        border: solid $secondary;
    }
    
    Button {
        margin: 1;
    }
    
    .cost-display {
        background: $success;
        color: $text;
        padding: 1;
        margin: 1;
    }
    
    .error-display {
        background: $error;
        color: $text;
        padding: 1;
        margin: 1;
    }
    
    .label {
        margin: 1 0;
    }
    """
    
    BINDINGS = [
        Binding("ctrl+e", "execute", "Execute (Ctrl+E)"),
        Binding("ctrl+s", "save", "Save Version (Ctrl+S)"),
        Binding("q", "quit", "Quit (Q)"),
    ]
    
    def __init__(self, prompt_name: Optional[str] = None):
        """
        Initialize playground app.
        
        Args:
            prompt_name: Optional prompt to open on start
        """
        super().__init__()
        self.manager = PromptManager()
        self.var_engine = VariableEngine()
        self.estimator = CostEstimator()
        self.selected_prompt = prompt_name
        self.current_content = ""
        self.variables: Dict[str, str] = {}
        self.current_model = "gpt-4"
        self.current_provider = "openai"
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        
        with Container(id="main-container"):
            # Left panel: Prompt list
            with VerticalScroll(id="prompt-list"):
                yield Label("📋 Prompts", classes="label")
                yield Static(id="prompt-list-content")
                yield Button("Refresh", id="refresh-button", variant="primary")
            
            # Center: Content editor
            with Vertical(id="content-area"):
                yield Label("📝 Prompt Content", classes="label")
                yield TextArea(id="content-editor", language="markdown")
                
                # Output panel
                with Container(id="output-panel"):
                    yield Label("💬 Output", classes="label")
                    yield Static(id="output-display", expand=True)
            
            # Right panel: Variables and actions
            with VerticalScroll(id="variables-panel"):
                yield Label("🔧 Variables & Controls", classes="label")
                yield Static(id="variables-list")
                yield Static(id="cost-display", classes="cost-display")
                
                with Horizontal():
                    yield Button("Execute (Ctrl+E)", id="execute-button", variant="success")
                    yield Button("Save (Ctrl+S)", id="save-button", variant="warning")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Called when app is mounted."""
        self._load_prompt_list()
        
        # Load selected prompt if provided
        if self.selected_prompt:
            self._load_prompt(self.selected_prompt)
    
    def _load_prompt_list(self) -> None:
        """Load list of available prompts."""
        # Get all prompt directories
        if not self.manager.prompts_dir.exists():
            content = "No prompts found.\nCreate some with 'promptv commit'."
        else:
            prompts = [
                d.name for d in self.manager.prompts_dir.iterdir()
                if d.is_dir() and not d.name.startswith('.')
            ]
            
            if not prompts:
                content = "No prompts found.\nCreate some with 'promptv commit'."
            else:
                lines = []
                for i, prompt in enumerate(sorted(prompts), 1):
                    marker = "→ " if prompt == self.selected_prompt else "  "
                    lines.append(f"{marker}{i}. {prompt}")
                content = "\n".join(lines)
        
        list_widget = self.query_one("#prompt-list-content", Static)
        list_widget.update(content)
    
    def _load_prompt(self, prompt_name: str) -> None:
        """
        Load a prompt into the editor.
        
        Args:
            prompt_name: Name of the prompt to load
        """
        try:
            # Get latest version
            content, metadata = self.manager.get_prompt_with_metadata(prompt_name, "latest")
            
            self.selected_prompt = prompt_name
            self.current_content = content
            
            # Update editor
            editor = self.query_one("#content-editor", TextArea)
            editor.text = content
            
            # Extract variables
            self.variables = {}
            var_names = self.var_engine.extract_variables(content)
            for var in var_names:
                self.variables[var] = ""
            
            # Update UI
            self._update_variables_display()
            self._update_cost_display()
            self._load_prompt_list()  # Refresh to show selection
            
        except PromptNotFoundError as e:
            self._show_error(f"Prompt not found: {e}")
    
    def _update_variables_display(self) -> None:
        """Update the variables display."""
        if not self.variables:
            content = "No variables detected.\n\nVariables use {{variable}} syntax."
        else:
            lines = ["Required Variables:\n"]
            for var_name, var_value in self.variables.items():
                value_display = var_value if var_value else "(not set)"
                lines.append(f"• {var_name}: {value_display}")
            content = "\n".join(lines)
        
        vars_widget = self.query_one("#variables-list", Static)
        vars_widget.update(content)
    
    def _update_cost_display(self) -> None:
        """Update cost estimation display."""
        try:
            if not self.current_content:
                return
            
            # Render with variables if all are set
            if self.variables and all(v for v in self.variables.values()):
                rendered_content = self.var_engine.render(
                    self.current_content,
                    self.variables
                )
            else:
                rendered_content = self.current_content
            
            # Estimate cost
            estimate = self.estimator.estimate_cost(
                prompt=rendered_content,
                model=self.current_model,
                provider=self.current_provider,
                output_tokens=500,  # Default estimate
            )
            
            content = f"""💰 Cost Estimate:

Model: {self.current_model}
Input tokens: {estimate['input_tokens']}
Output tokens: {estimate['output_tokens']} (est.)
Input cost: ${estimate['input_cost']:.6f}
Output cost: ${estimate['output_cost']:.6f}
Total: ${estimate['total_cost']:.6f}
"""
            
            cost_widget = self.query_one("#cost-display", Static)
            cost_widget.update(content)
            
        except Exception as e:
            cost_widget = self.query_one("#cost-display", Static)
            cost_widget.update(f"Cost estimation error: {e}")
    
    def _show_error(self, message: str) -> None:
        """
        Show error message in output panel.
        
        Args:
            message: Error message to display
        """
        output_widget = self.query_one("#output-display", Static)
        output_widget.update(f"❌ Error: {message}")
    
    def _show_output(self, content: str) -> None:
        """
        Show content in output panel.
        
        Args:
            content: Content to display
        """
        output_widget = self.query_one("#output-display", Static)
        output_widget.update(content)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "execute-button":
            self.action_execute()
        elif event.button.id == "save-button":
            self.action_save()
        elif event.button.id == "refresh-button":
            self._load_prompt_list()
    
    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Handle text area changes."""
        if event.text_area.id == "content-editor":
            self.current_content = event.text_area.text
            
            # Re-extract variables
            var_names = self.var_engine.extract_variables(self.current_content)
            
            # Preserve existing variable values, add new ones
            new_variables = {}
            for var in var_names:
                new_variables[var] = self.variables.get(var, "")
            self.variables = new_variables
            
            # Update displays
            self._update_variables_display()
            self._update_cost_display()
    
    def action_execute(self) -> None:
        """Execute the prompt (mock)."""
        try:
            # Check if all variables are set
            if not self.current_content:
                self._show_error("No prompt loaded")
                return
            
            missing_vars = [v for v, val in self.variables.items() if not val]
            if missing_vars:
                self._show_error(
                    f"Missing variables: {', '.join(missing_vars)}\n\n"
                    "In a real implementation, you would set these via input fields."
                )
                return
            
            # Render prompt
            if self.variables:
                rendered = self.var_engine.render(self.current_content, self.variables)
            else:
                rendered = self.current_content
            
            # Mock LLM response
            mock_response = f"""🤖 Mock LLM Response

Prompt sent to {self.current_provider}/{self.current_model}:

{rendered}

---

Mock Response:
This is a simulated response. In the full implementation, this would:
1. Use SecretsManager to get API keys
2. Call the actual LLM API (OpenAI, Anthropic, etc.)
3. Stream the response in real-time
4. Track actual usage and cost

For now, this demonstrates the UI flow.
"""
            
            self._show_output(mock_response)
            
        except Exception as e:
            self._show_error(str(e))
    
    def action_save(self) -> None:
        """Save current content as new version."""
        try:
            if not self.selected_prompt:
                self._show_error("No prompt selected")
                return
            
            if not self.current_content:
                self._show_error("No content to save")
                return
            
            # In full implementation, would show dialog for commit message
            # For now, use auto-generated message
            message = "Updated from playground"
            
            # Save as new version using manager
            result = self.manager.set_prompt(
                name=self.selected_prompt,
                content=self.current_content,
                message=message
            )
            
            self._show_output(
                f"✅ Saved as version {result['version']}\n\n"
                f"Message: {message}\n"
                f"Path: {result['file_path']}"
            )
            
        except Exception as e:
            self._show_error(str(e))
    
    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()


def run_playground(prompt_name: Optional[str] = None) -> None:
    """
    Run the playground TUI application.
    
    Args:
        prompt_name: Optional prompt to open on start
    """
    app = PlaygroundApp(prompt_name=prompt_name)
    app.run()