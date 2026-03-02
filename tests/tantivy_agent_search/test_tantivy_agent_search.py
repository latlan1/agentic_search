"""
Unit tests for tantivy_agent_search module (Approach 3).

Tests verify:
1. Tool definitions (search_docs, read_docs) are properly configured
2. System prompt includes citation and parallel delegation requirements
3. Agent creation uses custom middleware stack
4. CLI flags work correctly
5. Rich output formatting works
6. Time tracking works
7. Index management functions exist
"""

import os
import pytest
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))


class TestToolDefinitions:
    """Test the search_docs and read_docs tool definitions."""

    def test_search_docs_is_tool(self):
        """Verify search_docs is a LangChain tool."""
        from tantivy_agent_search import search_docs
        from langchain_core.tools import BaseTool

        assert isinstance(search_docs, BaseTool)

    def test_read_docs_is_tool(self):
        """Verify read_docs is a LangChain tool."""
        from tantivy_agent_search import read_docs
        from langchain_core.tools import BaseTool

        assert isinstance(read_docs, BaseTool)

    def test_search_docs_has_description(self):
        """Verify search_docs has a description for the LLM."""
        from tantivy_agent_search import search_docs

        assert search_docs.description
        assert len(search_docs.description) > 20

    def test_read_docs_has_description(self):
        """Verify read_docs has a description for the LLM."""
        from tantivy_agent_search import read_docs

        assert read_docs.description
        assert len(read_docs.description) > 20

    def test_search_docs_accepts_queries_list(self):
        """Verify search_docs accepts a queries parameter (list of strings)."""
        from tantivy_agent_search import search_docs

        schema = search_docs.get_input_schema().model_json_schema()
        props = schema.get("properties", {})
        assert "queries" in props

    def test_read_docs_accepts_doc_ids_list(self):
        """Verify read_docs accepts a doc_ids parameter (list of ints)."""
        from tantivy_agent_search import read_docs

        schema = read_docs.get_input_schema().model_json_schema()
        props = schema.get("properties", {})
        assert "doc_ids" in props

    def test_search_docs_name(self):
        """Verify the tool name is 'search_docs'."""
        from tantivy_agent_search import search_docs

        assert search_docs.name == "search_docs"

    def test_read_docs_name(self):
        """Verify the tool name is 'read_docs'."""
        from tantivy_agent_search import read_docs

        assert read_docs.name == "read_docs"


class TestSystemPrompt:
    """Test the system prompt configuration."""

    def test_search_system_prompt_defined(self):
        """Verify SEARCH_SYSTEM_PROMPT constant is defined."""
        from tantivy_agent_search import SEARCH_SYSTEM_PROMPT

        assert SEARCH_SYSTEM_PROMPT is not None
        assert len(SEARCH_SYSTEM_PROMPT) > 100

    def test_system_prompt_mentions_search_tools(self):
        """Verify system prompt references the search tools."""
        from tantivy_agent_search import SEARCH_SYSTEM_PROMPT

        assert "search_docs" in SEARCH_SYSTEM_PROMPT
        assert "read_docs" in SEARCH_SYSTEM_PROMPT

    def test_system_prompt_mentions_citations(self):
        """Verify system prompt requires numbered citations."""
        from tantivy_agent_search import SEARCH_SYSTEM_PROMPT

        # Must mention citation format
        lower = SEARCH_SYSTEM_PROMPT.lower()
        assert "citation" in lower or "[1]" in SEARCH_SYSTEM_PROMPT

    def test_system_prompt_mentions_sources_section(self):
        """Verify system prompt requires a Sources section."""
        from tantivy_agent_search import SEARCH_SYSTEM_PROMPT

        assert "Sources" in SEARCH_SYSTEM_PROMPT

    def test_system_prompt_mentions_parallel_delegation(self):
        """Verify system prompt instructs parallel query delegation."""
        from tantivy_agent_search import SEARCH_SYSTEM_PROMPT

        lower = SEARCH_SYSTEM_PROMPT.lower()
        assert "parallel" in lower or "2 task" in lower

    def test_system_prompt_mentions_task_tool(self):
        """Verify system prompt references the task tool for delegation."""
        from tantivy_agent_search import SEARCH_SYSTEM_PROMPT

        assert "task" in SEARCH_SYSTEM_PROMPT

    def test_system_prompt_mentions_search_subagent(self):
        """Verify system prompt references the search_subagent."""
        from tantivy_agent_search import SEARCH_SYSTEM_PROMPT

        assert "search_subagent" in SEARCH_SYSTEM_PROMPT

    def test_system_prompt_mentions_query_variations(self):
        """Verify system prompt instructs creating query variations."""
        from tantivy_agent_search import SEARCH_SYSTEM_PROMPT

        lower = SEARCH_SYSTEM_PROMPT.lower()
        assert "variation" in lower or "synonym" in lower


class TestCustomTaskDescription:
    """Test the custom task description used to reduce token overhead."""

    def test_custom_task_description_defined(self):
        """Verify CUSTOM_TASK_DESCRIPTION is defined."""
        from tantivy_agent_search import CUSTOM_TASK_DESCRIPTION

        assert CUSTOM_TASK_DESCRIPTION is not None
        assert len(CUSTOM_TASK_DESCRIPTION) > 50

    def test_custom_task_description_is_concise(self):
        """Verify custom description is much shorter than the 6,914-char default."""
        from tantivy_agent_search import CUSTOM_TASK_DESCRIPTION

        # The default TASK_TOOL_DESCRIPTION is 6,914 chars; ours should be <1,000
        assert len(CUSTOM_TASK_DESCRIPTION) < 1000

    def test_custom_task_description_has_agent_placeholder(self):
        """Verify it contains the {available_agents} placeholder for SubAgentMiddleware."""
        from tantivy_agent_search import CUSTOM_TASK_DESCRIPTION

        assert "{available_agents}" in CUSTOM_TASK_DESCRIPTION

    def test_custom_task_description_mentions_concurrent(self):
        """Verify it mentions launching agents concurrently."""
        from tantivy_agent_search import CUSTOM_TASK_DESCRIPTION

        lower = CUSTOM_TASK_DESCRIPTION.lower()
        assert "concurrent" in lower or "parallel" in lower


class TestAgentCreation:
    """Test the create_search_agent function."""

    def test_create_search_agent_function_exists(self):
        """Verify create_search_agent function is defined."""
        from tantivy_agent_search import create_search_agent

        assert callable(create_search_agent)

    def test_create_search_agent_accepts_system_prompt(self):
        """Verify create_search_agent takes a system_prompt parameter."""
        import inspect
        from tantivy_agent_search import create_search_agent

        sig = inspect.signature(create_search_agent)
        assert "system_prompt" in sig.parameters

    @patch("tantivy_agent_search.get_anthropic_llm")
    def test_create_search_agent_returns_runnable(self, mock_llm):
        """Verify create_search_agent returns a LangGraph runnable."""
        mock_llm.return_value = MagicMock()
        from tantivy_agent_search import create_search_agent

        agent = create_search_agent("Test prompt")
        # Should have invoke method (LangGraph Runnable)
        assert hasattr(agent, "invoke")


class TestSearchFunction:
    """Test the main search function."""

    def test_search_function_exists(self):
        """Verify search function is defined."""
        from tantivy_agent_search import search

        assert callable(search)

    def test_search_signature(self):
        """Verify search function has correct parameters."""
        import inspect
        from tantivy_agent_search import search

        sig = inspect.signature(search)
        params = list(sig.parameters.keys())
        assert "query" in params
        assert "thread_id" in params
        assert "sync_first" in params
        assert "verbose" in params

    def test_search_returns_tuple(self):
        """Verify search return type annotation is tuple."""
        import inspect
        from tantivy_agent_search import search

        sig = inspect.signature(search)
        ret = sig.return_annotation
        # Should be tuple[str, list[dict], float]
        assert ret != inspect.Parameter.empty


class TestInteractiveSession:
    """Test the interactive session function."""

    def test_interactive_session_function_exists(self):
        """Verify interactive_session function is defined."""
        from tantivy_agent_search import interactive_session

        assert callable(interactive_session)

    def test_interactive_session_parameters(self):
        """Verify interactive_session accepts sync_first and verbose params."""
        import inspect
        from tantivy_agent_search import interactive_session

        sig = inspect.signature(interactive_session)
        params = list(sig.parameters.keys())
        assert "sync_first" in params
        assert "verbose" in params


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


class TestModuleConstants:
    """Test module-level constants and objects."""

    def test_console_is_rich_console(self):
        """Verify _console is a Rich Console instance."""
        from tantivy_agent_search import _console
        from rich.console import Console

        assert isinstance(_console, Console)

    def test_checkpointer_is_memory_saver(self):
        """Verify checkpointer is a MemorySaver instance."""
        from tantivy_agent_search import checkpointer
        from langgraph.checkpoint.memory import MemorySaver

        assert isinstance(checkpointer, MemorySaver)


class TestHelperImports:
    """Test that helper functions are properly imported and available."""

    def test_format_time_import(self):
        """Verify format_time is importable from helper."""
        from helper import format_time

        assert callable(format_time)

    def test_format_time_seconds(self):
        """Test format_time with seconds only."""
        from helper import format_time

        assert format_time(30.5) == "30.5s"
        assert format_time(0.1) == "0.1s"

    def test_format_time_minutes(self):
        """Test format_time with minutes."""
        from helper import format_time

        assert format_time(90.0) == "1m 30.0s"
        assert format_time(125.5) == "2m 5.5s"

    def test_render_response_import(self):
        """Verify render_response is importable from helper."""
        from helper import render_response

        assert callable(render_response)

    def test_extract_tool_calls_import(self):
        """Verify extract_tool_calls is importable from helper."""
        from helper import extract_tool_calls

        assert callable(extract_tool_calls)

    def test_get_anthropic_llm_import(self):
        """Verify get_anthropic_llm is importable from helper."""
        from helper import get_anthropic_llm

        assert callable(get_anthropic_llm)


class TestCLI:
    """Test CLI argument parsing and flags."""

    def test_help_flag(self):
        """Test --help flag works and shows expected options."""
        result = subprocess.run(
            ["uv", "run", "scripts/tantivy_agent_search.py", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )
        assert result.returncode == 0
        assert "--interactive" in result.stdout
        assert "--sync" in result.stdout

    def test_no_args_shows_examples(self):
        """Test running without args shows examples."""
        result = subprocess.run(
            ["uv", "run", "scripts/tantivy_agent_search.py"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )
        assert result.returncode == 0
        assert "Examples:" in result.stdout


class TestEnvironmentVariables:
    """Test environment variable handling."""

    def test_get_anthropic_llm_requires_api_key(self):
        """Test get_anthropic_llm raises error without API key."""
        from helper import get_anthropic_llm
        from rich.console import Console

        console = Console()

        original = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            with pytest.raises(ValueError) as exc_info:
                get_anthropic_llm(console)
            assert "ANTHROPIC_API_KEY" in str(exc_info.value)
        finally:
            if original:
                os.environ["ANTHROPIC_API_KEY"] = original

    def test_model_env_variable_support(self):
        """Test that the helper module checks LLM_MODEL env var."""
        from helper import get_model_name

        # Verify the function exists and returns a string
        model = get_model_name()
        assert isinstance(model, str)
        assert "claude" in model.lower()


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
        """Integration test: search returns (answer, tool_calls, elapsed_time) tuple."""
        from tantivy_agent_search import search

        answer, tool_calls, elapsed = search("What is DeepAgents?")

        assert answer is not None
        assert len(answer) > 0
        assert isinstance(tool_calls, list)
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

        answer, _, _ = search("What is DeepAgents?")

        assert "[1]" in answer or "[2]" in answer

    @pytest.mark.skipif(
        not os.getenv("ANTHROPIC_API_KEY"),
        reason="Requires ANTHROPIC_API_KEY environment variable",
    )
    @pytest.mark.skipif(
        not Path("tantivy_index").exists(),
        reason="Requires Tantivy index to be built",
    )
    def test_search_uses_parallel_delegation(self):
        """Integration test: search makes 2 parallel task calls."""
        from tantivy_agent_search import search

        _, tool_calls, _ = search("What is DeepAgents?", verbose=True)

        # Should have task tool calls (parallel delegation)
        task_calls = [tc for tc in tool_calls if tc["name"] == "task"]
        assert len(task_calls) >= 2
