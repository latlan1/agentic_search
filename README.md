# Agentic Search

Four approaches to agentic search over Markdown documentation corpora, inspired by Benjamin Anderson's article: [Agentic Search for Dummies](https://benanderson.work/blog/agentic-search-for-dummies/).

## Overview

This project implements four distinct approaches to documentation search using AI agents:

| Approach | Script / Config | Technology | Use Case |
|----------|-----------------|------------|----------|
| **1. DeepAgent** | `deep_agent_search.py` | DeepAgents + Virtual FS | Dynamic corpus, no index needed |
| **2. DeepAgents CLI** | `.deepagents/` | DeepAgents CLI tool | Interactive sessions, real-time discovery |
| **3. Tantivy LG Agent** | `tantivy_lg_agent_search.py` | LangGraph + Tantivy | Production baseline, ranked results with LLM |
| **4. DeepAgent + Tantivy** | `tantivy_agent_search.py` | DeepAgents subagents + Tantivy | Parallel delegated search with token-optimized middleware |

All approaches search over the same documentation corpus:
- **DeepAgents docs** (12 files) - `data/deepagents_raw_md/`

Only Approaches 1 and 2 (with File system read access) search over:
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

# Optional: Override default model (default: claude-sonnet-4-5-20250929)
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
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
│  (Sonnet 4.5)           │
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

See `DEEP_AGENT_SEARCH_CHEATSHEET.md` for detailed usage.

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
│  (Sonnet 4.5)           │
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
brew install direnv

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
deepagents --model claude-sonnet-4-5-20250929

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

## Approach 3: Tantivy LG Agent (LangGraph + Tantivy)

Baseline LangGraph + Tantivy agent implemented in `scripts/tantivy_lg_agent_search.py`. This approach uses a direct LangGraph workflow (`StateGraph`) with `search_docs` and `read_docs` tools, plus conversation memory via `MemorySaver`.

### Architecture

```
User Query
    │
    ▼
┌─────────────────────────┐
│ tantivy_lg_agent_search │
│ - LangGraph StateGraph  │
│ - search_docs tool      │
│ - read_docs tool        │
│ - MemorySaver           │
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│ Tantivy Index           │
│ - BM25 search           │
│ - RRF fusion            │
│ - Two-phase retrieval   │
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│ Anthropic Claude        │
│ (Sonnet 4.5)            │
└─────────────────────────┘
    │
    ▼
Answer with Citations
```

### Key Features

- **Direct LangGraph workflow**: `StateGraph` + `ToolNode` execution loop
- **BM25 + RRF retrieval**: Fast ranked full-text search with query fusion
- **Two-phase search**: `search_docs()` previews, `read_docs()` loads full content
- **Conversation memory**: Multi-turn sessions via `MemorySaver`
- **Operational utilities**: `--sync`, `--graph`, and `--version` flags

### Usage

```bash
# Single query
uv run scripts/tantivy_lg_agent_search.py "How do I create a subagent?"

# Interactive mode
uv run scripts/tantivy_lg_agent_search.py --interactive

# Sync index before searching
uv run scripts/tantivy_lg_agent_search.py --sync "What is memory persistence?"

# Generate graph visualization
uv run scripts/tantivy_lg_agent_search.py --graph
```

**Best for**: Production baseline with straightforward LangGraph + Tantivy architecture.

See `TANTIVY_LG_CHEATSHEET.md` for detailed usage.

---

## Approach 4: DeepAgent (2 subagent) + Tantivy Agent

A DeepAgent-based agent that delegates search to **parallel subagents** backed by Tantivy. The parent agent formulates 2 query variations, dispatches them concurrently via `task` tool calls, then consolidates results into an answer with numbered citations.

### Architecture

```
User Query
    → Parent Agent (create_agent + minimal middleware)
        → Formulates 2 query variations (synonyms/related concepts)
        → Delegates both IN PARALLEL via task tool
            ┌─────────────────────────────────────────────┐
            │  search_subagent #1                         │
            │  search_docs(queries) → read_docs(ids)      │
            │  → returns findings                         │
            ├─────────────────────────────────────────────┤
            │  search_subagent #2                         │
            │  search_docs(queries) → read_docs(ids)      │
            │  → returns findings                         │
            └─────────────────────────────────────────────┘
        → Consolidates results from both subagents
        → Generates answer with numbered citations [1], [2]

Tantivy Index (BM25 + RRF)
    ← Built/synced by IndexManager from data/deepagents_raw_md/*.md files
```

### Token-Optimized Middleware

Uses `create_agent` (langchain) instead of `create_deep_agent` for full control over the middleware stack. This reduces per-query token usage from ~46,000 to ~12,000 — fitting within Anthropic's 30k tokens/min rate limit.

| Optimization | Token savings |
|-------------|--------------|
| Custom `task_description` (~400 chars vs 6,914 default) | ~1,500/call |
| `default_middleware=[]` on subagents | ~2,000/subagent call |
| 2 parallel queries (reduced from 3) | ~4,400/query |

### Key Features

- **Parallel subagent delegation**: 2 concurrent search tasks for better recall
- **BM25 + RRF**: Full-text search with multi-query fusion
- **Two-phase search**: Preview results (`search_docs`), then read full content (`read_docs`)
- **Token-optimized middleware**: Custom middleware stack (~12k tokens/query)
- **Multi-turn memory**: Conversation persistence via `MemorySaver`
- **Auto-sync**: Optionally sync index before searching

### Usage

```bash
# Single query
uv run scripts/tantivy_agent_search.py "How do I create a subagent?"

# Interactive mode
uv run scripts/tantivy_agent_search.py --interactive

# Sync index before searching
uv run scripts/tantivy_agent_search.py --sync "What is memory persistence?"
```

**Best for**: Production use, complex queries, multi-turn conversations.

See `TANTIVY_CHEATSHEET.md` for detailed usage.

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
│   ├── tantivy_lg_agent_search.py # Approach 3: LangGraph + Tantivy
│   ├── tantivy_agent_search.py  # Approach 4: DeepAgent (2 subagent) + Tantivy
│   ├── tantivy_index_manager.py # Index management utilities (for Approaches 3 & 4)
│   ├── tantivy_search.py        # Direct Tantivy CLI (utility)
│   └── trace_viewer.py          # Execution trace viewer
├── tests/
│   ├── deep_agent_search/       # Tests for Approach 1
│   ├── deepagents_cli/          # Tests for Approach 2
│   ├── tantivy_search/          # Tests for Tantivy utilities
│   └── tantivy_agent_search/    # Tests for Approaches 3/4 Tantivy agents
├── prepare/                     # Planning documents and research
│   ├── deep_agent_search_plan.md
│   ├── deepagents_cli_plan.md
│   ├── tantivy_agent_search_plan.md
│   └── research.md
├── AGENTS.md                    # Agent instructions for AI assistants
├── DEEP_AGENT_SEARCH_CHEATSHEET.md
├── DEEPAGENTS_CLI_CHEATSHEET.md
├── TANTIVY_LG_CHEATSHEET.md
├── TANTIVY_CHEATSHEET.md
└── pyproject.toml
```

---

## Running Tests

```bash
# Run all tests (120 passing, 5 skipped)
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

Approaches 3 and 4 support multiple queries that are fused using RRF:

```
RRF_score(doc) = Σ 1/(k + rank_i)
```

Where `k=60` is a constant and `rank_i` is the document's rank in query i. This allows "spray and pray" searching with multiple query variations for better recall.

### Two-Phase Search

Approaches 3 and 4 implement a two-phase search pattern:
1. **search_docs()** - Returns previews (doc_id, filename, description, score)
2. **read_docs()** - Returns full content for selected documents

This prevents context window bloat when exploring search results.

### Numbered Citations

Agent-based approaches (1, 3, and 4) generate responses with numbered citations:

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

| Feature | Approach 1 | Approach 2 | Approach 3 | Approach 4 |
|---------|------------|------------|------------|------------|
| Technology | DeepAgents script | DeepAgents CLI | LangGraph + Tantivy | DeepAgents subagents + Tantivy |
| Index required | No | No | Yes | Yes |
| Ranked results | No | No | Yes (BM25+RRF) | Yes (BM25+RRF) |
| Multi-query fusion | No | No | Yes | Yes |
| Parallel search | No | No | No (single agent + tools loop) | Yes (2 concurrent subagents) |
| Interactive mode | Yes | Yes (built-in) | Yes | Yes |
| Session persistence | No | Yes | No | No |
| Setup complexity | Low | Low | Medium | Medium-High |
| Best for | Dynamic docs | Interactive sessions | Production baseline | Production with delegated parallel search |

---

## Planning Documents

Detailed implementation plans for each approach are in `prepare/`:

- `prepare/deep_agent_search_plan.md` - Approach 1 design and implementation
- `prepare/deepagents_cli_plan.md` - DeepAgents CLI configuration
- `prepare/tantivy_agent_search_plan.md` - Tantivy agent design notes (primarily Approach 4)
- `prepare/research.md` - Background research and references

---

## License

MIT
