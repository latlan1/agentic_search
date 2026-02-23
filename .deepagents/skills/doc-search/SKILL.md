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
- `write_file` on any `data/` path
- `edit_file` on any `data/` path  
- `shell` commands that modify files
- `web_search` - only use local docs
- `fetch_url` - only use local docs

### Required Actions
- Always use `ls` or `glob` to check current files
- Always cite source files
- Only search within `data/` directory
