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

import os
import re
import sys
from pathlib import Path
from typing import Any
from dotenv import load_dotenv

from deepagents import create_deep_agent
from deepagents.backends import StateBackend
from deepagents.backends.utils import create_file_data
from deepagents.middleware.filesystem import FilesystemMiddleware
from langgraph.checkpoint.memory import MemorySaver
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, ToolMessage

# Rich console for beautiful terminal output
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

load_dotenv()

# Initialize rich console
console = Console()

# Anthropic Claude configuration
DEFAULT_MODEL = "claude-sonnet-4-20250514"  # Claude Sonnet 4.5

# Paths to documentation
DOCS_DIRS = {
    "deepagents": Path("data/deepagents_raw_md"),
    "langgraph": Path("data/langgraph_raw_md"),
}

# Virtual filesystem paths
VIRTUAL_ROOT = "/docs"

# Read-only tools - filter out write_file and edit_file
READ_ONLY_TOOLS = {"ls", "read_file", "grep", "glob"}

# Global verbose flag
VERBOSE = True


def load_documentation_files() -> dict[str, dict]:
    """
    Load all markdown files from documentation directories into a dictionary
    suitable for seeding the StateBackend.
    
    Returns:
        Dictionary mapping virtual paths to file data objects.
        Example: {"/docs/deepagents/overview.md": {"content": "# Overview\n...", ...}}
    """
    files = {}
    
    for corpus_name, docs_dir in DOCS_DIRS.items():
        if not docs_dir.exists():
            console.print(f"[yellow]Warning:[/yellow] {docs_dir} does not exist, skipping")
            continue
        
        for md_file in sorted(docs_dir.glob("*.md")):
            # Create virtual path: /docs/deepagents/deepagents-overview.md
            virtual_path = f"{VIRTUAL_ROOT}/{corpus_name}/{md_file.name}"
            content = md_file.read_text(encoding="utf-8", errors="ignore")
            # Use create_file_data to format properly for StateBackend
            files[virtual_path] = create_file_data(content)
    
    return files


def get_real_path(virtual_path: str) -> Path:
    """Convert a virtual path back to a real filesystem path."""
    # /docs/deepagents/file.md -> data/deepagents_raw_md/file.md
    if virtual_path.startswith(VIRTUAL_ROOT):
        rest = virtual_path[len(VIRTUAL_ROOT)+1:]  # Remove /docs/
        parts = rest.split("/", 1)
        if len(parts) == 2:
            corpus, filename = parts
            if corpus in DOCS_DIRS:
                return DOCS_DIRS[corpus] / filename
    return Path(virtual_path)


# System prompt for the search agent
SEARCH_SYSTEM_PROMPT = """You are an expert documentation search agent. Your job is to answer questions about the DeepAgents and LangGraph documentation.

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


# Global checkpointer for multi-turn conversations
checkpointer = MemorySaver()


def filter_tools_read_only(tools: list) -> list:
    """
    Filter the standard FilesystemMiddleware tools to only include read-only operations.
    This removes write_file and edit_file from the available tools.
    """
    return [t for t in tools if t.name in READ_ONLY_TOOLS]


def get_anthropic_llm():
    """
    Create a ChatAnthropic instance configured for Claude Sonnet 4.5.
    """
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY environment variable is required. "
            "Get your API key at https://console.anthropic.com/settings/keys"
        )
    
    model_name = os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL)
    os.environ["ANTHROPIC_API_KEY"] = anthropic_api_key
    
    return ChatAnthropic(model=model_name)


def create_search_agent(files: dict[str, dict]):
    """
    Create a DeepAgent configured for read-only documentation search.
    """
    model = get_anthropic_llm()
    
    agent = create_deep_agent(
        model=model,
        system_prompt=SEARCH_SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )
    
    if hasattr(agent, 'tools'):
        agent.tools = filter_tools_read_only(agent.tools)
    
    return agent, files


def display_tool_call(tool_name: str, tool_input: dict, tool_output: str, call_number: int):
    """Display a tool call in a nice formatted box."""
    # Create a table for the tool call
    table = Table(show_header=False, box=box.ROUNDED, expand=True, padding=(0, 1))
    table.add_column("Key", style="cyan", width=12)
    table.add_column("Value", style="white")
    
    table.add_row("Tool", Text(tool_name, style="bold green"))
    
    # Format input nicely
    for key, value in tool_input.items():
        if isinstance(value, str) and len(value) > 80:
            value = value[:77] + "..."
        table.add_row(f"  {key}", str(value))
    
    # Truncate output for display
    output_display = tool_output
    if len(output_display) > 500:
        output_display = output_display[:497] + "..."
    
    console.print(Panel(
        table,
        title=f"[bold blue]Tool Call #{call_number}[/bold blue]",
        border_style="blue",
        padding=(0, 1),
    ))
    
    # Show output in a separate panel
    console.print(Panel(
        Text(output_display, style="dim"),
        title="[dim]Output[/dim]",
        border_style="dim",
        padding=(0, 1),
    ))
    console.print()


def extract_tool_calls(messages: list) -> list[dict]:
    """Extract tool calls and their results from message history."""
    tool_calls = []
    tool_results = {}
    
    # First pass: collect all tool results
    for msg in messages:
        if isinstance(msg, ToolMessage):
            tool_results[msg.tool_call_id] = msg.content
    
    # Second pass: match tool calls with results
    for msg in messages:
        if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append({
                    "name": tc["name"],
                    "input": tc["args"],
                    "output": tool_results.get(tc["id"], ""),
                })
    
    return tool_calls


def make_citations_clickable(response: str, base_path: Path) -> str:
    """
    Convert virtual paths in citations to clickable file:// URLs.
    
    Transforms: [file.md](/docs/corpus/file.md)
    To: [file.md](file:///absolute/path/to/file.md)
    """
    def replace_path(match):
        text = match.group(1)
        virtual_path = match.group(2)
        real_path = get_real_path(virtual_path)
        if real_path.exists():
            absolute_path = real_path.resolve()
            return f"[{text}](file://{absolute_path})"
        return match.group(0)
    
    # Match markdown links with virtual paths
    pattern = r'\[([^\]]+)\]\((/docs/[^)]+)\)'
    return re.sub(pattern, replace_path, response)


def render_response(response: str, tool_calls: list[dict] | None = None):
    """Render the response with rich markdown formatting in a nice box."""
    # Get base path for making citations clickable
    base_path = Path.cwd()
    
    # Make citations clickable
    response = make_citations_clickable(response, base_path)
    
    # Show tool calls if verbose mode and we have them
    if VERBOSE and tool_calls:
        console.print()
        console.print(Panel(
            "[bold]Tool Execution Trace[/bold]",
            style="bold yellow",
            box=box.DOUBLE,
        ))
        console.print()
        
        for i, tc in enumerate(tool_calls, 1):
            display_tool_call(tc["name"], tc["input"], tc["output"], i)
    
    # Render the main response in a panel
    console.print()
    console.print(Panel(
        Markdown(response),
        title="[bold green]Answer[/bold green]",
        border_style="green",
        padding=(1, 2),
        box=box.DOUBLE,
    ))


def search(query: str, thread_id: str = "default", verbose: bool = False) -> tuple[str, list[dict]]:
    """
    Search the documentation corpus and return an answer with citations.
    
    Args:
        query: The user's question
        thread_id: Conversation thread ID for multi-turn memory
        verbose: If True, return tool calls for display
        
    Returns:
        Tuple of (answer string, list of tool calls)
    """
    # Load documentation into virtual filesystem
    files = load_documentation_files()
    
    if not files:
        return "Error: No documentation files found. Please check the data/ directory.", []
    
    console.print(f"[dim]Loaded {len(files)} documentation files into virtual filesystem[/dim]")
    
    # Create the agent
    agent, files = create_search_agent(files)
    
    # Invoke with the documentation files seeded into state
    result = agent.invoke(
        {
            "messages": [{"role": "user", "content": query}],
            "files": files,
        },
        config={"configurable": {"thread_id": thread_id}}
    )
    
    # Extract tool calls for verbose mode
    tool_calls = extract_tool_calls(result["messages"]) if verbose else []
    
    # Extract the final response
    return result["messages"][-1].content, tool_calls


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
    
    console.print(Panel(
        f"""[bold]Deep Agent Search - Interactive Mode[/bold]

[cyan]Session ID:[/cyan] {thread_id}

[yellow]How it works:[/yellow]
- All {sum(len(list(d.glob('*.md'))) for d in DOCS_DIRS.values() if d.exists())} docs loaded into virtual filesystem
- Conversation memory persists across queries
- Agent uses grep/ls/read_file to search (no chunking)
- Type [bold]/verbose[/bold] to toggle tool call visibility
- Type [bold]quit[/bold] or [bold]exit[/bold] to end session""",
        title="[bold green]Session Started[/bold green]",
        border_style="green",
        box=box.DOUBLE,
    ))
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
                console.print(f"[yellow]Verbose mode: {'ON' if VERBOSE else 'OFF'}[/yellow]")
                continue
            
            console.print()
            with console.status("[bold green]Searching...[/bold green]"):
                answer, tool_calls = search(query, thread_id=thread_id, verbose=VERBOSE)
            
            render_response(answer, tool_calls)
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
        console.print(Panel(
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
        ))
        sys.exit(1)
    
    # Check for flags
    if "--verbose" in args or "-v" in args:
        VERBOSE = True
        args = [a for a in args if a not in ("--verbose", "-v")]
    
    if "--interactive" in args or "-i" in args:
        interactive_session(verbose=VERBOSE)
        return
    
    query = " ".join(args)
    
    console.print(Panel(
        f"[bold]Query:[/bold] {query}",
        border_style="blue",
    ))
    console.print()
    
    with console.status("[bold green]Searching documentation...[/bold green]"):
        answer, tool_calls = search(query, verbose=VERBOSE)
    
    render_response(answer, tool_calls)


if __name__ == "__main__":
    main()
