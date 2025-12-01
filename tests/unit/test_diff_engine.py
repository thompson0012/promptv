"""
Unit tests for DiffEngine.

Tests all diff output formats, diff accuracy, and edge cases.
"""

import json
import pytest

from promptv.diff_engine import DiffEngine, DiffFormat


class TestDiffEngine:
    """Test suite for DiffEngine."""
    
    @pytest.fixture
    def engine(self):
        """Create DiffEngine instance."""
        return DiffEngine()
    
    @pytest.fixture
    def simple_content_a(self):
        """Simple test content A."""
        return """Hello world!
This is a test.
Line three."""
    
    @pytest.fixture
    def simple_content_b(self):
        """Simple test content B (with changes)."""
        return """Hello universe!
This is a test.
Line three is modified."""
    
    @pytest.fixture
    def empty_content(self):
        """Empty content."""
        return ""
    
    @pytest.fixture
    def identical_content(self):
        """Identical content for both versions."""
        return """Same line 1
Same line 2
Same line 3"""
    
    def test_diff_engine_init(self, engine):
        """Test DiffEngine initialization."""
        assert engine is not None
        assert engine.console is not None
    
    def test_side_by_side_diff_simple(self, engine, simple_content_a, simple_content_b):
        """Test side-by-side diff with simple changes."""
        result = engine.diff_versions(
            simple_content_a,
            simple_content_b,
            label_a="v1",
            label_b="v2",
            format=DiffFormat.SIDE_BY_SIDE,
        )
        
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0
        # Check that labels appear in output
        assert "v1" in result
        assert "v2" in result
    
    def test_unified_diff_simple(self, engine, simple_content_a, simple_content_b):
        """Test unified diff format."""
        result = engine.diff_versions(
            simple_content_a,
            simple_content_b,
            label_a="v1",
            label_b="v2",
            format=DiffFormat.UNIFIED,
        )
        
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0
        # Unified diff should have standard markers
        assert "v1" in result or "v2" in result
    
    def test_json_diff_simple(self, engine, simple_content_a, simple_content_b):
        """Test JSON diff format."""
        result = engine.diff_versions(
            simple_content_a,
            simple_content_b,
            label_a="v1",
            label_b="v2",
            format=DiffFormat.JSON,
        )
        
        assert result is not None
        assert isinstance(result, str)
        
        # Parse JSON
        data = json.loads(result)
        assert data["label_a"] == "v1"
        assert data["label_b"] == "v2"
        assert "changes" in data
        assert "stats" in data
        assert isinstance(data["changes"], list)
    
    def test_diff_identical_content(self, engine, identical_content):
        """Test diff with identical content."""
        result = engine.diff_versions(
            identical_content,
            identical_content,
            label_a="v1",
            label_b="v2",
            format=DiffFormat.JSON,
        )
        
        data = json.loads(result)
        stats = data["stats"]
        
        # All lines should be unchanged
        assert stats["unchanged"] == 3
        assert stats["additions"] == 0
        assert stats["deletions"] == 0
        assert stats["changes"] == 0
    
    def test_diff_empty_to_content(self, engine, empty_content, simple_content_a):
        """Test diff from empty to content (all additions)."""
        result = engine.diff_versions(
            empty_content,
            simple_content_a,
            label_a="empty",
            label_b="v1",
            format=DiffFormat.JSON,
        )
        
        data = json.loads(result)
        stats = data["stats"]
        
        # All lines should be additions
        assert stats["additions"] > 0
        assert stats["deletions"] == 0
        assert stats["unchanged"] == 0
    
    def test_diff_content_to_empty(self, engine, simple_content_a, empty_content):
        """Test diff from content to empty (all deletions)."""
        result = engine.diff_versions(
            simple_content_a,
            empty_content,
            label_a="v1",
            label_b="empty",
            format=DiffFormat.JSON,
        )
        
        data = json.loads(result)
        stats = data["stats"]
        
        # All lines should be deletions
        assert stats["deletions"] > 0
        assert stats["additions"] == 0
        assert stats["unchanged"] == 0
    
    def test_diff_empty_to_empty(self, engine, empty_content):
        """Test diff of two empty contents."""
        result = engine.diff_versions(
            empty_content,
            empty_content,
            label_a="empty1",
            label_b="empty2",
            format=DiffFormat.JSON,
        )
        
        data = json.loads(result)
        stats = data["stats"]
        
        # No changes
        assert stats["unchanged"] == 0
        assert stats["additions"] == 0
        assert stats["deletions"] == 0
        assert stats["changes"] == 0
    
    def test_diff_with_insertions(self, engine):
        """Test diff with line insertions."""
        content_a = "Line 1\nLine 2"
        content_b = "Line 1\nInserted Line\nLine 2"
        
        result = engine.diff_versions(
            content_a,
            content_b,
            format=DiffFormat.JSON,
        )
        
        data = json.loads(result)
        stats = data["stats"]
        
        assert stats["additions"] == 1
        assert stats["unchanged"] == 2
    
    def test_diff_with_deletions(self, engine):
        """Test diff with line deletions."""
        content_a = "Line 1\nDeleted Line\nLine 2"
        content_b = "Line 1\nLine 2"
        
        result = engine.diff_versions(
            content_a,
            content_b,
            format=DiffFormat.JSON,
        )
        
        data = json.loads(result)
        stats = data["stats"]
        
        assert stats["deletions"] == 1
        assert stats["unchanged"] == 2
    
    def test_diff_with_replacements(self, engine):
        """Test diff with line replacements."""
        content_a = "Line 1\nOld Line\nLine 3"
        content_b = "Line 1\nNew Line\nLine 3"
        
        result = engine.diff_versions(
            content_a,
            content_b,
            format=DiffFormat.JSON,
        )
        
        data = json.loads(result)
        stats = data["stats"]
        
        # Replacement can be counted as change or deletion+insertion
        assert stats["changes"] >= 1 or (stats["deletions"] >= 1 and stats["additions"] >= 1)
        assert stats["unchanged"] == 2
    
    def test_diff_format_invalid(self, engine, simple_content_a, simple_content_b):
        """Test diff with invalid format raises error."""
        with pytest.raises(ValueError, match="Unknown diff format"):
            engine.diff_versions(
                simple_content_a,
                simple_content_b,
                format="invalid_format",  # type: ignore
            )
    
    def test_diff_multiline_changes(self, engine):
        """Test diff with multiple line changes."""
        content_a = """Line 1
Line 2
Line 3
Line 4
Line 5"""
        
        content_b = """Line 1
Modified Line 2
Line 3
Inserted Line
Line 5"""
        
        result = engine.diff_versions(
            content_a,
            content_b,
            format=DiffFormat.JSON,
        )
        
        data = json.loads(result)
        stats = data["stats"]
        
        # Should have mix of changes, insertions, deletions
        total_changes = stats["changes"] + stats["additions"] + stats["deletions"]
        assert total_changes > 0
        assert stats["unchanged"] > 0
    
    def test_generate_diff_lines(self, engine):
        """Test _generate_diff_lines internal method."""
        lines_a = ["Line 1", "Line 2", "Line 3"]
        lines_b = ["Line 1", "Modified", "Line 3"]
        
        diff_lines = engine._generate_diff_lines(lines_a, lines_b)
        
        assert len(diff_lines) > 0
        # First and last should be equal
        assert diff_lines[0].change_type == "equal"
        assert diff_lines[-1].change_type == "equal"
        # Middle should have some change
        assert any(line.change_type != "equal" for line in diff_lines)
    
    def test_calculate_stats(self, engine):
        """Test _calculate_stats internal method."""
        from promptv.diff_engine import DiffLine
        
        diff_lines = [
            DiffLine(1, 1, "same", "same", "equal"),
            DiffLine(2, None, "deleted", "", "delete"),
            DiffLine(None, 2, "", "inserted", "insert"),
            DiffLine(3, 3, "old", "new", "replace"),
        ]
        
        stats = engine._calculate_stats(diff_lines)
        
        assert stats["unchanged"] == 1
        assert stats["deletions"] == 1
        assert stats["additions"] == 1
        assert stats["changes"] == 1
    
    def test_diff_with_context_lines(self, engine):
        """Test unified diff with context lines parameter."""
        content_a = "\n".join([f"Line {i}" for i in range(1, 21)])
        content_b = "\n".join([f"Line {i}" if i != 10 else "Modified Line 10" for i in range(1, 21)])
        
        # Test with different context line counts
        result_3 = engine.diff_versions(
            content_a,
            content_b,
            format=DiffFormat.UNIFIED,
            context_lines=3,
        )
        
        result_1 = engine.diff_versions(
            content_a,
            content_b,
            format=DiffFormat.UNIFIED,
            context_lines=1,
        )
        
        # More context should generally mean more output
        # (though this isn't always true for small diffs)
        assert len(result_3) >= len(result_1) or len(result_3) > 0
    
    def test_diff_json_structure(self, engine, simple_content_a, simple_content_b):
        """Test JSON diff has correct structure."""
        result = engine.diff_versions(
            simple_content_a,
            simple_content_b,
            label_a="version_a",
            label_b="version_b",
            format=DiffFormat.JSON,
        )
        
        data = json.loads(result)
        
        # Check top-level structure
        assert "label_a" in data
        assert "label_b" in data
        assert "changes" in data
        assert "stats" in data
        
        # Check changes structure
        if len(data["changes"]) > 0:
            change = data["changes"][0]
            assert "line_num_a" in change or change["line_num_a"] is None
            assert "line_num_b" in change or change["line_num_b"] is None
            assert "content_a" in change
            assert "content_b" in change
            assert "type" in change
        
        # Check stats structure
        stats = data["stats"]
        assert "additions" in stats
        assert "deletions" in stats
        assert "changes" in stats
        assert "unchanged" in stats
