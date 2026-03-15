#!/usr/bin/env python3
"""
Evaluation script for comparing 3 agentic search approaches.

Metrics collected:
- Chunk hit rate: Which reference files were consulted
- Response score: 0 (poor), 1 (adequate), 2 (excellent)
- Time to complete: Wall clock seconds

Usage:
    # Run all approaches on all questions
    uv run evaluation/run_evaluation.py

    # Run specific approach
    uv run evaluation/run_evaluation.py --approach 1
    uv run evaluation/run_evaluation.py --approach 3

    # Run specific question
    uv run evaluation/run_evaluation.py --question Q1

    # Run with delay between questions (avoids 30k tokens/min rate limit)
    uv run evaluation/run_evaluation.py --approach 3 --delay 90

    # Skip approaches that require API keys (dry run)
    uv run evaluation/run_evaluation.py --dry-run
"""

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))


@dataclass
class EvaluationResult:
    """Result of running one approach on one question."""
    question_id: str
    approach: int
    question: str
    response: str
    time_seconds: float
    files_consulted: list[str] = field(default_factory=list)
    chunk_hit_rate: float = 0.0
    response_score: int = -1  # -1 = not yet scored
    error: Optional[str] = None
    stderr: Optional[str] = None  # Captured stderr for debugging


def load_test_set() -> dict:
    """Load the test set JSON."""
    test_set_path = PROJECT_ROOT / "evaluation" / "test_set.json"
    with open(test_set_path) as f:
        return json.load(f)


def get_reference_files(test_case: dict) -> set[str]:
    """Extract unique reference file names from a test case."""
    files = set()
    for chunk in test_case.get("reference_chunks", []):
        files.add(chunk["file"])
    return files


def _extract_files_from_output(output: str) -> list[str]:
    """Extract referenced documentation files from output text."""
    DOC_FILES = [
        "deepagents-subagents.md", "deepagents-long-term-memory.md",
        "deepagents-human-in-the-loop.md", "deepagents-skills.md",
        "deepagents-backends.md", "deepagents-middleware.md",
        "deepagents-harness.md", "deepagents-cli.md",
        "deepagents-overview.md", "deepagents-quickstart.md",
        "deepagents-customization.md", "deepagents-products.md",
    ]
    files_consulted = []
    for doc_file in DOC_FILES:
        if doc_file in output and doc_file not in files_consulted:
            files_consulted.append(doc_file)
    return files_consulted


def run_approach_1(question: str, verbose: bool = False) -> tuple[str, list[str], float, str]:
    """
    Run Approach 1: DeepAgent with Virtual Filesystem.
    
    Returns: (response, files_consulted, time_seconds, stderr)
    """
    start = time.time()
    
    cmd = [
        "uv", "run", "scripts/deep_agent_search.py",
        question
    ]
    if verbose:
        cmd.insert(3, "--verbose")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=PROJECT_ROOT
        )
        elapsed = time.time() - start
        
        # Combine stdout + stderr for file detection (Rich may output to either)
        combined = result.stdout + "\n" + result.stderr
        files_consulted = _extract_files_from_output(combined)
        
        return result.stdout, files_consulted, elapsed, result.stderr
        
    except subprocess.TimeoutExpired:
        return "ERROR: Timeout after 120 seconds", [], 120.0, ""
    except Exception as e:
        return f"ERROR: {str(e)}", [], time.time() - start, ""


def run_approach_2(question: str) -> tuple[str, list[str], float, str]:
    """
    Run Approach 2: DeepAgents CLI.
    
    Note: The CLI is interactive, so we simulate by describing what it would do.
    For actual testing, you'd need to use pexpect or similar.
    
    Returns: (response, files_consulted, time_seconds, stderr)
    """
    # The DeepAgents CLI is interactive and can't easily be scripted
    # For this evaluation, we'll note that it would need manual testing
    return (
        "SKIPPED: DeepAgents CLI requires interactive session. "
        "Run manually with: deepagents",
        [],
        0.0,
        ""
    )


def run_approach_3(question: str, verbose: bool = False) -> tuple[str, list[str], float, str]:
    """
    Run Approach 3: LangGraph + Tantivy Agent.
    
    Returns: (response, files_consulted, time_seconds, stderr)
    """
    start = time.time()
    
    cmd = [
        "uv", "run", "scripts/tantivy_agent_search.py",
        question
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=PROJECT_ROOT
        )
        elapsed = time.time() - start
        
        # Combine stdout + stderr for file detection (Rich may output to either,
        # and rate limit errors appear in stderr)
        combined = result.stdout + "\n" + result.stderr
        files_consulted = _extract_files_from_output(combined)
        
        return result.stdout, files_consulted, elapsed, result.stderr
        
    except subprocess.TimeoutExpired:
        return "ERROR: Timeout after 120 seconds", [], 120.0, ""
    except Exception as e:
        return f"ERROR: {str(e)}", [], time.time() - start, ""


def calculate_chunk_hit_rate(files_consulted: list[str], reference_files: set[str]) -> float:
    """Calculate what percentage of reference files were consulted."""
    if not reference_files:
        return 1.0
    hits = len(set(files_consulted) & reference_files)
    return hits / len(reference_files)


def run_evaluation(
    approaches: list[int] = [1, 2, 3],
    question_ids: Optional[list[str]] = None,
    dry_run: bool = False,
    verbose: bool = False,
    delay: int = 0,
) -> list[EvaluationResult]:
    """
    Run evaluation across specified approaches and questions.
    
    Args:
        delay: Seconds to wait between questions (helps avoid rate limits).
    """
    test_set = load_test_set()
    results = []
    
    # Filter test cases
    test_cases = test_set["test_cases"]
    if question_ids:
        test_cases = [tc for tc in test_cases if tc["id"] in question_ids]
    
    print(f"\n{'='*60}")
    print(f"AGENTIC SEARCH EVALUATION")
    print(f"{'='*60}")
    print(f"Approaches: {approaches}")
    print(f"Questions: {[tc['id'] for tc in test_cases]}")
    print(f"Dry run: {dry_run}")
    if delay > 0:
        print(f"Delay between questions: {delay}s")
    print(f"{'='*60}\n")
    
    first_question = True
    for tc in test_cases:
        question_id = tc["id"]
        question = tc["question"]
        reference_files = get_reference_files(tc)
        
        # Apply delay between questions (not before the first one)
        if delay > 0 and not first_question and not dry_run:
            print(f"\n  ⏳ Waiting {delay}s to avoid rate limits...", flush=True)
            time.sleep(delay)
        first_question = False
        
        print(f"\n{'─'*60}")
        print(f"[{question_id}] {question[:60]}...")
        print(f"Reference files: {reference_files}")
        print(f"{'─'*60}")
        
        for approach in approaches:
            print(f"\n  Approach {approach}: ", end="", flush=True)
            
            if dry_run:
                print("SKIPPED (dry run)")
                results.append(EvaluationResult(
                    question_id=question_id,
                    approach=approach,
                    question=question,
                    response="DRY RUN - No actual execution",
                    time_seconds=0.0,
                    files_consulted=[],
                    chunk_hit_rate=0.0,
                    response_score=-1
                ))
                continue
            
            # Run the appropriate approach
            if approach == 1:
                response, files, elapsed, stderr = run_approach_1(question, verbose)
            elif approach == 2:
                response, files, elapsed, stderr = run_approach_2(question)
            elif approach == 3:
                response, files, elapsed, stderr = run_approach_3(question, verbose)
            else:
                response, files, elapsed, stderr = f"Unknown approach {approach}", [], 0.0, ""
            
            hit_rate = calculate_chunk_hit_rate(files, reference_files)
            
            print(f"{elapsed:.1f}s | Files: {len(files)} | Hit rate: {hit_rate:.0%}")
            if stderr and ("rate_limit" in stderr.lower() or "overloaded" in stderr.lower()
                          or "429" in stderr or "529" in stderr):
                print(f"  ⚠ Rate limit detected in stderr")
            
            # Check for errors
            error = None
            if response.startswith("ERROR:") or response.startswith("SKIPPED:"):
                error = response
            
            # Truncate stderr for storage (keep last 1000 chars for debugging — errors appear at end)
            stderr_truncated = stderr[-1000:] if stderr and len(stderr) > 1000 else stderr
            
            results.append(EvaluationResult(
                question_id=question_id,
                approach=approach,
                question=question,
                response=response[:2000] if len(response) > 2000 else response,  # Truncate
                time_seconds=elapsed,
                files_consulted=files,
                chunk_hit_rate=hit_rate,
                response_score=-1,  # To be scored manually
                error=error,
                stderr=stderr_truncated if stderr_truncated else None
            ))
    
    return results


def save_results(results: list[EvaluationResult], output_path: Optional[Path] = None):
    """Save results to JSON file."""
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = PROJECT_ROOT / "evaluation" / f"results_{timestamp}.json"
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump([asdict(r) for r in results], f, indent=2)
    
    print(f"\nResults saved to: {output_path}")
    return output_path


def print_summary(results: list[EvaluationResult]):
    """Print a summary table of results."""
    print(f"\n{'='*80}")
    print("EVALUATION SUMMARY")
    print(f"{'='*80}")
    
    # Group by approach
    by_approach = {1: [], 2: [], 3: []}
    for r in results:
        by_approach[r.approach].append(r)
    
    print(f"\n{'Approach':<12} {'Avg Time':<12} {'Avg Hit Rate':<15} {'Errors':<10}")
    print(f"{'-'*50}")
    
    for approach in [1, 2, 3]:
        approach_results = by_approach[approach]
        if not approach_results:
            continue
        
        # Filter out skipped/errored
        valid = [r for r in approach_results if r.error is None]
        
        if valid:
            avg_time = sum(r.time_seconds for r in valid) / len(valid)
            avg_hit_rate = sum(r.chunk_hit_rate for r in valid) / len(valid)
        else:
            avg_time = 0
            avg_hit_rate = 0
        
        errors = len([r for r in approach_results if r.error])
        
        approach_name = {1: "DeepAgent", 2: "CLI", 3: "Tantivy"}[approach]
        print(f"{approach_name:<12} {avg_time:>8.1f}s    {avg_hit_rate:>10.0%}      {errors}")
    
    print(f"\n{'─'*80}")
    print("Detailed Results by Question:")
    print(f"{'─'*80}")
    
    # Group by question
    by_question = {}
    for r in results:
        if r.question_id not in by_question:
            by_question[r.question_id] = {}
        by_question[r.question_id][r.approach] = r
    
    for qid in sorted(by_question.keys()):
        print(f"\n[{qid}]")
        for approach in [1, 2, 3]:
            if approach in by_question[qid]:
                r = by_question[qid][approach]
                status = "ERROR" if r.error else f"{r.time_seconds:.1f}s, {r.chunk_hit_rate:.0%} hit"
                approach_name = {1: "DeepAgent", 2: "CLI", 3: "Tantivy"}[approach]
                print(f"  {approach_name:<12}: {status}")


def main():
    parser = argparse.ArgumentParser(description="Run agentic search evaluation")
    parser.add_argument("--approach", type=int, choices=[1, 2, 3],
                       help="Run only this approach")
    parser.add_argument("--question", type=str,
                       help="Run only this question ID (e.g., Q1)")
    parser.add_argument("--dry-run", action="store_true",
                       help="Don't actually run approaches, just show what would run")
    parser.add_argument("--verbose", action="store_true",
                       help="Show verbose output from approaches")
    parser.add_argument("--delay", type=int, default=0,
                       help="Seconds to wait between questions to avoid rate limits (recommended: 90 for Approach 3)")
    parser.add_argument("--output", type=Path,
                       help="Output file path for results JSON")
    
    args = parser.parse_args()
    
    approaches = [args.approach] if args.approach else [1, 2, 3]
    question_ids = [args.question] if args.question else None
    
    # Check for API key
    if not args.dry_run and not os.environ.get("ANTHROPIC_API_KEY"):
        print("WARNING: ANTHROPIC_API_KEY not set. Approaches 1 and 3 will fail.")
        print("Set it with: export ANTHROPIC_API_KEY=your_key")
        print("Or run with --dry-run to skip actual execution.\n")
    
    results = run_evaluation(
        approaches=approaches,
        question_ids=question_ids,
        dry_run=args.dry_run,
        verbose=args.verbose,
        delay=args.delay,
    )
    
    print_summary(results)
    
    if not args.dry_run:
        save_results(results, args.output)
    
    print("\n" + "="*80)
    print("MANUAL SCORING REQUIRED")
    print("="*80)
    print("""
After reviewing the responses, score each on a 0-2 scale:
  0 = Poor   - Missing most key points, incorrect, or irrelevant
  1 = Adequate - Covers some key points but incomplete
  2 = Excellent - Covers all/most key points accurately

Edit the results JSON file to add scores, then run:
  uv run evaluation/analyze_results.py results_XXXXXX.json
""")


if __name__ == "__main__":
    main()
