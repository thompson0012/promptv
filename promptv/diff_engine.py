"""
DiffEngine for comparing prompt versions with beautiful formatting.

Supports multiple output formats:
- Side-by-side: Visual comparison with color-coded changes
- Unified: Traditional unified diff format
- JSON: Programmatic access to diff data
"""

import difflib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

from rich.console import Console
from rich.table import Table
from rich.text import Text


class DiffFormat(str, Enum):
    """Supported diff output formats."""
    
    SIDE_BY_SIDE = "side-by-side"
    UNIFIED = "unified"
    JSON = "json"


@dataclass
class DiffLine:
    """Represents a single line in a diff."""
    
    line_num_a: Optional[int]
    line_num_b: Optional[int]
    content_a: str
    content_b: str
    change_type: str  # 'equal', 'insert', 'delete', 'replace'


class DiffEngine:
    """
    Engine for generating diffs between prompt versions.
    
    Provides multiple output formats with intelligent diff highlighting
    and beautiful terminal formatting using Rich.
    """
    
    def __init__(self, console: Optional[Console] = None):
        """
        Initialize DiffEngine.
        
        Args:
            console: Rich Console instance. Creates new one if not provided.
        """
        self.console = console or Console()
    
    def diff_versions(
        self,
        content_a: str,
        content_b: str,
        label_a: str = "Version A",
        label_b: str = "Version B",
        format: DiffFormat = DiffFormat.SIDE_BY_SIDE,
        context_lines: int = 3,
    ) -> str:
        """
        Generate diff between two versions.
        
        Args:
            content_a: First version content
            content_b: Second version content
            label_a: Label for first version (e.g., "v1", "prod")
            label_b: Label for second version (e.g., "v2", "staging")
            format: Output format (side-by-side, unified, json)
            context_lines: Number of context lines for unified diff
        
        Returns:
            Formatted diff string based on selected format
        """
        if format == DiffFormat.SIDE_BY_SIDE:
            return self._side_by_side_diff(content_a, content_b, label_a, label_b)
        elif format == DiffFormat.UNIFIED:
            return self._unified_diff(content_a, content_b, label_a, label_b, context_lines)
        elif format == DiffFormat.JSON:
            return self._json_diff(content_a, content_b, label_a, label_b)
        else:
            raise ValueError(f"Unknown diff format: {format}")
    
    def _side_by_side_diff(
        self,
        content_a: str,
        content_b: str,
        label_a: str,
        label_b: str,
    ) -> str:
        """
        Generate side-by-side diff with color coding and git-style markers.
        
        Uses Rich Table to display two columns with color-coded changes:
        - Red with '--': Deletions (in left column)
        - Green with '++': Additions (in right column)
        - Yellow with '~~': Modifications (in both columns)
        - White: Unchanged (in both columns)
        
        Args:
            content_a: First version content
            content_b: Second version content
            label_a: Label for first version
            label_b: Label for second version
        
        Returns:
            Rendered table as string
        """
        lines_a = content_a.splitlines()
        lines_b = content_b.splitlines()
        
        # Create Rich table
        table = Table(
            title=f"Diff: {label_a} ↔ {label_b}",
            show_header=True,
            header_style="bold magenta",
            border_style="blue",
            expand=True,
        )
        
        table.add_column(f"  {label_a}", style="dim", width=50)
        table.add_column(f"  {label_b}", style="dim", width=50)
        
        # Generate diff using SequenceMatcher
        diff_lines = self._generate_diff_lines(lines_a, lines_b)
        
        # Add rows to table
        for diff_line in diff_lines:
            left_text = Text()
            right_text = Text()
            
            if diff_line.change_type == "equal":
                # Unchanged lines - show in both columns
                left_text.append(f"{diff_line.line_num_a or ' ':3} ", style="dim")
                left_text.append("   ")  # No marker
                left_text.append(diff_line.content_a)
                right_text.append(f"{diff_line.line_num_b or ' ':3} ", style="dim")
                right_text.append("   ")  # No marker
                right_text.append(diff_line.content_b)
                
            elif diff_line.change_type == "delete":
                # Deleted line - show only in left column with '--'
                left_text.append(f"{diff_line.line_num_a or ' ':3} ", style="dim")
                left_text.append("-- ", style="red bold")
                left_text.append(diff_line.content_a, style="red")
                right_text.append("    ")  # Empty right side
                
            elif diff_line.change_type == "insert":
                # Inserted line - show only in right column with '++'
                left_text.append("    ")  # Empty left side
                right_text.append(f"{diff_line.line_num_b or ' ':3} ", style="dim")
                right_text.append("++ ", style="green bold")
                right_text.append(diff_line.content_b, style="green")
                
            elif diff_line.change_type == "replace":
                # Modified line - show in both columns with '~~'
                left_text.append(f"{diff_line.line_num_a or ' ':3} ", style="dim")
                left_text.append("~~ ", style="yellow bold")
                left_text.append(diff_line.content_a, style="yellow")
                right_text.append(f"{diff_line.line_num_b or ' ':3} ", style="dim")
                right_text.append("~~ ", style="yellow bold")
                right_text.append(diff_line.content_b, style="yellow")
            
            table.add_row(left_text, right_text)
        
        # Render table to string
        with self.console.capture() as capture:
            self.console.print(table)
        
        return capture.get()
    
    def _unified_diff(
        self,
        content_a: str,
        content_b: str,
        label_a: str,
        label_b: str,
        context_lines: int = 3,
    ) -> str:
        """
        Generate unified diff format.
        
        Uses Python's difflib to generate traditional unified diff output.
        
        Args:
            content_a: First version content
            content_b: Second version content
            label_a: Label for first version
            label_b: Label for second version
            context_lines: Number of context lines
        
        Returns:
            Unified diff string
        """
        lines_a = content_a.splitlines(keepends=True)
        lines_b = content_b.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            lines_a,
            lines_b,
            fromfile=label_a,
            tofile=label_b,
            lineterm='',
            n=context_lines,
        )
        
        # Apply color coding using Rich
        result = Text()
        for line in diff:
            if line.startswith('---') or line.startswith('+++'):
                result.append(line + '\n', style="bold")
            elif line.startswith('@@'):
                result.append(line + '\n', style="cyan")
            elif line.startswith('-'):
                result.append(line + '\n', style="red")
            elif line.startswith('+'):
                result.append(line + '\n', style="green")
            else:
                result.append(line + '\n')
        
        with self.console.capture() as capture:
            self.console.print(result)
        
        return capture.get()
    
    def _json_diff(
        self,
        content_a: str,
        content_b: str,
        label_a: str,
        label_b: str,
    ) -> str:
        """
        Generate JSON representation of diff.
        
        Useful for programmatic access to diff data.
        
        Args:
            content_a: First version content
            content_b: Second version content
            label_a: Label for first version
            label_b: Label for second version
        
        Returns:
            JSON string with diff data
        """
        lines_a = content_a.splitlines()
        lines_b = content_b.splitlines()
        
        diff_lines = self._generate_diff_lines(lines_a, lines_b)
        
        # Convert to JSON-serializable format
        diff_data = {
            "label_a": label_a,
            "label_b": label_b,
            "changes": [
                {
                    "line_num_a": line.line_num_a,
                    "line_num_b": line.line_num_b,
                    "content_a": line.content_a,
                    "content_b": line.content_b,
                    "type": line.change_type,
                }
                for line in diff_lines
            ],
            "stats": self._calculate_stats(diff_lines),
        }
        
        return json.dumps(diff_data, indent=2)
    
    def _generate_diff_lines(
        self,
        lines_a: List[str],
        lines_b: List[str],
    ) -> List[DiffLine]:
        """
        Generate list of DiffLine objects using SequenceMatcher.
        
        This provides intelligent diff matching that handles insertions,
        deletions, and replacements.
        
        Args:
            lines_a: Lines from first version
            lines_b: Lines from second version
        
        Returns:
            List of DiffLine objects
        """
        matcher = difflib.SequenceMatcher(None, lines_a, lines_b)
        diff_lines: List[DiffLine] = []
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                # Unchanged lines
                for i, j in zip(range(i1, i2), range(j1, j2)):
                    diff_lines.append(
                        DiffLine(
                            line_num_a=i + 1,
                            line_num_b=j + 1,
                            content_a=lines_a[i],
                            content_b=lines_b[j],
                            change_type="equal",
                        )
                    )
            
            elif tag == "delete":
                # Deleted lines (only in A)
                for i in range(i1, i2):
                    diff_lines.append(
                        DiffLine(
                            line_num_a=i + 1,
                            line_num_b=None,
                            content_a=lines_a[i],
                            content_b="",
                            change_type="delete",
                        )
                    )
            
            elif tag == "insert":
                # Inserted lines (only in B)
                for j in range(j1, j2):
                    diff_lines.append(
                        DiffLine(
                            line_num_a=None,
                            line_num_b=j + 1,
                            content_a="",
                            content_b=lines_b[j],
                            change_type="insert",
                        )
                    )
            
            elif tag == "replace":
                # Modified lines - pair them up
                len_a = i2 - i1
                len_b = j2 - j1
                max_len = max(len_a, len_b)
                
                for k in range(max_len):
                    line_a_idx = i1 + k if k < len_a else None
                    line_b_idx = j1 + k if k < len_b else None
                    
                    if line_a_idx is not None and line_b_idx is not None:
                        # Both sides have content - replacement
                        diff_lines.append(
                            DiffLine(
                                line_num_a=line_a_idx + 1,
                                line_num_b=line_b_idx + 1,
                                content_a=lines_a[line_a_idx],
                                content_b=lines_b[line_b_idx],
                                change_type="replace",
                            )
                        )
                    elif line_a_idx is not None:
                        # Only left side - deletion
                        diff_lines.append(
                            DiffLine(
                                line_num_a=line_a_idx + 1,
                                line_num_b=None,
                                content_a=lines_a[line_a_idx],
                                content_b="",
                                change_type="delete",
                            )
                        )
                    elif line_b_idx is not None:
                        # Only right side - insertion
                        diff_lines.append(
                            DiffLine(
                                line_num_a=None,
                                line_num_b=line_b_idx + 1,
                                content_a="",
                                content_b=lines_b[line_b_idx],
                                change_type="insert",
                            )
                        )
        
        return diff_lines
    
    def _calculate_stats(self, diff_lines: List[DiffLine]) -> Dict[str, int]:
        """
        Calculate statistics about the diff.
        
        Args:
            diff_lines: List of DiffLine objects
        
        Returns:
            Dictionary with stats (additions, deletions, changes, unchanged)
        """
        stats = {
            "additions": 0,
            "deletions": 0,
            "changes": 0,
            "unchanged": 0,
        }
        
        for line in diff_lines:
            if line.change_type == "equal":
                stats["unchanged"] += 1
            elif line.change_type == "insert":
                stats["additions"] += 1
            elif line.change_type == "delete":
                stats["deletions"] += 1
            elif line.change_type == "replace":
                stats["changes"] += 1
        
        return stats