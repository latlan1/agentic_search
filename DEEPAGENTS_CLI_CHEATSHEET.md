# DeepAgents CLI Cheatsheet

Quick reference for using the DeepAgents CLI documentation search agent.

## Setup (One-Time)

```bash
# 1. Install deepagents-cli globally
uv tool install deepagents-cli

# 2. Configure your API key
cp .env.example .env.anthropic
# Edit .env.anthropic with your Anthropic API key

# 3. (Optional) Install direnv for auto-loading env vars
brew install direnv
echo 'eval "$(direnv hook zsh)"' >> ~/.zshrc  # or ~/.bashrc
source ~/.zshrc
direnv allow
```

## Running the Agent

```bash
# Start interactive session (env vars auto-loaded by direnv)
deepagents

# Or manually export first (if not using direnv)
export ANTHROPIC_API_KEY="your-key"
deepagents

# Use a specific model
deepagents --model claude-opus-4-5-20250514
deepagents --model claude-sonnet-4-5-20250514

# Set a default model (persists across sessions)
deepagents --default-model claude-sonnet-4-5-20250514

# Resume last session
deepagents -r

# Resume specific thread
deepagents -r abc123
```

## Interactive Commands

| Command | Description |
|---------|-------------|
| `/remember` | Save conversation insights to memory |
| `/tokens` | Show token usage |
| `/clear` | Clear conversation history |
| `/threads` | Show session info |
| `/exit` | Exit the CLI |

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Enter` | Submit message |
| `Ctrl+J` | New line |
| `Ctrl+E` | Open external editor |
| `Shift+Tab` | Toggle auto-approve |
| `@filename` | Auto-complete file |
| `Ctrl+C` | Interrupt |
| `Ctrl+D` | Exit |

## Shell Commands

Run shell commands directly with `!` prefix:
```bash
> !ls data/
> !git status
```

## Viewing Past Traces

The trace viewer lets you audit past agent queries, tool calls, and results.

```bash
# List all threads
uv run scripts/trace_viewer.py list

# View a thread's conversation
uv run scripts/trace_viewer.py view THREAD_ID

# View with full content (no truncation)
uv run scripts/trace_viewer.py view THREAD_ID --full

# View as JSON (for scripting)
uv run scripts/trace_viewer.py view THREAD_ID --json

# Show tool calls summary only
uv run scripts/trace_viewer.py tools THREAD_ID

# Search threads by content
uv run scripts/trace_viewer.py search "subagent"

# Export thread to JSON file
uv run scripts/trace_viewer.py export THREAD_ID output.json
```

### Trace Viewer Aliases

Add to your `.bashrc` or `.zshrc`:
```bash
alias trace="uv run scripts/trace_viewer.py"
alias trace-list="trace list"
alias trace-tools="trace tools"
```

Then use:
```bash
trace list
trace view d78
trace tools d78
trace search "grep"
```

## SQLite Database

The DeepAgents CLI stores all threads in `~/.deepagents/sessions.db`.

### Direct SQLite Queries

```bash
# List threads with message counts
sqlite3 ~/.deepagents/sessions.db \
  "SELECT thread_id, COUNT(*) FROM checkpoints GROUP BY thread_id"

# Find threads from today
sqlite3 ~/.deepagents/sessions.db \
  "SELECT DISTINCT thread_id FROM checkpoints ORDER BY checkpoint_id DESC LIMIT 10"
```

## Project Skills

The `doc-search` skill is auto-loaded when working in this directory.

```bash
# List project skills
deepagents skills list --project

# View skill details
deepagents skills info doc-search --project
```

## LangSmith Tracing (Optional)

For cloud-based tracing with visualization:

```bash
# Add to .env.anthropic
LANGCHAIN_TRACING=true
LANGCHAIN_API_KEY=your_langsmith_key
DEEPAGENTS_LANGSMITH_PROJECT=doc-search

# View traces at https://smith.langchain.com
```

## Quick Examples

```bash
# Ask about DeepAgents
> How do I create a subagent?

# Ask about LangGraph
> What is LangGraph persistence?

# Compare both
> What's the difference between DeepAgents and LangGraph?

# Follow-up questions (context is maintained)
> Can you show me a code example?
```

## File Locations

| Path | Purpose |
|------|---------|
| `.deepagents/AGENTS.md` | Project context |
| `.deepagents/skills/doc-search/SKILL.md` | Search skill definition |
| `~/.deepagents/sessions.db` | Thread/checkpoint storage |
| `~/.deepagents/agent/memories/` | Agent memory files |
| `data/deepagents_raw_md/` | DeepAgents docs (12 files) |
| `data/langgraph_raw_md/` | LangGraph docs (29 files) |
