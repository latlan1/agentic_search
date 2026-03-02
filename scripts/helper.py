# LLM Model Configuration
# Fallback model if LLM_MODEL env var is not set or invalid
import os
import re
from pathlib import Path
from deepagents.backends.utils import create_file_data
from langchain_anthropic import ChatAnthropic

from langchain_core.messages import AIMessage, ToolMessage
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from rich.console import Console

FALLBACK_MODEL = "claude-sonnet-4-5-20250929"  # Claude Sonnet 4.5

# Read-only tools - filter out write_file and edit_file
READ_ONLY_TOOLS = {"ls", "read_file", "grep", "glob", "write_todos", "task"}

# Paths to documentation
DOCS_DIRS = {
    "deepagents": Path("data/deepagents_raw_md"),
    "langgraph": Path("data/langgraph_raw_md"),
}

# Virtual filesystem paths
VIRTUAL_ROOT = "/docs"

# Global verbose flag
VERBOSE = True


def get_model_name() -> str:
    """
    Get the LLM model name from environment with fallback.

    Priority:
    1. LLM_MODEL environment variable (shared across all approaches)
    2. FALLBACK_MODEL constant (hardcoded fallback)
    """
    model = os.getenv("LLM_MODEL") or FALLBACK_MODEL
    return model


def filter_tools_read_only(tools: list) -> list:
    """
    Filter the standard FilesystemMiddleware tools to only include read-only operations.
    This removes write_file and edit_file from the available tools.
    """
    return [t for t in tools if t.name in READ_ONLY_TOOLS]


def get_anthropic_llm(console):
    """
    Create a ChatAnthropic instance configured for Claude Sonnet 4.5.

    Model resolution priority:
    1. LLM_MODEL env var (shared across all approaches)
    2. FALLBACK_MODEL constant (hardcoded fallback)
    """
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY environment variable is required. "
            "Get your API key at https://console.anthropic.com/settings/keys"
        )

    model_name = get_model_name()
    console.print(f"[dim]Using model: {model_name}[/dim]")
    return ChatAnthropic(model_name=model_name)  # type: ignore[call-arg]


def display_tool_call(
    tool_name: str, tool_input: dict, tool_output: str, call_number: int, console
):
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

    console.print(
        Panel(
            table,
            title=f"[bold blue]Tool Call #{call_number}[/bold blue]",
            border_style="blue",
            padding=(0, 1),
        )
    )

    # Show output in a separate panel
    console.print(
        Panel(
            Text(output_display, style="dim"),
            title="[dim]Output[/dim]",
            border_style="dim",
            padding=(0, 1),
        )
    )
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
        if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append(
                    {
                        "name": tc["name"],
                        "input": tc["args"],
                        "output": tool_results.get(tc["id"], ""),
                    }
                )

    return tool_calls


def get_real_path(virtual_path: str) -> Path:
    """Convert a virtual path back to a real filesystem path."""
    # /docs/deepagents/file.md -> data/deepagents_raw_md/file.md
    if virtual_path.startswith(VIRTUAL_ROOT):
        rest = virtual_path[len(VIRTUAL_ROOT) + 1 :]  # Remove /docs/
        parts = rest.split("/", 1)
        if len(parts) == 2:
            corpus, filename = parts
            if corpus in DOCS_DIRS:
                return DOCS_DIRS[corpus] / filename
    return Path(virtual_path)


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
    pattern = r"\[([^\]]+)\]\((/docs/[^)]+)\)"
    return re.sub(pattern, replace_path, response)


def render_response(
    response: str, console: Console, tool_calls: list[dict] | None = None
):
    """Render the response with rich markdown formatting in a nice box."""
    # Get base path for making citations clickable
    base_path = Path.cwd()

    # Make citations clickable
    response = make_citations_clickable(response, base_path)

    # Show tool calls if verbose mode and we have them
    if VERBOSE and tool_calls:
        console.print()
        console.print(
            Panel(
                "[bold]Tool Execution Trace[/bold]",
                style="bold yellow",
                box=box.DOUBLE,
            )
        )
        console.print()

        for i, tc in enumerate(tool_calls, 1):
            display_tool_call(tc["name"], tc["input"], tc["output"], i, console)

    # Render the main response in a panel
    console.print()
    console.print(
        Panel(
            Markdown(response),
            title="[bold green]Answer[/bold green]",
            border_style="green",
            padding=(1, 2),
            box=box.DOUBLE,
        )
    )


def load_documentation_files(console) -> dict[str, dict]:
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
            console.print(
                f"[yellow]Warning:[/yellow] {docs_dir} does not exist, skipping"
            )
            continue

        for md_file in sorted(docs_dir.glob("*.md")):
            # Create virtual path: /docs/deepagents/deepagents-overview.md
            virtual_path = f"{VIRTUAL_ROOT}/{corpus_name}/{md_file.name}"
            content = md_file.read_text(encoding="utf-8", errors="ignore")
            # Use create_file_data to format properly for StateBackend
            files[virtual_path] = create_file_data(content)

    return files


def format_time(seconds: float) -> str:
    """Format elapsed time in a human-readable way."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"{minutes}m {remaining_seconds:.1f}s"
