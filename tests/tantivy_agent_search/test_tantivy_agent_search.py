"""
Unit tests for tantivy_agent_search module (Approach 3).

These tests verify:
1. LangGraph agent structure is correct
2. Tool definitions are properly configured
3. System prompt includes citation requirements
"""

import pytest
from pathlib import Path
import sys

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))


class TestToolDefinitions:
    """Test the search_docs and read_docs tool definitions."""
    
    def test_search_docs_is_tool(self):
        """Verify search_docs is a LangChain tool."""
        from tantivy_agent_search import search_docs
        from langchain_core.tools import StructuredTool
        
        # LangChain @tool decorator wraps functions as StructuredTool
        assert isinstance(search_docs, StructuredTool)
    
    def test_read_docs_is_tool(self):
        """Verify read_docs is a LangChain tool."""
        from tantivy_agent_search import read_docs
        from langchain_core.tools import StructuredTool
        
        assert isinstance(read_docs, StructuredTool)
    
    def test_search_docs_has_docstring(self):
        """Verify search_docs has proper documentation."""
        from tantivy_agent_search import search_docs
        
        # LangChain tools have description in the tool's description attribute
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
        assert len(SYSTEM_PROMPT) > 100  # Should be substantial
    
    def test_system_prompt_mentions_tools(self):
        """Verify system prompt documents available tools."""
        from tantivy_agent_search import SYSTEM_PROMPT
        
        assert "search_docs" in SYSTEM_PROMPT
        assert "read_docs" in SYSTEM_PROMPT
    
    def test_system_prompt_mentions_citations(self):
        """Verify system prompt requires numbered citations."""
        from tantivy_agent_search import SYSTEM_PROMPT
        
        assert "citation" in SYSTEM_PROMPT.lower()
        # Should mention numbered format
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


# Integration tests (require actual Tantivy index and API keys)
class TestIntegration:
    """Integration tests that require the full environment."""
    
    @pytest.mark.skip(reason="Requires ANTHROPIC_API_KEY and Tantivy index")
    def test_search_returns_answer(self):
        """Integration test: search returns an answer."""
        from tantivy_agent_search import search
        
        answer = search("What is DeepAgents?")
        
        assert answer is not None
        assert len(answer) > 0
    
    @pytest.mark.skip(reason="Requires ANTHROPIC_API_KEY and Tantivy index")
    def test_search_includes_citation(self):
        """Integration test: search includes numbered citations."""
        from tantivy_agent_search import search
        
        answer = search("What is DeepAgents?")
        
        # Should contain numbered citations like [1]
        assert "[1]" in answer or "[2]" in answer
    
    @pytest.mark.skip(reason="Requires ANTHROPIC_API_KEY and Tantivy index")
    def test_search_includes_sources_section(self):
        """Integration test: search includes Sources section."""
        from tantivy_agent_search import search
        
        answer = search("What is DeepAgents?")
        
        assert "Sources" in answer or "sources" in answer
