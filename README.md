# Agentic Search for Deep Markdown

Three approaches to agentic search over Markdown documentation corpora, inspired by Benjamin Anderson's article: [Agentic Search for Dummies](https://benanderson.work/blog/agentic-search-for-dummies/).

## Overview

This project implements three distinct approaches to documentation search using AI agents:

| Approach | Script / Config | Technology | Use Case |
|----------|-----------------|------------|----------|
| **1. DeepAgent** | `deep_agent_search.py` | DeepAgents + Virtual FS | Dynamic corpus, no index needed |
| **2. DeepAgents CLI** | `.deepagents/` | DeepAgents CLI tool | Interactive sessions, real-time discovery |
| **3. Tantivy Agent** | `tantivy_agent_search.py` | LangGraph + Tantivy | Production, ranked results with LLM |

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
# Required for all approaches
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

## Approach 2: DeepAgents CLI

Uses the `deepagents-cli` tool with project-specific configuration in `.deepagents/`. Provides an interactive multi-turn conversation interface with real-time file discovery - no index required.

### Architecture

```
User Query
    │
    ▼
┌─────────────────────────┐
│  deepagents CLI         │
│  - Interactive REPL     │
│  - Session persistence  │
│  - Human-in-the-loop    │
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│  .deepagents/           │
│  - AGENTS.md (context)  │
│  - skills/doc-search/   │
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│  File System Tools      │
│  ls, grep, glob, read   │
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

- **Interactive REPL**: Built-in multi-turn conversation interface
- **Session persistence**: Resume previous conversations across restarts
- **Real-time file discovery**: No index needed, searches files directly
- **Human-in-the-loop**: Safety controls for tool execution
- **Project skills**: Custom `doc-search` skill auto-loaded

### Setup

```bash
# Install DeepAgents CLI as a global tool
uv tool install deepagents-cli

# Configure Anthropic API key
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### Usage

```bash
# Start interactive session
deepagents

# Use a specific model
deepagents --model claude-sonnet-4-5-20250514

# Resume last session
deepagents -r

# Resume specific thread
deepagents -r abc123
```

### Interactive Commands

| Command | Description |
|---------|-------------|
| `/remember` | Save conversation insights to memory |
| `/tokens` | Show token usage |
| `/clear` | Clear conversation history |
| `/threads` | Show session info |
| `/exit` | Exit the CLI |

**Best for**: Interactive exploration, multi-turn conversations, and when a CLI interface is preferred.

See `DEEPAGENTS_CLI_CHEATSHEET.md` for detailed usage.

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

## Directory Structure

```
agentic_search/
├── data/
│   ├── deepagents_raw_md/       # DeepAgents documentation (12 files)
│   └── langgraph_raw_md/        # LangGraph documentation (29 files)
├── augmented_jsonl_index/       # LLM-generated keywords/descriptions
├── tantivy_index/               # Tantivy full-text index (generated)
├── .deepagents/                 # Approach 2: DeepAgents CLI configuration
│   ├── AGENTS.md                # Project context
│   └── skills/doc-search/       # Search skill
├── scripts/
│   ├── deep_agent_search.py     # Approach 1: DeepAgent
│   ├── tantivy_agent_search.py  # Approach 3: LangGraph Agent
│   ├── tantivy_index_manager.py # Index management utilities (for Approach 3)
│   ├── tantivy_search.py        # Direct Tantivy CLI (utility)
│   └── trace_viewer.py          # Execution trace viewer
├── tests/
│   ├── deep_agent_search/       # Tests for Approach 1
│   ├── deepagents_cli/          # Tests for Approach 2
│   ├── tantivy_search/          # Tests for Tantivy utilities
│   └── tantivy_agent_search/    # Tests for Approach 3
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

Approach 3 supports multiple queries that are fused using RRF:

```
RRF_score(doc) = Σ 1/(k + rank_i)
```

Where `k=60` is a constant and `rank_i` is the document's rank in query i. This allows "spray and pray" searching with multiple query variations for better recall.

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

---

## Comparison

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
