# Agentic Search for Deep Markdown

Three approaches to agentic search over Markdown documentation corpora, inspired by Benjamin Anderson's article: [Agentic Search for Dummies](https://benanderson.work/blog/agentic-search-for-dummies/).

## Overview

This project implements three distinct approaches to documentation search using AI agents:

| Approach | Script | Technology | Use Case |
|----------|--------|------------|----------|
| **1. DeepAgent** | `deep_agent_search.py` | DeepAgents + Virtual FS | Dynamic corpus, no index needed |
| **2. Tantivy Search** | `tantivy_search.py` | Tantivy CLI | Direct search, no LLM required |
| **3. Tantivy Agent** | `tantivy_agent_search.py` | LangGraph + Tantivy | Production, ranked results with LLM |

Additionally, a **DeepAgents CLI** configuration (`.deepagents/`) provides an alternative interactive interface.

All approaches search over the same documentation corpus:
- **DeepAgents docs** (12 files) - `data/deepagents_raw_md/`
- **LangGraph docs** (29 files) - `data/langgraph_raw_md/`

## Installation

```bash
# Clone the repository
git clone https://github.com/latlan1/agentic_search.git
cd agentic_search

# Install dependencies with uv
uv sync
```

## Environment Setup

Create a `.env` file in the project root:

```bash
# Required for Approaches 1 and 3
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional: Override default model (default: claude-sonnet-4-20250514)
ANTHROPIC_MODEL=claude-sonnet-4-20250514
```

---

## Approach 1: DeepAgent with Virtual Filesystem

Uses the DeepAgents library to create an agent with built-in file system tools (`ls`, `grep`, `glob`, `read_file`). Documents are loaded into a virtual filesystem via `StateBackend` - no index building required.

### Architecture

```
User Query
    │
    ▼
┌─────────────────────────┐
│  deep_agent_search.py   │
│  create_deep_agent()    │
│  - StateBackend         │
│  - Filtered tools       │
│  - MemorySaver          │
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│  Virtual Filesystem     │
│  /docs/deepagents/*.md  │
│  /docs/langgraph/*.md   │
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│  Anthropic Claude       │
│  (Sonnet 4)             │
└─────────────────────────┘
    │
    ▼
Answer with Citations
```

### Key Features

- **Read-only access**: `write_file` and `edit_file` tools are filtered out
- **Virtual filesystem**: Documents loaded via `StateBackend` (no disk writes)
- **Multi-turn memory**: Conversation persistence via `MemorySaver` checkpointer
- **No index required**: Files loaded fresh on each invocation

### Usage

```bash
# Single query
uv run scripts/deep_agent_search.py "How do I create a subagent?"

# Interactive mode (multi-turn conversation)
uv run scripts/deep_agent_search.py --interactive

# Verbose mode (see tool calls)
uv run scripts/deep_agent_search.py --verbose "What is context quarantine?"
```

**Best for**: Small, frequently changing corpora where index maintenance is not desired.

---

## Approach 2: Tantivy Search (CLI)

Direct BM25 full-text search using Tantivy. No LLM required - returns raw search results with Reciprocal Rank Fusion (RRF) for multiple queries.

### Architecture

```
┌─────────────────────────┐
│  tantivy_index_manager  │
│  - Build index          │
│  - Incremental updates  │
│  - File watcher         │
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Tantivy Index          │
│  tantivy_index/         │
│  - BM25 scoring         │
│  - Full-text search     │
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│  tantivy_search.py      │
│  - search(queries)      │
│  - read(doc_ids)        │
│  - RRF fusion           │
└─────────────────────────┘
```

### Key Features

- **Fast BM25 search**: Full-text search with Tantivy
- **RRF fusion**: Multiple queries fused with Reciprocal Rank Fusion
- **Two-phase API**: `search()` for previews, `read()` for full content
- **No LLM required**: Direct search results without AI processing
- **File watcher**: Auto-index new/modified files with `watchdog`

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

# Watch for file changes (auto-reindex)
uv run scripts/tantivy_index_manager.py watch

# Show index statistics
uv run scripts/tantivy_index_manager.py stats
```

**Best for**: Quick searches, debugging, building indexes, and when LLM is not needed.

---

## Approach 3: LangGraph + Tantivy Agent

A LangGraph-based agent with `search_docs` and `read_docs` tools backed by Tantivy. Provides ranked BM25 results with RRF and LLM-generated answers with numbered citations.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    tantivy_agent_search                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────┐    ┌──────────────────┐                 │
│  │  File Watcher  │───▶│  Index Manager   │                 │
│  │  (watchdog)    │    │  (incremental)   │                 │
│  └────────────────┘    └────────┬─────────┘                 │
│         │                       │                            │
│         │ monitors              ▼                            │
│         ▼              ┌──────────────────┐                 │
│  ┌────────────────┐    │  Tantivy Index   │                 │
│  │   data/        │    └────────┬─────────┘                 │
│  │  ├── deepagents_raw_md/      │                           │
│  │  └── langgraph_raw_md/       │ search/read               │
│  └────────────────┘             ▼                            │
│                        ┌──────────────────────┐             │
│                        │  LangGraph Agent     │             │
│                        │  ┌────────────────┐  │             │
│                        │  │  search_docs   │  │             │
│                        │  │  read_docs     │  │             │
│                        │  └────────────────┘  │             │
│                        │         │            │             │
│                        │         ▼            │             │
│                        │  ┌────────────────┐  │             │
│                        │  │ Anthropic LLM  │  │             │
│                        │  │  (Claude 4.5)  │  │             │
│                        │  └────────────────┘  │             │
│                        └──────────────────────┘             │
│                                 │                            │
│                                 ▼                            │
│                        ┌──────────────────────┐             │
│                        │  MemorySaver         │             │
│                        │  (multi-turn)        │             │
│                        └──────────────────────┘             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Key Features

- **BM25 + RRF**: Full-text search with multi-query fusion
- **Two-phase search**: Preview results, then read full content
- **Multi-turn memory**: Conversation persistence via `MemorySaver`
- **Auto-sync**: Optionally sync index before searching
- **Graph visualization**: Generate PNG of LangGraph workflow

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

**Best for**: Production use, complex queries, multi-turn conversations.

---

## DeepAgents CLI (Alternative)

A separate configuration using the `deepagents-cli` tool for interactive documentation search.

### Setup

```bash
# Install DeepAgents CLI as a global tool
uv tool install deepagents-cli

# Configure Anthropic API key
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Run the CLI
deepagents
```

### Features

- Built-in interactive multi-turn conversations
- Real-time file discovery (no index)
- Session persistence across restarts
- Human-in-the-loop for safety

See `DEEPAGENTS_CLI_CHEATSHEET.md` for detailed usage.

---

## Directory Structure

```
agentic_search/
├── data/
│   ├── deepagents_raw_md/       # DeepAgents documentation (12 files)
│   └── langgraph_raw_md/        # LangGraph documentation (29 files)
├── augmented_jsonl_index/       # LLM-generated keywords/descriptions
├── tantivy_index/               # Tantivy full-text index (generated)
├── .deepagents/                 # DeepAgents CLI configuration
│   ├── AGENTS.md                # Project context
│   └── skills/doc-search/       # Search skill
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
│   ├── deep_agent_search_plan.md
│   ├── deepagents_cli_plan.md
│   ├── tantivy_agent_search_plan.md
│   └── research.md
├── AGENTS.md                    # Agent instructions for AI assistants
├── DEEP_AGENT_SEARCH_CHEATSHEET.md
├── DEEPAGENTS_CLI_CHEATSHEET.md
├── TANTIVY_CHEATSHEET.md
└── pyproject.toml
```

---

## Running Tests

```bash
# Run all tests (99 passing, 12 skipped)
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

Where `k=60` is a constant and `rank_i` is the document's rank in query i. This allows "spray and pray" searching with multiple query variations for better recall.

### Two-Phase Search

Approaches 2 and 3 implement a two-phase search pattern:
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

---

## Comparison

| Feature | Approach 1 | Approach 2 | Approach 3 |
|---------|------------|------------|------------|
| Index required | No | Yes | Yes |
| LLM required | Yes | No | Yes |
| Ranked results | No | Yes (BM25) | Yes (BM25+RRF) |
| Multi-query fusion | No | Yes | Yes |
| Numbered citations | Yes | N/A | Yes |
| Interactive mode | Yes | No | Yes |
| File watching | No | Yes | Yes |
| Setup complexity | Low | Medium | Medium |
| Best for | Dynamic docs | CLI search | Production |

---

## Planning Documents

Detailed implementation plans for each approach are in `prepare/`:

- `prepare/deep_agent_search_plan.md` - Approach 1 design and implementation
- `prepare/deepagents_cli_plan.md` - DeepAgents CLI configuration
- `prepare/tantivy_agent_search_plan.md` - Approach 3 design and implementation
- `prepare/research.md` - Background research and references

---

## License

MIT
