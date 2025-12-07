"""
Utility functions for promptv CLI.
"""
from typing import Dict
from urllib.parse import urlparse
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from promptv.models import CostEstimate


def is_valid_url(url: str) -> bool:
    """
    Validate if a string is a valid URL.
    
    Args:
        url: URL string to validate
        
    Returns:
        True if valid URL, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc]) and result.scheme in ['http', 'https']
    except Exception:
        return False


def format_cost_estimate(cost: CostEstimate, show_detail: bool = True) -> None:
    """
    Display a formatted cost estimate using Rich.
    
    Args:
        cost: CostEstimate object to format
        show_detail: Whether to show detailed breakdown (default: True)
    """
    console = Console()
    
    if show_detail:
        # Create detailed table
        table = Table(title="Cost Estimate", show_header=True, header_style="bold cyan")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green", justify="right")
        
        # Add rows
        table.add_row("Provider", cost.provider)
        table.add_row("Model", cost.model)
        table.add_row("", "")  # Spacer
        table.add_row("Input Tokens", f"{cost.input_tokens:,}")
        table.add_row("Estimated Output Tokens", f"{cost.estimated_output_tokens:,}")
        table.add_row("Total Tokens", f"{cost.total_tokens:,}", style="bold")
        table.add_row("", "")  # Spacer
        table.add_row("Input Cost", f"${cost.input_cost:.6f}")
        table.add_row("Estimated Output Cost", f"${cost.estimated_output_cost:.6f}")
        table.add_row("Total Cost", f"${cost.total_cost:.6f}", style="bold green")
        
        console.print(table)
    else:
        # Simple one-line output
        console.print(
            f"[cyan]{cost.provider}/{cost.model}[/cyan]: "
            f"[green]{cost.total_tokens:,}[/green] tokens, "
            f"[bold green]${cost.total_cost:.6f}[/bold green]"
        )


def format_cost_comparison(comparisons: Dict[str, CostEstimate]) -> None:
    """
    Display a comparison table of costs across multiple models.
    
    Args:
        comparisons: Dictionary mapping "provider/model" to CostEstimate
    """
    console = Console()
    
    # Create comparison table
    table = Table(
        title="Cost Comparison Across Models",
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("Provider/Model", style="cyan")
    table.add_column("Input Tokens", justify="right")
    table.add_column("Output Tokens", justify="right")
    table.add_column("Total Tokens", justify="right")
    table.add_column("Input Cost", justify="right")
    table.add_column("Output Cost", justify="right")
    table.add_column("Total Cost", justify="right", style="bold green")
    
    # Sort by total cost (cheapest first)
    sorted_comparisons = sorted(
        [(k, v) for k, v in comparisons.items() if v is not None],
        key=lambda x: x[1].total_cost
    )
    
    # Add rows
    for key, cost in sorted_comparisons:
        table.add_row(
            key,
            f"{cost.input_tokens:,}",
            f"{cost.estimated_output_tokens:,}",
            f"{cost.total_tokens:,}",
            f"${cost.input_cost:.6f}",
            f"${cost.estimated_output_cost:.6f}",
            f"${cost.total_cost:.6f}"
        )
    
    # Add failed models if any
    failed = [k for k, v in comparisons.items() if v is None]
    if failed:
        console.print()
        console.print("[yellow]Warning:[/yellow] Could not estimate cost for:", style="yellow")
        for model in failed:
            console.print(f"  - {model}", style="dim")
        console.print()
    
    console.print(table)
    
    # Highlight cheapest option
    if sorted_comparisons:
        cheapest_key, cheapest_cost = sorted_comparisons[0]
        console.print()
        console.print(
            Panel(
                f"[bold green]Cheapest option:[/bold green] {cheapest_key} "
                f"at ${cheapest_cost.total_cost:.6f}",
                border_style="green"
            )
        )


def format_token_count(tokens: int, model: str, provider: str) -> None:
    """
    Display a simple token count.
    
    Args:
        tokens: Number of tokens
        model: Model name
        provider: Provider name
    """
    console = Console()
    console.print(
        f"[cyan]{provider}/{model}[/cyan]: [bold green]{tokens:,}[/bold green] tokens"
    )


def confirm_cost(cost: CostEstimate, threshold: float = 0.10) -> bool:
    """
    Prompt user to confirm if cost exceeds threshold.
    
    Args:
        cost: CostEstimate object
        threshold: Cost threshold in USD (default: $0.10)
    
    Returns:
        True if user confirms or cost is below threshold, False otherwise
    """
    if cost.total_cost < threshold:
        return True
    
    console = Console()
    
    # Display cost estimate
    console.print()
    console.print(
        Panel(
            f"[yellow]Warning:[/yellow] Estimated cost is [bold]${cost.total_cost:.6f}[/bold]\n"
            f"This exceeds the threshold of ${threshold:.2f}",
            title="Cost Confirmation Required",
            border_style="yellow"
        )
    )
    
    format_cost_estimate(cost, show_detail=True)
    console.print()
    
    # Prompt for confirmation
    response = console.input("[yellow]Continue?[/yellow] (y/N): ")
    return response.lower() in ('y', 'yes')


def format_error(error_message: str, suggestion: str = None) -> None:
    """
    Display a formatted error message.
    
    Args:
        error_message: Error message to display
        suggestion: Optional suggestion for fixing the error
    """
    console = Console()
    
    content = f"[bold red]Error:[/bold red] {error_message}"
    if suggestion:
        content += f"\n\n[cyan]Suggestion:[/cyan] {suggestion}"
    
    console.print(Panel(content, border_style="red", title="Error"))


def format_success(message: str) -> None:
    """
    Display a formatted success message.
    
    Args:
        message: Success message to display
    """
    console = Console()
    console.print(f"[bold green]✓[/bold green] {message}")