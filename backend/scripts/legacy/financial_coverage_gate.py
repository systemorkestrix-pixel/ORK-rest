from __future__ import annotations

import inspect
import dis
import os
from pathlib import Path
import sys
import trace
import unittest
from importlib import import_module

BACKEND_DIR = Path(__file__).resolve().parents[1]
TESTS_DIR = BACKEND_DIR / "tests"
MIN_FINANCIAL_COVERAGE = 80.0
TARGET_TEST_PATTERNS = [
    "test_phase3_actual_cogs.py",
    "test_phase4_refund_lifecycle.py",
    "test_phase6_critical_paths.py",
]
TARGET_FUNCTIONS: dict[str, list[str]] = {
    "application.financial_engine.domain.collections": [
        "collect_order_payment",
    ],
    "application.financial_engine.domain.refunds": [
        "refund_order",
    ],
    "application.financial_engine.domain.expenses": [
        "approve_expense",
        "reject_expense",
    ],
    "application.financial_engine.domain.shifts": [
        "close_cash_shift",
    ],
}

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET", "phase6-coverage-secret-0123456789abcdef0123456789")
os.environ.setdefault("APP_ENV", "development")


def _load_suite() -> unittest.TestSuite:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for pattern in TARGET_TEST_PATTERNS:
        suite.addTests(loader.discover(start_dir=str(TESTS_DIR), pattern=pattern))
    return suite


def _function_source_lines(fn) -> set[int]:
    return {line_no for _, line_no in dis.findlinestarts(fn.__code__) if line_no is not None}


def _collect_target_lines() -> tuple[dict[Path, dict[str, set[int]]], set[tuple[Path, int]]]:
    per_file: dict[Path, dict[str, set[int]]] = {}
    all_lines: set[tuple[Path, int]] = set()

    for module_name, function_names in TARGET_FUNCTIONS.items():
        module = import_module(module_name)
        for function_name in function_names:
            fn = getattr(module, function_name, None)
            if fn is None:
                raise RuntimeError(f"Coverage gate target missing: {module_name}.{function_name}")
            source_file = Path(inspect.getsourcefile(fn) or "").resolve()
            lines = _function_source_lines(fn)
            if source_file not in per_file:
                per_file[source_file] = {}
            per_file[source_file][f"{module_name}.{function_name}"] = lines
            for line_no in lines:
                all_lines.add((source_file, line_no))
    return per_file, all_lines


def _run_tests_with_trace() -> tuple[unittest.TestResult, trace.CoverageResults]:
    tracer = trace.Trace(
        count=True,
        trace=False,
        ignoredirs=[sys.prefix, sys.exec_prefix],
    )
    suite = _load_suite()
    runner = unittest.TextTestRunner(verbosity=1)
    result = tracer.runfunc(runner.run, suite)
    return result, tracer.results()


def main() -> int:
    result, trace_results = _run_tests_with_trace()
    if not result.wasSuccessful():
        print("Financial coverage gate blocked: dependent test suite failed.")
        return 1

    per_file_lines, all_target_lines = _collect_target_lines()
    executed_lines = {
        (Path(file_name).resolve(), line_no)
        for (file_name, line_no), count in trace_results.counts.items()
        if count > 0
    }

    if not all_target_lines:
        print("Financial coverage gate blocked: no target lines discovered.")
        return 1

    covered_lines = all_target_lines & executed_lines
    coverage_pct = (len(covered_lines) / len(all_target_lines)) * 100.0

    print("Financial critical-path coverage report:")
    print(f"- Target modules: {', '.join(TARGET_FUNCTIONS.keys())}")
    print(f"- Covered lines: {len(covered_lines)} / {len(all_target_lines)}")
    print(f"- Coverage: {coverage_pct:.2f}%")
    for source_file, functions in per_file_lines.items():
        print(f"- Source file: {source_file}")
        for function_name, function_lines in functions.items():
            if not function_lines:
                pct = 100.0
                covered = 0
                total = 0
            else:
                covered = len({(source_file, line_no) for line_no in function_lines} & executed_lines)
                total = len(function_lines)
                pct = (covered / total) * 100.0
            print(f"  - {function_name}: {covered}/{total} ({pct:.2f}%)")

    if coverage_pct < MIN_FINANCIAL_COVERAGE:
        print(
            f"Financial coverage gate failed: {coverage_pct:.2f}% is below the "
            f"required {MIN_FINANCIAL_COVERAGE:.2f}%."
        )
        return 1

    print(
        f"Financial coverage gate passed: {coverage_pct:.2f}% >= "
        f"{MIN_FINANCIAL_COVERAGE:.2f}%."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
