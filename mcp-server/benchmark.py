"""
MCP Tool Latency Benchmark
Runs each tool N times and reports p50/p95/p99 latencies.

Usage:
    python benchmark.py                  # All tools, 50 iterations each
    python benchmark.py --tool query_major_detail  # Single tool
    python benchmark.py --iterations 20  # Custom count
    python benchmark.py --json           # Output as JSON
"""

import time
import json
import statistics
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from data_store import store
from config import DB_PATH


def benchmark_tool(name, handler, args, iterations=50):
    """Benchmark a single tool handler."""
    latencies = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        asyncio.run(handler(args))
        elapsed = (time.perf_counter() - t0) * 1000
        latencies.append(elapsed)

    latencies.sort()
    return {
        "tool": name,
        "iterations": iterations,
        "p50_ms": round(latencies[len(latencies)//2], 2),
        "p95_ms": round(latencies[int(len(latencies)*0.95)], 2),
        "p99_ms": round(latencies[int(len(latencies)*0.99)], 2),
        "min_ms": round(latencies[0], 2),
        "max_ms": round(latencies[-1], 2),
        "mean_ms": round(statistics.mean(latencies), 2),
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="MCP Tool Latency Benchmark")
    parser.add_argument("--tool", type=str, help="Benchmark a single tool by name")
    parser.add_argument("--iterations", type=int, default=50)
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    # Initialize data store
    store.initialize()

    # Import handlers after store init
    import server

    all_benchmarks = [
        ("query_major_detail", server._query_major_detail,
         {"major_name": "软件工程"}),
        ("query_major_branches", server._query_major_branches,
         {"major_name": "自动化"}),
        ("search_majors", server._search_majors,
         {"category": "工学"}),
        ("query_city_industry", server._query_city_industry,
         {"name": "合肥"}),
        ("query_school_info", server._query_school_info,
         {"query_type": "tiers"}),
        ("query_rules", server._query_rules,
         {"province": "广东"}),
        ("query_career_data", server._query_career_data,
         {"query_type": "salary_paths"}),
        ("search_knowledge_base", server._search_knowledge_base,
         {"query": "电气工程"}),
        ("query_school_by_major", server._query_school_by_major,
         {"major_name": "软件工程"}),
        ("query_major_by_school", server._query_major_by_school,
         {"school_name": "成电"}),
    ]

    if args.tool:
        all_benchmarks = [(n, h, a) for n, h, a in all_benchmarks if n == args.tool]
        if not all_benchmarks:
            print(f"Unknown tool: {args.tool}")
            sys.exit(1)

    results = []
    for name, handler, handler_args in all_benchmarks:
        print(f"  {name}...", end=" ", flush=True)
        r = benchmark_tool(name, handler, handler_args, args.iterations)
        results.append(r)
        print(f"p50={r['p50_ms']:.1f}ms p95={r['p95_ms']:.1f}ms mean={r['mean_ms']:.1f}ms")

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    all_p50 = [r['p50_ms'] for r in results]
    slowest = max(results, key=lambda r: r['p50_ms'])
    fastest = min(results, key=lambda r: r['p50_ms'])

    print(f"\n--- Summary ({len(results)} tools, {args.iterations} iterations) ---")
    print(f"  Overall avg p50: {statistics.mean(all_p50):.1f}ms")
    print(f"  Slowest: {slowest['tool']} ({slowest['p50_ms']:.1f}ms)")
    print(f"  Fastest: {fastest['tool']} ({fastest['p50_ms']:.1f}ms)")

    report_path = Path(__file__).parent / "benchmark_results.json"
    report_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"  Saved to {report_path}")


if __name__ == "__main__":
    main()
