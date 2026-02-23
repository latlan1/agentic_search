"""
Unit tests for deep_agent_search module.

These tests verify:
1. Documentation file loading works correctly
2. Tool filtering removes write operations
3. Virtual paths are correctly mapped
"""

import pytest
from pathlib import Path
import sys

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))


class TestLoadDocumentationFiles:
    """Test the load_documentation_files() function."""
    
    def test_load_documentation_files_returns_dict(self):
        """Verify load_documentation_files returns a dictionary."""
        from deep_agent_search import load_documentation_files
        
        files = load_documentation_files()
        
        assert isinstance(files, dict)
    
    def test_load_documentation_files_has_content(self):
        """Verify documentation files are loaded."""
        from deep_agent_search import load_documentation_files
        
        files = load_documentation_files()
        
        # Should load all markdown files (41 total: 12 deepagents + 29 langgraph)
        assert len(files) > 0
    
    def test_virtual_paths_are_correct(self):
        """Verify virtual paths follow the expected format."""
        from deep_agent_search import load_documentation_files
        
        files = load_documentation_files()
        
        for path in files.keys():
            assert path.startswith("/docs/"), f"Path should start with /docs/: {path}"
            assert path.endswith(".md"), f"Path should end with .md: {path}"
    
    def test_both_corpora_are_loaded(self):
        """Verify both deepagents and langgraph docs are loaded."""
        from deep_agent_search import load_documentation_files
        
        files = load_documentation_files()
        
        deepagent_files = [p for p in files if "/deepagents/" in p]
        langgraph_files = [p for p in files if "/langgraph/" in p]
        
        assert len(deepagent_files) > 0, "Should load deepagents documentation"
        assert len(langgraph_files) > 0, "Should load langgraph documentation"
    
    def test_files_have_proper_format(self):
        """Verify files are formatted with create_file_data (dict with content key)."""
        from deep_agent_search import load_documentation_files
        
        files = load_documentation_files()
        
        for path, file_data in files.items():
            assert isinstance(file_data, dict), f"File data should be a dict: {path}"
            assert "content" in file_data, f"File data should have 'content' key: {path}"


class TestFilterToolsReadOnly:
    """Test the filter_tools_read_only() function."""
    
    def test_filter_removes_write_file(self):
        """Verify write_file is filtered out."""
        from deep_agent_search import filter_tools_read_only
        
        class MockTool:
            def __init__(self, name):
                self.name = name
        
        tools = [
            MockTool("ls"),
            MockTool("read_file"),
            MockTool("write_file"),
        ]
        
        filtered = filter_tools_read_only(tools)
        filtered_names = {t.name for t in filtered}
        
        assert "write_file" not in filtered_names
    
    def test_filter_removes_edit_file(self):
        """Verify edit_file is filtered out."""
        from deep_agent_search import filter_tools_read_only
        
        class MockTool:
            def __init__(self, name):
                self.name = name
        
        tools = [
            MockTool("ls"),
            MockTool("read_file"),
            MockTool("edit_file"),
        ]
        
        filtered = filter_tools_read_only(tools)
        filtered_names = {t.name for t in filtered}
        
        assert "edit_file" not in filtered_names
    
    def test_filter_keeps_read_only_tools(self):
        """Verify read-only tools are kept."""
        from deep_agent_search import filter_tools_read_only, READ_ONLY_TOOLS
        
        class MockTool:
            def __init__(self, name):
                self.name = name
        
        all_tools = [
            MockTool("ls"),
            MockTool("read_file"),
            MockTool("grep"),
            MockTool("glob"),
            MockTool("write_file"),
            MockTool("edit_file"),
        ]
        
        filtered = filter_tools_read_only(all_tools)
        filtered_names = {t.name for t in filtered}
        
        # Verify all READ_ONLY_TOOLS are present
        for tool_name in READ_ONLY_TOOLS:
            assert tool_name in filtered_names, f"Tool {tool_name} should be kept"
    
    def test_filter_returns_only_expected_tools(self):
        """Verify only expected read-only tools remain."""
        from deep_agent_search import filter_tools_read_only, READ_ONLY_TOOLS
        
        class MockTool:
            def __init__(self, name):
                self.name = name
        
        all_tools = [
            MockTool("ls"),
            MockTool("read_file"),
            MockTool("grep"),
            MockTool("glob"),
            MockTool("write_file"),
            MockTool("edit_file"),
            MockTool("unknown_tool"),
        ]
        
        filtered = filter_tools_read_only(all_tools)
        filtered_names = {t.name for t in filtered}
        
        # Verify exactly the read-only tools are present
        assert filtered_names == READ_ONLY_TOOLS


class TestConstants:
    """Test module constants are correctly defined."""
    
    def test_read_only_tools_defined(self):
        """Verify READ_ONLY_TOOLS constant is defined correctly."""
        from deep_agent_search import READ_ONLY_TOOLS
        
        expected_tools = {"ls", "read_file", "grep", "glob"}
        assert READ_ONLY_TOOLS == expected_tools
    
    def test_virtual_root_defined(self):
        """Verify VIRTUAL_ROOT constant is defined."""
        from deep_agent_search import VIRTUAL_ROOT
        
        assert VIRTUAL_ROOT == "/docs"
    
    def test_docs_dirs_defined(self):
        """Verify DOCS_DIRS constant is defined."""
        from deep_agent_search import DOCS_DIRS
        
        assert "deepagents" in DOCS_DIRS
        assert "langgraph" in DOCS_DIRS
    
    def test_system_prompt_includes_citations(self):
        """Verify system prompt mentions citations."""
        from deep_agent_search import SEARCH_SYSTEM_PROMPT
        
        assert "citation" in SEARCH_SYSTEM_PROMPT.lower()


class TestVirtualPathMapping:
    """Test the virtual path mapping logic."""
    
    def test_deepagents_path_mapping(self):
        """Verify deepagents files map to /docs/deepagents/."""
        from deep_agent_search import load_documentation_files
        
        files = load_documentation_files()
        
        deepagent_files = [p for p in files if "/deepagents/" in p]
        for path in deepagent_files:
            assert path.startswith("/docs/deepagents/")
    
    def test_langgraph_path_mapping(self):
        """Verify langgraph files map to /docs/langgraph/."""
        from deep_agent_search import load_documentation_files
        
        files = load_documentation_files()
        
        langgraph_files = [p for p in files if "/langgraph/" in p]
        for path in langgraph_files:
            assert path.startswith("/docs/langgraph/")


# Integration tests (require actual deepagents library)
class TestIntegration:
    """Integration tests that require the full environment."""
    
    @pytest.mark.skip(reason="Requires GitHub Copilot token and full environment")
    def test_search_returns_answer(self):
        """Integration test: search returns an answer."""
        from deep_agent_search import search
        
        answer = search("What is DeepAgents?")
        
        assert answer is not None
        assert len(answer) > 0
    
    @pytest.mark.skip(reason="Requires GitHub Copilot token and full environment")
    def test_search_includes_citation(self):
        """Integration test: search includes citations."""
        from deep_agent_search import search
        
        answer = search("What is DeepAgents?")
        
        # Should contain a citation in brackets
        assert "[" in answer and "]" in answer
