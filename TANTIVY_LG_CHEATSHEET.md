# Tantivy Cheatsheet

Quick reference for using Tantivy full-text search in Python.

---

## Installation

```bash
uv add tantivy
# or
pip install tantivy
```

---

## Schema Definition

```python
import tantivy

schema_builder = tantivy.SchemaBuilder()

# Text fields (searchable, optionally stored)
schema_builder.add_text_field("title", stored=True)
schema_builder.add_text_field("body", stored=True)
schema_builder.add_text_field("tags", stored=True)

# Integer fields (for IDs, counts)
schema_builder.add_integer_field("doc_id", stored=True, indexed=True)

# Build the schema
schema = schema_builder.build()
```

### Field Types

| Type | Method | Use Case |
|------|--------|----------|
| Text | `add_text_field()` | Searchable content |
| Integer | `add_integer_field()` | IDs, counts, timestamps |
| Float | `add_float_field()` | Scores, ratings |
| Bytes | `add_bytes_field()` | Binary data |

### Field Options

| Option | Description |
|--------|-------------|
| `stored=True` | Field value retrievable from index |
| `indexed=True` | Field is searchable |
| `fast=True` | Enable fast field for sorting/aggregation |

---

## Index Creation

```python
from pathlib import Path

INDEX_DIR = Path("my_index")
INDEX_DIR.mkdir(exist_ok=True)

# Create index with schema
index = tantivy.Index(schema, path=str(INDEX_DIR))

# Or open existing index
index = tantivy.Index.open(str(INDEX_DIR))
```

---

## Indexing Documents

```python
# Get a writer
writer = index.writer()

# Add documents
doc = tantivy.Document(
    doc_id=1,
    title="My Document",
    body="This is the document content.",
    tags="python search",
)
writer.add_document(doc)

# Commit changes (required!)
writer.commit()

# Reload index to see new documents
index.reload()
```

### Batch Indexing

```python
writer = index.writer()

for i, item in enumerate(data):
    doc = tantivy.Document(
        doc_id=i,
        title=item["title"],
        body=item["content"],
    )
    writer.add_document(doc)

writer.commit()
index.reload()
```

---

## Searching

### Basic Search

```python
# Get a searcher
searcher = index.searcher()

# Parse and execute query
query = index.parse_query("search terms", ["title", "body"])
results = searcher.search(query, limit=10)

# Process results
for score, doc_address in results.hits:
    doc = searcher.doc(doc_address)
    print(f"Score: {score}")
    print(f"Title: {doc.get_first('title')}")
```

### Query Syntax

| Syntax | Description | Example |
|--------|-------------|---------|
| `term` | Single term | `python` |
| `"phrase"` | Exact phrase | `"hello world"` |
| `field:term` | Field-specific | `title:python` |
| `term1 term2` | OR (default) | `python rust` |
| `+term` | Must contain | `+python +fast` |
| `-term` | Must not contain | `python -slow` |
| `term*` | Prefix match | `pyth*` |
| `term~2` | Fuzzy match | `pythn~2` |

### Multi-Field Search

```python
# Search across multiple fields
search_fields = ["title", "body", "tags"]
query = index.parse_query("python tutorial", search_fields)
results = searcher.search(query, limit=10)
```

---

## Retrieving Documents

```python
# Get document by address (from search results)
doc = searcher.doc(doc_address)

# Get field values
title = doc.get_first("title")        # First value
all_tags = doc.get_all("tags")        # All values (list)
doc_id = doc.get_first("doc_id")      # Integer field
```

---

## Reciprocal Rank Fusion (RRF)

Combine results from multiple queries:

```python
def rrf_search(index, queries: list[str], limit: int = 10) -> list:
    """Multi-query search with RRF fusion."""
    searcher = index.searcher()
    search_fields = ["title", "body", "tags"]
    
    # Track document ranks per query
    doc_ranks: dict[int, list[int]] = {}
    
    for query_str in queries:
        query = index.parse_query(query_str, search_fields)
        results = searcher.search(query, limit=limit * 2)
        
        for rank, (score, doc_addr) in enumerate(results.hits):
            doc = searcher.doc(doc_addr)
            doc_id = doc.get_first("doc_id")
            if doc_id not in doc_ranks:
                doc_ranks[doc_id] = []
            doc_ranks[doc_id].append(rank)
    
    # Calculate RRF scores
    k = 60  # Standard RRF constant
    rrf_scores = {}
    for doc_id, ranks in doc_ranks.items():
        rrf_scores[doc_id] = sum(1.0 / (k + r) for r in ranks)
    
    # Sort by RRF score
    return sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:limit]
```

---

## Complete Example

```python
#!/usr/bin/env python3
"""Complete Tantivy example."""

from pathlib import Path
import tantivy

# 1. Define schema
schema_builder = tantivy.SchemaBuilder()
schema_builder.add_integer_field("doc_id", stored=True, indexed=True)
schema_builder.add_text_field("title", stored=True)
schema_builder.add_text_field("content", stored=True)
schema = schema_builder.build()

# 2. Create index
INDEX_DIR = Path("example_index")
INDEX_DIR.mkdir(exist_ok=True)
index = tantivy.Index(schema, path=str(INDEX_DIR))

# 3. Index documents
writer = index.writer()

docs = [
    {"title": "Python Basics", "content": "Learn Python programming fundamentals."},
    {"title": "Rust Tutorial", "content": "Getting started with Rust language."},
    {"title": "Search Engines", "content": "How full-text search works with Python."},
]

for i, doc_data in enumerate(docs):
    doc = tantivy.Document(
        doc_id=i,
        title=doc_data["title"],
        content=doc_data["content"],
    )
    writer.add_document(doc)

writer.commit()
index.reload()

# 4. Search
searcher = index.searcher()
query = index.parse_query("Python", ["title", "content"])
results = searcher.search(query, limit=5)

print(f"Found {len(results.hits)} results:\n")
for score, doc_addr in results.hits:
    doc = searcher.doc(doc_addr)
    print(f"[{doc.get_first('doc_id')}] {doc.get_first('title')}")
    print(f"    Score: {score:.4f}")
    print(f"    Content: {doc.get_first('content')[:50]}...")
    print()
```

---

## Project Scripts Reference

### Index Manager

```bash
# Build index from scratch
uv run scripts/tantivy_index_manager.py build

# Sync index with files (incremental)
uv run scripts/tantivy_index_manager.py sync

# Watch for file changes
uv run scripts/tantivy_index_manager.py watch

# Show statistics
uv run scripts/tantivy_index_manager.py stats
```

### Search CLI

```bash
# Basic search
uv run scripts/tantivy_search.py search "query terms"

# Multi-query with RRF
uv run scripts/tantivy_search.py search "term1" "term2" "term3"

# Read document by ID
uv run scripts/tantivy_search.py read 0 1 2
```

### Agent Search

```bash
# Single query with AI agent
uv run scripts/tantivy_agent_search.py "How do subagents work?"

# Interactive mode
uv run scripts/tantivy_agent_search.py --interactive

# With index sync
uv run scripts/tantivy_agent_search.py --sync "What is context isolation?"
```

---

## Performance Tips

1. **Batch writes**: Add multiple documents before calling `commit()`
2. **Limit results**: Use reasonable `limit` values (10-100)
3. **Reload sparingly**: Only call `index.reload()` after commits
4. **Use stored fields wisely**: Only store fields you need to retrieve
5. **Index paths**: Use SSDs for index storage

---

## Common Patterns

### Incremental Updates with Hashing

```python
import hashlib

def compute_hash(content: str) -> str:
    return hashlib.md5(content.encode()).hexdigest()

# Track document hashes to detect changes
metadata = {"path": {"doc_id": 0, "hash": "abc123"}}

# Only re-index if content changed
new_hash = compute_hash(new_content)
if metadata.get(path, {}).get("hash") != new_hash:
    # Re-index document
    pass
```

### Search with Fallback

```python
def search_with_fallback(query: str, limit: int = 10):
    results = searcher.search(index.parse_query(query, fields), limit=limit)
    
    if not results.hits:
        # Try fuzzy search
        fuzzy_query = f"{query}~2"
        results = searcher.search(index.parse_query(fuzzy_query, fields), limit=limit)
    
    return results
```

---

## Resources

- [Tantivy GitHub](https://github.com/quickwit-oss/tantivy)
- [tantivy-py Documentation](https://github.com/quickwit-oss/tantivy-py)
- [Query Syntax Reference](https://docs.rs/tantivy/latest/tantivy/query/struct.QueryParser.html)
