# 🤖 AI Autonomous Engineer (Phase 4)

Welcome to the **AI Autonomous Engineer**, a next-generation multi-agent platform capable of writing, testing, deploying, and maintaining production-level code completely autonomously. 

Powered by the **Autonomous Engineer Core** for orchestration and communication, and the **Claude Flow 6-step deep reasoning pipeline**, this system takes a plain English prompt and delivers fully tested, refactored, and committed code via a premium web-based dashboard.

---

## 🏗️ Architecture Overview

The system operates across three tightly integrated layers:

1. **Coordination (HiClaw Matrix Rooms)**
   - The central nervous system of the team.
   - Manages message routing, standardizes inputs/outputs using a strict **13-field format**, and coordinates Task Lifecycles.
   - Schedules tasks using an **Explicit DAG Priority Queue**, guaranteeing dependencies are met before execution.

2. **Intelligence (Claude Flow)**
   - The brain inside every worker agent.
   - Executes a rigorous 6-step loop for every task: `Research → Plan → Code → Test → Validate → Refine`.
   - Constrained by **Token Budgets** and **Early Stopping** mechanisms to prevent infinite loops and control API costs.

3. **Specialization (Worker Agents)**
   - **Manager Agent (CEO):** Understands user goals, decomposes them, delegates to workers, and aggregates results. Never touches code directly.
   - **Software Developer:** Uses `fs_tools` to write actual application code and files to the disk.
   - **QA Engineer:** Specialized into **UI (Playwright)**, **API (Pytest)**, **Performance (Locust)**, and **Regression** roles.
   - **Code Reviewer:** Audits code quality and uses `cli_tools` to execute static analysis, linters, and syntax checks.
   - **DevOps Engineer:** Crafts Docker/CI pipelines, manages infrastructure, and uses **GitHub/CI tools** to commit code and open Pull Requests.

---

## ✨ Phase 3 Features

This system has been upgraded to **Phase 3**, transforming it into a production-grade engineering platform with real-world integrations:

* **GitHub & CI/CD Integration:** Native support for triggering GitHub Actions, reading pipeline logs, and opening Pull Requests via the `gh` CLI.
* **CI/CD Self-Healing Loop:** The Manager Agent autonomously detects CI failures post-deployment and enqueues high-priority debugging tasks for the developer.
* **Real-Time Terminal Dashboard:** Launch with `--dashboard` to see a live execution trace of all agents, DAG states, and failure metrics.
* **Fuzzy Path Matching:** Intelligent file resolution (using `difflib`) to handle user typos and locate the correct source files for testing.
* **Persistent Memory IO:** Project context, error patterns, task histories, and **fix strategies** are saved natively to a `memory/` folder in JSON format.
* **13-Field Protocol:** Strict adherence to the HiClaw communication standard for robust inter-agent state tracking.

---

## 📂 Project Structure

```text
├── main.py              # CLI / REPL Entry Point
├── orchestrator.py      # HiClaw ↔ Manager Initialization
├── config/
│   └── settings.py      # Global config, agent thresholds, budgets
├── core/
│   ├── claude_flow.py   # 6-step reasoning engine implementation
│   ├── hiclaw_bridge.py # HiClaw room/message coordination
│   ├── memory.py        # Persistent JSON brain mapping
│   ├── message.py       # 10-Field Message Protocol definition
│   ├── task_pipeline.py # DAG Priority Queue executor
│   └── tools/           # Phase 2 Real Mutaion Toolset
│       ├── cli_tools.py # Terminal command execution
│       ├── fs_tools.py  # Disk I/O manipulation
│       ├── git_tools.py # Repository management
│       └── test_tools.py# Test discovery and execution
├── agents/              # The AI Employees
│   ├── manager.py       
│   └── workers/         # Domain-specific specialists
│       ├── code_reviewer.py
│       ├── devops_engineer.py
│       ├── qa_engineer.py
│       └── software_developer.py
├── memory/              # (Auto-generated) Persistent brain files
└── tests/               # Self-test suites
```

---

## 🚀 Getting Started

To dive right in and start utilizing your AI employees, please check out the **[USAGE.md](USAGE.md)**. It contains detailed, step-by-step instructions on how to submit tasks, monitor the system, and configure the internal budget!
