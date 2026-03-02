#!/usr/bin/env python3
"""
Tantivy Agent Search - LangGraph agent with Tantivy full-text search.

A LangGraph-based agent that uses Tantivy search/read tools for fast,
efficient documentation search. Supports multi-turn conversations via
MemorySaver checkpointer.

Key Features:
- BM25 full-text search with Reciprocal Rank Fusion (RRF)
- Two-phase search: search (preview) -> read (full content)
- Multi-turn conversation memory
- Anthropic Claude Sonnet 4 for reasoning
- Automatic index building/updating via IndexManager
- Rich markdown terminal output

Usage:
    uv run scripts/tantivy_agent_search.py "How do I create a subagent?"
    uv run scripts/tantivy_agent_search.py --interactive
    uv run scripts/tantivy_agent_search.py --sync "What is context quarantine?"
    uv run scripts/tantivy_agent_search.py --graph  # Generate PNG visualization

Environment Variables:
    ANTHROPIC_API_KEY - Your Anthropic API key
    LLM_MODEL - Model to use (default: claude-sonnet-4)
"""

import time
import uuid
from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.tools import tool
from langchain.agents import create_agent
from langchain_anthropic.middleware import AnthropicPromptCachingMiddleware
from deepagents.middleware.subagents import SubAgentMiddleware, SubAgent
from deepagents.middleware.summarization import SummarizationMiddleware
from deepagents.backends.state import StateBackend
from deepagents.middleware.patch_tool_calls import PatchToolCallsMiddleware
from helper import (
    get_anthropic_llm,
    extract_tool_calls,
    render_response,
    format_time,
    VERBOSE,
)

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich import box

from tantivy_index_manager import IndexManager
from tantivy_search import DocumentSearchIndex

load_dotenv()

# Global checkpointer for multi-turn conversations
checkpointer = MemorySaver()

_search_index: DocumentSearchIndex | None = None
_index_manager: IndexManager | None = None
_console = Console()


def get_search_index() -> DocumentSearchIndex:
    """Get or create the search index instance."""
    global _search_index, _index_manager

    if _search_index is None:
        if _index_manager is None:
            _index_manager = IndexManager()
        _index_manager.ensure_index_exists()
        _search_index = DocumentSearchIndex()

    return _search_index


def get_index_manager() -> IndexManager:
    """Get or create the index manager instance."""
    global _index_manager
    if _index_manager is None:
        _index_manager = IndexManager()
    return _index_manager


@tool
def search_docs(queries: list[str], limit: int = 5) -> str:
    """
    Search the documentation corpus for relevant documents.

    Use multiple query variations to improve recall. Results are fused using
    Reciprocal Rank Fusion (RRF) for better ranking.

    Args:
        queries: One or more search queries. Use multiple phrasings of the
                 same concept to improve results.
                 Example: ["subagent", "spawn subagent", "delegate task"]
        limit: Maximum number of results to return (default 5)

    Returns:
        A formatted list of search results with doc_id, filename, description,
        and relevance score. Use read_docs() to retrieve full document content.

    Example:
        search_docs(["create subagent", "subagent delegation", "task tool"])
    """
    index = get_search_index()
    results = index.search(queries, limit=limit)

    if not results:
        return "No results found for the given queries."

    output = f"Found {len(results)} results:\n\n"
    for r in results:
        desc = (
            r.description[:200] + "..." if len(r.description) > 200 else r.description
        )
        output += f"[doc_id={r.doc_id}] {r.filename} (score: {r.score:.4f})\n"
        if desc:
            output += f"  Description: {desc}\n"
        output += "\n"

    output += "Use read_docs(doc_ids=[...]) to read full content of relevant documents."
    return output


@tool
def read_docs(doc_ids: list[int]) -> str:
    """
    Read the full content of documents by their doc_id.

    Use this after search_docs() to retrieve the complete text of documents
    that appear relevant based on their description and filename.

    Args:
        doc_ids: List of document IDs to retrieve (from search_docs results)

    Returns:
        Full content of the requested documents, formatted with filenames
        and paths for numbered citation purposes.

    Example:
        read_docs([1, 3, 5])
    """
    index = get_search_index()
    documents = index.read(doc_ids)

    if not documents:
        return "No documents found for the given IDs."

    output = ""
    for i, doc in enumerate(documents, 1):
        output += f"\n{'='*70}\n"
        output += f"[{i}] FILE: {doc.filename}\n"
        output += f"    PATH: {doc.path}\n"
        output += f"    DOC_ID: {doc.doc_id}\n"
        output += f"{'='*70}\n\n"
        output += doc.content
        output += f"\n{'='*70}\n"

    return output


CUSTOM_TASK_DESCRIPTION = """Delegate a search task to a subagent. The subagent runs autonomously and returns a single result.

Available agents:
{available_agents}

Launch multiple agents concurrently by issuing multiple tool calls in one response. Each invocation is stateless — provide all necessary context in the description."""

SEARCH_SYSTEM_PROMPT = """You answer questions about DeepAgents and LangGraph docs by delegating to search_subagent.

**Tools:** task (delegates to search_subagent)

**search_subagent tools:** search_docs(queries, limit), read_docs(doc_ids)

**Workflow:**
1. Create 2 query variations using synonyms (e.g., "subagent" / "delegate task")
2. Delegate both IN PARALLEL using 2 task calls in ONE response
3. Each task prompt: "Search for [variation] using search_docs with multiple query phrasings, then read the top results with read_docs. Return filenames, paths, and key content."
4. Consolidate results into answer with numbered citations [1], [2]

**Citation format:**
Answer text [1]. More text [2].

---
**Sources:**
[1] [file.md](path/to/file.md)
[2] [file2.md](path/to/file2.md)"""


def create_search_agent(system_prompt):
    """
    Create an agent configured for read-only documentation search.

    Uses create_agent (langchain) directly instead of create_deep_agent to
    control the middleware stack and minimize per-request token overhead.

    Removed middleware (not needed for search):
    - TodoListMiddleware (~1,182 tokens/call — no todos needed)
    - FilesystemMiddleware (~841 tokens/call — no fs access needed)
    - MemoryMiddleware (~1,116 tokens/call — no AGENTS.md loading)

    Custom overrides:
    - task_description: ~400 chars vs default 6,914 chars (-1,500 tokens)
    - default_middleware=[]: subagents get no middleware overhead (-2,000 tokens/call)
    - general_purpose_agent=False: only search_subagent available
    - system_prompt=None on SubAgentMiddleware: skip TASK_SYSTEM_PROMPT (-535 tokens)
    """
    model = get_anthropic_llm(_console)

    search_subagent: SubAgent = {
        "name": "search_subagent",
        "description": "Searches and reads documentation using BM25 full-text search. Has search_docs and read_docs tools.",
        "system_prompt": "Search and read documents as instructed. Return filenames, paths, and key content. Be concise.",
        "tools": [search_docs, read_docs],
    }

    # Minimal middleware stack — only what's needed
    middleware = [
        SubAgentMiddleware(
            default_model=model,
            default_tools=None,
            subagents=[search_subagent],
            default_middleware=[],  # No TodoList/Filesystem/Summarization on subagents
            general_purpose_agent=False,  # Only search_subagent, no general-purpose
            task_description=CUSTOM_TASK_DESCRIPTION,  # ~400 chars vs 6,914 default
            system_prompt=None,  # Skip TASK_SYSTEM_PROMPT injection (535 tokens)
        ),
        SummarizationMiddleware(
            model=model,
            backend=StateBackend,  # Factory: Callable[[ToolRuntime], BackendProtocol]
            trigger=("tokens", 170000),
            keep=("messages", 6),
            trim_tokens_to_summarize=None,
            truncate_args_settings={
                "trigger": ("messages", 20),
                "keep": ("messages", 20),
            },
        ),
        AnthropicPromptCachingMiddleware(unsupported_model_behavior="ignore"),
        PatchToolCallsMiddleware(),
    ]

    agent = create_agent(
        model,
        system_prompt=system_prompt,
        tools=[],  # Parent only delegates via task — no direct tools
        middleware=middleware,
        checkpointer=checkpointer,
    )

    return agent.with_config({"recursion_limit": 1000})


def search(
    query: str,
    thread_id: str = "default",
    sync_first: bool = False,
    verbose: bool = False,
) -> tuple[str, list[dict], float]:
    """
    Search the documentation corpus and return an answer with citations.

    Returns:
        Tuple of (answer, elapsed_time_seconds)
    """
    start_time = time.time()

    if sync_first:
        manager = get_index_manager()
        manager.ensure_index_exists()
        added, updated, removed = manager.sync_all()
        if added + updated + removed > 0:
            _console.print(
                f"[dim]Index synced: {added} added, {updated} updated, {removed} removed[/dim]"
            )
            global _search_index
            _search_index = None

    agent = create_search_agent(SEARCH_SYSTEM_PROMPT)
    result = agent.invoke(
        {
            "messages": [{"role": "user", "content": query}],
        },
        config={"configurable": {"thread_id": thread_id}},
    )

    elapsed_time = time.time() - start_time

    # Extract tool calls for verbose mode
    tool_calls = extract_tool_calls(result["messages"]) if verbose else []

    # Extract the final response
    return result["messages"][-1].content, tool_calls, elapsed_time


def interactive_session(sync_first: bool = False, verbose: bool = True):
    """Run an interactive multi-turn conversation session."""
    import uuid

    if sync_first:
        manager = get_index_manager()
        manager.ensure_index_exists()
        added, updated, removed = manager.sync_all()
        _console.print(
            f"[dim]Index synced: {added} added, {updated} updated, {removed} removed[/dim]"
        )
    else:
        get_index_manager().ensure_index_exists()

    global VERBOSE
    VERBOSE = verbose

    thread_id = str(uuid.uuid4())
    _console.print(
        Panel.fit(
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
    _console.print()

    while True:
        try:
            query = _console.input("[bold blue]You:[/bold blue] ").strip()
            if not query:
                continue
            if query.lower() in ("quit", "exit"):
                _console.print("[yellow]Goodbye![/yellow]")
                break
            if query.lower() == "/sync":
                manager = get_index_manager()
                added, updated, removed = manager.sync_all()
                _console.print(
                    f"[dim]Index synced: {added} added, {updated} updated, {removed} removed[/dim]"
                )
                global _search_index
                _search_index = None
                continue
            if query.lower() == "/verbose":
                VERBOSE = not VERBOSE
                _console.print(
                    f"[yellow]Verbose mode: {'ON' if VERBOSE else 'OFF'}[/yellow]"
                )
                continue

            _console.print()
            with _console.status("[bold green]Searching...[/bold green]"):
                answer, tool_calls, elapsed = search(
                    query, thread_id=thread_id, verbose=VERBOSE
                )
            render_response(answer, _console, tool_calls)
            _console.print(f"[dim]Completed in {format_time(elapsed)}[/dim]")
            _console.print()
        except KeyboardInterrupt:
            _console.print("\n[yellow]Goodbye![/yellow]")
            break


def main():
    """CLI entry point."""
    import argparse

    global VERBOSE

    parser = argparse.ArgumentParser(
        description="Tantivy RAG Agent Search - LangGraph agent with full-text search"
    )
    parser.add_argument(
        "query",
        nargs="*",
        help="Search query (omit for interactive mode with --interactive)",
    )
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Run in interactive multi-turn mode",
    )
    parser.add_argument(
        "--sync",
        "-s",
        action="store_true",
        help="Sync index with current files before searching",
    )
    parser.add_argument(
        "--thread", default="default", help="Thread ID for conversation continuity"
    )

    args = parser.parse_args()

    if args.interactive:
        interactive_session(sync_first=args.sync)
    elif args.query:
        query = " ".join(args.query)
        _console.print(f"[bold]Searching for:[/bold] {query}")
        _console.print()
        with _console.status("[bold green]Searching...[/bold green]"):
            answer, tool_calls, elapsed = search(
                query, thread_id=args.thread, sync_first=args.sync, verbose=VERBOSE
            )
        render_response(answer, _console, tool_calls)
        _console.print(f"[dim]Completed in {format_time(elapsed)}[/dim]")
        _console.print()
    else:
        parser.print_help()
        _console.print("\n[bold]Examples:[/bold]")
        _console.print(
            "  uv run scripts/tantivy_agent_search.py 'How do I create a subagent?'"
        )
        _console.print("  uv run scripts/tantivy_agent_search.py --interactive")
        _console.print(
            "  uv run scripts/tantivy_agent_search.py --sync 'What is memory persistence?'"
        )


if __name__ == "__main__":
    main()
