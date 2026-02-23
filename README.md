# Agentic Search for Deep Markdown

Three approaches to agentic search over Markdown documentation corpora, inspired by Benjamin Anderson's article: [Agentic Search for Dummies](https://benanderson.work/blog/agentic-search-for-dummies/).

## Overview

This project implements three distinct approaches to documentation search using AI agents:

| Approach | Script | Technology | Use Case |
|----------|--------|------------|----------|
| **1. DeepAgent** | `deep_agent_search.py` | DeepAgents + Virtual FS | Dynamic corpus, no index needed |
| **2. Tantivy Search** | `tantivy_search.py` | Tantivy CLI | Direct search, no LLM required |
| **3. Tantivy Agent** | `tantivy_agent_search.py` | LangGraph + Tantivy | Production, ranked results with LLM |

All approaches search over the same documentation corpus:
- **DeepAgents docs** (12 files) - `data/deepagents_raw_md/`
- **LangGraph docs** (29 files) - `data/langgraph_raw_md/`

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd agentic_search

# Install dependencies with uv
uv sync
```

## Environment Setup

Create a `.env` file in the project root:

```bash
# Required for Approach 1 and 3
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional: Override default model
ANTHROPIC_MODEL=claude-sonnet-4-20250514
```

## Approach 1: DeepAgent with Virtual Filesystem

Uses the DeepAgents library to create an agent with built-in file system tools (`ls`, `grep`, `glob`, `read_file`). Documents are loaded into a virtual filesystem - no index building required.

**Best for**: Small, frequently changing corpora

```bash
# Single query
uv run scripts/deep_agent_search.py "How do I create a subagent?"

# Interactive mode (multi-turn conversation)
uv run scripts/deep_agent_search.py --interactive

# Verbose mode (see tool calls)
uv run scripts/deep_agent_search.py --verbose "What is context quarantine?"
```

## Approach 2: Tantivy Search (CLI)

Direct BM25 full-text search using Tantivy. No LLM required - returns raw search results.

**Best for**: Quick searches, debugging, building indexes

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

## Approach 3: LangGraph + Tantivy Agent

A LangGraph-based agent with `search_docs` and `read_docs` tools backed by Tantivy. Provides ranked BM25 results with Reciprocal Rank Fusion (RRF) and LLM-generated answers with numbered citations.

**Best for**: Production use, complex queries, multi-turn conversations

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

## Directory Structure

```
agentic_search/
├── data/
│   ├── deepagents_raw_md/       # DeepAgents documentation (12 files)
│   └── langgraph_raw_md/        # LangGraph documentation (29 files)
├── augmented_jsonl_index/       # LLM-generated keywords/descriptions
├── tantivy_index/               # Tantivy full-text index (generated)
├── scripts/
│   ├── deep_agent_search.py     # Approach 1: DeepAgent
│   ├── tantivy_search.py        # Approach 2: Tantivy CLI
│   ├── tantivy_agent_search.py  # Approach 3: LangGraph Agent
│   ├── tantivy_index_manager.py # Index management utilities
│   └── trace_viewer.py          # Execution trace viewer
├── tests/
│   ├── deep_agent_search/       # Tests for DeepAgent script
│   ├── deepagents_cli/          # Tests for DeepAgents CLI config
│   ├── tantivy_search/          # Tests for Tantivy CLI (search + index manager)
│   └── tantivy_agent_search/    # Tests for Tantivy Agent
├── prepare/                     # Planning documents and research
├── AGENTS.md                    # Agent instructions for AI assistants
├── DEEP_AGENT_SEARCH_CHEATSHEET.md
├── DEEPAGENTS_CLI_CHEATSHEET.md
├── TANTIVY_CHEATSHEET.md
└── pyproject.toml
```

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

## Key Concepts

### Reciprocal Rank Fusion (RRF)

Approaches 2 and 3 support multiple queries that are fused using RRF:

```
RRF_score(doc) = Σ 1/(k + rank_i)
```

This allows "spray and pray" searching with multiple query variations for better recall.

### Two-Phase Search

Approach 3 implements a two-phase search pattern:
1. **search_docs()** - Returns previews (doc_id, filename, description, score)
2. **read_docs()** - Returns full content for selected documents

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

## Comparison

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

## License

MIT
