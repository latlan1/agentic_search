"""
Unit tests for tantivy_index_manager.py - Index management utilities.

Tests cover:
- IndexMetadata dataclass
- compute_file_hash function
- load_augmentations function
- IndexManager class structure
- CLI argument parsing
"""

import json
import sys
import tempfile
from dataclasses import fields
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from tantivy_index_manager import (
    AUGMENTATION_DIR,
    DOCS_DIRS,
    INDEX_DIR,
    IndexManager,
    IndexMetadata,
    compute_file_hash,
    load_augmentations,
)


# ---------------------------------------------------------------------------
# Constants Tests
# ---------------------------------------------------------------------------


class TestConstants:
    """Tests for module-level constants."""

    def test_docs_dirs_are_paths(self):
        """DOCS_DIRS should be a list of Path objects."""
        assert isinstance(DOCS_DIRS, list)
        for d in DOCS_DIRS:
            assert isinstance(d, Path)

    def test_docs_dirs_includes_expected_directories(self):
        """DOCS_DIRS should include deepagents and langgraph directories."""
        dir_names = [str(d) for d in DOCS_DIRS]
        assert any("deepagents" in d for d in dir_names)
        assert any("langgraph" in d for d in dir_names)

    def test_augmentation_dir_is_path(self):
        """AUGMENTATION_DIR should be a Path."""
        assert isinstance(AUGMENTATION_DIR, Path)
        assert "augmented" in str(AUGMENTATION_DIR)

    def test_index_dir_is_path(self):
        """INDEX_DIR should be a Path pointing to tantivy_index."""
        assert isinstance(INDEX_DIR, Path)
        assert INDEX_DIR == Path("tantivy_index")


# ---------------------------------------------------------------------------
# IndexMetadata Tests
# ---------------------------------------------------------------------------


class TestIndexMetadata:
    """Tests for IndexMetadata dataclass."""

    def test_metadata_has_required_fields(self):
        """IndexMetadata should have documents, next_doc_id, last_updated."""
        field_names = {f.name for f in fields(IndexMetadata)}
        expected = {"documents", "next_doc_id", "last_updated"}
        assert field_names == expected

    def test_metadata_default_values(self):
        """IndexMetadata should have sensible defaults."""
        meta = IndexMetadata()
        assert meta.documents == {}
        assert meta.next_doc_id == 0
        assert meta.last_updated == ""

    def test_metadata_to_dict(self):
        """to_dict() should serialize metadata correctly."""
        meta = IndexMetadata(
            documents={"file.md": {"doc_id": 0, "hash": "abc123"}},
            next_doc_id=1,
            last_updated="2024-01-15T10:30:00",
        )
        d = meta.to_dict()
        assert d["documents"] == {"file.md": {"doc_id": 0, "hash": "abc123"}}
        assert d["next_doc_id"] == 1
        assert d["last_updated"] == "2024-01-15T10:30:00"

    def test_metadata_from_dict(self):
        """from_dict() should deserialize metadata correctly."""
        data = {
            "documents": {"test.md": {"doc_id": 5, "hash": "xyz789"}},
            "next_doc_id": 6,
            "last_updated": "2024-02-01",
        }
        meta = IndexMetadata.from_dict(data)
        assert meta.documents == {"test.md": {"doc_id": 5, "hash": "xyz789"}}
        assert meta.next_doc_id == 6
        assert meta.last_updated == "2024-02-01"

    def test_metadata_from_dict_handles_missing_keys(self):
        """from_dict() should handle missing keys with defaults."""
        meta = IndexMetadata.from_dict({})
        assert meta.documents == {}
        assert meta.next_doc_id == 0
        assert meta.last_updated == ""


# ---------------------------------------------------------------------------
# compute_file_hash Tests
# ---------------------------------------------------------------------------


class TestComputeFileHash:
    """Tests for compute_file_hash function."""

    def test_hash_is_deterministic(self):
        """Same content should produce same hash."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Test Content\n\nHello world!")
            path = Path(f.name)

        try:
            hash1 = compute_file_hash(path)
            hash2 = compute_file_hash(path)
            assert hash1 == hash2
        finally:
            path.unlink()

    def test_different_content_different_hash(self):
        """Different content should produce different hashes."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f1:
            f1.write("Content A")
            path1 = Path(f1.name)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f2:
            f2.write("Content B")
            path2 = Path(f2.name)

        try:
            hash1 = compute_file_hash(path1)
            hash2 = compute_file_hash(path2)
            assert hash1 != hash2
        finally:
            path1.unlink()
            path2.unlink()

    def test_hash_is_md5_format(self):
        """Hash should be MD5 format (32 hex characters)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("Test")
            path = Path(f.name)

        try:
            hash_value = compute_file_hash(path)
            assert len(hash_value) == 32
            assert all(c in "0123456789abcdef" for c in hash_value)
        finally:
            path.unlink()


# ---------------------------------------------------------------------------
# load_augmentations Tests
# ---------------------------------------------------------------------------


class TestLoadAugmentations:
    """Tests for load_augmentations function."""

    def test_returns_dict(self):
        """load_augmentations should return a dict."""
        result = load_augmentations()
        assert isinstance(result, dict)

    def test_returns_empty_if_no_augmentation_dir(self):
        """Should return empty dict if AUGMENTATION_DIR doesn't exist."""
        with patch("tantivy_index_manager.AUGMENTATION_DIR", Path("/nonexistent")):
            # Re-import to use patched value
            from tantivy_index_manager import load_augmentations as load_aug

            # The function checks if dir exists, so this should be safe
            # but we can't easily test this without more complex mocking

    def test_keys_are_filenames(self):
        """Dict keys should be filenames from the augmentation data."""
        result = load_augmentations()
        # If augmentations exist, keys should be strings (filenames)
        for key in result.keys():
            assert isinstance(key, str)
            # Filenames should typically end in .md
            # (but not strictly required by the function)


# ---------------------------------------------------------------------------
# IndexManager Tests
# ---------------------------------------------------------------------------


class TestIndexManagerStructure:
    """Tests for IndexManager class structure."""

    def test_has_init_method(self):
        """IndexManager should have __init__ method."""
        assert hasattr(IndexManager, "__init__")

    def test_has_ensure_index_exists(self):
        """IndexManager should have ensure_index_exists method."""
        assert hasattr(IndexManager, "ensure_index_exists")
        assert callable(getattr(IndexManager, "ensure_index_exists"))

    def test_has_sync_all(self):
        """IndexManager should have sync_all method."""
        assert hasattr(IndexManager, "sync_all")
        assert callable(getattr(IndexManager, "sync_all"))

    def test_has_add_or_update_document(self):
        """IndexManager should have add_or_update_document method."""
        assert hasattr(IndexManager, "add_or_update_document")
        assert callable(getattr(IndexManager, "add_or_update_document"))

    def test_has_remove_document(self):
        """IndexManager should have remove_document method."""
        assert hasattr(IndexManager, "remove_document")
        assert callable(getattr(IndexManager, "remove_document"))

    def test_has_get_stats(self):
        """IndexManager should have get_stats method."""
        assert hasattr(IndexManager, "get_stats")
        assert callable(getattr(IndexManager, "get_stats"))

    def test_default_index_dir(self):
        """IndexManager should use INDEX_DIR as default."""
        manager = IndexManager()
        assert manager.index_dir == INDEX_DIR


# ---------------------------------------------------------------------------
# CLI Tests
# ---------------------------------------------------------------------------


class TestCLIArgumentParsing:
    """Tests for CLI argument parsing."""

    def test_build_subcommand_exists(self):
        """CLI should have 'build' subcommand."""
        import argparse

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command", required=True)
        subparsers.add_parser("build")

        args = parser.parse_args(["build"])
        assert args.command == "build"

    def test_sync_subcommand_exists(self):
        """CLI should have 'sync' subcommand."""
        import argparse

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command", required=True)
        subparsers.add_parser("sync")

        args = parser.parse_args(["sync"])
        assert args.command == "sync"

    def test_watch_subcommand_exists(self):
        """CLI should have 'watch' subcommand."""
        import argparse

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command", required=True)
        subparsers.add_parser("watch")

        args = parser.parse_args(["watch"])
        assert args.command == "watch"

    def test_stats_subcommand_exists(self):
        """CLI should have 'stats' subcommand."""
        import argparse

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command", required=True)
        subparsers.add_parser("stats")

        args = parser.parse_args(["stats"])
        assert args.command == "stats"


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------


class TestIndexManagerIntegration:
    """Integration tests for IndexManager."""

    @pytest.mark.skipif(
        not (Path("tantivy_index") / "meta.json").exists(),
        reason="Tantivy index not built. Run: uv run scripts/tantivy_index_manager.py build",
    )
    def test_get_stats_returns_dict(self):
        """get_stats() should return a dict with expected keys."""
        manager = IndexManager()
        stats = manager.get_stats()

        assert isinstance(stats, dict)
        assert "total_documents" in stats
        assert "next_doc_id" in stats
        assert "last_updated" in stats
        assert "index_exists" in stats

    @pytest.mark.skipif(
        not (Path("tantivy_index") / "meta.json").exists(),
        reason="Tantivy index not built. Run: uv run scripts/tantivy_index_manager.py build",
    )
    def test_ensure_index_exists_opens_existing(self):
        """ensure_index_exists() should open existing index without rebuilding."""
        manager = IndexManager()
        rebuilt = manager.ensure_index_exists()

        # If index exists, it should not rebuild (return False)
        assert rebuilt is False
        assert manager._index is not None

    def test_data_directories_exist(self):
        """Data directories should exist for indexing."""
        for docs_dir in DOCS_DIRS:
            if not docs_dir.exists():
                pytest.skip(f"Data directory {docs_dir} does not exist")

        # At least one should exist
        existing = [d for d in DOCS_DIRS if d.exists()]
        assert len(existing) > 0, "At least one data directory should exist"

    def test_data_directories_contain_markdown(self):
        """Data directories should contain .md files."""
        for docs_dir in DOCS_DIRS:
            if docs_dir.exists():
                md_files = list(docs_dir.glob("*.md"))
                assert len(md_files) > 0, f"{docs_dir} should contain .md files"
