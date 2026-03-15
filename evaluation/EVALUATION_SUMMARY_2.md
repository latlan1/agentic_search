# Evaluation Summary: Subagent Delegation Architecture

**Date**: 2026-03-02
**Test Set**: 5 questions on DeepAgents documentation
**Approach Tested**: Approach 3 (LangGraph + Tantivy) with parallel subagent delegation
**Baseline**: Approach 3 (direct tool access, no subagents) from 2026-02-22

---

## Architecture Change

The key change was replacing the single-agent direct-tool architecture with a **parallel subagent delegation** pattern:

- **Baseline**: Single agent with direct `search_docs`/`read_docs` tools, built via `create_deep_agent`
- **New**: Parent agent delegates to **2 parallel subagents** via `task` tool, built via `create_agent` with manual middleware stack

Three token optimizations were applied to fit within Anthropic's 30k input tokens/min rate limit:

1. Custom `task_description` on SubAgentMiddleware (~400 chars vs default 6,914 chars)
2. Stripped default middleware from subagents (`default_middleware=[]`)
3. Reduced from 3 to 2 parallel query delegations

This reduced per-query token consumption from **~46,000 to ~12,000 input tokens**.

---

## Per-Question Results

### New Architecture (Subagent Delegation)

| Question | Difficulty | Time | Hit Rate | Files Consulted |
|----------|------------|------|----------|-----------------|
| Q1: Subagents purpose/when NOT to use | Easy | 39.9s | 100% | deepagents-subagents.md, deepagents-middleware.md, deepagents-harness.md, deepagents-overview.md |
| Q2: Long-term memory configuration | Medium | 92.1s | 50% | deepagents-long-term-memory.md, deepagents-harness.md, deepagents-overview.md |
| Q3: HITL decision types | Easy | 82.0s | 100% | deepagents-human-in-the-loop.md, deepagents-cli.md |
| Q4: Skills vs tools difference | Medium | 76.2s | 100% | deepagents-skills.md, deepagents-cli.md, deepagents-quickstart.md, deepagents-customization.md |
| Q5: Research agent (multi-hop) | Hard | 106.2s | 100% | deepagents-subagents.md, deepagents-long-term-memory.md |
| **Average** | | **79.3s** | **90%** | |

### Baseline (Direct Tool, No Subagent)

| Question | Difficulty | Time | Hit Rate | Files Consulted |
|----------|------------|------|----------|-----------------|
| Q1: Subagents purpose/when NOT to use | Easy | 20.8s | 100% | deepagents-subagents.md, deepagents-overview.md |
| Q2: Long-term memory configuration | Medium | 29.6s | 100% | deepagents-long-term-memory.md, deepagents-backends.md, deepagents-harness.md, deepagents-overview.md |
| Q3: HITL decision types | Easy | 18.1s | 100% | deepagents-human-in-the-loop.md |
| Q4: Skills vs tools difference | Medium | 27.6s | 100% | deepagents-skills.md, deepagents-overview.md, deepagents-quickstart.md, deepagents-customization.md |
| Q5: Research agent (multi-hop) | Hard | 76.7s | 100% | deepagents-subagents.md, deepagents-long-term-memory.md + 3 others |
| **Average** | | **34.6s** | **100%** | |

---

## Head-to-Head Comparison

| Metric | Baseline (Direct) | New (Subagent) | Delta |
|--------|-------------------|----------------|-------|
| **Avg Time** | 34.6s | 79.3s | +129% (2.3x slower) |
| **Avg Hit Rate** | 100% | 90% | -10% |
| **Errors** | 0 | 0 (when rate limit respected) | -- |
| **Tokens/Query** | ~46,000 | ~12,000 | -74% |
| **Parallel Queries** | No | Yes (2 concurrent) | -- |

---

## Analysis

### Why is the subagent architecture slower?

The subagent delegation pattern adds overhead at multiple levels:

1. **Orchestration cost**: The parent agent must formulate 2 query variations, dispatch them via `task` tool calls, wait for both to complete, then consolidate results
2. **Double LLM calls**: Each subagent makes its own LLM call for search planning, plus the parent makes calls for delegation and consolidation
3. **Sequential phases**: Parent plans -> subagents execute in parallel -> parent consolidates (3 serial LLM round-trips minimum vs 1-2 for direct)

### Why did Q2 hit rate drop to 50%?

Q2 requires finding content in both `deepagents-long-term-memory.md` and `deepagents-backends.md`. The subagent architecture found the first file but missed `deepagents-backends.md`. This is likely because:

- The 2 parallel query variations did not produce sufficiently different keyword coverage
- The BM25 ranking for "backends" was lower than the read threshold
- With direct tool access, the single agent had more flexibility to iteratively refine its search

### Token efficiency vs latency tradeoff

The subagent architecture achieved its primary goal: **74% reduction in tokens per query** (from ~46k to ~12k), bringing it safely within Anthropic's 30k tokens/min rate limit. However, this came at the cost of 2.3x higher latency and a 10% hit rate reduction.

### Rate limiting remains the main operational challenge

- Running 5 questions sequentially with 90s delays still caused Q2-Q4 to fail with 429 errors
- Only 120s delays between individual runs (separate process invocations) worked reliably
- The agent script does not catch rate limit exceptions gracefully (unhandled `anthropic.RateLimitError` crashes the process)

---

## Recommendations

1. **For low-latency use cases**: Use the baseline direct-tool architecture. It is faster and more accurate for this corpus size (12 files).

2. **For token-constrained environments**: The subagent architecture is the better choice when operating near rate limits or with limited token budgets.

3. **Future improvements**:
   - Add retry logic with exponential backoff for 429 errors in `tantivy_agent_search.py`
   - Experiment with 3 query variations (if rate limit headroom allows) to improve recall
   - Consider hybrid approach: direct tools for simple queries, subagent delegation for complex multi-hop questions

---

## Result Files

| File | Description |
|------|-------------|
| `results_approach3_subagent_final.json` | Consolidated new architecture results (all 5 questions) |
| `results_20260222_214309.json` | Baseline results (direct tool, pre-subagent) |
| `results_20260222_214009.json` | Approach 1 (DeepAgent) baseline results |
| `EVALUATION_SUMMARY.md` | Previous evaluation summary (baseline only) |
| `EVAL_SUMMARY.md` | This file |
