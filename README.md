# 🤖 AI Autonomous Engineer (Phase 4)

Welcome to the **AI Autonomous Engineer**, a next-generation multi-agent platform capable of writing, testing, deploying, and maintaining production-level code completely autonomously. 

Powered by the **Autonomous Engineer Core** for orchestration and the **Claude Flow 6-step deep reasoning pipeline**, this system takes a plain English prompt and delivers fully tested, refactored, and committed code via a premium web-based dashboard or CLI.

---

## 🚀 Quick Start & Usage

### 🛠️ Prerequisites
The framework relies on standard Python 3.9+ libraries.
1. Install testing and observability dependencies:
   ```bash
   pip install pytest pytest-asyncio playwright locust
   ```
2. Install GitHub CLI (`gh`) and Git for deployment permissions.

### 💻 Starting the Web UI (Recommended)
You can manage the AI team using the Interactive Engineering Platform. It features project management, real-time agent observability, and an integrated chat system.
```bash
python start_platform.py
```
* **Dashboard Access:** Open your browser to `http://localhost:3000`.
* **The Manager Chat:** Use the chat box to assign multi-step goals directly to the CEO Manager Agent.

### ⌨️ CLI Operation Modes
If you prefer running the engine strictly from the terminal:
- **Single-Task Mode:** pass a prompt straight via arguments.
  ```bash
  python main.py "Create a math library, write tests, and open a PR on GitHub"
  ```
- **Real-Time Observability Terminal:** Launch with `--dashboard` for an interactive CLI dashboard tracking DAG states and active matrix rooms.
  ```bash
  python main.py "Your task description" --dashboard
  ```
- **Interactive REPL Mode:**
  ```bash
  python main.py --interactive
  ```

---

## 🏗️ Architecture: The Tri-Layer Sovereign System

The platform is structured on a hierarchical "Manager-Worker" model composed of three abstraction layers:

1. **Coordination (HiClaw Matrix Rooms)**
   - The central nervous system of the team routed through `core/hiclaw_bridge.py`.
   - Standardizes inter-agent IO using a strict **13-field format**.
2. **Scheduling (Explicit DAG Task Pipeline)**
   - The ManagerAgent decomposes complex requests into a Directed Acyclic Graph (DAG) queuing system (`core/task_pipeline.py`), guaranteeing dependencies execute in order.
3. **Execution (Claude Flow Engine)**
   - The cognitive brain inside the Worker Agents hitting a rigorous 6-step loop: `Understand → Decompose → Propose → Execute → Validate → Refine`.

### The Agent Team
- **Manager (CEO):** Translates user intent, breaks down dependencies, and assigns tasks.
- **Software Developer:** Uses `fs_tools` to write/mutate application files.
- **QA Engineer:** Implements UI (Playwright), API (FastAPI/Flask), Performance, and Regression suites.
- **DevOps Engineer:** Handles Docker pipelines and Git PR logic.

### Component Diagram
```mermaid
graph TD
    User((User Request)) --> Orchestrator[Orchestrator Loop]
    Orchestrator --> Dashboard[Live Terminal Dashboard]
    Orchestrator --> Manager[Manager Agent]
    
    subgraph "The Orchestration Core"
        Manager -->|Decompose| DAG[Task DAG / Priority Queue]
        DAG -->|Dispatch| ParallelExecutor[Parallel Executor]
    end
    
    subgraph "Autonomous Worker Layer"
        ParallelExecutor --> Dev[Software Developer]
        ParallelExecutor --> QA[QA Engineer - UI/API/Perf]
        ParallelExecutor --> DevOps[DevOps - Docker/CI]
    end
    
    subgraph "External Integration"
        Dev -->|FS Tools| Disk[(Local Filesystem)]
        QA -->|Test Tools| Pytest[Pytest Suite]
        DevOps -->|Git/CI Tools| GitHub[GitHub Actions]
    end
```

---

## ✨ Phase 4: Agentic Testing Engine

The hallmark of the Phase 4 Engine is its ability to test itself natively without hallucinations:

* **Sandbox Executor:** Spins off completely isolated subprocess environments mapping virtual environments (`.venv`), ensuring test executions are safe and dynamically bounded by CPU limits.
* **Intelligent Patch Engine:** Triages testing errors using Heuristics (Rule-based Regex fixing) or LLMs (Dynamic Code Bug logic-solvers). An LLM handling a `CodeBug` patches the source logic implicitly. It will never loosen a valid test case to fake a "success" state.
* **The 5-Iteration Convergence Cycle:** Agents pass outputs to the Sandbox and run a self-healing patch loop up to 5 times before requiring human escalation.
* **Coverage Deadlines (`pytest-cov`):** The system verifies total coverage percentages against source code. If coverage falls below config bounds (e.g. 70%), the QA Agent writes explicit Gap-filling testing paths using the generated JSON `.coverage` report.
* **MANDATORY Quality Scorer:** Inside the Validate Step 5, agents self-assess output. If completeness or correctness thresholds fail, the code is blocked from execution.

---

## 🔑 Tokens and Authorization

To power the LLM Patching and Code Generation Models, the engine natively utilizes **Claude-3-5-sonnet** or OpenAI compatible endpoints.

**Setup Instructions:**
1. Create a `.env` file in the root directory.
2. Add your authentication token: `ANTHROPIC_API_KEY="..."`

*(Note: Without a valid token, the Platform auto-defaults into **Heuristic Mode**, bypassing AI generation and patching via Regex constraints).*

---

## 💾 Memory & Configuration

### Persistent JSON State
The system preserves task histories and contexts natively in the local `memory/` folder to persist states across restarts:
- `memory/project_context.json`: High-level goals.
- `memory/task_history.json`: Complete audit trails.
- `memory/test_failures.json`: Historical bug patterns for the QA role.
- `memory/fix_strategies.json`: Learned repair patterns for CI failures.

### Guardrails / Cost Config
Update the thresholds inside `config/settings.py` to prevent runaway reasoning loops:
```python
MAX_RETRIES = 3 
TIMEOUT_PER_TOOL = 30  # Max sec per subprocess call
TOKEN_BUDGET_PER_TASK = 100000 
```
