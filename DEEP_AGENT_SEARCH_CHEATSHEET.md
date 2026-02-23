# Deep Agent Search Cheatsheet

Quick reference for using the DeepAgents-based documentation search (Approach 1).

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

### 2. Get API Key

Get your Anthropic API key at: https://console.anthropic.com/settings/keys

---

## Usage

### Single Query

```bash
# Basic search
uv run scripts/deep_agent_search.py "How do I create a subagent?"

# With verbose mode (see tool calls)
uv run scripts/deep_agent_search.py --verbose "What is context quarantine?"
uv run scripts/deep_agent_search.py -v "How does memory work?"
```

### Interactive Mode (Multi-turn)

```bash
# Start interactive session
uv run scripts/deep_agent_search.py --interactive

# With verbose mode
uv run scripts/deep_agent_search.py --interactive --verbose
```

Example session:
```
╔══════════════════════════════════════════════════════════════╗
║ Deep Agent Search - Interactive Mode                          ║
╠══════════════════════════════════════════════════════════════╣
║ Session ID: abc-123-def                                       ║
║                                                               ║
║ How it works:                                                 ║
║ - All 41 docs loaded into virtual filesystem                  ║
║ - Conversation memory persists across queries                 ║
║ - Agent uses grep/ls/read_file to search (no chunking)       ║
║ - Type /verbose to toggle tool call visibility               ║
║ - Type quit or exit to end session                           ║
╚══════════════════════════════════════════════════════════════╝

You: What is a deep agent?

╔══════════════════════════════════════════════════════════════╗
║ Answer                                                        ║
╠══════════════════════════════════════════════════════════════╣
║ A deep agent is... [formatted markdown response]              ║
║                                                               ║
║ ---                                                           ║
║ ## Sources                                                    ║
║ 1. [deepagents-overview.md](file:///path/to/file) - Overview  ║
╚══════════════════════════════════════════════════════════════╝

You: /verbose
Verbose mode: ON

You: How do I add memory to it?

╔══ Tool Call #1 ══════════════════════════════════════════════╗
║ Tool: grep                                                    ║
║   pattern: memory                                             ║
║   path: /docs/                                                ║
╚══════════════════════════════════════════════════════════════╝
[Output: matches in 3 files...]

╔══ Tool Call #2 ══════════════════════════════════════════════╗
║ Tool: read_file                                               ║
║   path: /docs/deepagents/deepagents-long-term-memory.md       ║
╚══════════════════════════════════════════════════════════════╝
[Output: file content...]

╔══════════════════════════════════════════════════════════════╗
║ Answer                                                        ║
╠══════════════════════════════════════════════════════════════╣
║ To add memory to a deep agent... [uses conversation context]  ║
╚══════════════════════════════════════════════════════════════╝

You: quit
Goodbye!
```

---

## How It Works (No Chunking!)

### Document Loading Strategy

Unlike RAG systems that chunk documents, this approach loads **entire documents** into a virtual filesystem:

```
data/deepagents_raw_md/          →    /docs/deepagents/
  deepagents-overview.md         →      deepagents-overview.md
  deepagents-subagents.md        →      deepagents-subagents.md
  ...                            →      ...

data/langgraph_raw_md/           →    /docs/langgraph/
  langgraph-overview.md          →      langgraph-overview.md
  ...                            →      ...
```

### Agent Search Strategy

The agent uses **file system tools** to search, not embeddings:

1. **`grep(pattern, path)`** - Find files containing keywords
   - Returns: list of matching files with line numbers
   - Does NOT load file content into context

2. **`ls(path)`** - Browse directory structure
   - Returns: file listing
   - Useful when grep returns no results

3. **`read_file(path)`** - Load full file content
   - Only called for files the agent wants to examine
   - Full document loaded (no chunking)

4. **`glob(pattern, path)`** - Find files by name pattern
   - Example: `glob("*memory*", "/docs/")` finds files with "memory" in name

### Handling No Results

The system prompt instructs the agent to iterate:

```
If grep returns 0 results:
  1. Try alternative keywords/synonyms
  2. Use broader patterns
  3. Browse with ls to find files manually
  4. Try multiple approaches before giving up
```

### Interactive Mode Memory

In interactive mode:
1. A unique `thread_id` is created for the session
2. LangGraph's `MemorySaver` stores conversation history
3. The agent can reference previous Q&A in follow-up questions
4. Documents are loaded once at start, not re-loaded per query

---

## Verbose Mode

See exactly which tools the agent calls and in what order:

```bash
# Single query with tool visibility
uv run scripts/deep_agent_search.py --verbose "What is a skill?"

# Or toggle in interactive mode
You: /verbose
Verbose mode: ON
```

Output shows:
- Tool name (grep, ls, read_file, glob)
- Input parameters
- Output/results (truncated for display)
- Call order (numbered)

---

## Citations

### Format

Responses end with a numbered Sources section:

```markdown
---
## Sources

1. [deepagents-subagents.md](file:///Users/you/project/data/deepagents_raw_md/deepagents-subagents.md) - Subagent delegation guide
2. [langgraph-persistence.md](file:///Users/you/project/data/langgraph_raw_md/langgraph-persistence.md) - Memory persistence
```

### Clickable Links

Citations are converted to `file://` URLs that open in your editor/browser:
- **VS Code**: Cmd+Click to open file
- **Terminal**: May open in default app (depends on terminal)
- **iTerm2**: Cmd+Click opens file

---

## System Prompt (LLM Instructions)

The agent receives this prompt that instructs it how to search and format responses:

**Key sections:**
1. **Available Documentation** - Lists `/docs/deepagents/` and `/docs/langgraph/`
2. **Available Tools** - ls, read_file, grep, glob (read-only)
3. **Search Strategy** - Start broad, narrow down, iterate if needed
4. **Handling Edge Cases** - What to do when grep returns 0 results
5. **Response Format** - Must end with numbered Sources section

The prompt does NOT tell the agent to "summarize" - it instructs it to:
- Synthesize information from multiple sources
- Include code examples when helpful
- Always cite sources with full paths

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Yes | - | Your Anthropic API key |
| `ANTHROPIC_MODEL` | No | `claude-sonnet-4-20250514` | Model to use |

### Override Model

```bash
# Use a different Claude model
export ANTHROPIC_MODEL="claude-3-5-sonnet-20241022"
uv run scripts/deep_agent_search.py "What is a skill?"
```

---

## Command Reference

| Command | Description |
|---------|-------------|
| `uv run scripts/deep_agent_search.py "query"` | Single search |
| `uv run scripts/deep_agent_search.py -v "query"` | Search with tool visibility |
| `uv run scripts/deep_agent_search.py -i` | Interactive mode |
| `uv run scripts/deep_agent_search.py -i -v` | Interactive + verbose |

### Interactive Commands

| Command | Description |
|---------|-------------|
| `/verbose` | Toggle tool call visibility |
| `quit` or `exit` | End session |
| Ctrl+C | Force exit |

---

## Example Queries

```bash
# DeepAgents questions
uv run scripts/deep_agent_search.py "How do I create a skill in DeepAgents?"
uv run scripts/deep_agent_search.py "What middleware options are available?"
uv run scripts/deep_agent_search.py -v "How does the harness work?"

# LangGraph questions
uv run scripts/deep_agent_search.py "How do I add persistence to a LangGraph agent?"
uv run scripts/deep_agent_search.py "What is the difference between Graph API and Functional API?"
uv run scripts/deep_agent_search.py -v "How do I implement human-in-the-loop?"
```

---

## Troubleshooting

### "ANTHROPIC_API_KEY environment variable is required"

```bash
echo $ANTHROPIC_API_KEY  # Check if set
export ANTHROPIC_API_KEY="sk-ant-..."
```

### "No documentation files found"

```bash
ls data/deepagents_raw_md/
ls data/langgraph_raw_md/
```

### Agent Says "No Information Found"

The agent may not find results if:
1. Keywords don't match document content
2. Information doesn't exist in the corpus

Try:
- Different phrasing
- Enable verbose mode to see what the agent searched for
- Check if the topic is covered: `grep -r "keyword" data/`

### Slow Response

Normal - the agent makes multiple tool calls (grep → read_file → grep → ...). Each call takes time. Enable verbose mode to see progress.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Query                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Claude Sonnet 4.5 (LLM)                        │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              System Prompt                           │    │
│  │  - Search strategy                                   │    │
│  │  - Tool descriptions                                 │    │
│  │  - Response format (citations required)              │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
        ┌─────────┐     ┌─────────┐     ┌─────────┐
        │  grep   │     │   ls    │     │read_file│
        └─────────┘     └─────────┘     └─────────┘
              │               │               │
              └───────────────┼───────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Virtual Filesystem (StateBackend)              │
│  /docs/                                                      │
│  ├── deepagents/                                             │
│  │   ├── deepagents-overview.md                              │
│  │   ├── deepagents-subagents.md                             │
│  │   └── ... (12 files)                                      │
│  └── langgraph/                                              │
│      ├── langgraph-overview.md                               │
│      └── ... (29 files)                                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Rich Terminal Output                            │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ ╔═══════════════════════════════════════════════╗   │    │
│  │ ║ Answer (Markdown rendered)                    ║   │    │
│  │ ║                                               ║   │    │
│  │ ║ ## Sources                                    ║   │    │
│  │ ║ 1. [file.md](file://path) - description      ║   │    │
│  │ ╚═══════════════════════════════════════════════╝   │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## Files

| File | Description |
|------|-------------|
| `scripts/deep_agent_search.py` | Main script |
| `data/deepagents_raw_md/` | DeepAgents documentation (12 files) |
| `data/langgraph_raw_md/` | LangGraph documentation (29 files) |
| `DEEP_AGENT_SEARCH_CHEATSHEET.md` | This file |
