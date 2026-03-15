# Approach 4 Cheatsheet: DeepAgent (2 subagent) + Tantivy

Quick reference for using the DeepAgent (2 subagent) + Tantivy agent search (`scripts/tantivy_agent_search.py`, Approach 4).

---

## Setup

### 1. Set Environment Variable

```bash
# Option A: Export directly
export ANTHROPIC_API_KEY="sk-ant-..."

# Option B: Add to .env file
echo 'ANTHROPIC_API_KEY=sk-ant-...' >> .env

# Option C: Use .envrc with direnv
echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> .envrc
direnv allow
```

### 2. Build the Index

```bash
# Build Tantivy index from documentation files
uv run scripts/tantivy_index_manager.py build

# Or let it auto-build on first search
uv run scripts/tantivy_agent_search.py "any query"
```

---

## Usage

### Single Query

```bash
# Basic search
uv run scripts/tantivy_agent_search.py "How do I create a subagent?"

# Sync index before searching (picks up new/changed files)
uv run scripts/tantivy_agent_search.py --sync "What is memory persistence?"
```

### Interactive Mode (Multi-turn)

```bash
# Start interactive session
uv run scripts/tantivy_agent_search.py --interactive

# With index sync on startup
uv run scripts/tantivy_agent_search.py --interactive --sync
```

Example session:
```
╔══════════════════════════════════════════════════════════════╗
║ Deep Agent Search - Interactive Mode                          ║
╠══════════════════════════════════════════════════════════════╣
║ Session ID: abc-123-def                                       ║
║                                                               ║
║ How it works:                                                 ║
║ - Type /verbose to toggle tool call visibility               ║
║ - Type /sync to re-sync the index                            ║
║ - Type quit or exit to end session                           ║
╚══════════════════════════════════════════════════════════════╝

You: What is a deep agent?

╔══════════════════════════════════════════════════════════════╗
║ Answer                                                        ║
╠══════════════════════════════════════════════════════════════╣
║ A deep agent is... [formatted markdown response]              ║
║                                                               ║
║ ---                                                           ║
║ **Sources:**                                                  ║
║ [1] [deepagents-overview.md](data/deepagents_raw_md/...)      ║
╚══════════════════════════════════════════════════════════════╝
Completed in 47.6s

You: quit
Goodbye!
```

### Interactive Commands

| Command | Description |
|---------|-------------|
| `/verbose` | Toggle tool call visibility |
| `/sync` | Re-sync Tantivy index with files |
| `quit` or `exit` | End session |
| Ctrl+C | Force exit |

---

## Architecture: Parallel Subagent Delegation (Approach 4)

The agent uses a **parent-subagent** pattern where the parent delegates search to 2 concurrent subagents:

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
```

### Why Subagents?

Each subagent searches with a different query variation (e.g., "subagent" vs "delegate task"). This improves recall — different phrasings surface different documents. Results are then consolidated by the parent agent.

### Why 2 Subagents (Not 3)?

Token budget. Each subagent invocation costs LLM tokens. With 3 subagents the total reached ~46,000 input tokens/query, exceeding Anthropic's 30k tokens/min rate limit. Reducing to 2 subagents brings it to ~12,000 tokens/query while still providing good recall via query variation.

---

## Token Optimization

### The Problem

The original `create_deep_agent` hardcodes a middleware stack that injects ~4,400 tokens of system prompts and tool descriptions per LLM call. With multiple subagents, total overhead exceeded Anthropic's 30k tokens/min rate limit.

### The Solution

Replace `create_deep_agent` with `create_agent` (from langchain) for full control over the middleware stack.

| Optimization | What changed | Token savings |
|-------------|-------------|--------------|
| Custom `task_description` | ~400 chars vs 6,914 default | ~1,500/call |
| `default_middleware=[]` | Subagents get no middleware overhead | ~2,000/subagent call |
| 2 parallel queries | Reduced from 3 subagent invocations | ~4,400/query |

### Middleware Stack Comparison

| Middleware | Old (create_deep_agent) | New (create_agent) |
|-----------|------------------------|-------------------|
| TodoListMiddleware | Included (~1,182 tokens) | Removed |
| FilesystemMiddleware | Included (~841 tokens) | Removed |
| MemoryMiddleware | Included (~1,116 tokens) | Removed |
| SubAgentMiddleware | Default 6,914-char desc | Custom ~400-char desc |
| SummarizationMiddleware | Included | Included (with StateBackend) |
| AnthropicPromptCachingMiddleware | Included | Included |
| PatchToolCallsMiddleware | Included | Included |
| **Subagent middleware** | All of the above | **None** (`default_middleware=[]`) |

**Result**: ~12,000 tokens/query (down from ~46,000).

---

## Two-Phase Search

The subagents use a two-phase pattern to avoid loading unnecessary content:

### Phase 1: Search (Preview)

```python
search_docs(queries=["subagent", "delegate task"], limit=5)
```

Returns previews — doc_id, filename, description, BM25 score. No full content loaded.

### Phase 2: Read (Full Content)

```python
read_docs(doc_ids=[1, 3, 5])
```

Loads full document text only for the most relevant results. This prevents context window bloat.

---

## Reciprocal Rank Fusion (RRF)

When multiple query variations are passed to `search_docs`, results are fused using RRF:

```
RRF_score(doc) = Sigma 1/(k + rank_i)
```

Where `k=60` and `rank_i` is the document's rank in query i. Documents appearing in multiple query results get boosted.

---

## Citations

### Format

Responses end with numbered sources:

```markdown
Subagents allow you to delegate tasks to specialized agents [1].
You can create them using the `Task` tool [2].

---
**Sources:**
[1] [deepagents-subagents.md](data/deepagents_raw_md/deepagents-subagents.md)
[2] [deepagents-context.md](data/deepagents_raw_md/deepagents-context.md)
```

---

## Index Management

### Build / Sync

```bash
# Build index from scratch
uv run scripts/tantivy_index_manager.py build

# Incremental sync (add new, update changed, remove deleted)
uv run scripts/tantivy_index_manager.py sync

# Watch for file changes (auto-sync)
uv run scripts/tantivy_index_manager.py watch

# Show index statistics
uv run scripts/tantivy_index_manager.py stats
```

### Auto-Build

The agent automatically builds the index on first use if it doesn't exist. Use `--sync` to force a sync before searching.

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Yes | - | Your Anthropic API key |
| `ANTHROPIC_MODEL` | No | `claude-sonnet-4-5-20250929` | Model to use |

### Override Model

```bash
export ANTHROPIC_MODEL="claude-3-5-sonnet-20241022"
uv run scripts/tantivy_agent_search.py "What is a skill?"
```

---

## Command Reference

| Command | Description |
|---------|-------------|
| `uv run scripts/tantivy_agent_search.py "query"` | Single search |
| `uv run scripts/tantivy_agent_search.py -i` | Interactive mode |
| `uv run scripts/tantivy_agent_search.py -s "query"` | Sync index + search |
| `uv run scripts/tantivy_agent_search.py -i -s` | Interactive + sync |
| `uv run scripts/tantivy_agent_search.py --thread abc` | Custom thread ID |

---

## Example Queries

```bash
# DeepAgents questions
uv run scripts/tantivy_agent_search.py "How do subagents work in DeepAgents?"
uv run scripts/tantivy_agent_search.py "What middleware options are available?"
uv run scripts/tantivy_agent_search.py "How does context quarantine work?"

# LangGraph questions
uv run scripts/tantivy_agent_search.py "How do I add persistence to a LangGraph agent?"
uv run scripts/tantivy_agent_search.py "What is the difference between Graph API and Functional API?"
uv run scripts/tantivy_agent_search.py "How do I implement human-in-the-loop?"
```

---

## Troubleshooting

### "ANTHROPIC_API_KEY environment variable is required"

```bash
echo $ANTHROPIC_API_KEY  # Check if set
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Rate Limit Errors (429)

The token-optimized middleware should keep usage under 30k tokens/min. If you still hit limits:
- Wait 60 seconds between queries
- Check if `ANTHROPIC_MODEL` is set to an unexpected model

### "Index not found" / Empty Results

```bash
# Rebuild the index
uv run scripts/tantivy_index_manager.py build

# Verify data files exist
ls data/deepagents_raw_md/
ls data/langgraph_raw_md/
```

### Slow Response

Normal — the agent makes multiple LLM calls (parent + 2 subagents). Typical time is 30-60 seconds depending on network and model latency.

---

## Files

| File | Description |
|------|-------------|
| `scripts/tantivy_agent_search.py` | Main Approach 4 agent script |
| `scripts/tantivy_search.py` | Tantivy search index (search/read tools) |
| `scripts/tantivy_index_manager.py` | Index build/sync/watch utilities |
| `scripts/helper.py` | Shared utilities (LLM, rendering, tool extraction) |
| `tantivy_index/` | Generated Tantivy index directory |
| `augmented_jsonl_index/` | LLM-generated keywords/descriptions |
| `TANTIVY_CHEATSHEET.md` | This file (Approach 4) |
| `TANTIVY_LG_CHEATSHEET.md` | Approach 3 (LangGraph + Tantivy) cheatsheet |
