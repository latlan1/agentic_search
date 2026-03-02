#!/usr/bin/env python3
"""
Deep Agent Search - Agentic search over documentation using DeepAgents.

This implementation uses DeepAgents' built-in file system tools (ls, read_file,
grep, glob) with a StateBackend to create a virtual filesystem containing the
markdown documentation. The agent can search and read files but cannot modify them.

Key Features:
- Read-only access to documentation (write_file and edit_file filtered out)
- Virtual filesystem via StateBackend
- Multi-query search using grep and glob
- Answers with citations (numbered, clickable)
- Multi-turn conversation memory via checkpointer
- Anthropic Claude Sonnet 4.5 as the LLM
- Rich markdown rendering in terminal
- Verbose mode to see tool calls

Usage:
    uv run scripts/deep_agent_search.py "How do I create a subagent?"
    uv run scripts/deep_agent_search.py --interactive
    uv run scripts/deep_agent_search.py --verbose "What is a skill?"

Environment Variables:
    ANTHROPIC_API_KEY - Your Anthropic API key (required)
"""

import sys
import time
from dotenv import load_dotenv

from langgraph.checkpoint.memory import MemorySaver
from deepagents import create_deep_agent

# from deepagents.backends import StateBackend
# from deepagents.middleware.filesystem import FilesystemMiddleware

from helper import (
    get_anthropic_llm,
    load_documentation_files,
    extract_tool_calls,
    render_response,
    format_time,
    VERBOSE,
)

# Rich console for beautiful terminal output
# type: ignore comments suppress LSP false positives for runtime-valid imports
from rich.console import Console
from rich import box
from rich.panel import Panel

load_dotenv()

# Global checkpointer for multi-turn conversations
checkpointer = MemorySaver()

# Initialize rich console
console = Console()

# System prompt for the search agent
SEARCH_SYSTEM_PROMPT = """You are an expert documentation search agent. Your job is to answer questions about the DeepAgents and LangGraph documentation. Spawn & delegate to multiple parallel subagents to search through multiple markdown files at once using the tools at your disposal.

## Available Documentation

You have access to a virtual filesystem containing markdown documentation:
- `/docs/deepagents/` - DeepAgents library documentation (12 files)
- `/docs/langgraph/` - LangGraph framework documentation (29 files)

## Available Tools

You have access to these READ-ONLY file system tools:
- `ls(path)` - List files in a directory
- `read_file(file_path)` - Read the contents of a file
- `grep(pattern, path)` - Search for a regex pattern in files
- `glob(pattern, path)` - Find files matching a glob pattern
- `write_todos(content)` - Add a TODO item to your internal list (for planning, not for file writing)
- `task(description)` - Spawn a subagent to execute a task to your internal list (for planning)

## Search Strategy

1. **Start broad**: Use `grep` to search for keywords, or `ls("/docs/")` to see available sections
2. **Handle no results**: If grep returns no matches, try:
   - Different keywords or synonyms
   - Broader patterns (e.g., "memory" instead of "long-term memory")
   - Use `ls` to browse available files manually
3. **Read promising files**: Use `read_file` to read the full content of relevant documents
4. **Try multiple approaches**: If first search fails, iterate with different queries

## Handling Edge Cases

- If grep returns 0 results: Try alternative search terms or browse with ls
- If a file doesn't exist: Check the path with ls first
- If content seems wrong: Read a different file that might be more relevant
- Always verify your findings before synthesizing the answer

## Response Format

Your response MUST follow this exact format:

1. **Answer Section**: Provide a clear, comprehensive answer using markdown formatting
2. **Citations Section**: At the END of your response, include a numbered list of all sources:

```
---
## Sources

1. [deepagents-subagents.md](/docs/deepagents/deepagents-subagents.md) - Description of what you found
2. [langgraph-persistence.md](/docs/langgraph/langgraph-persistence.md) - Description of what you found
```

## Important Guidelines

- Search multiple files if needed for a complete answer
- Include code examples when they help explain concepts
- ALWAYS end with a numbered Sources section listing every file you referenced
- Use the full virtual path in citations for clickability
- If no relevant information is found after multiple attempts, say so clearly
"""


def create_search_agent(system_prompt):
    """
    Create a DeepAgent configured for read-only documentation search.
    """
    model = get_anthropic_llm(console)

    agent = create_deep_agent(
        model=model,
        system_prompt=system_prompt,
        checkpointer=checkpointer,
    )

    # Filter out write tools from the agent's available tools
    # The agent object has a 'tools' attribute at runtime that LSP doesn't recognize
    if hasattr(agent, "tools"):
        agent.tools = filter_tools_read_only(agent.tools)  # type: ignore[attr-defined]

    return agent


def search(
    query: str, thread_id: str = "default", verbose: bool = False
) -> tuple[str, list[dict], float]:
    """
    Search the documentation corpus and return an answer with citations.

    Args:
        query: The user's question
        thread_id: Conversation thread ID for multi-turn memory
        verbose: If True, return tool calls for display

    Returns:
        Tuple of (answer string, list of tool calls, elapsed time in seconds)
    """
    start_time = time.time()

    # Load documentation into virtual filesystem
    files = load_documentation_files(console)

    if not files:
        return (
            "Error: No documentation files found. Please check the data/ directory.",
            [],
            0.0,
        )

    console.print(
        f"[dim]Loaded {len(files)} documentation files into virtual filesystem[/dim]"
    )

    # Create the agent
    agent = create_search_agent(SEARCH_SYSTEM_PROMPT)

    # Invoke with the documentation files seeded into state
    result = agent.invoke(
        {
            "messages": [{"role": "user", "content": query}],
            "files": files,
        },
        config={"configurable": {"thread_id": thread_id}},
    )

    elapsed_time = time.time() - start_time

    # Extract tool calls for verbose mode
    tool_calls = extract_tool_calls(result["messages"]) if verbose else []

    # Extract the final response
    return result["messages"][-1].content, tool_calls, elapsed_time


def interactive_session(verbose: bool = True):
    """
    Run an interactive multi-turn conversation session.

    How Interactive Mode Works:
    --------------------------
    1. Documents are loaded ONCE into a virtual filesystem at session start
    2. A unique thread_id is created for the session
    3. LangGraph's MemorySaver checkpointer stores conversation history
    4. Each query reuses the same thread_id, so the agent remembers context
    5. The agent can refer back to previous questions/answers
    6. No document chunking - full files are available via read_file tool

    The agent iterates by:
    - Using grep/glob to find relevant files (doesn't load content)
    - Calling read_file only for files it wants to examine
    - If no results, the system prompt instructs it to try alternatives
    """
    import uuid

    global VERBOSE
    VERBOSE = verbose

    thread_id = str(uuid.uuid4())

    console.print(
        Panel(
            f"""[bold]Deep Agent Search - Interactive Mode[/bold]

[cyan]Session ID:[/cyan] {thread_id}

[yellow]How it works:[/yellow]
- Type [bold]/verbose[/bold] to toggle tool call visibility
- Type [bold]quit[/bold] or [bold]exit[/bold] to end session""",
            title="[bold green]Session Started[/bold green]",
            border_style="green",
            box=box.DOUBLE,
        )
    )
    console.print()

    while True:
        try:
            query = console.input("[bold cyan]You:[/bold cyan] ").strip()
            if not query:
                continue
            if query.lower() in ("quit", "exit"):
                console.print("[yellow]Goodbye![/yellow]")
                break
            if query.lower() == "/verbose":
                VERBOSE = not VERBOSE
                console.print(
                    f"[yellow]Verbose mode: {'ON' if VERBOSE else 'OFF'}[/yellow]"
                )
                continue

            console.print()
            with console.status("[bold green]Searching...[/bold green]"):
                answer, tool_calls, elapsed = search(
                    query, thread_id=thread_id, verbose=VERBOSE
                )

            render_response(answer, console, tool_calls)
            console.print(f"[dim]Completed in {format_time(elapsed)}[/dim]")
            console.print()

        except KeyboardInterrupt:
            console.print("\n[yellow]Goodbye![/yellow]")
            break


def main():
    """CLI entry point."""
    global VERBOSE

    # Parse arguments
    args = sys.argv[1:]

    if not args:
        console.print(
            Panel(
                """[bold]Usage:[/bold]
  uv run scripts/deep_agent_search.py '<query>'
  uv run scripts/deep_agent_search.py --interactive
  uv run scripts/deep_agent_search.py --verbose '<query>'

[bold]Examples:[/bold]
  uv run scripts/deep_agent_search.py 'How do I create a subagent?'
  uv run scripts/deep_agent_search.py --verbose 'What is context quarantine?'
  uv run scripts/deep_agent_search.py --interactive

[bold]Flags:[/bold]
  --interactive, -i    Multi-turn conversation mode
  --verbose, -v        Show tool calls and results""",
                title="[bold]Deep Agent Search[/bold]",
                border_style="blue",
            )
        )
        sys.exit(1)

    # Check for flags
    if "--verbose" in args or "-v" in args:
        VERBOSE = True
        args = [a for a in args if a not in ("--verbose", "-v")]

    if "--interactive" in args or "-i" in args:
        interactive_session(verbose=VERBOSE)
        return

    query = " ".join(args)

    console.print(
        Panel(
            f"[bold]Query:[/bold] {query}",
            border_style="blue",
        )
    )
    console.print()

    with console.status("[bold green]Searching documentation...[/bold green]"):
        answer, tool_calls, elapsed = search(query, verbose=VERBOSE)

    render_response(answer, console, tool_calls)
    console.print(f"\n[dim]Completed in {format_time(elapsed)}[/dim]")


if __name__ == "__main__":
    main()
