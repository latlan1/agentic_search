# Deep Agent Search Implementation Plan

## Overview for Approach 1

This document outlines a detailed implementation plan for **deep_agent_search**, a new feature that implements agentic search using the DeepAgents library with file system tools operating on a virtual filesystem containing the markdown documentation corpus.

### Goals

1. Create a search agent using `deepagents.create_deep_agent()` that can search documentation files
2. Use the virtual filesystem (`StateBackend`) to expose markdown files without allowing modifications to the original files in `data/`
3. Provide the standard DeepAgents built-in tools (`ls`, `read_file`, `grep`, `glob`) for the agent to search documentation - these are the same tools typically available to deep agents, not custom/bespoke tools
4. Generate answers with citations from the documentation corpus
5. Support both DeepAgents and LangGraph documentation (41 total files)
6. Enable multi-turn conversation memory for follow-up questions

### Key Constraint

> **CRITICAL**: The agent must NOT have `write_file` or `edit_file` tools enabled. The `data/` folder contains the source documentation and must remain read-only.

---

## Architecture

```
                              User Query
                                  |
                                  v
                    +---------------------------+
                    |   deep_agent_search.py    |
                    |                           |
                    |  create_deep_agent(       |
                    |    backend=StateBackend,  |
                    |    tools=[filtered],      |
                    |    checkpointer=...,      |
                    |    system_prompt=...      |
                    |  )                        |
                    +---------------------------+
                                  |
                                  v
                    +---------------------------+
                    |     StateBackend          |
                    |  (Virtual Filesystem)     |
                    |                           |
                    |  /docs/deepagents/        |
                    |    - overview.md          |
                    |    - quickstart.md        |
                    |    - ...                  |
                    |  /docs/langgraph/         |
                    |    - overview.md          |
                    |    - quickstart.md        |
                    |    - ...                  |
                    +---------------------------+
                                  |
                                  v
                    +---------------------------+
                    |   Agent Tool Calls        |
                    |   (Built-in Tools)        |
                    |                           |
                    |  ls("/docs/")             |
                    |  glob("**/*.md")          |
                    |  grep("subagent", ...)    |
                    |  read_file("/docs/...")   |
                    +---------------------------+
                                  |
                                  v
                    +---------------------------+
                    |   GitHub Models API       |
                    |   (GPT-4o via ChatOpenAI) |
                    |   - Synthesize answer     |
                    |   - Include citations     |
                    +---------------------------+
                                  |
                                  v
                              Answer with
                              Citations
```

---

## Implementation Details

### 1. File Structure

```
scripts/
  deep_agent_search.py      # Main implementation (Approach 1)

data/
  deepagents_raw_md/        # 12 markdown files (READ-ONLY)
  langgraph_raw_md/         # 29 markdown files (READ-ONLY)
```

### 2. Core Implementation: `scripts/deep_agent_search.py`

```python
#!/usr/bin/env python3
"""
Deep Agent Search - Agentic search over documentation using DeepAgents.

This implementation uses DeepAgents' built-in file system tools (ls, read_file, 
grep, glob) with a StateBackend to create a virtual filesystem containing the 
markdown documentation. The agent can search and read files but cannot modify them.

Key Features:
- Read-only access to documentation (write_file and edit_file filtered out)
- Virtual filesystem via StateBackend
- Multi-query search using grep and glob
- Answers with citations
- Multi-turn conversation memory via checkpointer
- GPT-5 via GitHub Copilot as the LLM
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

from deepagents import create_deep_agent
from deepagents.backends import StateBackend
from deepagents.middleware.filesystem import FilesystemMiddleware
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()

# Paths to documentation
DOCS_DIRS = {
    "deepagents": Path("data/deepagents_raw_md"),
    "langgraph": Path("data/langgraph_raw_md"),
}

# Virtual filesystem paths
VIRTUAL_ROOT = "/docs"

# Read-only tools - filter out write_file and edit_file
READ_ONLY_TOOLS = {"ls", "read_file", "grep", "glob"}


def load_documentation_files() -> dict[str, str]:
    """
    Load all markdown files from documentation directories into a dictionary
    suitable for seeding the StateBackend.
    
    Returns:
        Dictionary mapping virtual paths to file contents.
        Example: {"/docs/deepagents/overview.md": "# Overview\n..."}
    """
    files = {}
    
    for corpus_name, docs_dir in DOCS_DIRS.items():
        if not docs_dir.exists():
            print(f"Warning: {docs_dir} does not exist, skipping")
            continue
        
        for md_file in sorted(docs_dir.glob("*.md")):
            # Create virtual path: /docs/deepagents/deepagents-overview.md
            virtual_path = f"{VIRTUAL_ROOT}/{corpus_name}/{md_file.name}"
            content = md_file.read_text(encoding="utf-8", errors="ignore")
            files[virtual_path] = content
    
    return files


# System prompt for the search agent
SEARCH_SYSTEM_PROMPT = """You are an expert documentation search agent. Your job is to answer questions about the DeepAgents and LangGraph documentation.

## Available Documentation

You have access to a virtual filesystem containing markdown documentation:
- `/docs/deepagents/` - DeepAgents library documentation (12 files)
- `/docs/langgraph/` - LangGraph framework documentation (29 files)

## Available Tools

You have access to these READ-ONLY file system tools:
- `ls(path)` - List files in a directory
- `read_file(file_path)` - Read the contents of a file
- `grep(pattern, path)` - Search for a regex pattern in files
- `glob(pattern, path)` - Find files matching a glob pattern

## Search Strategy

1. **Start broad**: Use `ls("/docs/")` to see available documentation sections
2. **Find relevant files**: Use `grep` to search for keywords across files, or `glob` to find files by name pattern
3. **Read promising files**: Use `read_file` to read the full content of relevant documents
4. **Synthesize answer**: Combine information from multiple sources if needed

## Response Format

ALWAYS include citations in your response:
- Reference specific files: [deepagents-subagents.md]
- Quote relevant passages when helpful
- If information is not found, say so clearly

## Example Workflow

For a question like "How do I create a subagent?":

1. `grep("subagent", "/docs/")` to find files mentioning subagents
2. `read_file("/docs/deepagents/deepagents-subagents.md")` to get full content
3. Synthesize the answer with citations

## Important Guidelines

- Search multiple files if needed for a complete answer
- Prefer specific, actionable information over general summaries
- Include code examples when they help explain concepts
- Always cite the source file for information you provide
"""


# Global checkpointer for multi-turn conversations
checkpointer = MemorySaver()


def filter_tools_read_only(tools: list) -> list:
    """
    Filter the standard FilesystemMiddleware tools to only include read-only operations.
    This removes write_file and edit_file from the available tools.
    
    Args:
        tools: List of tools from FilesystemMiddleware
        
    Returns:
        Filtered list containing only read-only tools (ls, read_file, grep, glob)
    """
    return [t for t in tools if t.name in READ_ONLY_TOOLS]


def create_search_agent(files: dict[str, str]):
    """
    Create a DeepAgent configured for read-only documentation search.
    
    Uses GPT-5 via GitHub Copilot as the LLM and filters out write tools
    from the standard FilesystemMiddleware.
    
    Args:
        files: Dictionary of virtual paths to file contents
        
    Returns:
        Configured DeepAgent with read-only file system tools
    """
    # Use GPT-5 via GitHub Copilot
    model = "github-copilot:gpt-5"
    
    # Create the agent with checkpointer for multi-turn conversations
    # The FilesystemMiddleware provides built-in tools, which we filter
    agent = create_deep_agent(
        model=model,
        system_prompt=SEARCH_SYSTEM_PROMPT,
        checkpointer=checkpointer,
        # Tools will be filtered after agent creation
    )
    
    # Filter out write tools from the agent's available tools
    # This uses the standard built-in tools, just filtered
    if hasattr(agent, 'tools'):
        agent.tools = filter_tools_read_only(agent.tools)
    
    return agent, files


def search(query: str, thread_id: str = "default") -> str:
    """
    Search the documentation corpus and return an answer with citations.
    
    Supports multi-turn conversations via thread_id for follow-up questions.
    
    Args:
        query: The user's question
        thread_id: Conversation thread ID for multi-turn memory (default: "default")
        
    Returns:
        Answer with citations from the documentation
    """
    # Load documentation into virtual filesystem
    files = load_documentation_files()
    
    if not files:
        return "Error: No documentation files found. Please check the data/ directory."
    
    print(f"Loaded {len(files)} documentation files into virtual filesystem")
    
    # Create the agent
    agent, files = create_search_agent(files)
    
    # Invoke with the documentation files seeded into state
    # Use thread_id for conversation continuity
    result = agent.invoke(
        {
            "messages": [{"role": "user", "content": query}],
            "files": files,  # Seed the StateBackend with documentation
        },
        config={"configurable": {"thread_id": thread_id}}
    )
    
    # Extract the final response
    return result["messages"][-1].content


def interactive_session():
    """
    Run an interactive multi-turn conversation session.
    Allows follow-up questions with conversation memory.
    """
    import uuid
    
    thread_id = str(uuid.uuid4())
    print("Deep Agent Search - Interactive Mode")
    print("=" * 60)
    print(f"Session ID: {thread_id}")
    print("Type 'quit' or 'exit' to end the session.")
    print("=" * 60)
    print()
    
    while True:
        try:
            query = input("You: ").strip()
            if not query:
                continue
            if query.lower() in ("quit", "exit"):
                print("Goodbye!")
                break
            
            print()
            answer = search(query, thread_id=thread_id)
            print(f"Agent: {answer}")
            print()
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: uv run scripts/deep_agent_search.py '<query>'")
        print("       uv run scripts/deep_agent_search.py --interactive")
        print()
        print("Examples:")
        print("  uv run scripts/deep_agent_search.py 'How do I create a subagent?'")
        print("  uv run scripts/deep_agent_search.py 'What is context quarantine?'")
        print("  uv run scripts/deep_agent_search.py --interactive")
        sys.exit(1)
    
    # Check for interactive mode
    if sys.argv[1] == "--interactive":
        interactive_session()
        return
    
    query = " ".join(sys.argv[1:])
    print(f"Searching for: {query}\n")
    print("-" * 60)
    
    answer = search(query)
    print(answer)


if __name__ == "__main__":
    main()
```

### 3. Read-Only Tool Configuration (Tool Filtering)

The implementation uses the standard built-in tools from `FilesystemMiddleware` and filters them to exclude write operations. This ensures we use the same tools typically available to deep agents, not custom/bespoke tools.

```python
from deepagents.middleware.filesystem import FilesystemMiddleware

# Define which tools are read-only
READ_ONLY_TOOLS = {"ls", "read_file", "grep", "glob"}

def filter_tools_read_only(tools: list) -> list:
    """
    Filter the standard FilesystemMiddleware tools to only include read-only operations.
    This removes write_file and edit_file from the available tools.
    """
    return [t for t in tools if t.name in READ_ONLY_TOOLS]

# After creating the agent, filter its tools
agent = create_deep_agent(...)
agent.tools = filter_tools_read_only(agent.tools)
```

**Why Tool Filtering?**
- Uses the exact same built-in tools that DeepAgents provides
- No custom tool implementations needed
- Simple and maintainable
- Guaranteed compatibility with DeepAgents updates

### 4. Multi-Turn Conversation Memory

Multi-turn conversation support is a core feature, enabling follow-up questions:

```python
from langgraph.checkpoint.memory import MemorySaver

# Global checkpointer for conversation persistence
checkpointer = MemorySaver()

def create_search_agent(files: dict[str, str]):
    agent = create_deep_agent(
        model="github-copilot:gpt-5",
        system_prompt=SEARCH_SYSTEM_PROMPT,
        checkpointer=checkpointer,  # Enable conversation memory
    )
    return agent, files

def search(query: str, thread_id: str = "default") -> str:
    agent, files = create_search_agent(files)
    
    # Use consistent thread_id for conversation continuity
    result = agent.invoke(
        {"messages": [{"role": "user", "content": query}], "files": files},
        config={"configurable": {"thread_id": thread_id}}
    )
    
    return result["messages"][-1].content
```

**Interactive Mode:**

```bash
$ uv run scripts/deep_agent_search.py --interactive

Deep Agent Search - Interactive Mode
============================================================
Session ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890
Type 'quit' or 'exit' to end the session.
============================================================

You: How do I create a subagent?
Agent: Based on [deepagents-subagents.md], you can create subagents using...

You: What about using a custom LangGraph workflow?
Agent: Following up on subagents, you can use CompiledSubAgent for custom workflows...

You: quit
Goodbye!
```

### 5. StateBackend File Seeding

The `StateBackend` stores files in the agent's state. We seed it with documentation files at invocation time:

```python
def search(query: str, thread_id: str = "default") -> str:
    # Load all markdown files
    files = load_documentation_files()
    
    # Create agent with checkpointer
    agent = create_deep_agent(
        model="github-copilot:gpt-5",
        checkpointer=checkpointer,
        ...
    )
    
    # Invoke with files seeded into state and thread_id for memory
    result = agent.invoke(
        {
            "messages": [{"role": "user", "content": query}],
            "files": files,  # This populates the StateBackend
        },
        config={"configurable": {"thread_id": thread_id}}
    )
    
    return result["messages"][-1].content
```

### 6. Virtual Path Mapping

Map real file paths to virtual paths for clean agent interaction:

| Real Path | Virtual Path |
|-----------|--------------|
| `data/deepagents_raw_md/deepagents-overview.md` | `/docs/deepagents/deepagents-overview.md` |
| `data/deepagents_raw_md/deepagents-subagents.md` | `/docs/deepagents/deepagents-subagents.md` |
| `data/langgraph_raw_md/langgraph-overview.md` | `/docs/langgraph/langgraph-overview.md` |
| ... | ... |

---

## Dependencies

Add to `pyproject.toml`:

```toml
[project]
dependencies = [
    "deepagents>=0.3.8",
    "python-dotenv>=1.0.0",
    "langchain>=0.3.0",
    "langgraph>=0.2.0",
]
```

Install:

```bash
uv add python-dotenv langchain langgraph
```

---

## Environment Configuration

Create `.env.example`:

```bash
# LLM Configuration - GPT-5 via GitHub Copilot
GITHUB_TOKEN=your_github_copilot_token_here

# Note: The model is hardcoded to github-copilot:gpt-5 in the implementation
# No need to set LLM_PROVIDER or LLM_MODEL environment variables
```

---

## Usage Examples

### Single Query Mode

```bash
# Search for information about subagents
uv run scripts/deep_agent_search.py "How do I create a subagent in DeepAgents?"

# Ask about LangGraph concepts
uv run scripts/deep_agent_search.py "What is the difference between Graph API and Functional API in LangGraph?"

# Cross-reference documentation
uv run scripts/deep_agent_search.py "How do DeepAgents and LangGraph handle state persistence?"
```

### Interactive Mode (Multi-Turn Conversations)

```bash
# Start an interactive session with conversation memory
uv run scripts/deep_agent_search.py --interactive
```

### Expected Output

```
Searching for: How do I create a subagent in DeepAgents?

------------------------------------------------------------
Loaded 41 documentation files into virtual filesystem

## Creating Subagents in DeepAgents

Based on the documentation in [deepagents-subagents.md], you can create subagents using two methods:

### Method 1: Dictionary Configuration

```python
research_subagent = {
    "name": "research-agent",
    "description": "Used to research more in depth questions",
    "system_prompt": "You are a great researcher",
    "tools": [internet_search],
    "model": "github-copilot:gpt-5",  # Optional: override model
}

agent = create_deep_agent(
    model="github-copilot:gpt-5",
    subagents=[research_subagent]
)
```

### Method 2: CompiledSubAgent

For custom LangGraph workflows, use `CompiledSubAgent`:

```python
from deepagents import CompiledSubAgent

custom_subagent = CompiledSubAgent(
    name="data-analyzer",
    description="Specialized agent for complex data analysis",
    runnable=custom_langgraph_workflow
)

agent = create_deep_agent(subagents=[custom_subagent])
```

**Key Points** [deepagents-subagents.md]:
- Subagents provide "context quarantine" to isolate multi-step tasks
- Each subagent has its own context window
- Use the `task` tool to delegate work to subagents
- Subagents should return concise results to avoid context bloat
```

---

## Testing Plan

### Unit Tests

Create `tests/test_deep_agent_search.py`:

```python
import pytest
from pathlib import Path

# Test file loading
def test_load_documentation_files():
    from scripts.deep_agent_search import load_documentation_files
    
    files = load_documentation_files()
    
    # Should load all markdown files
    assert len(files) > 0
    
    # Check virtual paths are correct
    for path in files.keys():
        assert path.startswith("/docs/")
        assert path.endswith(".md")
    
    # Check both corpora are loaded
    deepagent_files = [p for p in files if "/deepagents/" in p]
    langgraph_files = [p for p in files if "/langgraph/" in p]
    
    assert len(deepagent_files) > 0
    assert len(langgraph_files) > 0


# Test tool filtering
def test_filter_tools_read_only():
    from scripts.deep_agent_search import filter_tools_read_only, READ_ONLY_TOOLS
    
    # Mock tools with names
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
    
    # Verify write tools are NOT present
    assert "write_file" not in filtered_names
    assert "edit_file" not in filtered_names
    
    # Verify read tools ARE present
    assert "ls" in filtered_names
    assert "read_file" in filtered_names
    assert "grep" in filtered_names
    assert "glob" in filtered_names


# Test that write tools are not available
def test_no_write_tools():
    from scripts.deep_agent_search import create_search_agent, load_documentation_files
    
    files = load_documentation_files()
    agent, _ = create_search_agent(files)
    
    # Get available tool names
    tool_names = [t.name for t in agent.tools]
    
    # Verify write tools are NOT present
    assert "write_file" not in tool_names
    assert "edit_file" not in tool_names
    
    # Verify read tools ARE present
    assert "ls" in tool_names
    assert "read_file" in tool_names


# Integration test
def test_search_returns_answer():
    from scripts.deep_agent_search import search
    
    answer = search("What is DeepAgents?")
    
    assert answer is not None
    assert len(answer) > 0
    # Should contain a citation
    assert "[" in answer and "]" in answer
```

### Manual Testing Checklist

- [ ] Agent can list documentation directories
- [ ] Agent can search with grep
- [ ] Agent can read file contents
- [ ] Agent cannot write or edit files (tools not available)
- [ ] Citations are included in responses
- [ ] Both DeepAgents and LangGraph docs are accessible
- [ ] Multi-turn conversations work in interactive mode
- [ ] Follow-up questions use conversation context

---

## Security Considerations

### Read-Only Enforcement

1. **StateBackend Isolation**: The `StateBackend` creates a virtual filesystem in memory. Even if write tools were available, they would only modify the in-memory state, not the actual files on disk.

2. **Tool Filtering**: By filtering out `write_file` and `edit_file` tools using the standard DeepAgents tools, the agent has no mechanism to attempt writes.

3. **Path Validation**: Virtual paths (`/docs/...`) cannot escape to the real filesystem when using `StateBackend`.

---

## Future Enhancements

### 1. Caching

Cache loaded documentation to avoid re-reading files on every query:

```python
from functools import lru_cache

@lru_cache(maxsize=1)
def load_documentation_files() -> tuple[tuple[str, str], ...]:
    # Return as tuple for hashability
    files = {}
    # ... load files ...
    return tuple(files.items())
```

### 2. Search Result Ranking

Add relevance scoring to grep results:

```python
def ranked_grep(pattern: str, path: str) -> list[dict]:
    matches = backend.grep_raw(pattern, path=path)
    
    # Score by frequency and position
    scored = []
    for match in matches:
        score = compute_relevance(match, pattern)
        scored.append({"match": match, "score": score})
    
    return sorted(scored, key=lambda x: x["score"], reverse=True)
```

### 3. Persistent Conversation History

Use a persistent store instead of MemorySaver for cross-session memory:

```python
from langgraph.checkpoint.postgres import PostgresSaver

# For production, use PostgreSQL
checkpointer = PostgresSaver(connection_string="postgresql://...")
```

---

## Implementation Checklist

- [ ] Create `scripts/deep_agent_search.py`
- [ ] Implement `load_documentation_files()` function
- [ ] Implement `filter_tools_read_only()` for tool filtering
- [ ] Create `create_search_agent()` with GPT-5 via GitHub Copilot
- [ ] Implement `search()` function with StateBackend seeding and thread_id
- [ ] Implement `interactive_session()` for multi-turn conversations
- [ ] Add CLI interface with `--interactive` flag
- [ ] Create `.env.example` with GitHub Copilot configuration
- [ ] Update `pyproject.toml` with dependencies
- [ ] Write unit tests in `tests/test_deep_agent_search.py`
- [ ] Test with sample queries
- [ ] Verify write tools are not accessible
- [ ] Test multi-turn conversations

---

## Summary

The **deep_agent_search** feature provides a safe, read-only way to search documentation using the DeepAgents library. By:

1. Using `StateBackend` to create an isolated virtual filesystem
2. Filtering out `write_file` and `edit_file` from standard built-in tools
3. Seeding the state with documentation content at runtime
4. Using GPT-5 via GitHub Copilot as the LLM
5. Enabling multi-turn conversation memory with `MemorySaver`
6. Providing clear system prompts with citation requirements

The implementation ensures that:
- Original documentation files in `data/` are never modified
- The agent has rich search capabilities using standard DeepAgents tools (ls, read_file, grep, glob)
- Responses include proper citations to source documents
- Follow-up questions are supported through conversation memory
- The system uses GPT-5 for high-quality responses

---

## Appendix A: DeepAgents API Reference

### create_deep_agent()

```python
agent = create_deep_agent(
    model="github-copilot:gpt-5",     # GPT-5 via GitHub Copilot
    system_prompt="...",              # Custom instructions
    tools=[...],                      # Additional tools (beyond built-ins)
    backend=StateBackend,             # Storage backend (default)
    subagents=[...],                  # Subagent configurations
    skills=["./skills/"],             # Skill directories
    checkpointer=MemorySaver(),       # For persistence and multi-turn memory
    interrupt_on={"tool": True},      # Human-in-the-loop
)
```

### Built-in File System Tools

| Tool | Description | Read-Only | Included |
|------|-------------|-----------|----------|
| `ls` | List directory contents | Yes | Yes |
| `read_file` | Read file contents | Yes | Yes |
| `glob` | Find files by pattern | Yes | Yes |
| `grep` | Search file contents | Yes | Yes |
| `write_file` | Create new files | **No** | **Filtered Out** |
| `edit_file` | Modify existing files | **No** | **Filtered Out** |

### StateBackend

- Stores files in agent state (memory)
- Persists within thread via checkpoints
- Shared between supervisor and subagents
- Files seeded via `invoke({"files": {...}})`

---

## Appendix B: Sample Queries for Testing

```bash
# DeepAgents queries
uv run scripts/deep_agent_search.py "What is context quarantine and why is it useful?"
uv run scripts/deep_agent_search.py "How do I configure human-in-the-loop for edit operations?"
uv run scripts/deep_agent_search.py "What backends are available for file storage?"

# LangGraph queries
uv run scripts/deep_agent_search.py "How do I create a StateGraph with conditional edges?"
uv run scripts/deep_agent_search.py "What is the difference between workflows and agents?"
uv run scripts/deep_agent_search.py "How do I add persistence to a LangGraph agent?"

# Cross-corpus queries
uv run scripts/deep_agent_search.py "Compare subagents in DeepAgents with subgraphs in LangGraph"
uv run scripts/deep_agent_search.py "How do both frameworks handle streaming?"

# Interactive mode for multi-turn conversations
uv run scripts/deep_agent_search.py --interactive
```
