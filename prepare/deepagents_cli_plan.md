# DeepAgents CLI Implementation Plan

> **STATUS: ✅ IMPLEMENTATION COMPLETE**
> 
> All phases have been implemented. The DeepAgents CLI is installed and configured.
> Run `./scripts/run_doc_search_cli.sh` to start the documentation search agent.

## Overview

This document outlines a **separate implementation** using the **DeepAgents CLI** (`deepagents-cli`) for agentic search over documentation. This is distinct from and does not replace the existing `scripts/deep_agent_search.py` implementation.

### Goals

1. Use DeepAgents CLI for built-in interactive multi-turn conversations
2. Search documentation **only** from the `data/` folder (no external sources)
3. Automatically reflect changes when files in `data/` are added/modified/removed
4. Use **Anthropic API** (Claude) as the LLM provider
5. Enforce read-only access to the `data/` folder through skill instructions

---

## Architecture

```
                        User
                          |
                          v
                   +-------------+
                   | deepagents  |
                   | CLI         |
                   +-------------+
                          |
                          v
            +---------------------------+
            |  .deepagents/             |
            |  ├── AGENTS.md            |  <-- Project context
            |  └── skills/              |
            |      └── doc-search/      |
            |          └── SKILL.md     |  <-- Search skill
            +---------------------------+
                          |
                          v
            +---------------------------+
            |  Anthropic API            |
            |  (Claude Sonnet 4.5)      |
            +---------------------------+
                          |
                          v
            +---------------------------+
            |  data/ (READ-ONLY)        |
            |  ├── deepagents_raw_md/   |  <-- 12 files
            |  └── langgraph_raw_md/    |  <-- 29 files
            +---------------------------+
```

---

## Key Design Decisions

### 1. Separate Implementation

This CLI-based approach is **completely separate** from the existing implementation:

| Aspect | `deep_agent_search.py` | DeepAgents CLI |
|--------|------------------------|----------------|
| Location | `scripts/deep_agent_search.py` | `.deepagents/` config |
| Dependencies | Already in `pyproject.toml` | `deepagents-cli` (separate tool) |
| Invocation | `uv run scripts/deep_agent_search.py` | `deepagents --agent doc-search` |
| Purpose | Programmatic API | Interactive terminal |

**No changes** will be made to:
- `scripts/deep_agent_search.py`
- `pyproject.toml` dependencies
- Existing test files

### 2. Dynamic Data Folder Reflection

The agent must automatically reflect any changes to the `data/` folder:

**Approach**: Use the CLI's built-in file system tools (`ls`, `glob`, `grep`, `read_file`) that operate on the **actual filesystem** rather than a cached/indexed copy.

```markdown
# In SKILL.md - instruct agent to always scan fresh

## Search Strategy

1. ALWAYS start by listing current files:
   - `ls data/deepagents_raw_md/`
   - `ls data/langgraph_raw_md/`
   
2. Use `glob` for pattern matching:
   - `glob("data/**/*.md")` to find all markdown files
   
3. Use `grep` for content search:
   - `grep("subagent", "data/")` to find mentions
   
4. Read specific files with `read_file`
```

**Why this works**: 
- No pre-built index to become stale
- Each search operation reads from disk
- New files are immediately discoverable
- Deleted files are immediately gone

### 3. Anthropic API Configuration

The DeepAgents CLI natively supports Anthropic. Simply set the API key:

```bash
# .env configuration
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

The CLI will automatically:
- Detect the Anthropic API key
- Use `claude-sonnet-4-5-20250929` as the default model
- No custom base URL or model string needed

To use a different Claude model:
```bash
deepagents --model claude-opus-4-5-20251101
```

### 4. Read-Only Enforcement via Skill Instructions

We enforce read-only access through clear instructions in the skill and AGENTS.md files. The agent is instructed to:

1. **Never use** `write_file` or `edit_file` on `data/` paths
2. **Never use** `shell` commands that modify files
3. **Only search** within the `data/` directory
4. **Never use** `web_search` or `fetch_url`

Additionally, the CLI's built-in **human-in-the-loop** provides a safety net:
- All `write_file`, `edit_file`, and `shell` operations require user approval
- User can reject any write attempt before it executes

**Note**: For stronger enforcement, additional technical mechanisms (filesystem permissions, git hooks, Docker) can be added later if needed.

---

## Implementation Steps

### Phase 1: Directory Structure ✅ COMPLETED

```
.deepagents/
├── AGENTS.md                    # Project-level agent context
└── skills/
    └── doc-search/
        └── SKILL.md             # Documentation search skill
```

### Phase 2: Create Configuration Files ✅ COMPLETED

#### File: `.deepagents/AGENTS.md`

```markdown
# Documentation Search Agent

This agent searches and answers questions about DeepAgents and LangGraph documentation.

## Project Structure

- Documentation: `data/` directory (READ-ONLY)
  - `data/deepagents_raw_md/` - DeepAgents library docs
  - `data/langgraph_raw_md/` - LangGraph framework docs

## Critical Rules

1. **READ-ONLY**: NEVER modify, create, or delete files in `data/`
2. **Data Folder Only**: ONLY search within `data/` - no external sources
3. **Fresh Scans**: Always use `ls`/`glob` to discover current files (no caching)
4. **Citations**: Always cite source filenames in responses

## What NOT To Do

- Do NOT use `write_file` or `edit_file` on paths starting with `data/`
- Do NOT use `shell` commands that modify the filesystem
- Do NOT use `web_search` or `fetch_url` - only local documentation
- Do NOT create new files anywhere in the project
```

#### File: `.deepagents/skills/doc-search/SKILL.md`

```markdown
---
name: doc-search
description: Search and answer questions about DeepAgents and LangGraph documentation from the data/ folder
---

# Documentation Search Skill

Use this skill when the user asks questions about:
- DeepAgents library (creating agents, subagents, middleware, backends, etc.)
- LangGraph framework (graphs, state, persistence, streaming, etc.)
- Comparing features between the two libraries

## Documentation Location

All documentation is in the `data/` directory:
- `data/deepagents_raw_md/*.md` - DeepAgents docs (12 files)
- `data/langgraph_raw_md/*.md` - LangGraph docs (29 files)

## Search Workflow

### Step 1: Discover Current Files
Always start by checking what files exist (they may have changed):
```
ls data/deepagents_raw_md/
ls data/langgraph_raw_md/
```

### Step 2: Search for Relevant Content
Use grep to find files containing relevant keywords:
```
grep "subagent" data/
grep "StateGraph" data/
```

### Step 3: Read Relevant Files
Read the full content of promising files:
```
read_file data/deepagents_raw_md/deepagents-subagents.md
```

### Step 4: Synthesize Answer
- Combine information from multiple files if needed
- Include code examples when helpful
- ALWAYS cite source files

## Response Format

Always include citations in your responses:
- Reference files: [deepagents-subagents.md]
- Quote relevant passages when helpful
- If information is not found, say so clearly

## CONSTRAINTS

### Forbidden Actions
- ❌ `write_file` on any `data/` path
- ❌ `edit_file` on any `data/` path  
- ❌ `shell` commands that modify files
- ❌ `web_search` - only use local docs
- ❌ `fetch_url` - only use local docs

### Required Actions
- ✅ Always use `ls` or `glob` to check current files
- ✅ Always cite source files
- ✅ Only search within `data/` directory
```

### Phase 3: Environment Configuration ✅ COMPLETED

#### File: `.env.anthropic` (new file, separate from existing .env)

```bash
# Anthropic API Configuration for DeepAgents CLI
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional: LangSmith tracing
# LANGCHAIN_TRACING=true
# LANGCHAIN_API_KEY=your_langsmith_api_key
```

### Phase 4: Wrapper Script ✅ COMPLETED

#### File: `scripts/run_doc_search_cli.sh`

```bash
#!/bin/bash
# Run DeepAgents CLI configured for documentation search
# Uses Anthropic API (Claude)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load Anthropic configuration
if [ -f "$PROJECT_ROOT/.env.anthropic" ]; then
    export $(grep -v '^#' "$PROJECT_ROOT/.env.anthropic" | xargs)
fi

# Verify API key is set
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "Error: ANTHROPIC_API_KEY not set"
    echo "Create .env.anthropic with your Anthropic API key"
    exit 1
fi

# Run DeepAgents CLI
cd "$PROJECT_ROOT"
exec deepagents "$@"
```

### Phase 5: Verification ✅ COMPLETED

After creating the files, verify the setup works:

```bash
# 1. Check skill is detected
deepagents skills list --project

# 2. Start the CLI and test
./scripts/run_doc_search_cli.sh

# 3. Test queries
> How do I create a subagent?
> What is LangGraph persistence?
```

---

## File Summary

| File | Purpose | Status |
|------|---------|--------|
| `.deepagents/AGENTS.md` | Project context for CLI | ✅ Created |
| `.deepagents/skills/doc-search/SKILL.md` | Search skill definition | ✅ Created |
| `.env.anthropic` | Anthropic API config (secrets) | ✅ Created |
| `.env.example` | Example env file (committable) | ✅ Created |
| `.envrc` | direnv auto-load env vars | ✅ Created |
| `scripts/trace_viewer.py` | View/audit past agent traces | ✅ Created |
| `DEEPAGENTS_CLI_CHEATSHEET.md` | Quick reference guide | ✅ Created |
| `deepagents_cli_plan.md` | This plan document | ✅ Created |

**No modifications to existing files**:
- `scripts/deep_agent_search.py` - unchanged
- `pyproject.toml` - unchanged (CLI installed separately via `uv tool`)
- `.env` / `.env.example` - unchanged

---

## Installation & Usage

### One-Time Setup

```bash
# 1. Install DeepAgents CLI as a tool (not a project dependency)
uv tool install deepagents-cli

# 2. Configure Anthropic API key
cp .env.example .env.anthropic
# Edit .env.anthropic and add your Anthropic API key

# 3. (Optional) Install direnv for auto-loading env vars
brew install direnv
echo 'eval "$(direnv hook zsh)"' >> ~/.zshrc
source ~/.zshrc
direnv allow
```

### Running the CLI

```bash
# With direnv (env vars auto-loaded)
deepagents

# Without direnv (manual export)
export ANTHROPIC_API_KEY="your-key"
deepagents

# Example session:
> How do I create a subagent?
[Agent searches data/deepagents_raw_md/, provides answer]

> What about LangGraph persistence?
[Agent uses conversation context, searches data/langgraph_raw_md/]

> /clear    # Clear conversation
> /exit     # Exit CLI
```

### Viewing Past Traces

```bash
# List all threads
uv run scripts/trace_viewer.py list

# View a thread's conversation
uv run scripts/trace_viewer.py view THREAD_ID

# Show tool calls only
uv run scripts/trace_viewer.py tools THREAD_ID

# Search threads
uv run scripts/trace_viewer.py search "query"

# Export to JSON
uv run scripts/trace_viewer.py export THREAD_ID output.json
```

---

## Comparison: Script vs CLI

| Feature | `deep_agent_search.py` | DeepAgents CLI |
|---------|------------------------|----------------|
| Multi-turn | Custom code | Built-in |
| Streaming | No | Yes |
| Session persistence | No | Yes |
| Memory across sessions | No | Yes |
| Human-in-the-loop | No | Yes |
| Slash commands | No | `/remember`, `/clear`, etc. |
| File auto-discovery | Loads at startup | Real-time via `ls`/`glob` |
| Installation | Project dependency | Global tool |

---

## Testing Checklist

After implementation, verify:

- [x] CLI starts without errors
- [x] Skill is detected by `deepagents skills list --project`
- [ ] Agent can list files in `data/`
- [ ] Agent can search with `grep`
- [ ] Agent can read files with `read_file`
- [ ] Agent refuses to write to `data/` (skill instruction)
- [ ] Agent prompts for approval on any write attempt (HITL)
- [ ] New files added to `data/` are discoverable
- [ ] Removed files are no longer found
- [ ] Multi-turn conversations work
- [ ] Anthropic API is used (check model in response)

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Agent ignores skill instructions | Human-in-the-loop + filesystem permissions |
| GitHub Models API incompatible | Test `OPENAI_BASE_URL` approach; fallback to direct API |
| CLI doesn't respect `OPENAI_BASE_URL` | May need to patch or use alternative approach |
| Performance (no index) | Acceptable for 41 files; could add caching later |
| Stale file listings | Always run `ls`/`glob` fresh |

---

## Future Enhancements

1. **Caching**: Add optional file content caching for performance
2. **Indexing**: Build Tantivy index for large corpora (>1000 files)
3. **Custom Commands**: Add slash commands for common searches
4. **Metrics**: Track query patterns and response quality

---

## Trace Viewer

The trace viewer (`scripts/trace_viewer.py`) reads from the DeepAgents SQLite database at `~/.deepagents/sessions.db` and provides:

- **Thread listing**: See all conversation threads
- **Conversation view**: Full message history with tool calls
- **Tool summary**: Just the tool calls and results
- **Search**: Find threads containing specific content
- **Export**: Save threads as JSON for external analysis

The database uses LangGraph's checkpoint format with msgpack serialization. The trace viewer decodes this automatically.

See `DEEPAGENTS_CLI_CHEATSHEET.md` for usage examples.
