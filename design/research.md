# Research Report: Agentic Search Implementation Analysis

## Executive Summary

This report provides an in-depth analysis of the `AGENTS.md` file and its associated codebase, which implements **two distinct approaches** for agentic search over Markdown documentation corpora. Both approaches are inspired by Benjamin Anderson's article ["Agentic Search for Dummies"](https://benanderson.work/blog/agentic-search-for-dummies/) and demonstrate production-quality patterns for enabling AI agents to search and retrieve information from document collections.

**Key Distinction**: The project implements two separate, independent approaches:
1. **Approach 1 (DeepAgent)**: Uses file system tools (ls, grep, read_file) for dynamic search
2. **Approach 2 (LangGraph + Tantivy)**: Uses explicit search/read tools backed by a full-text index

Both approaches use **GPT-5 via GitHub Copilot** as the LLM engine for formulating final responses with citations.

---

## 1. Project Overview

### 1.1 Purpose

The project implements two agentic search systems that allow AI agents to:
- Search a corpus of Markdown documentation files
- Retrieve relevant documents based on queries
- Read full document content on demand
- Generate final answers with citations using GPT-5

### 1.2 Inspiration

The approach is based on the "Agentic Search for Dummies" article, which advocates for:
- Full-text search with offline document augmentation
- Separation of `search()` and `read()` operations
- Multi-query fusion using Reciprocal Rank Fusion (RRF)
- Using Tantivy for fast, in-process full-text search

### 1.3 Key Principle: Use `uv` for Python Execution

All Python scripts must be run using `uv` instead of `python` directly:

```bash
# Correct
uv run scripts/build_tantivy_index.py
uv run scripts/tantivy_search.py search "query"

# Incorrect - do not use
python scripts/build_tantivy_index.py
```

---

## 2. Two Distinct Approaches

### 2.1 Comparison Table

| Feature | Approach 1 (DeepAgent) | Approach 2 (LangGraph + Tantivy) |
|---------|------------------------|----------------------------------|
| **Technology** | deepagents library | LangGraph + tantivy-py |
| **Search method** | File system tools (ls, grep, read_file) | Tantivy search/read tools |
| **Index required** | No | Yes (Tantivy) |
| **Ranked results** | No | Yes (BM25 + RRF) |
| **Multi-query fusion** | No | Yes |
| **Setup complexity** | Low | Medium |
| **Search speed** | Slower (file I/O) | Fast (indexed) |
| **Auto-update on new docs** | Yes | Requires rebuild |
| **Best for** | Small, dynamic corpus | Large, stable corpus |
| **LLM engine** | GPT-5 via GitHub Copilot | GPT-5 via GitHub Copilot |

### 2.2 Approach 1: DeepAgent with File System

**Concept**: Use the `deepagents` library to create an agent that treats data folders as a virtual file system. The agent uses built-in tools to search and retrieve documents.

**Tools available**:
- `ls` - List directory contents
- `grep` - Search file contents
- `read_file` - Read file content

**Advantages**:
- Simple setup - no index building required
- Automatically updated when new documents are added
- Leverages DeepAgent's planning and context management

**Script**: `scripts/deepagent_search.py`

### 2.3 Approach 2: LangGraph with Tantivy Search/Read Tools

**Concept**: Build a LangGraph agent that uses explicit `search` and `read` tools backed by a Tantivy full-text index.

**Tools available**:
- `search_docs(queries, limit)` - Search with ranked results
- `read_docs(doc_ids)` - Read full document content

**Advantages**:
- Ranked search results with relevance scores
- Efficient retrieval without reading every file
- Multi-query support with Reciprocal Rank Fusion (RRF)

**Scripts**:
- `scripts/build_tantivy_index.py` - Build the index
- `scripts/tantivy_search.py` - CLI for search/read
- `scripts/langgraph_search.py` - LangGraph agent

---

## 3. Architecture Overview

### 3.1 Folder Structure

```
data/
  deepagents_raw_md/           # 12 Markdown documents (~3,227 lines total)
    deepagents-overview.md
    deepagents-quickstart.md
    deepagents-subagents.md
    deepagents-long-term-memory.md
    deepagents-middleware.md
    deepagents-customization.md
    deepagents-cli.md
    deepagents-backends.md
    deepagents-harness.md
    deepagents-human-in-the-loop.md
    deepagents-skills.md
    deepagents-products.md
  langgraph_raw_md/            # 29 additional LangGraph docs
augmented_jsonl_index/         # LLM-augmented index files
  deepagents_index.jsonl       # Keywords/descriptions for deepagents docs
  langgraph_index.jsonl        # Keywords/descriptions for langgraph docs
tantivy_index/                 # Tantivy full-text index (created by build script)
scripts/
  build_tantivy_index.py       # Build the Tantivy index
  tantivy_search.py            # Search/Read CLI
  deepagent_search.py          # Approach 1: DeepAgent implementation
  langgraph_search.py          # Approach 2: LangGraph implementation
.env                           # Environment variables (GitHub Copilot, GPT-5)
```

### 3.2 Environment Configuration

The `.env` file contains credentials for GPT-5 via GitHub Copilot:

```bash
# GitHub Copilot credentials for GPT-5
GITHUB_TOKEN=your_github_copilot_token_here
LLM_MODEL=gpt-5
LLM_PROVIDER=github-copilot

# Optional: Additional API keys
ANTHROPIC_API_KEY=your_anthropic_key_here
OPENAI_API_KEY=your_openai_key_here
```

---

## 4. Corpus Analysis

### 4.1 Document Collection

The primary corpus consists of **12 deepagents documentation files** covering:

| Document | Lines | Topic |
|----------|-------|-------|
| `deepagents-cli.md` | 494 | Command-line interface usage |
| `deepagents-subagents.md` | 469 | Subagent delegation and context isolation |
| `deepagents-backends.md` | 358 | Storage backend implementations |
| `deepagents-customization.md` | 357 | Agent customization options |
| `deepagents-human-in-the-loop.md` | 305 | Human oversight patterns |
| `deepagents-long-term-memory.md` | 275 | Persistent memory across threads |
| `deepagents-skills.md` | 230 | Agent skill definitions |
| `deepagents-harness.md` | 217 | Testing harness |
| `deepagents-middleware.md` | 204 | Middleware architecture |
| `deepagents-quickstart.md` | 132 | Getting started guide |
| `deepagents-products.md` | 104 | Product overview |
| `deepagents-overview.md` | 82 | Library introduction |

### 4.2 Content Characteristics

The documents are **LangChain/LangGraph documentation** in MDX format containing:
- Code examples (Python)
- Mermaid diagrams
- Custom components (`<Card>`, `<CardGroup>`, `<ParamField>`, etc.)
- API references and configuration options
- Best practices and troubleshooting guides

### 4.3 Key Concepts Covered

1. **Deep Agents**: A standalone library for building sophisticated AI agents
2. **Subagent Delegation**: Spawning specialized agents for context isolation
3. **Long-term Memory**: Persistent storage across conversation threads
4. **File System Tools**: `ls`, `read_file`, `write_file`, `edit_file` for context management
5. **Planning**: Built-in `write_todos` tool for task decomposition

---

## 5. Tantivy Search Implementation (Approach 2)

### 5.1 Technology Choice

The implementation uses **Tantivy** (via `tantivy-py`), a Rust-based full-text search engine. Key benefits:

| Feature | Benefit |
|---------|---------|
| **Speed** | Rust-native performance, millisecond queries |
| **BM25 Ranking** | Industry-standard relevance scoring |
| **In-process** | No external server (unlike Elasticsearch) |
| **Easy installation** | `uv add tantivy` |

### 5.2 Index Schema

The Tantivy index stores 6 fields per document:

| Field | Type | Indexed | Stored | Purpose |
|-------|------|---------|--------|---------|
| `doc_id` | INT | Yes | Yes | Unique identifier for retrieval |
| `path` | TEXT | No | Yes | File path for display |
| `filename` | TEXT | Yes | Yes | Searchable filename |
| `content` | TEXT | Yes | Yes | Full document text |
| `keywords` | TEXT | Yes | Yes | LLM-generated keywords |
| `description` | TEXT | Yes | Yes | LLM-generated summary |

### 5.3 Offline Document Augmentation

The `augmented_jsonl_index/` folder contains JSONL files with LLM-generated metadata:

```json
{
  "filename": "deepagents-overview.md",
  "keywords": [
    "deep agents library",
    "LangGraph agents",
    "multi-step task automation",
    "subagent delegation",
    ...
  ],
  "description": "Overview of the deepagents library, a Python framework for building sophisticated agents..."
}
```

**Why augment?**
1. Improves search recall when queries don't match exact document text
2. Provides preview snippets for search results
3. Keywords can include semantic variations and synonyms

---

## 6. Search/Read API Separation

### 6.1 Core Design Principle

The implementation follows a critical design pattern from the article:

> "This API separates searching from reading. This is important because if you forced an AI to read every document it searched for, the context window would rapidly fill up with irrelevant or repeated documents."

### 6.2 API Functions

#### `search_docs(queries: list[str], limit: int = 10) -> str`

Returns a **results page** without full content:
- `doc_id` - For subsequent read() calls
- `filename` - Human-readable name
- `description` - Preview snippet (from augmentation)
- `score` - RRF score

#### `read_docs(doc_ids: list[int]) -> str`

Returns **full document content** for selected documents.

### 6.3 Agent Workflow (Approach 2)

```
User Query
    |
    v
[LangGraph Agent] --search_docs(["query1", "query2"])--> [Tantivy Index]
    |
    v
[Results Page: doc_id, filename, description]
    |
Agent decides which docs look relevant
    |
    v
[LangGraph Agent] --read_docs([doc_id_1, doc_id_3])--> [Tantivy Index]
    |
    v
[Full content for selected docs]
    |
    v
[GPT-5 generates answer with citations]
```

---

## 7. Reciprocal Rank Fusion (RRF)

### 7.1 Multi-Query Support

The search function accepts **multiple queries**, enabling "spray and pray" strategies:

```bash
uv run scripts/tantivy_search.py search "memory persistence" "long term storage" "agent state"
```

### 7.2 RRF Algorithm

Results from multiple queries are fused using Reciprocal Rank Fusion:

```
RRF_score(doc) = Σ 1/(k + rank_i)
```

Where:
- `k = 60` (standard constant)
- `rank_i` = document's rank in query `i`

### 7.3 Why RRF?

| Benefit | Explanation |
|---------|-------------|
| **Improved recall** | Multiple query variations increase chances of hitting relevant docs |
| **Rank normalization** | Combines results from queries with different score distributions |
| **Simple & effective** | No tuning required, works out of the box |

### 7.4 Implementation

```python
# Collect ranks from each query
for query_str in queries:
    query = self.index.parse_query(query_str, search_fields)
    results = self.searcher.search(query, limit=limit * 2).hits
    
    for rank, (score, doc_addr) in enumerate(results):
        doc_ranks[doc_id].append(rank)

# Calculate RRF scores
k = 60
for doc_id, ranks in doc_ranks.items():
    rrf_scores[doc_id] = sum(1.0 / (k + r) for r in ranks)

# Sort by RRF score descending
sorted_doc_ids = sorted(rrf_scores.keys(), key=lambda d: rrf_scores[d], reverse=True)
```

---

## 8. LLM Tool Integration

### 8.1 Tool Definitions

The `search_docs` and `read_docs` tools are implemented directly as LangChain `@tool` decorators:

```python
@tool
def search_docs(queries: list[str], limit: int = 10) -> str:
    """Search the documentation corpus for relevant documents."""
    results = search_index.search(queries, limit=limit)
    # Format and return results
    ...

@tool
def read_docs(doc_ids: list[int]) -> str:
    """Read the full content of documents by their doc_id."""
    documents = search_index.read(doc_ids)
    # Format and return content
    ...
```

### 8.2 GPT-5 Integration

Both approaches use GPT-5 via GitHub Copilot as the LLM engine:

```python
llm = ChatOpenAI(
    model=os.getenv("LLM_MODEL", "gpt-5"),
    api_key=os.getenv("GITHUB_TOKEN"),
    base_url="https://api.githubcopilot.com/v1",
)
```

---

## 9. CLI Interface

### 9.1 Commands

```bash
# Build the index (Approach 2 only)
uv run scripts/build_tantivy_index.py

# Search with single or multiple queries (Approach 2)
uv run scripts/tantivy_search.py search "subagents delegation"
uv run scripts/tantivy_search.py search "memory" "persistence" "storage" -n 5

# Read specific documents by ID (Approach 2)
uv run scripts/tantivy_search.py read 0 3 5

# Use DeepAgent for search (Approach 1)
uv run scripts/deep_agent_search.py "How do I create a subagent?"

# Use LangGraph agent for search (Approach 2)
uv run scripts/tantivy_agent_search.py "What is context quarantine?"
```

### 9.2 Example Output

```
$ uv run scripts/tantivy_search.py search "subagents" "delegation"
Found 5 results:

[1] deepagents-subagents.md (score: 0.0323)
    Path: data/deepagents_raw_md/deepagents-subagents.md
    Guide to subagent delegation in deepagents, covering how to spawn...

[2] deepagents-overview.md (score: 0.0161)
    Path: data/deepagents_raw_md/deepagents-overview.md
    Overview of the deepagents library, a Python framework for building...
```

---

## 10. Design Decisions Analysis

### 10.1 Why Not Embeddings?

The article explicitly addresses this:

| Embedding Weakness | Full-text Advantage |
|--------------------|---------------------|
| Worse with long documents | Works well with any document length |
| Requires chunking | No chunking needed |
| Adds inference overhead | Fast CPU-based search |
| Complex ranking fusion | Simple RRF fusion |
| "Vibe-based" matching | Predictable keyword matching |

For **agentic search**, full-text is advantageous because:
- Agents can write many query variations
- Agents can write longer, more exhaustive queries
- Agents can retry when initial queries fail
- Predictable results help agents learn search patterns

### 10.2 Why Separate Search and Read?

**Context window efficiency**: Without separation, every search would dump full document content into the agent's context, leading to:
- Rapid context exhaustion
- Repeated/irrelevant content
- Poor agent performance

The two-step approach mimics how humans use Google:
1. Scan results page (titles, snippets)
2. Click only on promising results

### 10.3 Why Two Approaches?

| Use Case | Best Approach |
|----------|---------------|
| Small corpus (<50 docs) | Approach 1 (DeepAgent) |
| Large corpus (100+ docs) | Approach 2 (LangGraph + Tantivy) |
| Frequently changing docs | Approach 1 (DeepAgent) |
| Stable documentation | Approach 2 (LangGraph + Tantivy) |
| Quick prototyping | Approach 1 (DeepAgent) |
| Production deployment | Approach 2 (LangGraph + Tantivy) |

---

## 11. Relationship to Deep Agents Library

### 11.1 Context

The corpus being indexed is documentation for the **deepagents** library, which itself implements:
- Planning and task decomposition (`write_todos` tool)
- Context management via file system tools
- Subagent spawning for context isolation
- Long-term memory via LangGraph Store

### 11.2 Meta-Level Observation

There's an interesting recursive relationship:
- The **search system** provides tools (`search`, `read`) for agents
- The **deepagents library** being searched provides similar tools (`ls`, `read_file`, `write_file`)
- Both address the same fundamental problem: **context management**

### 11.3 Potential Integration (But do NOT implment unless explicitly asked)

The Tantivy search index could be integrated as a tool within a deep agent:

```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    tools=[search_docs, read_docs],
    system_prompt="You can search the deepagents documentation..."
)
```

---

## 12. Current State and Gaps

### 12.1 What Exists

- Complete `AGENTS.md` specification with both approaches
- Tantivy build and search scripts (as code blocks)
- LangGraph agent implementation
- DeepAgent implementation
- CLI interface design
- Tool definitions for LLM integration
- `augmented_jsonl_index/` directory created

### 12.2 What's Missing

| Gap | Status |
|-----|--------|
| Augmentation JSONL files | Not yet generated |
| `scripts/` directory | Scripts exist as code blocks, not as files |
| `tantivy_index/` | Not built (requires running build script) |
| `.env` file | Template provided, credentials needed |

### 12.3 To Make Operational

1. Install dependencies: `uv add tantivy langgraph langchain-openai python-dotenv deepagents`
2. Create `.env` file with GitHub Copilot credentials
3. Extract scripts from AGENTS.md into `scripts/` directory
4. Generate augmentation JSONL files for each corpus
5. Build the Tantivy index: `uv run scripts/build_tantivy_index.py`

---

## 13. Key Takeaways

### 13.1 Core Principles

1. **Use `uv`** - All Python execution via `uv run`
2. **Separate search from read** - Critical for context efficiency
3. **Use full-text search** - Simple, predictable, fast
4. **Augment offline** - LLM-generated keywords improve recall
5. **Support multi-query** - RRF fusion handles vocabulary mismatch
6. **Two approaches** - Choose based on corpus size and update frequency

### 13.2 Design Philosophy

The implementation embodies a "less is more" philosophy:
- No embeddings (simpler architecture)
- No external servers (in-process Tantivy)
- No complex ranking (BM25 + RRF)
- Clear separation of concerns (search vs read)
- Direct tool implementation (no MCP overhead)

### 13.3 Applicability

This pattern is applicable to:
- Documentation search agents
- Knowledge base assistants
- Research tools
- Any corpus-based Q&A system

---

## 14. Recommendations

### 14.1 Immediate Actions

1. Extract scripts from AGENTS.md into `scripts/` directory
2. Generate the augmentation JSONL files
3. Build the Tantivy index
4. Test both approaches with sample queries

### 14.2 Enhancements

1. **Add error handling** - Better error messages for missing index
2. **Add tests** - Unit tests for search ranking logic
3. **Add caching** - Cache searcher for repeated queries
4. **Add filtering** - Filter by document type/date/metadata

### 14.3 Production Considerations

1. **Index updates** - Implement incremental indexing for new documents
2. **Monitoring** - Add query logging and performance metrics
3. **Scaling** - Consider distributed Tantivy for large corpora
4. **Security** - Validate queries to prevent injection attacks

---

## 15. Conclusion

The `AGENTS.md` implementation provides a solid, well-designed foundation for agentic search with two distinct approaches:

1. **DeepAgent Approach**: Simple, dynamic, file-system based
2. **LangGraph + Tantivy Approach**: Production-ready, ranked, indexed

Key innovations:
- Two-function API (search/read) for context efficiency
- Multi-query RRF for improved recall
- Offline augmentation for better searchability
- GPT-5 via GitHub Copilot for response generation with citations

The separation of concerns and predictable behavior make both approaches well-suited for LLM-based agents that need to reliably find and retrieve information from document corpora.

---

*Report generated: February 22, 2026*
*Based on analysis of: AGENTS.md, data/deepagents_raw_md/, data/langgraph_raw_md/, augmented_jsonl_index/*
