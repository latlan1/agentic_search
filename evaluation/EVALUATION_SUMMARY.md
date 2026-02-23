# Agentic Search Evaluation Summary

**Date**: 2026-02-22  
**Test Set**: 5 questions on DeepAgents documentation  
**Approaches Tested**: Approach 1 (DeepAgent) and Approach 3 (Tantivy Agent)  
**Note**: Approach 2 (DeepAgents CLI) is interactive and was not included in automated testing

---

## Overall Results

| Metric | Approach 1 (DeepAgent) | Approach 3 (Tantivy) |
|--------|------------------------|----------------------|
| **Avg Time** | 32.7s | 34.6s |
| **Avg Hit Rate** | 100% | 100% |
| **Files per Query** | 7-12 | 1-5 |
| **Errors** | 0 | 0 |

---

## Per-Question Results

| Question | Difficulty | Approach 1 Time | Approach 1 Hit | Approach 3 Time | Approach 3 Hit |
|----------|------------|-----------------|----------------|-----------------|----------------|
| Q1: Subagents purpose/when NOT to use | Easy | 20.7s | 100% (12 files) | 20.8s | 100% (2 files) |
| Q2: Long-term memory configuration | Medium | 28.4s | 100% (11 files) | 29.6s | 100% (4 files) |
| Q3: HITL decision types | Easy | 17.7s | 100% (7 files) | 18.1s | 100% (1 file) |
| Q4: Skills vs tools difference | Medium | 41.0s | 100% (12 files) | 27.6s | 100% (4 files) |
| Q5: Research agent (multi-hop) | Hard | 55.7s | 100% (12 files) | 76.7s | 100% (5 files) |

---

## Response Quality Assessment

Based on reviewing the actual responses from both approaches:

### Q1: Subagents (Easy, Single-hop)
**Expected Key Points**: Context bloat, context quarantine, when NOT to use (single-step tasks, need intermediate context, overhead outweighs benefits)

| Approach | Score | Notes |
|----------|-------|-------|
| Approach 1 | 2/2 | Comprehensive coverage of purpose and all three "when NOT to use" scenarios |
| Approach 3 | 2/2 | Excellent coverage with proper citations, clear structure |

### Q2: Long-term Memory (Medium, Single-hop)
**Expected Key Points**: CompositeBackend, StoreBackend, /memories/ path routing, cross-thread persistence, LangGraph Store

| Approach | Score | Notes |
|----------|-------|-------|
| Approach 1 | 2/2 | Full coverage including code examples |
| Approach 3 | 2/2 | Clear configuration steps with proper code examples |

### Q3: HITL Decisions (Easy, Single-hop)
**Expected Key Points**: approve, edit, reject, allowed_decisions configuration

| Approach | Score | Notes |
|----------|-------|-------|
| Approach 1 | 2/2 | All three decision types clearly explained |
| Approach 3 | 2/2 | Concise and accurate with code example |

### Q4: Skills vs Tools (Medium, Single-hop)
**Expected Key Points**: SKILL.md, progressive disclosure, context reduction, bundled capabilities, when to use each

| Approach | Score | Notes |
|----------|-------|-------|
| Approach 1 | 2/2 | Comprehensive comparison with usage guidelines |
| Approach 3 | 2/2 | Clear distinction with practical examples |

### Q5: Research Agent (Hard, Multi-hop)
**Expected Key Points**: Subagent configuration (name, description, system_prompt, tools), CompositeBackend, StoreBackend, /memories/ routing, concise return values

| Approach | Score | Notes |
|----------|-------|-------|
| Approach 1 | 2/2 | Full integration example combining both features |
| Approach 3 | 2/2 | Detailed step-by-step configuration with code |

---

## Summary Scores

| Approach | Q1 | Q2 | Q3 | Q4 | Q5 | Total | Avg |
|----------|----|----|----|----|----|----|-----|
| **Approach 1** | 2 | 2 | 2 | 2 | 2 | 10/10 | 2.0 |
| **Approach 3** | 2 | 2 | 2 | 2 | 2 | 10/10 | 2.0 |

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

### Approach 3 (LangGraph + Tantivy)

**Strengths**:
- Efficient retrieval (1-5 files per query)
- BM25 ranking surfaces most relevant documents first
- Two-phase search (preview then read) prevents context bloat
- Numbered citations with source links

**Weaknesses**:
- Requires index building (one-time setup)
- Slower on complex multi-hop queries (Q5: 76.7s vs 55.7s)
- Depends on keyword matching (may miss semantic matches)

### Approach 2 (DeepAgents CLI) - Not Tested
- Would require manual interactive testing
- Best for exploratory sessions with human-in-the-loop
- Session persistence across restarts

---

## Recommendations

| Use Case | Recommended Approach |
|----------|---------------------|
| **Production RAG system** | Approach 3 (Tantivy) - efficient, ranked results |
| **Dynamic corpus with frequent updates** | Approach 1 (DeepAgent) - no index maintenance |
| **Interactive exploration** | Approach 2 (DeepAgents CLI) |
| **Multi-hop reasoning** | Approach 1 or 3 (both perform well) |
| **Low token budget** | Approach 3 (fewer files read) |
| **Simple setup** | Approach 1 (no dependencies beyond LLM) |

---

## Files Generated

- `evaluation/results_20260222_214009.json` - Approach 1 raw results
- `evaluation/results_20260222_214309.json` - Approach 3 raw results
- `evaluation/EVALUATION_SUMMARY.md` - This summary

---

## Next Steps

1. [ ] Run Approach 2 (DeepAgents CLI) manually for comparison
2. [ ] Test with larger question set (20+ questions)
3. [ ] Add timing breakdown (search vs LLM generation)
4. [ ] Test with LangGraph documentation corpus
5. [ ] Evaluate citation accuracy (do cited files contain the claimed information?)
