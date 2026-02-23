# Documentation Search Agent

This agent searches and answers questions about DeepAgents and LangGraph documentation.

## LLM Model Configuration

**Required Model**: Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`)

This approach uses the DeepAgents CLI which reads the model from environment variables:
- Set `LLM_MODEL=claude-sonnet-4-5-20250929` in your `.env` file
- Or use the `--model` flag: `deepagents --model claude-sonnet-4-5-20250929`

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
