# Agentic Search Evaluation Summary

**Date**: 2026-02-22 (baseline), 2026-03-02 (subagent update)  
**Test Set**: 5 questions on DeepAgents documentation  
**Approaches Tested**: Approach 1 (DeepAgent), Approach 3 Baseline (direct tool), Approach 3 Subagent (parallel delegation)  
**Note**: Approach 2 (DeepAgents CLI) is interactive and was not included in automated testing

---

## Overall Results

| Metric | Approach 1 (DeepAgent) | Approach 3 Baseline (Direct Tool) | Approach 3 Subagent (Parallel Delegation) |
|--------|------------------------|-----------------------------------|-------------------------------------------|
| **Avg Time** | 32.7s | 34.6s | 79.3s |
| **Avg Hit Rate** | 100% | 100% | 90% |
| **Files per Query** | 7-12 | 1-5 | 2-4 |
| **Response Quality** | 2.0/2 | 2.0/2 | 1.8/2 |
| **Errors** | 0 | 0 | 0 (with 120s inter-query delay) |

---

## Per-Question Results

| Question | Difficulty | Ap1 Time | Ap1 Hit | Ap3 Baseline Time | Ap3 Baseline Hit | Ap3 Subagent Time | Ap3 Subagent Hit |
|----------|------------|----------|---------|-------------------|------------------|-------------------|------------------|
| Q1: Subagents purpose/when NOT to use | Easy | 20.7s | 100% (12 files) | 20.8s | 100% (2 files) | 39.9s | 100% (4 files) |
| Q2: Long-term memory configuration | Medium | 28.4s | 100% (11 files) | 29.6s | 100% (4 files) | 92.1s | 50% (3 files) |
| Q3: HITL decision types | Easy | 17.7s | 100% (7 files) | 18.1s | 100% (1 file) | 82.0s | 100% (2 files) |
| Q4: Skills vs tools difference | Medium | 41.0s | 100% (12 files) | 27.6s | 100% (4 files) | 76.2s | 100% (4 files) |
| Q5: Research agent (multi-hop) | Hard | 55.7s | 100% (12 files) | 76.7s | 100% (5 files) | 106.2s | 100% (2 files) |

---

## Response Quality Assessment

Based on reviewing the actual responses from both approaches:

### Q1: Subagents (Easy, Single-hop)
**Expected Key Points**: Context bloat, context quarantine, when NOT to use (single-step tasks, need intermediate context, overhead outweighs benefits)

| Approach | Score | Notes |
|----------|-------|-------|
| Approach 1 | 2/2 | Comprehensive coverage of purpose and all three "when NOT to use" scenarios |
| Approach 3 Baseline | 2/2 | Excellent coverage with proper citations, clear structure |
| Approach 3 Subagent | 2/2 | Covered all key points; consulted 4 files via parallel subagent queries |

### Q2: Long-term Memory (Medium, Single-hop)
**Expected Key Points**: CompositeBackend, StoreBackend, /memories/ path routing, cross-thread persistence, LangGraph Store

| Approach | Score | Notes |
|----------|-------|-------|
| Approach 1 | 2/2 | Full coverage including code examples |
| Approach 3 Baseline | 2/2 | Clear configuration steps with proper code examples |
| Approach 3 Subagent | 1/2 | Found deepagents-long-term-memory.md but missed deepagents-backends.md (50% hit rate); response covered core concepts but lacked CompositeBackend routing detail |

### Q3: HITL Decisions (Easy, Single-hop)
**Expected Key Points**: approve, edit, reject, allowed_decisions configuration

| Approach | Score | Notes |
|----------|-------|-------|
| Approach 1 | 2/2 | All three decision types clearly explained |
| Approach 3 Baseline | 2/2 | Concise and accurate with code example |
| Approach 3 Subagent | 2/2 | All three decision types covered with proper citations |

### Q4: Skills vs Tools (Medium, Single-hop)
**Expected Key Points**: SKILL.md, progressive disclosure, context reduction, bundled capabilities, when to use each

| Approach | Score | Notes |
|----------|-------|-------|
| Approach 1 | 2/2 | Comprehensive comparison with usage guidelines |
| Approach 3 Baseline | 2/2 | Clear distinction with practical examples |
| Approach 3 Subagent | 2/2 | Thorough comparison; consulted 4 files including deepagents-skills.md and deepagents-customization.md |

### Q5: Research Agent (Hard, Multi-hop)
**Expected Key Points**: Subagent configuration (name, description, system_prompt, tools), CompositeBackend, StoreBackend, /memories/ routing, concise return values

| Approach | Score | Notes |
|----------|-------|-------|
| Approach 1 | 2/2 | Full integration example combining both features |
| Approach 3 Baseline | 2/2 | Detailed step-by-step configuration with code |
| Approach 3 Subagent | 2/2 | Combined subagent and memory concepts correctly from 2 source files |

---

## Summary Scores

| Approach | Q1 | Q2 | Q3 | Q4 | Q5 | Total | Avg |
|----------|----|----|----|----|----|----|-----|
| **Approach 1** | 2 | 2 | 2 | 2 | 2 | 10/10 | 2.0 |
| **Approach 3 Baseline** | 2 | 2 | 2 | 2 | 2 | 10/10 | 2.0 |
| **Approach 3 Subagent** | 2 | 1 | 2 | 2 | 2 | 9/10 | 1.8 |

---

## Key Observations

### Approach 1 (DeepAgent with Virtual Filesystem)

**Strengths**:
- No index required - works directly with files
- Comprehensive file exploration (reads many files)
- Good for dynamic corpora that change frequently
- Consistent performance across query types

**Weaknesses**:
- Higher token usage (reads more files than necessary)
- Files consulted per query: 7-12 (often reads entire corpus)
- No ranking - relies on LLM to filter relevant content

### Approach 3 (LangGraph + Tantivy) — Baseline (Direct Tool)

**Strengths**:
- Efficient retrieval (1-5 files per query)
- BM25 ranking surfaces most relevant documents first
- Two-phase search (preview then read) prevents context bloat
- Numbered citations with source links

**Weaknesses**:
- Requires index building (one-time setup)
- Slower on complex multi-hop queries (Q5: 76.7s vs 55.7s)
- Depends on keyword matching (may miss semantic matches)

### Approach 3 (LangGraph + Tantivy) — Subagent Delegation

**Strengths**:
- 74% reduction in tokens per query (~12k vs ~46k), fits within 30k/min rate limit
- Parallel subagent queries with synonym/concept variations improve recall breadth
- Clean separation of search orchestration (parent) from search execution (subagents)
- Same two-phase search and numbered citations as baseline

**Weaknesses**:
- 2.3x slower than baseline (79.3s vs 34.6s avg) due to multi-round LLM orchestration
- Hit rate dropped from 100% to 90% (Q2 missed deepagents-backends.md)
- Requires 120s inter-query delays to avoid 429 rate limit errors
- No retry/backoff logic for rate limit errors (unhandled crash)

### Approach 2 (DeepAgents CLI) - Not Tested
- Would require manual interactive testing
- Best for exploratory sessions with human-in-the-loop
- Session persistence across restarts

---

## Recommendations

| Use Case | Recommended Approach |
|----------|---------------------|
| **Production RAG system** | Approach 3 Baseline (Tantivy) - efficient, ranked results |
| **Token-constrained environments** | Approach 3 Subagent - 74% fewer tokens per query |
| **Dynamic corpus with frequent updates** | Approach 1 (DeepAgent) - no index maintenance |
| **Interactive exploration** | Approach 2 (DeepAgents CLI) |
| **Multi-hop reasoning** | Approach 1 or 3 Baseline (both perform well) |
| **Low token budget** | Approach 3 Subagent (fewer tokens) or Baseline (fewer files) |
| **Simple setup** | Approach 1 (no dependencies beyond LLM) |
| **Lowest latency** | Approach 3 Baseline or Approach 1 |

---

## Files Generated

- `evaluation/results_20260222_214009.json` - Approach 1 raw results
- `evaluation/results_20260222_214309.json` - Approach 3 Baseline raw results
- `evaluation/results_approach3_subagent_final.json` - Approach 3 Subagent consolidated results
- `evaluation/EVALUATION_SUMMARY.md` - This summary
- `evaluation/EVAL_SUMMARY.md` - Detailed subagent vs baseline comparison

---

## Next Steps

1. [ ] Add retry logic with exponential backoff for 429 errors in `tantivy_agent_search.py`
2. [ ] Run Approach 2 (DeepAgents CLI) manually for comparison
3. [ ] Test with larger question set (20+ questions)
4. [ ] Add timing breakdown (search vs LLM generation)
5. [ ] Test with LangGraph documentation corpus
6. [ ] Evaluate citation accuracy (do cited files contain the claimed information?)
7. [ ] Experiment with 3 parallel subagent queries (if rate limit headroom allows)
