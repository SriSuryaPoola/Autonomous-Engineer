"""
Autonomous AI Engineering Team — CLI Entry Point.

Usage:
    python main.py "Build Playwright automation for login and dashboard"
    python main.py --interactive
    python main.py --status

Architecture:
    HiClaw (coordination) + Claude Flow (execution)
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orchestrator import Orchestrator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="autonomous-engineer",
        description=(
            "Autonomous AI Engineering Team — "
            "HiClaw coordination + Claude Flow execution"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py "Build Playwright automation for login and dashboard"
  python main.py "Create REST API with authentication and tests"
  python main.py --interactive
  python main.py --status
        """,
    )
    parser.add_argument(
        "task",
        nargs="?",
        default=None,
        help="The engineering task to execute (quoted string).",
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Start in interactive REPL mode.",
    )
    parser.add_argument(
        "--status", "-s",
        action="store_true",
        help="Show system status and exit.",
    )
    parser.add_argument(
        "--dashboard", "-d",
        action="store_true",
        help="Launch the real-time observability dashboard during execution.",
    )
    parser.add_argument(
        "--log-level", "-l",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set logging level (default: INFO).",
    )
    return parser.parse_args()


def main() -> None:
    # Fix Windows console encoding for emoji/unicode in logs
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

    args = parse_args()
    orchestrator = Orchestrator(log_level=args.log_level)

    if args.status:
        print(orchestrator.system_status())
        return

    if args.interactive:
        asyncio.run(orchestrator.interactive(use_dashboard=args.dashboard))
        return

    if args.task:
        result = asyncio.run(orchestrator.run(args.task, use_dashboard=args.dashboard))
        sys.exit(0 if result.status.value == "completed" else 1)
    else:
        print("Error: Please provide a task or use --interactive mode.")
        print("Run 'python main.py --help' for usage information.")
        sys.exit(1)


if __name__ == "__main__":
    main()
