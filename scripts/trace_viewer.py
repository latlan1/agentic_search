#!/usr/bin/env python3
import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import msgpack
from msgpack import ExtType

DEEPAGENTS_DIR = Path.home() / ".deepagents"
SESSIONS_DB = DEEPAGENTS_DIR / "sessions.db"


def decode_ext_type(code: int, data: bytes) -> dict:
    if code == 5:
        try:
            unpacked = msgpack.unpackb(data, raw=False, ext_hook=decode_ext_type)
            if isinstance(unpacked, (list, tuple)) and len(unpacked) >= 3:
                module_path = unpacked[0] if isinstance(unpacked[0], str) else ""
                class_name = unpacked[1] if isinstance(unpacked[1], str) else ""
                obj_data = unpacked[2] if isinstance(unpacked[2], dict) else {}
                
                msg_type = "unknown"
                if "human" in class_name.lower():
                    msg_type = "human"
                elif "ai" in class_name.lower():
                    msg_type = "ai"
                elif "tool" in class_name.lower():
                    msg_type = "tool"
                elif "system" in class_name.lower():
                    msg_type = "system"
                
                result = {"type": msg_type, "_class": class_name}
                result.update(obj_data)
                return result
            return {"_unpacked": unpacked}
        except Exception as e:
            return {"_error": str(e), "_raw_preview": data[:100].hex()}
    return {"_ext_code": code, "_raw_preview": data[:50].hex()}


def get_db_connection(db_path: Path = SESSIONS_DB) -> sqlite3.Connection:
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}", file=sys.stderr)
        print("Run deepagents at least once to create the database.", file=sys.stderr)
        sys.exit(1)
    return sqlite3.connect(db_path)


def decode_blob(blob: bytes) -> dict:
    try:
        return msgpack.unpackb(blob, raw=False, ext_hook=decode_ext_type)
    except Exception:
        return {"_raw": blob.hex()[:100] + "..." if len(blob) > 50 else blob.hex()}


def list_threads(db_path: Path = SESSIONS_DB, limit: int = 20) -> None:
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT DISTINCT thread_id, COUNT(*) as checkpoint_count
        FROM checkpoints
        GROUP BY thread_id
        ORDER BY checkpoint_id DESC
        LIMIT ?
    """, (limit,))
    
    threads = cursor.fetchall()
    conn.close()
    
    if not threads:
        print("No threads found.")
        return
    
    print(f"\n{'Thread ID':<40} {'Checkpoints':>12}")
    print("-" * 54)
    for thread_id, count in threads:
        print(f"{thread_id:<40} {count:>12}")
    print()


def extract_messages_from_checkpoint(checkpoint_data: dict) -> list[dict]:
    messages = []
    channel_values = checkpoint_data.get("channel_values", {})
    
    msgs = channel_values.get("messages", [])
    if isinstance(msgs, list):
        for msg in msgs:
            if isinstance(msg, dict):
                messages.append(msg)
            elif isinstance(msg, tuple) and len(msg) >= 2:
                messages.append(msg[1] if isinstance(msg[1], dict) else {"content": str(msg)})
    
    return messages


def extract_tool_calls(message: dict) -> list[dict]:
    tool_calls = []
    
    if "tool_calls" in message:
        for tc in message.get("tool_calls", []):
            tool_calls.append({
                "name": tc.get("name", "unknown"),
                "args": tc.get("args", {}),
                "id": tc.get("id", ""),
            })
    
    if message.get("type") == "tool" or message.get("role") == "tool":
        tool_calls.append({
            "name": message.get("name", "tool_result"),
            "result": message.get("content", ""),
            "tool_call_id": message.get("tool_call_id", ""),
        })
    
    return tool_calls


def format_message(msg: dict, show_full: bool = False) -> str:
    msg_type = msg.get("type", msg.get("role", "unknown"))
    content = msg.get("content", "")
    
    if isinstance(content, list):
        text_parts = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                text_parts.append(part.get("text", ""))
        content = "\n".join(text_parts)
    
    if not show_full and len(content) > 200:
        content = content[:200] + "..."
    
    lines = [f"[{msg_type.upper()}]"]
    
    if content:
        lines.append(content)
    
    tool_calls = extract_tool_calls(msg)
    for tc in tool_calls:
        if "result" in tc:
            result = tc["result"]
            if not show_full and len(str(result)) > 200:
                result = str(result)[:200] + "..."
            lines.append(f"  TOOL RESULT ({tc.get('name', 'unknown')}): {result}")
        else:
            args_str = json.dumps(tc.get("args", {}), indent=2)
            if not show_full and len(args_str) > 200:
                args_str = args_str[:200] + "..."
            lines.append(f"  TOOL CALL: {tc['name']}")
            lines.append(f"    Args: {args_str}")
    
    return "\n".join(lines)


def view_thread(
    thread_id: str,
    db_path: Path = SESSIONS_DB,
    show_full: bool = False,
    output_format: str = "terminal"
) -> None:
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT checkpoint_id, checkpoint, metadata
        FROM checkpoints
        WHERE thread_id = ?
        ORDER BY checkpoint_id ASC
    """, (thread_id,))
    
    checkpoints = cursor.fetchall()
    conn.close()
    
    if not checkpoints:
        print(f"No checkpoints found for thread: {thread_id}")
        return
    
    all_messages: list[dict] = []
    seen_ids: set[str] = set()
    
    for checkpoint_id, checkpoint_blob, metadata_blob in checkpoints:
        checkpoint_data = decode_blob(checkpoint_blob)
        messages = extract_messages_from_checkpoint(checkpoint_data)
        
        for msg in messages:
            msg_id = msg.get("id", str(len(all_messages)))
            if msg_id not in seen_ids:
                seen_ids.add(msg_id)
                all_messages.append(msg)
    
    if output_format == "json":
        print(json.dumps(all_messages, indent=2, default=str))
        return
    
    print(f"\n{'=' * 70}")
    print(f"Thread: {thread_id}")
    print(f"Total messages: {len(all_messages)}")
    print(f"{'=' * 70}\n")
    
    for i, msg in enumerate(all_messages):
        print(f"--- Message {i + 1} ---")
        print(format_message(msg, show_full=show_full))
        print()


def export_thread(
    thread_id: str,
    output_file: Path,
    db_path: Path = SESSIONS_DB
) -> None:
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT checkpoint_id, checkpoint, metadata
        FROM checkpoints
        WHERE thread_id = ?
        ORDER BY checkpoint_id ASC
    """, (thread_id,))
    
    checkpoints = cursor.fetchall()
    conn.close()
    
    if not checkpoints:
        print(f"No checkpoints found for thread: {thread_id}")
        return
    
    export_data = {
        "thread_id": thread_id,
        "exported_at": datetime.now().isoformat(),
        "checkpoints": [],
    }
    
    for checkpoint_id, checkpoint_blob, metadata_blob in checkpoints:
        checkpoint_data = decode_blob(checkpoint_blob)
        metadata = decode_blob(metadata_blob) if metadata_blob else {}
        
        export_data["checkpoints"].append({
            "checkpoint_id": checkpoint_id,
            "data": checkpoint_data,
            "metadata": metadata,
        })
    
    with open(output_file, "w") as f:
        json.dump(export_data, f, indent=2, default=str)
    
    print(f"Exported thread {thread_id} to {output_file}")


def search_threads(
    query: str,
    db_path: Path = SESSIONS_DB,
    limit: int = 10
) -> None:
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT DISTINCT thread_id FROM checkpoints")
    all_threads = [row[0] for row in cursor.fetchall()]
    
    matching_threads: list[tuple[str, str]] = []
    
    for thread_id in all_threads:
        cursor.execute("""
            SELECT checkpoint
            FROM checkpoints
            WHERE thread_id = ?
            ORDER BY checkpoint_id ASC
            LIMIT 5
        """, (thread_id,))
        
        for (checkpoint_blob,) in cursor.fetchall():
            checkpoint_data = decode_blob(checkpoint_blob)
            messages = extract_messages_from_checkpoint(checkpoint_data)
            
            for msg in messages:
                content = str(msg.get("content", ""))
                if query.lower() in content.lower():
                    snippet = content[:100] + "..." if len(content) > 100 else content
                    matching_threads.append((thread_id, snippet))
                    break
            else:
                continue
            break
        
        if len(matching_threads) >= limit:
            break
    
    conn.close()
    
    if not matching_threads:
        print(f"No threads found matching: {query}")
        return
    
    print(f"\nThreads matching '{query}':\n")
    for thread_id, snippet in matching_threads:
        print(f"Thread: {thread_id}")
        print(f"  {snippet}")
        print()


def show_tools_summary(thread_id: str, db_path: Path = SESSIONS_DB) -> None:
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT checkpoint
        FROM checkpoints
        WHERE thread_id = ?
        ORDER BY checkpoint_id ASC
    """, (thread_id,))
    
    checkpoints = cursor.fetchall()
    conn.close()
    
    if not checkpoints:
        print(f"No checkpoints found for thread: {thread_id}")
        return
    
    tool_calls: list[dict] = []
    seen_ids: set[str] = set()
    
    for (checkpoint_blob,) in checkpoints:
        checkpoint_data = decode_blob(checkpoint_blob)
        messages = extract_messages_from_checkpoint(checkpoint_data)
        
        for msg in messages:
            msg_id = msg.get("id", "")
            if msg_id in seen_ids:
                continue
            seen_ids.add(msg_id)
            
            if "tool_calls" in msg:
                for tc in msg.get("tool_calls", []):
                    tool_calls.append({
                        "type": "call",
                        "name": tc.get("name", "unknown"),
                        "args": tc.get("args", {}),
                        "id": tc.get("id", ""),
                    })
            
            if msg.get("type") == "tool" or msg.get("role") == "tool":
                tool_call_id = msg.get("tool_call_id", "")
                result = msg.get("content", "")
                if len(str(result)) > 500:
                    result = str(result)[:500] + "..."
                tool_calls.append({
                    "type": "result",
                    "name": msg.get("name", "unknown"),
                    "tool_call_id": tool_call_id,
                    "result": result,
                })
    
    if not tool_calls:
        print(f"No tool calls found in thread: {thread_id}")
        return
    
    print(f"\n{'=' * 70}")
    print(f"Tool Calls Summary - Thread: {thread_id}")
    print(f"{'=' * 70}\n")
    
    for i, tc in enumerate(tool_calls, 1):
        if tc["type"] == "call":
            print(f"{i}. CALL: {tc['name']}")
            args_str = json.dumps(tc["args"], indent=4)
            for line in args_str.split("\n"):
                print(f"     {line}")
        else:
            print(f"{i}. RESULT: {tc['name']}")
            result_lines = str(tc["result"]).split("\n")[:5]
            for line in result_lines:
                print(f"     {line[:100]}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="View and analyze DeepAgents CLI traces",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s list                     List all threads
  %(prog)s view THREAD_ID           View a thread's conversation
  %(prog)s view THREAD_ID --full    View with full message content
  %(prog)s tools THREAD_ID          Show tool calls summary
  %(prog)s search "subagent"        Search threads by content
  %(prog)s export THREAD_ID out.json  Export thread to JSON
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    list_parser = subparsers.add_parser("list", help="List all threads")
    list_parser.add_argument("-n", "--limit", type=int, default=20, help="Max threads to show")
    
    view_parser = subparsers.add_parser("view", help="View a thread's conversation")
    view_parser.add_argument("thread_id", help="Thread ID (can be partial)")
    view_parser.add_argument("--full", action="store_true", help="Show full message content")
    view_parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    tools_parser = subparsers.add_parser("tools", help="Show tool calls summary")
    tools_parser.add_argument("thread_id", help="Thread ID (can be partial)")
    
    search_parser = subparsers.add_parser("search", help="Search threads by content")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("-n", "--limit", type=int, default=10, help="Max results")
    
    export_parser = subparsers.add_parser("export", help="Export thread to JSON")
    export_parser.add_argument("thread_id", help="Thread ID")
    export_parser.add_argument("output", type=Path, help="Output file path")
    
    parser.add_argument("--db", type=Path, default=SESSIONS_DB, help="Path to sessions.db")
    
    args = parser.parse_args()
    
    def resolve_thread_id(partial_id: str, db_path: Path) -> str:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT DISTINCT thread_id FROM checkpoints WHERE thread_id LIKE ?",
            (f"{partial_id}%",)
        )
        matches = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        if not matches:
            print(f"No thread found matching: {partial_id}", file=sys.stderr)
            sys.exit(1)
        if len(matches) > 1:
            print(f"Multiple threads match '{partial_id}':", file=sys.stderr)
            for m in matches[:5]:
                print(f"  {m}", file=sys.stderr)
            sys.exit(1)
        return matches[0]
    
    if args.command == "list":
        list_threads(args.db, args.limit)
    
    elif args.command == "view":
        thread_id = resolve_thread_id(args.thread_id, args.db)
        output_format = "json" if args.json else "terminal"
        view_thread(thread_id, args.db, args.full, output_format)
    
    elif args.command == "tools":
        thread_id = resolve_thread_id(args.thread_id, args.db)
        show_tools_summary(thread_id, args.db)
    
    elif args.command == "search":
        search_threads(args.query, args.db, args.limit)
    
    elif args.command == "export":
        thread_id = resolve_thread_id(args.thread_id, args.db)
        export_thread(thread_id, args.output, args.db)


if __name__ == "__main__":
    main()
