# 🚀 HOW TO USE AI AUTONOMOUS ENGINEER (PHASE 4)

Welcome to your **Interactive Engineering Platform**. This guide covers the high-end web interface for managing your autonomous engineering team.

---

## 🛠️ QUICK START

1.  **Launch the Platform:**
    Run the unified start script from the project root:
    ```powershell
    python start_platform.py
    ```
    This launches both the **FastAPI Backend** and the **Interactive Web UI**.

2.  **Access the Dashboard:**
    Open your browser to: `http://localhost:3000`

3.  **Onboarding Tour:**
    The **AI Autonomous Engineer Tour** will automatically start for new users, guiding you through Project Management, Task Input, and the Real-time Dashboard.

---

## 🏗️ CORE MODULES & WORKFLOW

### 1. Project Management System
*   **Create Project:** Click `+ New Project` in the sidebar. Each project has its own isolated memory and history.
*   **Switching:** Click any project in the sidebar to load its state.

### 2. Interactive Chat (The Manager)
*   **Input:** Use the chat box to assign goals (e.g., "Build a React component for a weather app").
*   **Simulated Responses:** If the backend is offline, the UI enters a simulation mode to show you potential agent logic.
*   **Live Metrics:** Watch the top-bar for token usage and success rates.

### 3. Real-time Execution Dashboard
*   **Live DAG:** Switch to the `Dashboard` tab to see the agent dependency graph update as tasks are completed.
*   **Status Cards:** View real-time heartbeats from the Software Developer, QA Engineer, and DevOps agents.

### 4. Memory & History
*   **Persistence:** Every decision is logged in the `Memory` tab. Click JSON files to inspect agent reasoning and error logs.
*   **Audit Trail:** Perfect for understanding WHY an agent chose a specific implementation.

---

## ⚙️ SETTINGS & CONFIGURATION
Click the **Gear Icon** in the bottom-left sidebar to:
*   Adjust **Token Limits** (Safety first!).
*   Configure **Max Retries** for self-healing loops.
*   **Restart Tour** if you need a refresh on platform features.

---

## 💡 PRO TIPS
- **Be Specific:** The more details you provide in the chat, the better the agents perform.
- **Isolated Workspaces:** Use different projects for unrelated tasks to prevent memory pollution.
- **Reports:** Always check the `Reports` tab after completion for the final engineering summary and test results.

---
© 2026 AI Autonomous Engineer Team
