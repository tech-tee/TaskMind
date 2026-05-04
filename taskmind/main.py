#!/usr/bin/env python3
"""
TaskMind — AI-Powered Task Prioritization & Execution Agent
===========================================================
CLI entry point. All commands route through agent/core.py.

Usage:
  python main.py add "Finish the ML assignment before Friday"
  python main.py list
  python main.py run
  python main.py run <task-id>
  python main.py show <task-id>
  python main.py done <task-id>
  python main.py reprioritize
  python main.py report
  python main.py clear
"""

import argparse
import sys

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

load_dotenv()

console = Console()

BANNER = """
[bold cyan]████████╗ █████╗ ███████╗██╗  ██╗███╗   ███╗██╗███╗   ██╗██████╗ [/bold cyan]
[bold cyan]╚══██╔══╝██╔══██╗██╔════╝██║ ██╔╝████╗ ████║██║████╗  ██║██╔══██╗[/bold cyan]
[bold cyan]   ██║   ███████║███████╗█████╔╝ ██╔████╔██║██║██╔██╗ ██║██║  ██║[/bold cyan]
[bold cyan]   ██║   ██╔══██║╚════██║██╔═██╗ ██║╚██╔╝██║██║██║╚██╗██║██║  ██║[/bold cyan]
[bold cyan]   ██║   ██║  ██║███████║██║  ██╗██║ ╚═╝ ██║██║██║ ╚████║██████╔╝[/bold cyan]
[bold cyan]   ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚═════╝ [/bold cyan]
[dim]  AI-Powered Task Prioritization & Execution Agent | v1.0.0[/dim]
"""


def print_banner() -> None:
    console.print(BANNER)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="taskmind",
        description="TaskMind — AI-powered task prioritization agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="command", metavar="command")

    # add
    add_parser = subparsers.add_parser("add", help="Add and AI-plan a new task")
    add_parser.add_argument("task", nargs="+", help="Task description in plain English")

    # list
    subparsers.add_parser("list", help="Show all pending tasks sorted by priority")

    # run
    run_parser = subparsers.add_parser("run", help="Execute a task interactively")
    run_parser.add_argument(
        "task_id", nargs="?", default=None,
        help="Task ID to run (omit to auto-select highest priority)"
    )

    # show
    show_parser = subparsers.add_parser("show", help="Show full detail for a task")
    show_parser.add_argument("task_id", help="Task ID")

    # done
    done_parser = subparsers.add_parser("done", help="Mark a task as done")
    done_parser.add_argument("task_id", help="Task ID")

    # reprioritize
    subparsers.add_parser("reprioritize", help="Re-order all tasks using AI")

    # edit
    edit_parser = subparsers.add_parser("edit", help="Edit an existing task")
    edit_parser.add_argument("task_id", help="Task ID to edit")

    # report
    subparsers.add_parser("report", help="Show performance metrics (0–10,000 score)")

    # clear
    subparsers.add_parser("clear", help="Clear all tasks from session")

    args = parser.parse_args()

    if args.command is None:
        print_banner()
        parser.print_help()
        sys.exit(0)

    # Lazy import to avoid loading everything for --help
    from agent.core import TaskMindAgent
    agent = TaskMindAgent()

    if args.command == "add":
        raw = " ".join(args.task)
        agent.add_task(raw)

    elif args.command == "list":
        print_banner()
        agent.list_tasks()

    elif args.command == "run":
        agent.run(args.task_id)

    elif args.command == "show":
        agent.show_task(args.task_id)

    elif args.command == "done":
        agent.done(args.task_id)

    elif args.command == "reprioritize":
        agent.reprioritize()

    elif args.command == "report":
        from metrics.evaluator import display_report, evaluate
        report = evaluate(agent.session)
        display_report(report)

    elif args.command == "clear":
        agent.clear()


if __name__ == "__main__":
    main()
