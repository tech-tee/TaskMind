# 🧠 TaskMind — AI-Powered Task Prioritization & Execution Agent

> *"The future of productivity isn't a better Jira ticket. It's an agent that thinks for you."*

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![Powered by Grok](https://img.shields.io/badge/AI-Grok%20xAI-orange.svg)](https://x.ai)
[![Cursor Ready](https://img.shields.io/badge/Cursor-Ready-purple.svg)](https://cursor.sh)

---

## What is TaskMind?

TaskMind is a CLI-based AI agent that turns plain-English task descriptions into **structured,
prioritized, executable plans** — and remembers them across sessions.

**The problem it solves:** You have tasks in your head, tasks in your notes, tasks in chat
threads. None of them have priority scores. None of them have actionable subtasks. And by
tomorrow, you've forgotten half of them.

TaskMind fixes this in under 2 seconds per task.

```bash
$ python main.py add "Finish the ML assignment and submit before Friday"

🤖 TaskMind is planning: Finish the ML assignment and submit before Friday

╭─────────────────────────────────────────────────────╮
│  ✓ Task added!                                       │
│                                                      │
│  Complete and Submit ML Assignment Before Deadline   │
│  ID: a3f2b1c4  Priority: 20.0  Subtasks: 5          │
│                                                      │
│  High-urgency deadline task — execute sequentially.  │
│  AI latency: 412ms                                   │
╰─────────────────────────────────────────────────────╯
```

---

## Features

| Feature | Description |
|---|---|
| **AI Task Planning** | Claude decomposes any task into 3–7 actionable subtasks |
| **Priority Scoring** | Formula: `(urgency × impact) / effort` — transparent and auditable |
| **Session Memory** | All tasks persist in `.taskmind_session.json` across CLI sessions |
| **Interactive Execution** | `run` command walks you through each subtask with prompts |
| **AI Reprioritization** | Claude re-ranks all tasks with full context in one command |
| **Performance Metrics** | Quantified 0–10,000 score across 5 dimensions |
| **Cursor-Ready** | `.cursorrules` configures Cursor AI to understand the entire codebase |

---

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/yourusername/taskmind.git
cd taskmind
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### 3. Run

```bash
python main.py add "Prepare slides for the team presentation tomorrow"
python main.py list
python main.py run
python main.py report
```

---

## CLI Reference

```
python main.py <command> [args]
```

| Command | Args | Description |
|---|---|---|
| `add` | `"task description"` | AI-plan and add a new task |
| `list` | — | Show all pending tasks sorted by priority |
| `run` | `[task-id]` | Execute a task interactively (auto-selects highest priority) |
| `show` | `task-id` | Show full detail + subtasks for one task |
| `done` | `task-id` | Mark a task as complete |
| `reprioritize` | — | Ask Claude to re-order all tasks by priority |
| `report` | — | Show performance score (0–10,000) |
| `clear` | — | Clear all tasks from the session |

---

## Example Workflow

```bash
# 1. Add tasks (plain English)
python main.py add "Study for distributed systems exam on Monday"
python main.py add "Fix the memory leak bug in the payment service"
python main.py add "Write the weekly team update email"

# 2. See your prioritized queue
python main.py list

# 3. Let AI re-evaluate with full context
python main.py reprioritize

# 4. Execute the top task interactively
python main.py run

# 5. Check your performance score
python main.py report
```

---

## Performance Metrics (0–10,000)

TaskMind evaluates itself across 5 dimensions, each worth 2,000 points:

| Dimension | Formula | What It Measures |
|---|---|---|
| **Task Decomposition Quality** | `(subtask_count_score + description_richness) / 2` | Are subtasks 3–7, actionable, and specific? |
| **Prioritization Accuracy** | `1 - (formula_errors / total_tasks)` | Does `score == (U×I)/E` for every task? |
| **Context Retention** | `1 - (integrity_issues / checks)` | Are IDs, timestamps, and counts consistent? |
| **Response Latency** | Model tier scoring | Haiku=1800, Sonnet=1400, Opus=1000 |
| **User Goal Completion** | `(task_rate × 0.6) + (sub_rate × 0.4)` | % tasks and subtasks completed |

**Typical score with active usage:** 7,000–8,500 / 10,000

---

## Architecture

```
taskmind/
├── .cursorrules              ← Cursor AI configuration
├── .env.example              ← Environment template (never commit .env)
├── main.py                   ← CLI entry point (argparse)
├── agent/
│   ├── core.py               ← Agent orchestration
│   ├── planner.py            ← All Claude API calls
│   ├── executor.py           ← Interactive task execution
│   └── memory.py             ← JSON session persistence
├── metrics/
│   └── evaluator.py          ← 0–10,000 performance scoring
├── benchmarks/
│   └── comparison.md         ← TaskMind vs default Cursor/Claude
└── docs/
    └── self_review.md        ← 1-page summary + full thought process
```

**Key design principles:**
- All AI calls go through `agent/planner.py` only — no scattered API calls
- All disk I/O goes through `agent/memory.py` only — single source of truth
- No hardcoded secrets — all configuration via environment variables
- Dataclasses throughout — type-safe, Cursor-friendly, IDE-autocomplete-ready

---

## Cursor Configuration

This project includes `.cursorrules` which tells Cursor:
- The agent's architecture and file responsibilities
- Code style rules (type hints, docstrings, f-strings)
- Which files to touch for which kinds of changes
- Environment variable requirements
- Testing patterns (mock the API client)

Open the project in Cursor and it will automatically apply these rules to all AI suggestions.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `XAI_API_KEY` | *(required)* | Your xAI API key |
| `TASKMIND_MODEL` | `grok-3-fast` | Grok model to use |
| `TASKMIND_MAX_TOKENS` | `1024` | Max tokens per AI response |
| `TASKMIND_SESSION_FILE` | `.taskmind_session.json` | Session storage path |

---

## Security

- ✅ No API keys in source code — all via `.env` (gitignored)
- ✅ `.env.example` provided as safe template
- ✅ Session data is local-only — never transmitted except to Anthropic API
- ✅ `.gitignore` excludes all sensitive files

---

## Benchmark vs Default Cursor/Claude

See [`benchmarks/comparison.md`](benchmarks/comparison.md) for the full analysis.

**TL;DR:**

| | TaskMind | Default Cursor/Claude |
|---|---|---|
| Persistent memory | ✅ | ❌ |
| Quantified priority | ✅ | ❌ |
| Progress tracking | ✅ | ❌ |
| Performance score | ✅ 0–10,000 | ❌ |
| Open-ended reasoning | ❌ | ✅ |
| Code context awareness | ❌ | ✅ |

Estimated scores: **TaskMind ~7,540** vs **Default ~4,200** (on productivity tasks).

---

## Roadmap

- [ ] v1.5 — Per-call latency logging via `time.perf_counter()`
- [ ] v2.0 — Multi-agent: Planner + Executor + Critic loop
- [ ] v2.0 — Vector memory (ChromaDB) for cross-session similarity
- [ ] v2.0 — FastAPI + React web interface
- [ ] v3.0 — Calendar integration for auto-scheduling
- [ ] v3.0 — Team mode with shared session files

---

## License

MIT — use it, fork it, ship it.
