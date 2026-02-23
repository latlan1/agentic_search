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

| Approach | Script | Technology | Use Case |
|----------|--------|------------|----------|
| **Approach 1** | `deep_agent_search.py` | DeepAgents + Virtual FS | Dynamic corpus, no index |
| **Approach 2** | `tantivy_search.py` | Tantivy CLI | Direct search, no LLM |
| **Approach 3** | `tantivy_agent_search.py` | LangGraph + Tantivy | Production, ranked + LLM |

All approaches use **Anthropic Claude Sonnet 4** as the LLM engine for formulating final responses with citations.

---

## Environment Configuration

Create a `.env` file in the project root with the following:

```bash
# Required for Approaches 1 and 3
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
├── scripts/
│   ├── deep_agent_search.py         # Approach 1: DeepAgent implementation
│   ├── tantivy_search.py            # Approach 2: Tantivy CLI
│   ├── tantivy_agent_search.py      # Approach 3: LangGraph + Tantivy agent
│   ├── tantivy_index_manager.py     # Index management utilities
│   └── trace_viewer.py              # Execution trace viewer
├── tests/
│   ├── deep_agent_search/       # Tests for DeepAgent script
│   ├── deepagents_cli/          # Tests for DeepAgents CLI config
│   ├── tantivy_search/          # Tests for Tantivy CLI (search + index manager)
│   └── tantivy_agent_search/    # Tests for Tantivy Agent
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

## Approach 2: Tantivy Search (CLI)

### Concept

Direct BM25 full-text search using Tantivy. No LLM required - returns raw search results with RRF fusion for multiple queries.

### Key Features

- Fast BM25 search with Tantivy
- Reciprocal Rank Fusion for multi-query search
- Two-phase API: search() for previews, read() for full content
- No LLM required

### Usage

```bash
# Build the index (run once, or after adding documents)
uv run scripts/tantivy_index_manager.py build

# Search with single query
uv run scripts/tantivy_search.py search "subagents"

# Search with multiple queries (RRF fusion)
uv run scripts/tantivy_search.py search "memory" "persistence" "state"

# Read specific documents by ID
uv run scripts/tantivy_search.py read 0 3 5
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

Approaches 2 and 3 support multiple queries that are fused using RRF:

```
RRF_score(doc) = Σ 1/(k + rank_i)
```

Where `k=60` is a constant and `rank_i` is the document's rank in query i.

### Two-Phase Search

Approaches 2 and 3 implement a two-phase search pattern:
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
| Index required | No | Yes | Yes |
| LLM required | Yes | No | Yes |
| Ranked results | No | Yes (BM25) | Yes (BM25+RRF) |
| Multi-query fusion | No | Yes | Yes |
| Numbered citations | Yes | N/A | Yes |
| Interactive mode | Yes | No | Yes |
| Setup complexity | Low | Medium | Medium |
| Best for | Dynamic docs | CLI search | Production |
