"""
agent/planner.py
----------------
All Claude API calls live here.
Handles task prioritization, decomposition, and AI-powered planning.
"""

import json
import os
import time
import uuid
from typing import Optional

from openai import OpenAI

from agent.memory import Session, Subtask, Task

_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "XAI_API_KEY is not set. Copy .env.example to .env and add your key."
            )
        _client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
    return _client


def _get_model() -> str:
    return os.getenv("TASKMIND_MODEL", "llama-3.3-70b-versatile")


def _get_max_tokens() -> int:
    return int(os.getenv("TASKMIND_MAX_TOKENS", "1024"))


PLAN_SYSTEM_PROMPT = """You are TaskMind, an expert AI productivity agent.
Your job is to analyze a task description and return a structured JSON plan.

Return ONLY valid JSON. No preamble, no markdown fences, no explanation.

JSON schema:
{
  "title": "short task title (max 60 chars)",
  "urgency": <int 1-5>,
  "impact": <int 1-5>,
  "effort": <int 1-5>,
  "ai_notes": "one-line strategic insight about this task",
  "subtasks": [
    {"description": "actionable step (start with a verb)"},
    ...
  ]
}

Rules:
- urgency: 5 = do today, 1 = can wait weeks
- impact: 5 = huge value, 1 = negligible
- effort: 5 = days of work, 1 = under 30 minutes
- subtasks: 3 to 7 items, each concrete and actionable
- priority_score = (urgency * impact) / effort  (calculated externally)
"""


def plan_task(raw_input: str, existing_tasks: list[Task]) -> Task:
    """
    Send a raw task description to Claude and get back a fully structured Task.
    Returns a Task dataclass ready to be saved to the session.
    """
    context = ""
    if existing_tasks:
        context = "\n\nExisting tasks (for context/deduplication):\n"
        for t in existing_tasks[-5:]:  # last 5 tasks for context
            context += f"- [{t.status}] {t.title} (priority: {t.priority_score:.1f})\n"

    client = _get_client()
    start_time = time.time()

    response = client.chat.completions.create(
        model=_get_model(),
        max_tokens=_get_max_tokens(),
        messages=[
            {"role": "system", "content": PLAN_SYSTEM_PROMPT},
            {"role": "user", "content": f"Plan this task: {raw_input}{context}"},
        ],
    )

    latency_ms = (time.time() - start_time) * 1000
    raw_json = response.choices[0].message.content.strip()

    # Strip markdown fences if model misbehaves
    if raw_json.startswith("```"):
        raw_json = raw_json.split("```")[1]
        if raw_json.startswith("json"):
            raw_json = raw_json[4:]

    plan = json.loads(raw_json)

    urgency = int(plan["urgency"])
    impact = int(plan["impact"])
    effort = max(1, int(plan["effort"]))  # avoid division by zero
    priority_score = round((urgency * impact) / effort, 2)

    task_id = str(uuid.uuid4())[:8]
    subtasks = [
        Subtask(
            id=f"{task_id}-{i+1}",
            description=s["description"],
        )
        for i, s in enumerate(plan.get("subtasks", []))
    ]

    return Task(
        id=task_id,
        raw_input=raw_input,
        title=plan["title"],
        priority_score=priority_score,
        urgency=urgency,
        impact=impact,
        effort=effort,
        subtasks=subtasks,
        ai_notes=plan.get("ai_notes", ""),
        # Store latency on ai_notes for metrics access
    ), latency_ms


def reprioritize_all(session: Session) -> list[Task]:
    """
    Ask Claude to re-evaluate the priority order of all pending tasks
    given the full context of the session. Returns tasks sorted by score.
    """
    pending = [t for t in session.tasks if t.status != "done"]
    if not pending:
        return []

    task_list = "\n".join(
        f"{i+1}. [{t.id}] {t.title} | urgency={t.urgency} impact={t.impact} effort={t.effort}"
        for i, t in enumerate(pending)
    )

    client = _get_client()
    response = client.chat.completions.create(
        model=_get_model(),
        max_tokens=512,
        messages=[
            {
                "role": "system",
                "content": """You are a productivity coach. Given a list of tasks with urgency/impact/effort scores,
return ONLY a JSON array of task IDs in the recommended execution order (highest priority first).
Example: ["abc123", "def456"]""",
            },
            {"role": "user", "content": f"Reorder these tasks by priority:\n{task_list}"},
        ],
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    ordered_ids = json.loads(raw)
    id_to_task = {t.id: t for t in pending}
    reordered = [id_to_task[tid] for tid in ordered_ids if tid in id_to_task]
    # Append any tasks not returned by AI (safety)
    returned_ids = set(ordered_ids)
    reordered += [t for t in pending if t.id not in returned_ids]
    return reordered
