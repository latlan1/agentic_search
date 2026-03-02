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

import os
import sys
import time
import uuid
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

sys.path.insert(0, str(Path(__file__).parent))
from tantivy_index_manager import IndexManager
from tantivy_search import DocumentSearchIndex

load_dotenv()

# =============================================================================
# LLM Model Configuration
# =============================================================================
# Fallback model if LLM_MODEL env var is not set or invalid
FALLBACK_MODEL = "claude-sonnet-4-5-20250929"  # Claude Sonnet 4.5


def get_model_name() -> str:
    """
    Get the LLM model name from environment with fallback.

    Priority:
    1. LLM_MODEL environment variable (shared across all approaches)
    3. FALLBACK_MODEL constant (hardcoded fallback)
    """
    model = os.getenv("LLM_MODEL") or FALLBACK_MODEL
    return model


_search_index: DocumentSearchIndex | None = None
_index_manager: IndexManager | None = None
_checkpointer = MemorySaver()
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
def search_docs(queries: list[str], limit: int = 10) -> str:
    """
    Search the documentation corpus for relevant documents.

    Use multiple query variations to improve recall. Results are fused using
    Reciprocal Rank Fusion (RRF) for better ranking.

    Args:
        queries: One or more search queries. Use multiple phrasings of the
                 same concept to improve results.
                 Example: ["subagent", "spawn subagent", "delegate task"]
        limit: Maximum number of results to return (default 10)

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


SYSTEM_PROMPT = """You are an expert documentation search agent. Your job is to answer questions about the DeepAgents and LangGraph documentation using full-text search.

## Available Tools

1. **search_docs(queries, limit)**: Search the documentation index.
   - Use multiple query variations for better recall
   - Returns doc_id, filename, description, and score
   - Example: search_docs(["subagent", "delegate task", "spawn agent"], limit=5)

2. **read_docs(doc_ids)**: Read full document content by ID.
   - Use after search_docs to get complete text
   - Example: read_docs([1, 3])

## Search Strategy

1. **Formulate multiple queries**: Think of different ways to phrase the question
   - Synonyms: "subagent" vs "child agent" vs "delegate"
   - Concepts: "memory" vs "persistence" vs "state storage"

2. **Review search results**: Look at filenames and descriptions to identify relevant docs

3. **Read promising documents**: Use read_docs() to get full content

4. **Synthesize answer**: Combine information from multiple sources

## Citation Format (IMPORTANT)

You MUST use numbered citations in your responses. Format:

1. At the end of your response, include a "Sources" section with numbered references
2. In your answer text, reference sources using superscript-style numbers like [1], [2], etc.
3. Each source should include the filename as a clickable link

Example response format:
```
Subagents allow you to delegate tasks to specialized agents [1]. You can create them using the `task` tool with context isolation [2].

---
**Sources:**
[1] [deepagents-subagents.md](data/deepagents_raw_md/deepagents-subagents.md)
[2] [deepagents-context.md](data/deepagents_raw_md/deepagents-context.md)
```

## Important Guidelines

- Use 2-4 query variations in search_docs() to improve recall
- Only read documents that seem relevant based on descriptions
- Prefer specific, actionable information over general summaries
- Include code examples when they help explain concepts
- ALWAYS use numbered citations [1], [2], etc. with a Sources section at the end
"""


def get_llm() -> ChatAnthropic:
    """
    Create a ChatAnthropic instance.

    Model resolution priority:
    1. LLM_MODEL env var (shared across all approaches)
    2. FALLBACK_MODEL constant (hardcoded fallback)
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY environment variable is required. "
            "Get your API key from https://console.anthropic.com/settings/keys"
        )

    model_name = get_model_name()

    return ChatAnthropic(
        model=model_name,  # type: ignore[call-arg]
        api_key=api_key,  # type: ignore[call-arg]
    )


def create_agent():
    """Create a LangGraph agent with search/read tools."""
    llm = get_llm()
    tools = [search_docs, read_docs]
    llm_with_tools = llm.bind_tools(tools)

    def agent_node(state: MessagesState) -> dict:
        """Process messages and generate response or tool calls."""
        messages = state["messages"]

        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(messages)

        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def should_continue(state: MessagesState) -> Literal["tools", "__end__"]:
        """Determine whether to call tools or end."""
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:  # type: ignore[union-attr]
            return "tools"
        return END  # type: ignore[return-value]

    workflow = StateGraph(MessagesState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(tools))

    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges(
        "agent", should_continue, {"tools": "tools", END: END}
    )
    workflow.add_edge("tools", "agent")

    return workflow.compile(checkpointer=_checkpointer)


def get_graph_for_visualization():
    """Create a minimal agent graph for visualization (no checkpointer)."""
    llm = get_llm()
    tools = [search_docs, read_docs]
    llm_with_tools = llm.bind_tools(tools)

    def agent_node(state: MessagesState) -> dict:
        messages = state["messages"]
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(messages)
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def should_continue(state: MessagesState) -> Literal["tools", "__end__"]:
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:  # type: ignore[union-attr]
            return "tools"
        return END  # type: ignore[return-value]

    workflow = StateGraph(MessagesState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(tools))

    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges(
        "agent", should_continue, {"tools": "tools", END: END}
    )
    workflow.add_edge("tools", "agent")

    return workflow.compile()


def generate_graph_png(output_path: str = "langgraph_visualization.png") -> str:
    """Generate a PNG visualization of the LangGraph workflow."""
    graph = get_graph_for_visualization()
    drawable = graph.get_graph()
    png_data = drawable.draw_mermaid_png()

    with open(output_path, "wb") as f:
        f.write(png_data)

    return output_path


def format_time(seconds: float) -> str:
    """Format time duration as minutes and seconds."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.1f}s"


def search(
    query: str, thread_id: str = "default", sync_first: bool = False
) -> tuple[str, float]:
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

    agent = create_agent()
    result = agent.invoke(
        {"messages": [HumanMessage(content=query)]},
        config={"configurable": {"thread_id": thread_id}},
    )

    elapsed = time.time() - start_time

    for message in reversed(result["messages"]):
        if isinstance(message, AIMessage) and message.content:
            content = message.content
            # Handle case where content might be a list (multi-part response)
            if isinstance(content, list):
                content = str(content)
            return content, elapsed

    return "No answer generated.", elapsed


def print_response(answer: str, elapsed: float) -> None:
    """Print the response with rich markdown formatting and timing."""
    _console.print()
    _console.print(Panel(Markdown(answer), title="Response", border_style="green"))
    _console.print()
    _console.print(f"[dim]Time taken: {format_time(elapsed)}[/dim]")


def interactive_session(sync_first: bool = False):
    """Run an interactive multi-turn conversation session."""
    if sync_first:
        manager = get_index_manager()
        manager.ensure_index_exists()
        added, updated, removed = manager.sync_all()
        _console.print(
            f"[dim]Index synced: {added} added, {updated} updated, {removed} removed[/dim]"
        )
    else:
        get_index_manager().ensure_index_exists()

    thread_id = str(uuid.uuid4())
    _console.print(
        Panel.fit(
            f"[bold]Tantivy Agent Search - Interactive Mode[/bold]\n\n"
            f"Session ID: [cyan]{thread_id}[/cyan]\n"
            f"Type [green]'quit'[/green] or [green]'exit'[/green] to end the session.\n"
            f"Type [green]'/sync'[/green] to sync the index with current files.",
            border_style="blue",
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

            _console.print()
            with _console.status("[bold green]Searching...[/bold green]"):
                answer, elapsed = search(query, thread_id=thread_id)
            print_response(answer, elapsed)
            _console.print()
        except KeyboardInterrupt:
            _console.print("\n[yellow]Goodbye![/yellow]")
            break


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Tantivy Agent Search - LangGraph agent with full-text search"
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
    parser.add_argument(
        "--graph",
        "-g",
        nargs="?",
        const="langgraph_visualization.png",
        metavar="OUTPUT",
        help="Generate PNG visualization of the LangGraph workflow (default: langgraph_visualization.png)",
    )
    parser.add_argument(
        "--version",
        "-v",
        action="store_true",
        help="Show version and model information",
    )

    args = parser.parse_args()

    if args.version:
        model = get_model_name()
        _console.print(f"[bold]Tantivy Agent Search[/bold]")
        _console.print(f"Model: [cyan]{model}[/cyan]")
        _console.print(f"Fallback Model: [dim]{FALLBACK_MODEL}[/dim]")
        return

    if args.graph:
        output_path = generate_graph_png(args.graph)
        _console.print(f"[green]Graph visualization saved to:[/green] {output_path}")
        return

    if args.interactive:
        interactive_session(sync_first=args.sync)
    elif args.query:
        query = " ".join(args.query)
        _console.print(f"[bold]Searching for:[/bold] {query}")
        _console.print()
        with _console.status("[bold green]Searching...[/bold green]"):
            answer, elapsed = search(query, thread_id=args.thread, sync_first=args.sync)
        print_response(answer, elapsed)
    else:
        parser.print_help()
        _console.print("\n[bold]Examples:[/bold]")
        _console.print(
            "  uv run scripts/tantivy_lg_agent_search.py 'How do I create a subagent?'"
        )
        _console.print("  uv run scripts/tantivy_lg_agent_search.py --interactive")
        _console.print(
            "  uv run scripts/tantivy_lg_agent_search.py --sync 'What is memory persistence?'"
        )
        _console.print("  uv run scripts/tantivy_lg_agent_search.py --graph")
        _console.print("  uv run scripts/tantivy_lg_agent_search.py --version")


if __name__ == "__main__":
    main()
