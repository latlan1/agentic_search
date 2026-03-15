# Approach 3 Cheatsheet: LangGraph + Tantivy Agent

Quick reference for using the LangGraph + Tantivy baseline agent (`scripts/tantivy_lg_agent_search.py`, Approach 3).

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
uv run scripts/tantivy_lg_agent_search.py "any query"
```

---

## Usage

### Single Query

```bash
# Basic search
uv run scripts/tantivy_lg_agent_search.py "How do I create a subagent?"

# Sync index before searching (picks up new/changed files)
uv run scripts/tantivy_lg_agent_search.py --sync "What is memory persistence?"
```

### Interactive Mode (Multi-turn)

```bash
# Start interactive session
uv run scripts/tantivy_lg_agent_search.py --interactive

# With index sync on startup
uv run scripts/tantivy_lg_agent_search.py --interactive --sync
```

### Graph Visualization

```bash
# Generate LangGraph workflow PNG
uv run scripts/tantivy_lg_agent_search.py --graph

# Custom output path
uv run scripts/tantivy_lg_agent_search.py --graph docs/langgraph_workflow.png
```

### Version / Model Info

```bash
uv run scripts/tantivy_lg_agent_search.py --version
```

---

## Architecture: Direct LangGraph Tool Loop

Approach 3 uses a direct `StateGraph` + `ToolNode` cycle (no DeepAgents subagent middleware):

```
User Query
    -> LangGraph agent node
    -> Calls search_docs(queries, limit)
    -> Calls read_docs(doc_ids)
    -> Synthesizes final answer with citations
```

### Core Flow

1. Agent receives user question
2. Agent formulates search queries
3. `search_docs()` returns ranked previews (doc_id, filename, description, score)
4. Agent selects relevant documents
5. `read_docs()` fetches full content for selected IDs
6. Agent writes final answer with numbered citations

---

## Two-Phase Search

### Phase 1: Search (Preview)

```python
search_docs(queries=["subagent", "delegate task"], limit=10)
```

Returns previews only. Keeps retrieval fast and avoids loading irrelevant content.

### Phase 2: Read (Full Content)

```python
read_docs(doc_ids=[1, 3, 5])
```

Loads full documents only for the most relevant results.

---

## Reciprocal Rank Fusion (RRF)

When multiple query variations are used, Tantivy results are fused via RRF:

```
RRF_score(doc) = Sigma 1/(k + rank_i)
```

Where `k=60` and `rank_i` is rank in each query's result list.

---

## Citations

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

---

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Yes | - | Your Anthropic API key |
| `LLM_MODEL` | No | `claude-sonnet-4-5-20250929` | Model to use |

### Override Model

```bash
export LLM_MODEL="claude-sonnet-4-5-20250929"
uv run scripts/tantivy_lg_agent_search.py "What is a skill?"
```

---

## Command Reference

| Command | Description |
|---------|-------------|
| `uv run scripts/tantivy_lg_agent_search.py "query"` | Single search |
| `uv run scripts/tantivy_lg_agent_search.py -i` | Interactive mode |
| `uv run scripts/tantivy_lg_agent_search.py -s "query"` | Sync index + search |
| `uv run scripts/tantivy_lg_agent_search.py -i -s` | Interactive + sync |
| `uv run scripts/tantivy_lg_agent_search.py --thread abc` | Custom thread ID |
| `uv run scripts/tantivy_lg_agent_search.py --graph` | Generate graph visualization |
| `uv run scripts/tantivy_lg_agent_search.py --version` | Show model/version info |

### Interactive Commands

| Command | Description |
|---------|-------------|
| `/sync` | Re-sync Tantivy index with files |
| `quit` or `exit` | End session |
| Ctrl+C | Force exit |

---

## Example Queries

```bash
# DeepAgents questions
uv run scripts/tantivy_lg_agent_search.py "How do subagents work in DeepAgents?"
uv run scripts/tantivy_lg_agent_search.py "What middleware options are available?"

# LangGraph questions
uv run scripts/tantivy_lg_agent_search.py "How do I add persistence to a LangGraph agent?"
uv run scripts/tantivy_lg_agent_search.py "How do I implement human-in-the-loop?"
```

---

## Troubleshooting

### "ANTHROPIC_API_KEY environment variable is required"

```bash
echo $ANTHROPIC_API_KEY
export ANTHROPIC_API_KEY="sk-ant-..."
```

### "Index not found" / Empty Results

```bash
uv run scripts/tantivy_index_manager.py build
ls data/deepagents_raw_md/
ls data/langgraph_raw_md/
```

### Slow Response

Normal: this approach runs multiple LLM/tool turns in sequence. Typical time is 20-60 seconds depending on query complexity and network latency.

---

## Files

| File | Description |
|------|-------------|
| `scripts/tantivy_lg_agent_search.py` | Main Approach 3 agent script |
| `scripts/tantivy_search.py` | Tantivy search index (search/read tools) |
| `scripts/tantivy_index_manager.py` | Index build/sync/watch utilities |
| `tantivy_index/` | Generated Tantivy index directory |
| `augmented_jsonl_index/` | LLM-generated keywords/descriptions |
| `TANTIVY_LG_CHEATSHEET.md` | This file (Approach 3) |
| `TANTIVY_CHEATSHEET.md` | Approach 4 (DeepAgent 2-subagent + Tantivy) cheatsheet |
