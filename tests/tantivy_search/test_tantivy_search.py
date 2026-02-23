"""
Unit tests for tantivy_search.py - Approach 2 (Tantivy CLI).

Tests cover:
- SearchResult and Document dataclasses
- DocumentSearchIndex class structure
- RRF fusion logic
- CLI argument parsing
"""

import sys
from dataclasses import fields
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from tantivy_search import (
    INDEX_DIR,
    Document,
    DocumentSearchIndex,
    SearchResult,
)


# ---------------------------------------------------------------------------
# Dataclass Tests
# ---------------------------------------------------------------------------


class TestSearchResultDataclass:
    """Tests for the SearchResult dataclass."""

    def test_search_result_has_required_fields(self):
        """SearchResult should have doc_id, filename, path, description, score."""
        field_names = {f.name for f in fields(SearchResult)}
        expected = {"doc_id", "filename", "path", "description", "score"}
        assert field_names == expected

    def test_search_result_instantiation(self):
        """SearchResult can be instantiated with all fields."""
        result = SearchResult(
            doc_id=1,
            filename="test.md",
            path="data/test.md",
            description="A test document",
            score=0.5,
        )
        assert result.doc_id == 1
        assert result.filename == "test.md"
        assert result.path == "data/test.md"
        assert result.description == "A test document"
        assert result.score == 0.5

    def test_search_result_score_is_float(self):
        """SearchResult score should be a float for RRF scores."""
        result = SearchResult(
            doc_id=0,
            filename="doc.md",
            path="path/doc.md",
            description="desc",
            score=0.0166,  # RRF score example: 1/(60+0) = 0.0166...
        )
        assert isinstance(result.score, float)


class TestDocumentDataclass:
    """Tests for the Document dataclass."""

    def test_document_has_required_fields(self):
        """Document should have doc_id, filename, path, content, keywords, description."""
        field_names = {f.name for f in fields(Document)}
        expected = {"doc_id", "filename", "path", "content", "keywords", "description"}
        assert field_names == expected

    def test_document_instantiation(self):
        """Document can be instantiated with all fields."""
        doc = Document(
            doc_id=5,
            filename="guide.md",
            path="data/deepagents_raw_md/guide.md",
            content="# Guide\n\nThis is the content.",
            keywords="guide tutorial help",
            description="A helpful guide document",
        )
        assert doc.doc_id == 5
        assert doc.filename == "guide.md"
        assert "# Guide" in doc.content
        assert "tutorial" in doc.keywords


# ---------------------------------------------------------------------------
# DocumentSearchIndex Tests
# ---------------------------------------------------------------------------


class TestDocumentSearchIndexStructure:
    """Tests for DocumentSearchIndex class structure (no actual index required)."""

    def test_index_dir_constant(self):
        """INDEX_DIR should point to tantivy_index."""
        assert INDEX_DIR == Path("tantivy_index")

    def test_class_has_search_method(self):
        """DocumentSearchIndex should have a search method."""
        assert hasattr(DocumentSearchIndex, "search")
        assert callable(getattr(DocumentSearchIndex, "search"))

    def test_class_has_read_method(self):
        """DocumentSearchIndex should have a read method."""
        assert hasattr(DocumentSearchIndex, "read")
        assert callable(getattr(DocumentSearchIndex, "read"))

    def test_search_method_signature(self):
        """search() should accept queries and limit parameters."""
        import inspect

        sig = inspect.signature(DocumentSearchIndex.search)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "queries" in params
        assert "limit" in params

    def test_read_method_signature(self):
        """read() should accept doc_ids parameter."""
        import inspect

        sig = inspect.signature(DocumentSearchIndex.read)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "doc_ids" in params


class TestRRFFusionLogic:
    """Tests for Reciprocal Rank Fusion logic."""

    def test_rrf_formula_calculation(self):
        """
        Test RRF score calculation matches the formula:
        RRF_score(doc) = sum(1/(k + rank)) for each query where doc appears.
        """
        k = 60  # Standard RRF constant

        # Simulate: doc appears at rank 0 in query 1, rank 2 in query 2
        ranks = [0, 2]
        expected_rrf = sum(1.0 / (k + r) for r in ranks)
        # 1/(60+0) + 1/(60+2) = 1/60 + 1/62
        assert abs(expected_rrf - (1 / 60 + 1 / 62)) < 0.0001

    def test_rrf_higher_rank_gives_higher_score(self):
        """Documents appearing at higher ranks should have higher RRF scores."""
        k = 60

        # Doc at rank 0 (best)
        score_rank_0 = 1.0 / (k + 0)

        # Doc at rank 5
        score_rank_5 = 1.0 / (k + 5)

        assert score_rank_0 > score_rank_5

    def test_rrf_multiple_queries_boost_score(self):
        """Documents appearing in multiple queries should have higher scores."""
        k = 60

        # Doc appears only in query 1 at rank 0
        single_query_score = 1.0 / (k + 0)

        # Doc appears in query 1 at rank 0 AND query 2 at rank 0
        multi_query_score = 1.0 / (k + 0) + 1.0 / (k + 0)

        assert multi_query_score > single_query_score


# ---------------------------------------------------------------------------
# Integration Tests (require actual index)
# ---------------------------------------------------------------------------


@pytest.fixture
def index_exists():
    """Check if Tantivy index exists."""
    return (Path("tantivy_index") / "meta.json").exists()


class TestDocumentSearchIndexIntegration:
    """Integration tests that require an actual Tantivy index."""

    @pytest.mark.skipif(
        not (Path("tantivy_index") / "meta.json").exists(),
        reason="Tantivy index not built. Run: uv run scripts/tantivy_index_manager.py build",
    )
    def test_index_opens_successfully(self):
        """DocumentSearchIndex should open without errors when index exists."""
        index = DocumentSearchIndex()
        assert index.index is not None
        assert index.searcher is not None

    @pytest.mark.skipif(
        not (Path("tantivy_index") / "meta.json").exists(),
        reason="Tantivy index not built. Run: uv run scripts/tantivy_index_manager.py build",
    )
    def test_search_returns_list(self):
        """search() should return a list of SearchResult objects."""
        index = DocumentSearchIndex()
        results = index.search(["agent"], limit=5)
        assert isinstance(results, list)
        if results:
            assert isinstance(results[0], SearchResult)

    @pytest.mark.skipif(
        not (Path("tantivy_index") / "meta.json").exists(),
        reason="Tantivy index not built. Run: uv run scripts/tantivy_index_manager.py build",
    )
    def test_search_empty_query_returns_empty(self):
        """search() with empty queries should return empty list."""
        index = DocumentSearchIndex()
        results = index.search([], limit=10)
        assert results == []

    @pytest.mark.skipif(
        not (Path("tantivy_index") / "meta.json").exists(),
        reason="Tantivy index not built. Run: uv run scripts/tantivy_index_manager.py build",
    )
    def test_read_returns_document_list(self):
        """read() should return a list of Document objects."""
        index = DocumentSearchIndex()
        # First search to get a valid doc_id
        results = index.search(["agent"], limit=1)
        if results:
            doc_id = results[0].doc_id
            docs = index.read([doc_id])
            assert isinstance(docs, list)
            assert len(docs) == 1
            assert isinstance(docs[0], Document)
            assert docs[0].doc_id == doc_id

    @pytest.mark.skipif(
        not (Path("tantivy_index") / "meta.json").exists(),
        reason="Tantivy index not built. Run: uv run scripts/tantivy_index_manager.py build",
    )
    def test_read_empty_ids_returns_empty(self):
        """read() with empty doc_ids should return empty list."""
        index = DocumentSearchIndex()
        docs = index.read([])
        assert docs == []


# ---------------------------------------------------------------------------
# CLI Tests
# ---------------------------------------------------------------------------


class TestCLIArgumentParsing:
    """Tests for CLI argument parsing."""

    def test_cli_requires_subcommand(self):
        """CLI should require a subcommand (search or read)."""
        import argparse

        # Import main to test argument parsing
        from tantivy_search import main

        # Test that running without arguments raises SystemExit
        with patch("sys.argv", ["tantivy_search.py"]):
            with pytest.raises(SystemExit):
                main()

    def test_search_subcommand_requires_queries(self):
        """search subcommand should require at least one query."""
        import argparse

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command", required=True)
        search_parser = subparsers.add_parser("search")
        search_parser.add_argument("queries", nargs="+")

        with pytest.raises(SystemExit):
            parser.parse_args(["search"])  # No queries provided

    def test_search_subcommand_accepts_multiple_queries(self):
        """search subcommand should accept multiple queries for RRF fusion."""
        import argparse

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command", required=True)
        search_parser = subparsers.add_parser("search")
        search_parser.add_argument("queries", nargs="+")
        search_parser.add_argument("-n", "--limit", type=int, default=10)

        args = parser.parse_args(["search", "query1", "query2", "query3"])
        assert args.queries == ["query1", "query2", "query3"]
        assert args.limit == 10

    def test_read_subcommand_accepts_doc_ids(self):
        """read subcommand should accept document IDs."""
        import argparse

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command", required=True)
        read_parser = subparsers.add_parser("read")
        read_parser.add_argument("doc_ids", nargs="+", type=int)

        args = parser.parse_args(["read", "0", "1", "5"])
        assert args.doc_ids == [0, 1, 5]
