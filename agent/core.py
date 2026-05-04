"""
agent/core.py
-------------
Main agent orchestration. Ties together planning, execution, and memory.
This is the brain — it decides what to do and when.
"""

from rich.console import Console
from rich.panel import Panel
from rich.spinner import Spinner

from agent.executor import display_task_detail, display_task_queue, run_task
from agent.memory import Session, Task, clear_session, load_session, save_session
from agent.planner import plan_task, reprioritize_all

console = Console()


class TaskMindAgent:
    """
    Core agent class. Instantiate once per CLI invocation.
    All state is loaded from and saved to disk via memory.py.
    """

    def __init__(self) -> None:
        self.session: Session = load_session()

    # ------------------------------------------------------------------ #
    # Public commands (called by main.py)                                  #
    # ------------------------------------------------------------------ #

    def add_task(self, raw_input: str) -> Task:
        """Plan and add a new task to the session."""
        console.print(f"\n[bold cyan]🤖 TaskMind is planning:[/bold cyan] {raw_input}\n")

        with console.status("[bold]TaskMind is thinking...[/bold]", spinner="dots"):
            task, latency_ms = plan_task(raw_input, self.session.tasks)

        self.session.tasks.append(task)
        self.session.total_tasks_added += 1
        save_session(self.session)

        console.print(Panel(
            f"[bold green]✓ Task added![/bold green]\n\n"
            f"[bold]{task.title}[/bold]\n"
            f"[dim]ID:[/dim] {task.id}  "
            f"[dim]Priority:[/dim] [bold]{task.priority_score:.1f}[/bold]  "
            f"[dim]Subtasks:[/dim] {len(task.subtasks)}\n\n"
            f"[italic dim]{task.ai_notes}[/italic dim]\n\n"
            f"[dim]AI latency: {latency_ms:.0f}ms[/dim]",
            border_style="green",
            padding=(1, 2),
        ))

        return task

    def list_tasks(self) -> None:
        """Display the full task queue sorted by priority."""
        display_task_queue(self.session)

    def show_task(self, task_id: str) -> None:
        """Display full detail for a single task."""
        from agent.memory import get_task_by_id
        task = get_task_by_id(self.session, task_id)
        if task:
            display_task_detail(task)
        else:
            console.print(f"[red]No task with ID '{task_id}' found.[/red]")

    def run(self, task_id: str | None = None) -> None:
        """
        Execute a task interactively.
        If no task_id given, picks the highest-priority pending task.
        """
        if task_id is None:
            pending = sorted(
                [t for t in self.session.tasks if t.status != "done"],
                key=lambda t: t.priority_score,
                reverse=True,
            )
            if not pending:
                console.print("[green]No pending tasks — you're all caught up![/green]")
                return
            task_id = pending[0].id
            console.print(f"[dim]Auto-selected highest priority task: {task_id}[/dim]")

        run_task(self.session, task_id)

    def reprioritize(self) -> None:
        """Ask Claude to re-evaluate the priority order."""
        console.print("\n[bold cyan]🤖 Re-prioritizing with AI...[/bold cyan]")
        with console.status("[bold]TaskMind is Thinking...[/bold]", spinner="dots"):
            reordered = reprioritize_all(self.session)

        if not reordered:
            console.print("[yellow]No pending tasks to re-prioritize.[/yellow]")
            return

        # Rebuild task list with done tasks at end
        done = [t for t in self.session.tasks if t.status == "done"]
        self.session.tasks = reordered + done
        save_session(self.session)

        console.print("[green]✓ Tasks re-prioritized![/green]")
        display_task_queue(self.session)

    def done(self, task_id: str) -> None:
        """Mark a task as done manually."""
        from agent.memory import mark_task_done
        if mark_task_done(self.session, task_id):
            console.print(f"[green]✓ Task {task_id} marked as done.[/green]")
        else:
            console.print(f"[red]Task '{task_id}' not found.[/red]")

    def clear(self) -> None:
        """Clear all tasks from the session."""
        from rich.prompt import Confirm
        confirmed = Confirm.ask("[yellow]Clear ALL tasks? This cannot be undone.[/yellow]")
        if confirmed:
            clear_session(self.session)
            console.print("[green]Session cleared.[/green]")

    def edit(self, task_id: str) -> None:
        """Interactively edit an existing task's fields."""
        from agent.memory import get_task_by_id
        from rich.prompt import Prompt

        task = get_task_by_id(self.session, task_id)
        if not task:
            console.print(f"[red]Task '{task_id}' not found.[/red]")
            return

        console.print(f"\n[bold cyan]Editing task:[/bold cyan] {task.title}")
        console.print("[dim]Press Enter to keep current value.[/dim]\n")

        new_title = Prompt.ask(f"  Title", default=task.title)
        new_urgency = int(Prompt.ask(f"  Urgency (1-5)", default=str(task.urgency)))
        new_impact = int(Prompt.ask(f"  Impact (1-5)", default=str(task.impact)))
        new_effort = int(Prompt.ask(f"  Effort (1-5)", default=str(task.effort)))

        task.title = new_title
        task.urgency = new_urgency
        task.impact = new_impact
        task.effort = new_effort
        task.priority_score = round((new_urgency * new_impact) / max(1, new_effort), 2)

        save_session(self.session)
        console.print(f"\n[green]✓ Task updated! New priority score: {task.priority_score}[/green]")
