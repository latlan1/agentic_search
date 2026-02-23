#!/usr/bin/env python3
"""
Index Manager - Manages Tantivy index with incremental updates and file watching.

Features:
- Build index from scratch if it doesn't exist
- Incremental updates: add/update/delete individual documents
- File watcher using watchdog for automatic re-indexing
- Thread-safe index operations

Usage:
    uv run scripts/tantivy_index_manager.py watch
    uv run scripts/tantivy_index_manager.py build
    uv run scripts/tantivy_index_manager.py sync
    uv run scripts/tantivy_index_manager.py stats
"""

import hashlib
import json
import signal
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import tantivy
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

DOCS_DIRS = [
    Path("data/deepagents_raw_md"),
    Path("data/langgraph_raw_md"),
]
AUGMENTATION_DIR = Path("augmented_jsonl_index")
INDEX_DIR = Path("tantivy_index")


@dataclass
class IndexMetadata:
    """Tracks indexed documents and their hashes for incremental updates."""

    documents: dict[str, dict] = field(default_factory=dict)
    next_doc_id: int = 0
    last_updated: str = ""

    def to_dict(self) -> dict:
        return {
            "documents": self.documents,
            "next_doc_id": self.next_doc_id,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "IndexMetadata":
        return cls(
            documents=data.get("documents", {}),
            next_doc_id=data.get("next_doc_id", 0),
            last_updated=data.get("last_updated", ""),
        )


def compute_file_hash(path: Path) -> str:
    """Compute MD5 hash of file content for change detection."""
    content = path.read_bytes()
    return hashlib.md5(content).hexdigest()


def load_augmentations() -> dict[str, dict]:
    """Load all JSONL/JSON augmentation files into a dict keyed by filename.
    
    Supports:
    - JSON array: [{"filename": "a.md", ...}, {"filename": "b.md", ...}]
    - JSONL: one JSON object per line
    - Multi-object JSON: multiple JSON objects in one file (pretty-printed)
    """
    augments: dict[str, dict] = {}
    if not AUGMENTATION_DIR.exists():
        return augments

    for pattern in ["*.jsonl", "*.json"]:
        for aug_file in AUGMENTATION_DIR.glob(pattern):
            with open(aug_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                
                # Try parsing as a JSON array first
                if content.startswith("["):
                    try:
                        items = json.loads(content)
                        for obj in items:
                            if isinstance(obj, dict):
                                fname = obj.get("filename", "")
                                if fname:
                                    augments[fname] = obj
                        continue  # Successfully parsed, skip to next file
                    except json.JSONDecodeError:
                        pass
                
                # Try parsing as a single JSON object
                try:
                    obj = json.loads(content)
                    if isinstance(obj, dict):
                        fname = obj.get("filename", "")
                        if fname:
                            augments[fname] = obj
                        continue  # Successfully parsed, skip to next file
                except json.JSONDecodeError:
                    pass
                
                # Try parsing as multiple JSON objects (pretty-printed, separated by newlines)
                # Use a simple approach: find objects by matching braces
                decoder = json.JSONDecoder()
                idx = 0
                while idx < len(content):
                    # Skip whitespace
                    while idx < len(content) and content[idx] in " \t\n\r":
                        idx += 1
                    if idx >= len(content):
                        break
                    
                    try:
                        obj, end_idx = decoder.raw_decode(content, idx)
                        if isinstance(obj, dict):
                            fname = obj.get("filename", "")
                            if fname:
                                augments[fname] = obj
                        idx += end_idx
                    except json.JSONDecodeError:
                        # Skip this character and try again
                        idx += 1
                        
    return augments


class IndexManager:
    """Manages the Tantivy index with support for incremental updates."""

    def __init__(self, index_dir: Path = INDEX_DIR):
        self.index_dir = index_dir
        self.metadata_file = index_dir / "metadata.json"
        self._lock = threading.Lock()
        self._index: Optional[tantivy.Index] = None
        self._schema: Optional[tantivy.Schema] = None
        self._metadata: Optional[IndexMetadata] = None

    def _build_schema(self) -> tantivy.Schema:
        """Build the Tantivy schema."""
        builder = tantivy.SchemaBuilder()
        builder.add_integer_field("doc_id", stored=True, indexed=True)
        builder.add_text_field("path", stored=True)
        builder.add_text_field("filename", stored=True)
        builder.add_text_field("content", stored=True)
        builder.add_text_field("keywords", stored=True)
        builder.add_text_field("description", stored=True)
        return builder.build()

    def _load_metadata(self) -> IndexMetadata:
        """Load index metadata from disk."""
        if self.metadata_file.exists():
            try:
                data = json.loads(self.metadata_file.read_text())
                return IndexMetadata.from_dict(data)
            except (json.JSONDecodeError, KeyError):
                pass
        return IndexMetadata()

    def _save_metadata(self) -> None:
        """Save index metadata to disk."""
        if self._metadata:
            self._metadata.last_updated = datetime.now().isoformat()
            self.metadata_file.write_text(json.dumps(self._metadata.to_dict(), indent=2))

    def ensure_index_exists(self) -> bool:
        """Ensure the index exists. Build from scratch if needed."""
        with self._lock:
            if self.index_dir.exists() and (self.index_dir / "meta.json").exists():
                self._schema = self._build_schema()
                self._index = tantivy.Index.open(str(self.index_dir))
                self._metadata = self._load_metadata()
                return False
            else:
                self._full_rebuild()
                return True

    def _full_rebuild(self) -> None:
        """Perform a full index rebuild."""
        print("Building Tantivy index from scratch...")

        self.index_dir.mkdir(parents=True, exist_ok=True)
        self._schema = self._build_schema()
        self._index = tantivy.Index(self._schema, path=str(self.index_dir))
        self._metadata = IndexMetadata()

        writer = self._index.writer()
        augments = load_augmentations()

        for docs_dir in DOCS_DIRS:
            if not docs_dir.exists():
                print(f"  Warning: {docs_dir} does not exist, skipping")
                continue

            for md_file in sorted(docs_dir.glob("*.md")):
                doc_id = self._metadata.next_doc_id
                self._index_file(writer, md_file, doc_id, augments)

                self._metadata.documents[str(md_file)] = {
                    "doc_id": doc_id,
                    "hash": compute_file_hash(md_file),
                    "indexed_at": datetime.now().isoformat(),
                }
                self._metadata.next_doc_id += 1
                print(f"  Indexed [{doc_id}]: {md_file}")

        writer.commit()
        self._index.reload()
        self._save_metadata()
        print(f"\nIndex built with {self._metadata.next_doc_id} documents")

    def _index_file(
        self,
        writer: tantivy.IndexWriter,
        file_path: Path,
        doc_id: int,
        augments: dict[str, dict],
    ) -> None:
        """Index a single file."""
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        filename = file_path.name
        aug = augments.get(filename, {})
        keywords_list = aug.get("keywords", [])
        keywords_str = " ".join(keywords_list) if isinstance(keywords_list, list) else ""
        description = aug.get("description", "")

        doc = tantivy.Document(
            doc_id=doc_id,
            path=str(file_path),
            filename=filename,
            content=content,
            keywords=keywords_str,
            description=description,
        )
        writer.add_document(doc)

    def add_or_update_document(self, file_path: Path) -> Optional[int]:
        """Add a new document or update an existing one."""
        if file_path.suffix != ".md":
            return None

        with self._lock:
            if self._index is None or self._metadata is None:
                self.ensure_index_exists()
            
            assert self._index is not None
            assert self._metadata is not None

            path_str = str(file_path)
            file_hash = compute_file_hash(file_path)

            if path_str in self._metadata.documents:
                existing = self._metadata.documents[path_str]
                if existing["hash"] == file_hash:
                    print(f"  Skipping {file_path} (unchanged)")
                    return existing["doc_id"]

                doc_id = existing["doc_id"]
            else:
                doc_id = self._metadata.next_doc_id
                self._metadata.next_doc_id += 1

            writer = self._index.writer()
            augments = load_augmentations()
            self._index_file(writer, file_path, doc_id, augments)
            writer.commit()
            self._index.reload()

            self._metadata.documents[path_str] = {
                "doc_id": doc_id,
                "hash": file_hash,
                "indexed_at": datetime.now().isoformat(),
            }
            self._save_metadata()

            print(f"  Indexed [{doc_id}]: {file_path}")
            return doc_id

    def remove_document(self, file_path: Path) -> bool:
        """Remove a document from the index."""
        with self._lock:
            if self._metadata is None:
                self._metadata = self._load_metadata()
            
            path_str = str(file_path)
            if path_str in self._metadata.documents:
                del self._metadata.documents[path_str]
                self._save_metadata()
                print(f"  Removed from index: {file_path}")
                return True
            return False

    def sync_all(self) -> tuple[int, int, int]:
        """Synchronize the index with the current state of data directories."""
        with self._lock:
            if self._index is None or self._metadata is None:
                self.ensure_index_exists()
            
            assert self._index is not None
            assert self._metadata is not None
            
            # Return early if we just built the index
            if len(self._metadata.documents) == self._metadata.next_doc_id and self._metadata.next_doc_id > 0:
                current_files: set[str] = set()
                for docs_dir in DOCS_DIRS:
                    if docs_dir.exists():
                        for md_file in docs_dir.glob("*.md"):
                            current_files.add(str(md_file))
                if current_files == set(self._metadata.documents.keys()):
                    return (0, 0, 0)

            added = 0
            updated = 0
            removed = 0

            current_files = set()
            for docs_dir in DOCS_DIRS:
                if docs_dir.exists():
                    for md_file in docs_dir.glob("*.md"):
                        current_files.add(str(md_file))

            indexed_files = set(self._metadata.documents.keys())
            for removed_path in indexed_files - current_files:
                del self._metadata.documents[removed_path]
                removed += 1
                print(f"  Removed: {removed_path}")

            augments = load_augmentations()
            writer = self._index.writer()

            for file_path_str in current_files:
                file_path = Path(file_path_str)
                file_hash = compute_file_hash(file_path)

                if file_path_str in self._metadata.documents:
                    existing = self._metadata.documents[file_path_str]
                    if existing["hash"] != file_hash:
                        doc_id = self._metadata.next_doc_id
                        self._metadata.next_doc_id += 1
                        self._index_file(writer, file_path, doc_id, augments)
                        self._metadata.documents[file_path_str] = {
                            "doc_id": doc_id,
                            "hash": file_hash,
                            "indexed_at": datetime.now().isoformat(),
                        }
                        updated += 1
                        print(f"  Updated [{doc_id}]: {file_path}")
                else:
                    doc_id = self._metadata.next_doc_id
                    self._metadata.next_doc_id += 1
                    self._index_file(writer, file_path, doc_id, augments)
                    self._metadata.documents[file_path_str] = {
                        "doc_id": doc_id,
                        "hash": file_hash,
                        "indexed_at": datetime.now().isoformat(),
                    }
                    added += 1
                    print(f"  Added [{doc_id}]: {file_path}")

            if added > 0 or updated > 0:
                writer.commit()
                self._index.reload()

            self._save_metadata()
            return (added, updated, removed)

    def get_stats(self) -> dict:
        """Get index statistics."""
        if self._metadata is None:
            self._metadata = self._load_metadata()

        return {
            "total_documents": len(self._metadata.documents),
            "next_doc_id": self._metadata.next_doc_id,
            "last_updated": self._metadata.last_updated,
            "index_exists": self.index_dir.exists(),
        }


class MarkdownFileHandler(FileSystemEventHandler):
    """File system event handler for watching Markdown files."""

    def __init__(self, index_manager: IndexManager):
        self.index_manager = index_manager
        self._debounce_timers: dict[str, threading.Timer] = {}
        self._debounce_delay = 1.0

    def _debounced_update(self, file_path: Path, action: str) -> None:
        """Debounce file updates to avoid rapid successive re-indexing."""
        path_str = str(file_path)

        if path_str in self._debounce_timers:
            self._debounce_timers[path_str].cancel()

        def do_update():
            if action == "delete":
                self.index_manager.remove_document(file_path)
            else:
                self.index_manager.add_or_update_document(file_path)
            del self._debounce_timers[path_str]

        timer = threading.Timer(self._debounce_delay, do_update)
        self._debounce_timers[path_str] = timer
        timer.start()

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        src_path = event.src_path if isinstance(event.src_path, str) else event.src_path.decode()
        path = Path(src_path)
        if path.suffix == ".md":
            print(f"File created: {path}")
            self._debounced_update(path, "create")

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        src_path = event.src_path if isinstance(event.src_path, str) else event.src_path.decode()
        path = Path(src_path)
        if path.suffix == ".md":
            print(f"File modified: {path}")
            self._debounced_update(path, "modify")

    def on_deleted(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        src_path = event.src_path if isinstance(event.src_path, str) else event.src_path.decode()
        path = Path(src_path)
        if path.suffix == ".md":
            print(f"File deleted: {path}")
            self._debounced_update(path, "delete")


def start_watcher(index_manager: IndexManager) -> Any:
    """Start a file watcher for the data directories."""
    event_handler = MarkdownFileHandler(index_manager)
    observer = Observer()

    for docs_dir in DOCS_DIRS:
        if docs_dir.exists():
            observer.schedule(event_handler, str(docs_dir), recursive=False)
            print(f"Watching: {docs_dir}")

    observer.start()
    return observer


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Tantivy Index Manager - Build and maintain the search index"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("build", help="Build/rebuild the index from scratch")
    subparsers.add_parser("sync", help="Sync index with current files (incremental)")
    subparsers.add_parser("watch", help="Watch for file changes and update index")
    subparsers.add_parser("stats", help="Show index statistics")

    args = parser.parse_args()
    manager = IndexManager()

    if args.command == "build":
        manager._full_rebuild()

    elif args.command == "sync":
        manager.ensure_index_exists()
        added, updated, removed = manager.sync_all()
        print(f"\nSync complete: {added} added, {updated} updated, {removed} removed")

    elif args.command == "watch":
        print("Starting file watcher...")
        manager.ensure_index_exists()

        added, updated, removed = manager.sync_all()
        print(f"Initial sync: {added} added, {updated} updated, {removed} removed")

        observer = start_watcher(manager)

        def signal_handler(signum, frame):
            print("\nStopping watcher...")
            observer.stop()
            observer.join()
            print("Done.")
            exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        print("\nWatching for changes (Ctrl+C to stop)...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            signal_handler(None, None)

    elif args.command == "stats":
        stats = manager.get_stats()
        print("Index Statistics:")
        print(f"  Total documents: {stats['total_documents']}")
        print(f"  Next doc_id: {stats['next_doc_id']}")
        print(f"  Last updated: {stats['last_updated']}")
        print(f"  Index exists: {stats['index_exists']}")


if __name__ == "__main__":
    main()
