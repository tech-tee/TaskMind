"""
agent/executor.py
-----------------
Handles task execution flow, status transitions, and user interaction
during task working sessions.
"""

import time
from dataclasses import dataclass
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table

from agent.memory import Session, Task, mark_subtask_done, mark_task_done, save_session

console = Console()


@dataclass
class ExecutionResult:
    task_id: str
    subtasks_completed: int
    subtasks_total: int
    time_taken_seconds: float
    completed: bool


def display_task_queue(session: Session) -> None:
    """Print all pending tasks sorted by priority."""
    pending = sorted(
        [t for t in session.tasks if t.status != "done"],
        key=lambda t: t.priority_score,
        reverse=True,
    )

    if not pending:
        console.print("\n[bold green]✓ No pending tasks! You're all caught up.[/bold green]\n")
        return

    table = Table(
        title="[bold]TaskMind Queue[/bold]",
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
    )
    table.add_column("ID", style="dim", width=8)
    table.add_column("Title", style="bold white", min_width=30)
    table.add_column("Priority", justify="center", width=9)
    table.add_column("U/I/E", justify="center", width=7)
    table.add_column("Subtasks", justify="center", width=9)
    table.add_column("Status", width=12)

    for task in pending:
        done_subs = sum(1 for s in task.subtasks if s.status == "done")
        total_subs = len(task.subtasks)
        priority_color = (
            "red" if task.priority_score >= 15
            else "yellow" if task.priority_score >= 8
            else "green"
        )
        table.add_row(
            task.id,
            task.title,
            f"[{priority_color}]{task.priority_score:.1f}[/{priority_color}]",
            f"{task.urgency}/{task.impact}/{task.effort}",
            f"{done_subs}/{total_subs}",
            f"[dim]{task.status}[/dim]",
        )

    console.print()
    console.print(table)
    console.print(
        f"[dim]  Showing {len(pending)} pending task(s). "
        f"U=Urgency I=Impact E=Effort (1–5)[/dim]\n"
    )


def display_task_detail(task: Task) -> None:
    """Print a full task card with subtasks."""
    status_color = {"pending": "yellow", "in_progress": "blue", "done": "green"}.get(
        task.status, "white"
    )

    lines = [
        f"[bold]{task.title}[/bold]",
        f"",
        f"[dim]Priority Score:[/dim] [bold]{task.priority_score:.1f}[/bold]  "
        f"[dim]Urgency:[/dim] {task.urgency}  "
        f"[dim]Impact:[/dim] {task.impact}  "
        f"[dim]Effort:[/dim] {task.effort}",
        f"[dim]Status:[/dim] [{status_color}]{task.status}[/{status_color}]",
        f"",
        f"[italic dim]{task.ai_notes}[/italic dim]",
        f"",
        f"[bold cyan]Subtasks:[/bold cyan]",
    ]

    for sub in task.subtasks:
        icon = "✓" if sub.status == "done" else "○"
        color = "green" if sub.status == "done" else "white"
        lines.append(f"  [{color}]{icon} [{sub.id}] {sub.description}[/{color}]")

    console.print(Panel("\n".join(lines), border_style="cyan", padding=(1, 2)))


def run_task(session: Session, task_id: str) -> Optional[ExecutionResult]:
    """
    Interactive execution loop for a single task.
    Walks the user through each subtask with prompts.
    """
    from agent.memory import get_task_by_id

    task = get_task_by_id(session, task_id)
    if not task:
        console.print(f"[red]Task '{task_id}' not found.[/red]")
        return None

    if task.status == "done":
        console.print(f"[green]Task '{task.title}' is already done![/green]")
        return None

    task.status = "in_progress"
    save_session(session)

    console.print(f"\n[bold cyan]▶ Starting task:[/bold cyan] {task.title}\n")
    display_task_detail(task)

    start_time = time.time()
    pending_subs = [s for s in task.subtasks if s.status != "done"]

    for sub in pending_subs:
        console.print(f"\n[bold]Subtask:[/bold] {sub.description}")
        console.print(f"[dim]ID: {sub.id}[/dim]")

        done = Confirm.ask("  Mark this subtask as done?", default=True)
        if done:
            mark_subtask_done(session, task_id, sub.id)
            console.print(f"  [green]✓ Done[/green]")
        else:
            console.print(f"  [yellow]○ Skipped[/yellow]")

    elapsed = time.time() - start_time
    done_count = sum(1 for s in task.subtasks if s.status == "done")
    all_done = done_count == len(task.subtasks)

    if all_done:
        mark_task_done(session, task_id)
        console.print(
            Panel(
                f"[bold green]✓ Task complete![/bold green]\n"
                f"[dim]{task.title}[/dim]\n"
                f"Time taken: {elapsed:.0f}s",
                border_style="green",
            )
        )
    else:
        console.print(
            f"\n[yellow]Task partially done: {done_count}/{len(task.subtasks)} subtasks completed.[/yellow]"
        )

    return ExecutionResult(
        task_id=task_id,
        subtasks_completed=done_count,
        subtasks_total=len(task.subtasks),
        time_taken_seconds=elapsed,
        completed=all_done,
    )
