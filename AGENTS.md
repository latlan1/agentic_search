# Agentic Search for Deep Markdown

This document provides instructions for AI assistants working with this codebase. It implements three distinct approaches for agentic search over Markdown documentation corpora, inspired by Benjamin Anderson's article: https://benanderson.work/blog/agentic-search-for-dummies/

---

## Principles

### Use `uv` for all Python execution

All Python scripts in this project should be run using `uv` instead of `python` directly:

```bash
# Correct - use uv
uv run scripts/tantivy_index_manager.py build
uv run scripts/tantivy_search.py search "query"
uv run scripts/deep_agent_search.py "query"

# Incorrect - do not use python directly
python scripts/deep_agent_search.py  # Don't do this
```

This ensures consistent dependency management and reproducible environments.

---

## Overview

This project implements **three separate, distinct approaches** to agentic search:

| Approach | Script / Config | Technology | Use Case |
|----------|-----------------|------------|----------|
| **Approach 1** | `deep_agent_search.py` | DeepAgents + Virtual FS | Dynamic corpus, no index |
| **Approach 2** | `.deepagents/` | DeepAgents CLI | Interactive sessions, real-time discovery |
| **Approach 3** | `tantivy_agent_search.py` | LangGraph + Tantivy | Production, ranked + LLM |

All approaches use **Anthropic Claude Sonnet 4** as the LLM engine for formulating final responses with citations.

---

## Environment Configuration

Create a `.env` file in the project root with the following:

```bash
# Required for all approaches
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional: Override default model
ANTHROPIC_MODEL=claude-sonnet-4-20250514
```

---

## Folder Layout

```
agentic_search/
├── data/
│   ├── deepagents_raw_md/           # DeepAgents docs (12 files)
│   └── langgraph_raw_md/            # LangGraph docs (29 files)
├── augmented_jsonl_index/           # LLM-generated keywords/descriptions
│   ├── deepagents_index.jsonl
│   └── langgraph_index.jsonl
├── tantivy_index/                   # Tantivy full-text index (generated)
├── .deepagents/                     # Approach 2: DeepAgents CLI configuration
│   ├── AGENTS.md                    # Project context
│   └── skills/doc-search/           # Search skill
├── scripts/
│   ├── deep_agent_search.py         # Approach 1: DeepAgent implementation
│   ├── tantivy_agent_search.py      # Approach 3: LangGraph + Tantivy agent
│   ├── tantivy_index_manager.py     # Index management utilities (for Approach 3)
│   ├── tantivy_search.py            # Direct Tantivy CLI (utility)
│   └── trace_viewer.py              # Execution trace viewer
├── tests/
│   ├── deep_agent_search/       # Tests for Approach 1
│   ├── deepagents_cli/          # Tests for Approach 2
│   ├── tantivy_search/          # Tests for Tantivy utilities
│   └── tantivy_agent_search/    # Tests for Approach 3
├── prepare/                         # Planning documents and research
│   ├── deep_agent_search_plan.md
│   ├── tantivy_agent_search_plan.md
│   ├── deepagents_cli_plan.md
│   └── research.md
├── AGENTS.md                        # This file
├── DEEP_AGENT_SEARCH_CHEATSHEET.md
├── DEEPAGENTS_CLI_CHEATSHEET.md
├── TANTIVY_CHEATSHEET.md
├── README.md
└── pyproject.toml
```

---

## Approach 1: DeepAgent with Virtual Filesystem

### Concept

Uses the DeepAgents library to create an agent with built-in file system tools (`ls`, `read_file`, `grep`, `glob`). Documents are loaded into a virtual filesystem via StateBackend - no index building required.

### Key Features

- Read-only access (write_file and edit_file filtered out)
- Virtual filesystem via StateBackend
- Multi-turn conversation memory via checkpointer
- Rich markdown rendering in terminal
- Verbose mode to see tool calls

### Usage

```bash
# Single query
uv run scripts/deep_agent_search.py "How do I create a subagent?"

# Interactive mode
uv run scripts/deep_agent_search.py --interactive

# Verbose mode (see tool calls)
uv run scripts/deep_agent_search.py --verbose "What is context quarantine?"
```

---

## Approach 2: DeepAgents CLI

### Concept

Uses the `deepagents-cli` tool with project-specific configuration in `.deepagents/`. Provides an interactive multi-turn conversation interface with real-time file discovery - no index required.

### Key Features

- Interactive REPL with multi-turn conversations
- Session persistence across restarts
- Real-time file discovery (no index needed)
- Human-in-the-loop safety controls
- Project skills auto-loaded from `.deepagents/skills/`

### Usage

```bash
# Install DeepAgents CLI (one-time)
uv tool install deepagents-cli

# Start interactive session
deepagents

# Use a specific model
deepagents --model claude-sonnet-4-5-20250514

# Resume last session
deepagents -r
```

---

## Approach 3: LangGraph + Tantivy Agent

### Concept

A LangGraph-based agent with `search_docs` and `read_docs` tools backed by Tantivy. Provides ranked BM25 results with RRF fusion and LLM-generated answers with numbered citations.

### Key Features

- BM25 full-text search with RRF fusion
- Two-phase search: search (preview) -> read (full content)
- Multi-turn conversation memory
- Automatic index building/updating via IndexManager
- Graph visualization support

### Usage

```bash
# Single query
uv run scripts/tantivy_agent_search.py "How do I create a subagent?"

# Interactive mode
uv run scripts/tantivy_agent_search.py --interactive

# Sync index before searching
uv run scripts/tantivy_agent_search.py --sync "What is memory persistence?"

# Generate LangGraph visualization
uv run scripts/tantivy_agent_search.py --graph
```

---

## Running Tests

```bash
# Run all tests
uv run pytest

# Run tests for a specific component
uv run pytest tests/deep_agent_search/
uv run pytest tests/deepagents_cli/
uv run pytest tests/tantivy_search/
uv run pytest tests/tantivy_agent_search/

# Run with verbose output
uv run pytest -v
```

---

## Key Concepts

### Reciprocal Rank Fusion (RRF)

Approach 3 supports multiple queries that are fused using RRF:

```
RRF_score(doc) = Σ 1/(k + rank_i)
```

Where `k=60` is a constant and `rank_i` is the document's rank in query i.

### Two-Phase Search

Approach 3 implements a two-phase search pattern:
1. **search()** - Returns previews (doc_id, filename, description, score)
2. **read()** - Returns full content for selected documents

This prevents context window bloat when exploring search results.

### Numbered Citations

Both agent-based approaches (1 and 3) generate responses with numbered citations:

```
Subagents allow you to delegate tasks to specialized agents [1].
You can create them using the `Task` tool [2].

---
**Sources:**
[1] [deepagents-subagents.md](data/deepagents_raw_md/deepagents-subagents.md)
[2] [deepagents-context.md](data/deepagents_raw_md/deepagents-context.md)
```

---

## Comparison of Approaches

| Feature | Approach 1 | Approach 2 | Approach 3 |
|---------|------------|------------|------------|
| Technology | DeepAgents script | DeepAgents CLI | LangGraph + Tantivy |
| Index required | No | No | Yes |
| LLM required | Yes | Yes | Yes |
| Ranked results | No | No | Yes (BM25+RRF) |
| Multi-query fusion | No | No | Yes |
| Numbered citations | Yes | Yes | Yes |
| Interactive mode | Yes | Yes (built-in) | Yes |
| Session persistence | No | Yes | No |
| Setup complexity | Low | Low | Medium |
| Best for | Dynamic docs | Interactive sessions | Production |
