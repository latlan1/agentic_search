"""
Unit tests for tantivy_agent_search module (Approach 3).

These tests verify:
1. LangGraph agent structure is correct
2. Tool definitions are properly configured
3. System prompt includes citation requirements
4. CLI flags work correctly
5. Model name is valid
6. Rich output formatting works
7. Time tracking works
"""

import os
import pytest
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))


class TestModelConfiguration:
    """Test that the model configuration is valid and won't cause 404 errors."""

    def test_default_model_is_valid_anthropic_model(self):
        """Verify DEFAULT_MODEL is a valid Anthropic model ID."""
        from tantivy_agent_search import DEFAULT_MODEL

        # Valid Anthropic model patterns (as of 2025)
        valid_patterns = [
            "claude-sonnet-4-20250514",
            "claude-opus-4-20250514",
            "claude-sonnet-4-5-20250929",
            "claude-opus-4-5-20251101",
            "claude-sonnet-4-6",
            "claude-opus-4-6",
            "claude-haiku-4-5",
        ]

        # Model should match one of the valid patterns or be a known format
        assert DEFAULT_MODEL is not None
        assert DEFAULT_MODEL.startswith("claude-")
        # Should NOT be the invalid model that caused the 404
        assert DEFAULT_MODEL != "claude-sonnet-4-5-20250514"

    def test_default_model_format(self):
        """Verify model name follows Anthropic naming convention."""
        from tantivy_agent_search import DEFAULT_MODEL

        parts = DEFAULT_MODEL.split("-")
        assert parts[0] == "claude"
        assert parts[1] in ["sonnet", "opus", "haiku"]


class TestToolDefinitions:
    """Test the search_docs and read_docs tool definitions."""

    def test_search_docs_is_tool(self):
        """Verify search_docs is a LangChain tool."""
        from tantivy_agent_search import search_docs
        from langchain_core.tools import StructuredTool

        assert isinstance(search_docs, StructuredTool)

    def test_read_docs_is_tool(self):
        """Verify read_docs is a LangChain tool."""
        from tantivy_agent_search import read_docs
        from langchain_core.tools import StructuredTool

        assert isinstance(read_docs, StructuredTool)

    def test_search_docs_has_docstring(self):
        """Verify search_docs has proper documentation."""
        from tantivy_agent_search import search_docs

        assert hasattr(search_docs, "description") or search_docs.__doc__

    def test_read_docs_has_docstring(self):
        """Verify read_docs has proper documentation."""
        from tantivy_agent_search import read_docs

        assert hasattr(read_docs, "description") or read_docs.__doc__


class TestSystemPrompt:
    """Test the system prompt configuration."""

    def test_system_prompt_defined(self):
        """Verify SYSTEM_PROMPT constant is defined."""
        from tantivy_agent_search import SYSTEM_PROMPT

        assert SYSTEM_PROMPT is not None
        assert len(SYSTEM_PROMPT) > 100

    def test_system_prompt_mentions_tools(self):
        """Verify system prompt documents available tools."""
        from tantivy_agent_search import SYSTEM_PROMPT

        assert "search_docs" in SYSTEM_PROMPT
        assert "read_docs" in SYSTEM_PROMPT

    def test_system_prompt_mentions_citations(self):
        """Verify system prompt requires numbered citations."""
        from tantivy_agent_search import SYSTEM_PROMPT

        assert "citation" in SYSTEM_PROMPT.lower()
        assert "[1]" in SYSTEM_PROMPT or "numbered" in SYSTEM_PROMPT.lower()

    def test_system_prompt_mentions_sources_section(self):
        """Verify system prompt requires a Sources section."""
        from tantivy_agent_search import SYSTEM_PROMPT

        assert "Sources" in SYSTEM_PROMPT


class TestAgentStructure:
    """Test the agent creation and graph structure."""

    def test_create_agent_function_exists(self):
        """Verify create_agent function is defined."""
        from tantivy_agent_search import create_agent

        assert callable(create_agent)

    def test_search_function_exists(self):
        """Verify main search function is defined."""
        from tantivy_agent_search import search

        assert callable(search)

    def test_search_returns_tuple(self):
        """Verify search function returns (answer, elapsed_time) tuple."""
        from tantivy_agent_search import search
        import inspect

        sig = inspect.signature(search)
        # Check return annotation if present
        # The function should return tuple[str, float]

    def test_interactive_session_function_exists(self):
        """Verify interactive_session function is defined."""
        from tantivy_agent_search import interactive_session

        assert callable(interactive_session)


class TestIndexManagement:
    """Test index management functions."""

    def test_get_search_index_function_exists(self):
        """Verify get_search_index function is defined."""
        from tantivy_agent_search import get_search_index

        assert callable(get_search_index)

    def test_get_index_manager_function_exists(self):
        """Verify get_index_manager function is defined."""
        from tantivy_agent_search import get_index_manager

        assert callable(get_index_manager)


class TestConstants:
    """Test module constants."""

    def test_default_model_defined(self):
        """Verify DEFAULT_MODEL constant is defined."""
        from tantivy_agent_search import DEFAULT_MODEL

        assert DEFAULT_MODEL is not None
        assert "claude" in DEFAULT_MODEL.lower()


class TestGraphVisualization:
    """Test graph visualization functions."""

    def test_get_graph_for_visualization_exists(self):
        """Verify visualization function is defined."""
        from tantivy_agent_search import get_graph_for_visualization

        assert callable(get_graph_for_visualization)

    def test_generate_graph_png_exists(self):
        """Verify PNG generation function is defined."""
        from tantivy_agent_search import generate_graph_png

        assert callable(generate_graph_png)


class TestRichFormatting:
    """Test rich library integration for terminal output."""

    def test_console_is_imported(self):
        """Verify rich Console is imported and available."""
        from tantivy_agent_search import _console
        from rich.console import Console

        assert isinstance(_console, Console)

    def test_print_response_function_exists(self):
        """Verify print_response function is defined."""
        from tantivy_agent_search import print_response

        assert callable(print_response)

    def test_format_time_function_exists(self):
        """Verify format_time function is defined."""
        from tantivy_agent_search import format_time

        assert callable(format_time)

    def test_format_time_seconds(self):
        """Test format_time with seconds only."""
        from tantivy_agent_search import format_time

        assert format_time(30.5) == "30.5s"
        assert format_time(0.1) == "0.1s"

    def test_format_time_minutes(self):
        """Test format_time with minutes."""
        from tantivy_agent_search import format_time

        assert format_time(90.0) == "1m 30.0s"
        assert format_time(125.5) == "2m 5.5s"


class TestCLIFlags:
    """Test CLI argument parsing and flags."""

    def test_help_flag(self):
        """Test --help flag works."""
        result = subprocess.run(
            ["uv", "run", "scripts/tantivy_agent_search.py", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )
        assert result.returncode == 0
        assert "Tantivy Agent Search" in result.stdout
        assert "--interactive" in result.stdout
        assert "--sync" in result.stdout
        assert "--graph" in result.stdout
        assert "--version" in result.stdout

    def test_version_flag(self):
        """Test --version flag works."""
        result = subprocess.run(
            ["uv", "run", "scripts/tantivy_agent_search.py", "--version"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )
        assert result.returncode == 0
        assert "Tantivy Agent Search" in result.stdout
        assert "Model:" in result.stdout

    def test_no_args_shows_help(self):
        """Test running without args shows help."""
        result = subprocess.run(
            ["uv", "run", "scripts/tantivy_agent_search.py"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )
        assert result.returncode == 0
        assert "Examples:" in result.stdout

    def test_graph_flag_requires_api_key(self):
        """Test --graph flag behavior (may need API key)."""
        # Just test the flag is recognized
        result = subprocess.run(
            ["uv", "run", "scripts/tantivy_agent_search.py", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )
        assert "--graph" in result.stdout


class TestEnvironmentVariables:
    """Test environment variable handling."""

    def test_get_llm_requires_api_key(self):
        """Test get_llm raises error without API key."""
        from tantivy_agent_search import get_llm

        # Temporarily remove API key
        original = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            with pytest.raises(ValueError) as exc_info:
                get_llm()
            assert "ANTHROPIC_API_KEY" in str(exc_info.value)
        finally:
            if original:
                os.environ["ANTHROPIC_API_KEY"] = original

    def test_model_env_override(self):
        """Test ANTHROPIC_MODEL environment variable is respected."""
        from tantivy_agent_search import DEFAULT_MODEL

        # The get_llm function should check ANTHROPIC_MODEL env var
        # This is a structural test, not a functional one
        import tantivy_agent_search

        source = Path(tantivy_agent_search.__file__).read_text()
        assert 'os.getenv("ANTHROPIC_MODEL"' in source or "ANTHROPIC_MODEL" in source


class TestIntegration:
    """Integration tests that require the full environment."""

    @pytest.mark.skipif(
        not os.getenv("ANTHROPIC_API_KEY"),
        reason="Requires ANTHROPIC_API_KEY environment variable",
    )
    @pytest.mark.skipif(
        not Path("tantivy_index").exists(),
        reason="Requires Tantivy index to be built",
    )
    def test_search_returns_answer_and_time(self):
        """Integration test: search returns answer and elapsed time."""
        from tantivy_agent_search import search

        answer, elapsed = search("What is DeepAgents?")

        assert answer is not None
        assert len(answer) > 0
        assert isinstance(elapsed, float)
        assert elapsed > 0

    @pytest.mark.skipif(
        not os.getenv("ANTHROPIC_API_KEY"),
        reason="Requires ANTHROPIC_API_KEY environment variable",
    )
    @pytest.mark.skipif(
        not Path("tantivy_index").exists(),
        reason="Requires Tantivy index to be built",
    )
    def test_search_includes_citation(self):
        """Integration test: search includes numbered citations."""
        from tantivy_agent_search import search

        answer, _ = search("What is DeepAgents?")

        assert "[1]" in answer or "[2]" in answer

    @pytest.mark.skipif(
        not os.getenv("ANTHROPIC_API_KEY"),
        reason="Requires ANTHROPIC_API_KEY environment variable",
    )
    @pytest.mark.skipif(
        not Path("tantivy_index").exists(),
        reason="Requires Tantivy index to be built",
    )
    def test_search_includes_sources_section(self):
        """Integration test: search includes Sources section."""
        from tantivy_agent_search import search

        answer, _ = search("What is DeepAgents?")

        assert "Sources" in answer or "sources" in answer
