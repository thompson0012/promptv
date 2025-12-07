"""
Interactive testing session for prompts with LLM providers.

This module provides an interactive chat interface for testing prompts
with real LLM responses, including streaming output and cost tracking.
"""

import sys
import time
from typing import Optional
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

from promptv.llm_providers import LLMProvider, APIError, NetworkError, APIKeyError


class InteractiveTester:
    """
    Interactive testing session for prompts.
    
    Provides a chat interface where users can test prompts with real LLM responses,
    see streaming output, and track token usage and costs across the session.
    
    Example:
        >>> from promptv.llm_providers import create_provider
        >>> provider = create_provider("openai", "gpt-4", "sk-...")
        >>> tester = InteractiveTester(
        ...     provider=provider,
        ...     initial_prompt="You are a helpful assistant.",
        ...     show_costs=True
        ... )
        >>> tester.start_session()
    """
    
    def __init__(
        self,
        provider: LLMProvider,
        initial_prompt: str,
        show_costs: bool = True,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ):
        """
        Initialize interactive tester.
        
        Args:
            provider: LLM provider instance to use
            initial_prompt: Initial prompt/system message to send
            show_costs: Whether to display cost information (default: True)
            temperature: Optional temperature setting
            max_tokens: Optional max tokens setting
        """
        self.provider = provider
        self.initial_prompt = initial_prompt
        self.show_costs = show_costs
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Session state
        self.conversation_history = []
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_cost = 0.0
        self.message_count = 0
        self.session_start_time = None
        
        # Rich console for beautiful output
        self.console = Console()
    
    def start_session(self) -> None:
        """
        Start the interactive testing session.
        
        This method:
        1. Displays welcome message
        2. Sends initial prompt to LLM
        3. Enters interactive loop for user input
        4. Displays session summary on exit
        
        Exit commands: 'exit', 'quit', Ctrl+D, Ctrl+C
        """
        self.session_start_time = datetime.now()
        
        # Display welcome message
        self._display_welcome()
        
        try:
            # Send initial prompt
            self.console.print("\n[bold cyan]🤖 Assistant:[/bold cyan]")
            self._send_and_display(self.initial_prompt, is_initial=True)
            
            # Interactive loop
            while True:
                # Get user input
                user_message = self._handle_user_input()
                
                if user_message is None:
                    # User wants to exit
                    break
                
                # Send message and display response
                self.console.print("\n[bold cyan]🤖 Assistant:[/bold cyan]")
                self._send_and_display(user_message)
        
        except KeyboardInterrupt:
            self.console.print("\n\n[yellow]Session interrupted by user.[/yellow]")
        
        except Exception as e:
            self.console.print(f"\n\n[bold red]Error:[/bold red] {e}")
        
        finally:
            # Display session summary
            self._display_session_summary()
    
    def _display_welcome(self) -> None:
        """Display welcome message for the session."""
        welcome_panel = Panel(
            "[bold green]Interactive Prompt Testing Session[/bold green]\n\n"
            "Type your messages and press Enter to send.\n"
            "Commands: [cyan]exit[/cyan], [cyan]quit[/cyan], or press [cyan]Ctrl+D[/cyan] to end session.",
            title="🚀 PromptV Test Mode",
            border_style="green"
        )
        self.console.print(welcome_panel)
        self.console.print()
    
    def _handle_user_input(self) -> Optional[str]:
        """
        Handle user input from terminal.
        
        Returns:
            User message string, or None if user wants to exit
        """
        try:
            # Display prompt
            self.console.print("\n[bold green]You:[/bold green] ", end="")
            
            # Read input
            user_input = input()
            
            # Check for exit commands
            if user_input.strip().lower() in ['exit', 'quit']:
                return None
            
            # Check for empty input
            if not user_input.strip():
                self.console.print("[yellow]Empty message. Please type something or use 'exit' to quit.[/yellow]")
                return self._handle_user_input()  # Recursive call to get valid input
            
            return user_input.strip()
        
        except EOFError:
            # Ctrl+D pressed
            self.console.print("\n")
            return None
    
    def _send_and_display(self, user_message: str, is_initial: bool = False) -> None:
        """
        Send user message to LLM and display the response.
        
        Args:
            user_message: Message to send
            is_initial: Whether this is the initial prompt (default: False)
        """
        try:
            # Add user message to conversation history
            if is_initial:
                # Initial prompt is treated as a system message
                self.conversation_history.append({
                    "role": "system",
                    "content": user_message
                })
            else:
                self.conversation_history.append({
                    "role": "user",
                    "content": user_message
                })
            
            # Send message to provider
            response_text, prompt_tokens, completion_tokens, cost = self.provider.send_message(
                messages=self.conversation_history,
                stream=True,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # Add response to conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": response_text
            })
            
            # Update totals
            self.total_prompt_tokens += prompt_tokens
            self.total_completion_tokens += completion_tokens
            self.total_cost += cost
            self.message_count += 1
            
            # Display token usage and cost
            if self.show_costs:
                self._display_message_stats(prompt_tokens, completion_tokens, cost)
        
        except APIKeyError as e:
            self.console.print(f"\n[bold red]API Key Error:[/bold red] {e}")
            self.console.print("[yellow]Please check your API key and try again.[/yellow]")
            raise
        
        except APIError as e:
            self.console.print(f"\n[bold red]API Error:[/bold red] {e}")
            self.console.print("[yellow]The API returned an error. Please try again.[/yellow]")
            raise
        
        except NetworkError as e:
            self.console.print(f"\n[bold red]Network Error:[/bold red] {e}")
            self.console.print("[yellow]Please check your internet connection and try again.[/yellow]")
            raise
        
        except Exception as e:
            self.console.print(f"\n[bold red]Unexpected Error:[/bold red] {e}")
            raise
    
    def _display_message_stats(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        cost: float
    ) -> None:
        """
        Display token usage and cost for a single message.
        
        Args:
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            cost: Cost in dollars
        """
        total_tokens = prompt_tokens + completion_tokens
        
        stats_text = (
            f"[dim]Tokens: {total_tokens:,} "
            f"(input: {prompt_tokens:,}, output: {completion_tokens:,})"
        )
        
        if cost > 0:
            stats_text += f" | Cost: ${cost:.6f}"
        
        stats_text += "[/dim]"
        
        self.console.print(f"\n{stats_text}")
    
    def _display_session_summary(self) -> None:
        """Display summary statistics for the entire session."""
        self.console.print("\n")
        
        # Calculate session duration
        if self.session_start_time:
            duration = datetime.now() - self.session_start_time
            duration_seconds = int(duration.total_seconds())
            duration_str = f"{duration_seconds // 60}m {duration_seconds % 60}s"
        else:
            duration_str = "Unknown"
        
        # Create summary table
        table = Table(title="📊 Session Summary", border_style="blue")
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="green")
        
        table.add_row("Messages Sent", str(self.message_count))
        table.add_row("Session Duration", duration_str)
        table.add_row("Total Tokens", f"{self.total_prompt_tokens + self.total_completion_tokens:,}")
        table.add_row("  - Input Tokens", f"{self.total_prompt_tokens:,}")
        table.add_row("  - Output Tokens", f"{self.total_completion_tokens:,}")
        
        if self.show_costs and self.total_cost > 0:
            table.add_row("Total Cost", f"${self.total_cost:.6f}")
        
        self.console.print(table)
        
        # Farewell message
        self.console.print("\n[bold green]Thank you for testing with PromptV! 👋[/bold green]\n")
