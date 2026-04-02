# Autonomous AI Engineering Team — Detailed Usage Guide

This guide provides a comprehensive, step-by-step walkthrough on how to operate, configure, and monitor your Autonomous AI Engineering Team.

---

## 🛠️ Step 1: Prerequisites & Installation

The core framework is lightweight and relies on standard Python 3.9+ libraries.

### Setup Instructions
1. **Ensure Python 3.9+ is installed.**
2. **Install testing and observability dependencies.**
   ```bash
   pip install pytest pytest-asyncio playwright locust
   ```
3. **Ensure Git & GitHub CLI are installed.**
   - The DevOps engineer uses `git` and `gh` for commits and Pull Requests. Ensure they are authenticated and in your PATH.

---

## 🏃 Step 2: Running the System

### Option A: Single-Task CLI Mode
Pass a task directly as an argument using double quotes.

**Example Command:**
```bash
python main.py "Create a math library, write tests, and open a PR on GitHub"
```

### Option B: Real-Time Observability Dashboard (NEW)
Launch with the `--dashboard` flag to see a live terminal UI of all agent activities, DAG states, and tool status.
```bash
python main.py "Your task description" --dashboard
```

### Option C: Interactive REPL Mode
```bash
python main.py --interactive
```

---

## 📊 Step 3: Monitoring & Logging

### Observability Dashboard
The terminal dashboard provides:
- **Active Agents:** List of HiClaw agents currently polling for work.
- **DAG Execution:** Real-time progress bar of the task dependency graph.
- **Failure Tracking:** Live metrics on retries and tool errors.

### Detailed Debug Output
To see the internal inner-monologue (Claude Flow tokens), use the `-l DEBUG` flag:
```bash
python main.py -l DEBUG "Task description..."
```

---

## 🧠 Step 4: Accessing Persistent Memory

The AI Team retains context across executions in the `memory/` folder:
- **`memory/project_context.json`** — High-level goals.
- **`memory/task_history.json`** — Complete audit trail.
- **`memory/test_failures.json`** — Historical bug patterns used by the QA role.
- **`memory/fix_strategies.json`** — Learned repair patterns for CI failures.

---

## ⚙️ Step 5: Advanced Configuration & Cost Controls

Tune thresholds in `config/settings.py` for performance and budget:

```python
# Execution Limits
MAX_RETRIES = 3 
TIMEOUT_PER_TOOL = 30  # Max seconds per subprocess call
TOKEN_BUDGET_PER_TASK = 100000 
```

### Extending Capabilities
1. Add new tools to `core/tools/`.
2. Update the specialized Worker class (e.g., `qa_engineer.py` or `devops_engineer.py`) to utilize the new toolset via the Claude Flow validation loop.
