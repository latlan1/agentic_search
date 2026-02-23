#!/usr/bin/env python3
"""
Tantivy-based search API with search() and read() functions.

Follows the agentic search pattern:
- search(): returns a results page (doc_id, filename, snippet) without full content
- read(): retrieves full document content by doc_id

This separation prevents context window bloat when an agent explores search results.
"""

from dataclasses import dataclass
from pathlib import Path

import tantivy

INDEX_DIR = Path("tantivy_index")


@dataclass
class SearchResult:
    """A single search result (preview, not full content)."""
    doc_id: int
    filename: str
    path: str
    description: str
    score: float


@dataclass
class Document:
    """Full document content."""
    doc_id: int
    filename: str
    path: str
    content: str
    keywords: str
    description: str


class DocumentSearchIndex:
    """
    Tantivy search index for the Markdown corpus.
    
    Implements the two-function API from "Agentic Search for Dummies":
    - search(queries, limit) -> list of SearchResult
    - read(doc_ids) -> list of Document
    """

    def __init__(self, index_path: Path = INDEX_DIR):
        self.index = tantivy.Index.open(str(index_path))
        self.searcher = self.index.searcher()
        self.schema = self.index.schema

    def search(
        self,
        queries: list[str],
        limit: int = 10,
    ) -> list[SearchResult]:
        """
        Search the index with one or more queries.
        
        Multiple queries are executed separately and results are fused using
        Reciprocal Rank Fusion (RRF) to produce a single ranked list.
        
        Args:
            queries: List of search query strings
            limit: Maximum number of results to return
            
        Returns:
            List of SearchResult objects (without full content)
        """
        if not queries:
            return []

        # Fields to search
        search_fields = ["content", "keywords", "description", "filename"]

        # Collect results from each query with their ranks
        doc_ranks: dict[int, list[int]] = {}  # doc_id -> list of ranks

        for query_str in queries:
            query = self.index.parse_query(query_str, search_fields)
            results = self.searcher.search(query, limit=limit * 2).hits

            for rank, (score, doc_addr) in enumerate(results):
                doc = self.searcher.doc(doc_addr)
                doc_id = doc.get_first("doc_id")
                if doc_id is not None:
                    if doc_id not in doc_ranks:
                        doc_ranks[doc_id] = []
                    doc_ranks[doc_id].append(rank)

        # Reciprocal Rank Fusion
        # RRF score = sum(1 / (k + rank)) for each query where doc appears
        k = 60  # standard RRF constant
        rrf_scores: dict[int, float] = {}
        for doc_id, ranks in doc_ranks.items():
            rrf_scores[doc_id] = sum(1.0 / (k + r) for r in ranks)

        # Sort by RRF score descending
        sorted_doc_ids = sorted(rrf_scores.keys(), key=lambda d: rrf_scores[d], reverse=True)

        # Build result objects
        results = []
        for doc_id in sorted_doc_ids[:limit]:
            # Re-fetch document to get metadata
            query = self.index.parse_query(f"{doc_id}", ["doc_id"])
            hits = self.searcher.search(query, limit=1).hits
            if hits:
                _, doc_addr = hits[0]
                doc = self.searcher.doc(doc_addr)
                results.append(SearchResult(
                    doc_id=doc_id,
                    filename=doc.get_first("filename") or "",
                    path=doc.get_first("path") or "",
                    description=doc.get_first("description") or "",
                    score=rrf_scores[doc_id],
                ))

        return results

    def read(self, doc_ids: list[int]) -> list[Document]:
        """
        Retrieve full document content by doc_id.
        
        Args:
            doc_ids: List of document IDs to retrieve
            
        Returns:
            List of Document objects with full content
        """
        documents = []
        for doc_id in doc_ids:
            query = self.index.parse_query(f"{doc_id}", ["doc_id"])
            hits = self.searcher.search(query, limit=1).hits
            if hits:
                _, doc_addr = hits[0]
                doc = self.searcher.doc(doc_addr)
                documents.append(Document(
                    doc_id=doc_id,
                    filename=doc.get_first("filename") or "",
                    path=doc.get_first("path") or "",
                    content=doc.get_first("content") or "",
                    keywords=doc.get_first("keywords") or "",
                    description=doc.get_first("description") or "",
                ))
        return documents


# ---------------------------------------------------------------------------
# CLI Interface
# ---------------------------------------------------------------------------

def main():
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Search the documentation corpus using Tantivy"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # search subcommand
    search_parser = subparsers.add_parser("search", help="Search for documents")
    search_parser.add_argument("queries", nargs="+", help="Search queries")
    search_parser.add_argument("-n", "--limit", type=int, default=10, help="Max results")

    # read subcommand
    read_parser = subparsers.add_parser("read", help="Read documents by ID")
    read_parser.add_argument("doc_ids", nargs="+", type=int, help="Document IDs to read")

    args = parser.parse_args()

    try:
        index = DocumentSearchIndex()
    except Exception as e:
        print(f"Error opening index: {e}", file=sys.stderr)
        print("Run 'uv run scripts/tantivy_index_manager.py build' first to create the index.", file=sys.stderr)
        sys.exit(1)

    if args.command == "search":
        results = index.search(args.queries, limit=args.limit)
        if not results:
            print("No results found.")
        else:
            print(f"Found {len(results)} results:\n")
            for r in results:
                print(f"[{r.doc_id}] {r.filename} (score: {r.score:.4f})")
                print(f"    Path: {r.path}")
                desc = r.description[:200] + "..." if len(r.description) > 200 else r.description
                print(f"    {desc}\n")

    elif args.command == "read":
        documents = index.read(args.doc_ids)
        for doc in documents:
            print("=" * 80)
            print(f"Document ID: {doc.doc_id}")
            print(f"Filename: {doc.filename}")
            print(f"Path: {doc.path}")
            print("-" * 80)
            print(doc.content)
            print("=" * 80)


if __name__ == "__main__":
    main()
