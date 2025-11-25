#!/usr/bin/env python
"""CLI test runner for NotebookLM Automator.

Usage:
    python run_tests.py                     # Run all tests
    python run_tests.py --type unit         # Run only unit tests
    python run_tests.py --type api          # Run only API tests
    python run_tests.py --type ui           # Run only UI tests
    python run_tests.py --type e2e          # Run only E2E tests (requires NOTEBOOKLM_URL)
    python run_tests.py --type all          # Run all tests
    python run_tests.py -v                  # Verbose output
    python run_tests.py --coverage          # Run with coverage report
    python run_tests.py --type unit -v      # Combine options
"""

import argparse
import sys
from typing import List, Optional

import pytest


# Test type to directory/file mapping
TEST_PATHS = {
    "unit": "tests/unit/",
    "api": "tests/api/",
    "ui": "tests/ui/",
    "e2e": "tests/e2e/",
    "all": "tests/",
}


def build_pytest_args(
    test_type: str = "all",
    verbose: bool = False,
    coverage: bool = False,
    extra_args: Optional[List[str]] = None,
) -> List[str]:
    """Build pytest argument list based on options.

    Args:
        test_type: Type of tests to run (unit, api, ui, e2e, all)
        verbose: Enable verbose output
        coverage: Enable coverage reporting
        extra_args: Additional pytest arguments

    Returns:
        List of pytest arguments
    """
    args = []

    # Add test path
    test_path = TEST_PATHS.get(test_type, TEST_PATHS["all"])
    args.append(test_path)

    # Add verbose flag
    if verbose:
        args.append("-v")

    # Add coverage options
    if coverage:
        args.extend([
            "--cov=src/notebooklm_automator",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
        ])

    # Add extra arguments
    if extra_args:
        args.extend(extra_args)

    return args


def run_tests(
    test_type: str = "all",
    verbose: bool = False,
    coverage: bool = False,
    extra_args: Optional[List[str]] = None,
) -> int:
    """Run tests using pytest programmatically.

    Args:
        test_type: Type of tests to run (unit, api, ui, e2e, all)
        verbose: Enable verbose output
        coverage: Enable coverage reporting
        extra_args: Additional pytest arguments

    Returns:
        Exit code (0 = success, non-zero = failure)
    """
    args = build_pytest_args(test_type, verbose, coverage, extra_args)
    print(f"Running: pytest {' '.join(args)}")
    return pytest.main(args)


def main() -> int:
    """Main entry point for CLI test runner."""
    parser = argparse.ArgumentParser(
        description="Run NotebookLM Automator tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Test Types:
  unit    Unit tests for core modules (sources, audio, browser, selectors)
  api     API endpoint tests with mocked automator
  ui      UI/Playwright interaction tests with mocked page
  e2e     End-to-end tests (requires NOTEBOOKLM_URL environment variable)
  all     Run all tests (default)

Examples:
  python run_tests.py                     Run all tests
  python run_tests.py --type unit         Run unit tests only
  python run_tests.py --type api -v       Run API tests with verbose output
  python run_tests.py --coverage          Run all tests with coverage report
  python run_tests.py -- -k "test_add"    Pass extra args to pytest
        """,
    )

    parser.add_argument(
        "--type", "-t",
        choices=["unit", "api", "ui", "e2e", "all"],
        default="all",
        help="Type of tests to run (default: all)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--coverage", "-c",
        action="store_true",
        help="Run with coverage reporting",
    )
    parser.add_argument(
        "extra_args",
        nargs="*",
        help="Additional arguments to pass to pytest",
    )

    args = parser.parse_args()

    # Print header
    print("=" * 60)
    print("NotebookLM Automator Test Runner")
    print("=" * 60)
    print(f"Test type: {args.type}")
    if args.type == "e2e":
        import os
        if not os.getenv("NOTEBOOKLM_URL"):
            print("\nWARNING: NOTEBOOKLM_URL not set. E2E tests will be skipped.")
    print()

    # Run tests
    exit_code = run_tests(
        test_type=args.type,
        verbose=args.verbose,
        coverage=args.coverage,
        extra_args=args.extra_args if args.extra_args else None,
    )

    # Print summary
    print()
    print("=" * 60)
    if exit_code == 0:
        print("All tests passed!")
    else:
        print(f"Tests failed with exit code: {exit_code}")
    print("=" * 60)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
