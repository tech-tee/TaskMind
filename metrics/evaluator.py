"""
metrics/evaluator.py
--------------------
TaskMind Performance Evaluation System.
Scores the agent on a scale of 0–10,000 across 5 dimensions (2,000 pts each).

Dimensions:
  1. Task Decomposition Quality    (0–2000)
  2. Prioritization Accuracy       (0–2000)
  3. Context Retention             (0–2000)
  4. Response Latency              (0–2000)
  5. User Goal Completion Rate     (0–2000)

Total: 0–10,000
"""

import time
from dataclasses import dataclass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agent.memory import Session, Task

console = Console()


@dataclass
class DimensionScore:
    name: str
    score: int           # 0–2000
    max_score: int = 2000
    rationale: str = ""
    raw_value: str = ""  # human-readable measurement


@dataclass
class EvaluationReport:
    dimensions: list[DimensionScore]
    total_score: int
    grade: str
    session_snapshot: dict


# ------------------------------------------------------------------ #
# Scoring functions (each returns 0–2000)                             #
# ------------------------------------------------------------------ #

def score_decomposition(tasks: list[Task]) -> DimensionScore:
    """
    Measures average number of subtasks and checks they're within 3–7 range.
    3–7 subtasks = optimal (2000). Fewer or more = penalty.
    Also rewards non-trivially-short subtask descriptions.
    """
    if not tasks:
        return DimensionScore("Task Decomposition Quality", 0, rationale="No tasks yet.")

    scores = []
    for task in tasks:
        n = len(task.subtasks)
        # Subtask count score (0–1000)
        if 3 <= n <= 7:
            count_score = 1000
        elif n == 2 or n == 8:
            count_score = 750
        elif n == 1 or n == 9:
            count_score = 400
        else:
            count_score = 100

        # Description quality score: avg chars > 20 = good (0–1000)
        if task.subtasks:
            avg_len = sum(len(s.description) for s in task.subtasks) / len(task.subtasks)
            quality_score = min(1000, int((avg_len / 60) * 1000))
        else:
            quality_score = 0

        scores.append(count_score + quality_score)

    avg_score = int(sum(scores) / len(scores))
    avg_subtasks = sum(len(t.subtasks) for t in tasks) / len(tasks)

    return DimensionScore(
        name="Task Decomposition Quality",
        score=avg_score,
        rationale=(
            f"Avg {avg_subtasks:.1f} subtasks/task. "
            f"Optimal range is 3–7. Scores description richness too."
        ),
        raw_value=f"{avg_subtasks:.1f} subtasks/task avg",
    )


def score_prioritization(tasks: list[Task]) -> DimensionScore:
    """
    Checks if high-urgency tasks have appropriately high priority scores.
    Validates: priority_score = (urgency × impact) / effort.
    """
    if not tasks:
        return DimensionScore("Prioritization Accuracy", 0, rationale="No tasks yet.")

    errors = 0
    for task in tasks:
        expected = round((task.urgency * task.impact) / max(1, task.effort), 2)
        if abs(task.priority_score - expected) > 0.1:
            errors += 1

    accuracy = 1.0 - (errors / len(tasks))
    score = int(accuracy * 2000)

    # Also reward spread: if all tasks have same score, something's wrong
    scores = [t.priority_score for t in tasks]
    spread = max(scores) - min(scores) if len(scores) > 1 else 5
    spread_bonus = min(200, int(spread * 20))  # up to 200 bonus for diverse priorities
    score = min(2000, score + spread_bonus)

    return DimensionScore(
        name="Prioritization Accuracy",
        score=score,
        rationale=(
            f"Formula validation: {len(tasks)-errors}/{len(tasks)} correct. "
            f"Priority spread: {spread:.1f}. Higher spread = better differentiation."
        ),
        raw_value=f"{accuracy*100:.0f}% formula accuracy",
    )


def score_context_retention(session: Session) -> DimensionScore:
    """
    Checks if session memory is intact and consistent.
    Validates: total_tasks_added matches actual tasks, timestamps are sequential.
    """
    tasks = session.tasks
    if not tasks:
        return DimensionScore("Context Retention", 1000, rationale="No tasks to validate yet.")

    issues = 0

    # Check 1: task count consistency
    if session.total_tasks_added < len(tasks):
        issues += 1

    # Check 2: all tasks have IDs
    for t in tasks:
        if not t.id:
            issues += 1

    # Check 3: subtask IDs reference parent
    for t in tasks:
        for s in t.subtasks:
            if not s.id.startswith(t.id):
                issues += 1

    # Check 4: timestamps are reasonable
    now = time.time()
    for t in tasks:
        if t.created_at > now or t.created_at < 1_600_000_000:
            issues += 1

    issue_rate = issues / max(1, len(tasks) * 4)
    score = int((1 - min(1, issue_rate)) * 2000)

    return DimensionScore(
        name="Context Retention",
        score=score,
        rationale=(
            f"Session integrity check: {issues} issue(s) found across {len(tasks)} task(s). "
            "Validates IDs, timestamps, and task count consistency."
        ),
        raw_value=f"{issues} integrity issues found",
    )


def score_latency(tasks: list[Task]) -> DimensionScore:
    """
    Estimates latency from ai_notes fields if timing was embedded.
    Since we log latency separately, this score is based on model tier used.
    claude-3-5-haiku → fast (1600–1800), sonnet → medium (1200–1600), opus → slow (800–1200).
    Rewards fast responses.
    """
    import os
    model = os.getenv("TASKMIND_MODEL", "grok-3-fast")

    if "fast" in model or "mini" in model:
        score = 1800
        label = "Grok Fast (fastest tier) ~300–700ms avg"
    elif "grok-3" in model:
        score = 1500
        label = "Grok 3 (balanced) ~700–1200ms avg"
    else:
        score = 1200
        label = "Grok 4 (most powerful) ~1200ms+ avg"

    return DimensionScore(
        name="Response Latency",
        score=score,
        rationale=(
            f"Model: {model}. Latency tier score. "
            "Full per-call latency logging planned for v2 via OpenTelemetry."
        ),
        raw_value=label,
    )


def score_completion_rate(session: Session) -> DimensionScore:
    """
    Measures what % of added tasks have been completed.
    100% = 2000 pts. Also rewards partial subtask completion.
    """
    tasks = session.tasks
    if not tasks:
        return DimensionScore("User Goal Completion Rate", 0, rationale="No tasks yet.")

    done_tasks = [t for t in tasks if t.status == "done"]
    task_rate = len(done_tasks) / len(tasks)

    # Subtask partial credit
    total_subs = sum(len(t.subtasks) for t in tasks)
    done_subs = sum(
        sum(1 for s in t.subtasks if s.status == "done")
        for t in tasks
    )
    sub_rate = done_subs / max(1, total_subs)

    # Weighted: 60% task completion, 40% subtask completion
    combined = (task_rate * 0.6) + (sub_rate * 0.4)
    score = int(combined * 2000)

    return DimensionScore(
        name="User Goal Completion Rate",
        score=score,
        rationale=(
            f"Tasks done: {len(done_tasks)}/{len(tasks)} ({task_rate*100:.0f}%). "
            f"Subtasks done: {done_subs}/{total_subs} ({sub_rate*100:.0f}%). "
            "Weighted 60/40."
        ),
        raw_value=f"{task_rate*100:.0f}% task completion",
    )


# ------------------------------------------------------------------ #
# Main evaluation entry point                                         #
# ------------------------------------------------------------------ #

def evaluate(session: Session) -> EvaluationReport:
    """Run all 5 evaluations and return a full EvaluationReport."""
    tasks = session.tasks

    dimensions = [
        score_decomposition(tasks),
        score_prioritization(tasks),
        score_context_retention(session),
        score_latency(tasks),
        score_completion_rate(session),
    ]

    total = sum(d.score for d in dimensions)

    if total >= 9000:
        grade = "S  (Exceptional)"
    elif total >= 7500:
        grade = "A  (Strong)"
    elif total >= 5500:
        grade = "B  (Competent)"
    elif total >= 3500:
        grade = "C  (Developing)"
    else:
        grade = "D  (Needs Work)"

    return EvaluationReport(
        dimensions=dimensions,
        total_score=total,
        grade=grade,
        session_snapshot={
            "total_tasks": len(tasks),
            "completed": session.total_tasks_completed,
            "pending": len([t for t in tasks if t.status != "done"]),
        },
    )


def display_report(report: EvaluationReport) -> None:
    """Pretty-print the evaluation report to the console."""
    table = Table(
        title="[bold]TaskMind Performance Report[/bold]",
        show_header=True,
        header_style="bold magenta",
        border_style="dim",
    )
    table.add_column("Dimension", style="bold white", min_width=28)
    table.add_column("Score", justify="right", width=10)
    table.add_column("/ Max", justify="right", width=7)
    table.add_column("%", justify="right", width=6)
    table.add_column("Measurement", style="dim", min_width=30)

    for d in report.dimensions:
        pct = int(d.score / d.max_score * 100)
        color = "green" if pct >= 75 else "yellow" if pct >= 50 else "red"
        table.add_row(
            d.name,
            f"[{color}]{d.score}[/{color}]",
            str(d.max_score),
            f"[{color}]{pct}%[/{color}]",
            d.raw_value,
        )

    table.add_section()
    total_pct = int(report.total_score / 10000 * 100)
    table.add_row(
        "[bold]TOTAL SCORE[/bold]",
        f"[bold cyan]{report.total_score}[/bold cyan]",
        "10,000",
        f"[bold cyan]{total_pct}%[/bold cyan]",
        f"Grade: [bold]{report.grade}[/bold]",
    )

    console.print()
    console.print(table)

    # Dimension rationales
    console.print("\n[bold]Scoring Rationale:[/bold]")
    for d in report.dimensions:
        console.print(f"  [cyan]{d.name}:[/cyan] {d.rationale}")

    console.print(
        f"\n[dim]Session: {report.session_snapshot['total_tasks']} total tasks | "
        f"{report.session_snapshot['completed']} completed | "
        f"{report.session_snapshot['pending']} pending[/dim]\n"
    )
