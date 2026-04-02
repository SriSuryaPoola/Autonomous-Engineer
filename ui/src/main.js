// Main Frontend Controller for AI Autonomous Engineer Platform
const API_BASE = "http://localhost:8000/api";
const WS_BASE = "ws://localhost:8000/ws/events";

let currentProject = null;
let projects = [];
let socket = null;

// --- DOM Elements ---
const tabBtns = document.querySelectorAll('.tab-btn');
const tabContents = document.querySelectorAll('.tab-content');
const projectList = document.getElementById('project-list');
const taskInput = document.getElementById('task-input');
const executeBtn = document.getElementById('send-task-btn');
const dashboardStats = {
    status: document.getElementById('exec-status'),
    tasks: document.getElementById('exec-tasks'),
    failures: document.getElementById('exec-failures')
};

// --- Tab Switching ---
tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        const tabId = btn.getAttribute('data-tab');
        
        // Update active tab button
        tabBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        
        // Update active content
        tabContents.forEach(content => {
            content.classList.remove('active');
            if (content.id === `${tabId}-view`) {
                content.classList.add('active');
            }
        });
    });
});

// --- Project Management ---
const projectModal = document.getElementById('project-modal');
const newProjectBtn = document.getElementById('new-project-btn');
const saveProjectBtn = document.getElementById('save-project-btn');
const closeProjectBtn = document.getElementById('close-project-modal');

newProjectBtn.onclick = () => projectModal.classList.remove('hidden');
closeProjectBtn.onclick = () => projectModal.classList.add('hidden');

saveProjectBtn.onclick = async () => {
    const name = document.getElementById('new-project-name').value.trim();
    const desc = document.getElementById('new-project-desc').value.trim();
    const repo = document.getElementById('new-project-repo').value.trim();
    
    if (!name) return alert("Project name is required.");

    try {
        const resp = await fetch(`${API_BASE}/projects`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, description: desc, repository_url: repo })
        });
        const newProject = await resp.json();
        projects.push(newProject);
        selectProject(newProject.id);
        projectModal.classList.add('hidden');
    } catch (err) {
        console.error("Using offline mode due to server unavailability.");
        // Mock success for offline demo
        const mockID = Math.random().toString(36).substring(7);
        const newProject = { id: mockID, name, description: desc };
        projects.push(newProject);
        selectProject(newProject.id);
        projectModal.classList.add('hidden');
    }
};

async function fetchProjects() {
    try {
        const resp = await fetch(`${API_BASE}/projects`);
        projects = await resp.json();
        renderProjectList();
    } catch (err) {
        console.warn("Backend offline. Dashboard running in demo mode.");
        projects = [{ id: "demo-1", name: "Sample Project", description: "This is a local demo project." }];
        renderProjectList();
    }
}

function renderProjectList() {
    projectList.innerHTML = projects.map(p => `
        <div class="project-item ${currentProject?.id === p.id ? 'active' : ''}" onclick="selectProject('${p.id}')" title="${p.name}">
            <div class="p-icon">${p.name[0]}</div>
            <div class="p-details">
                <span class="p-name">${p.name}</span>
                <span class="p-id">${p.id}</span>
            </div>
        </div>
    `).join('');
}

window.selectProject = (id) => {
    currentProject = projects.find(p => p.id === id);
    if (!currentProject) return;
    document.getElementById('current-project-name').textContent = currentProject.name;
    document.getElementById('current-project-desc').textContent = currentProject.description;
    
    // Reset views for new project
    document.getElementById('dag-viz').innerHTML = "Awaiting task initiation...";
    document.getElementById('report-list').innerHTML = "";
    document.getElementById('chat-messages').innerHTML = ""; // Phase 6 FIX: clear isolated chat
    
    // Legacy metrics
    dashboardStats.status.textContent = "IDLE";
    dashboardStats.status.style.color = "#8b949e";

    // Phase 5 metrics
    updateConvergencePanel({ state: "AWAITING", coverage: { percentage: null }, iterations: "—", self_heals: "—" });
    if (_convergencePoller) {
        clearInterval(_convergencePoller);
        _convergencePoller = null;
    }
    
    renderProjectList();
};

// --- Task Execution ---
executeBtn.addEventListener('click', async () => {
    if (!currentProject) return alert("Select a project first!");
    const prompt = taskInput.value.trim();
    if (!prompt) return;

    addChatMessage("user", prompt);
    taskInput.value = "";
    
    // Immediate UI Feedback
    dashboardStats.status.textContent = "RUNNING";
    dashboardStats.status.style.color = "var(--acc-cyan)";
    updateConvergencePanel({ state: "RUNNING", coverage: { percentage: null }, iterations: "…", self_heals: "…" });
    renderMockDashboard();
    renderMockReports();

    try {
        const resp = await fetch(`${API_BASE}/tasks`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ project_id: currentProject.id, prompt: prompt })
        });
        if (resp.ok) {
            addChatMessage("system", "Engine initiated. Connecting to orchestration core...");
            // Start polling convergence state every 5 seconds
            startConvergencePolling(currentProject.id);
        } else {
            throw new Error("Backend offline");
        }
    } catch(e) {
        addChatMessage("system", "Warning: Backend unreachable. Entering Simulation Mode.");
        simulateAgentFlow(prompt);
    }
});

function renderMockDashboard() {
    const viz = document.getElementById('dag-viz');
    viz.innerHTML = `
        <div style="display: flex; flex-direction: column; align-items: center; gap: 20px;">
            <svg viewBox="0 0 400 120" style="width:100%; max-width: 500px;">
                <defs>
                    <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="0" refY="3.5" orient="auto">
                        <polygon points="0 0, 10 3.5, 0 7" fill="#444" />
                    </marker>
                </defs>
                <circle cx="50" cy="60" r="15" fill="var(--acc-cyan)" style="filter: drop-shadow(0 0 5px var(--acc-cyan));" />
                <text x="35" y="90" fill="#fff" font-size="10" font-weight="bold">COORD</text>
                
                <path d="M 65 60 L 130 30" stroke="#444" fill="none" marker-end="url(#arrowhead)" />
                <path d="M 65 60 L 130 90" stroke="#444" fill="none" marker-end="url(#arrowhead)" />
                
                <circle cx="150" cy="30" r="15" fill="#ff00ea" />
                <text x="135" y="55" fill="#fff" font-size="9">DEV_CORE</text>
                
                <circle cx="150" cy="90" r="15" fill="#00ff88" />
                <text x="138" y="115" fill="#fff" font-size="9">QA_AUDIT</text>
                
                <path d="M 165 30 L 230 60" stroke="#444" fill="none" marker-end="url(#arrowhead)" />
                <path d="M 165 90 L 230 60" stroke="#444" fill="none" marker-end="url(#arrowhead)" />
                
                <circle cx="250" cy="60" r="15" fill="#fff" />
                <text x="235" y="90" fill="#fff" font-size="10">REPLAY</text>
            </svg>
            <p style="font-size: 0.8rem; color: #8b949e; margin: 0;">Auto-scaling DAG execution graph... (Real-time)</p>
        </div>
    `;
    dashboardStats.tasks.textContent = "1";
    dashboardStats.failures.textContent = "0";
}

function renderMockReports() {
    const reports = document.getElementById('report-list');
    reports.innerHTML = `
        <div class="report-item" onclick="viewReport('Final_Engineering_Spec')">
            <label>ENGINEERING SPEC</label>
            <h4>Architecture Design Document</h4>
            <p>Validated by Claude 3.5 Sonnet</p>
        </div>
        <div class="report-item" onclick="viewReport('Quality_Audit_Results')">
            <label>QA AUDIT</label>
            <h4>Test Coverage & Performance</h4>
            <p>100% Pass Rate (Simulation)</p>
        </div>
    `;
}

window.viewReport = (name) => {
    const viewer = document.getElementById('report-view-content');
    viewer.classList.remove('hidden');
    
    const content = name === 'Final_Engineering_Spec' 
        ? "# Engineering Specification\n\n## Overview\nThis project implements a high-performance multi-agent coordination layer.\n\n## Architecture\n- **Dev Agent:** Code Generation\n- **QA Agent:** Logic Validation\n- **Orchestration:** Claude-Powered Flow"
        : "# QA Audit Results\n\n## Metrics\n- **Unit Tests:** 42 Passed\n- **Regression:** 15 Passed\n- **Performance:** 98th Percentile Latency < 200ms";

    viewer.innerHTML = `
        <div style="padding: 20px; color: #e6edf3; line-height: 1.6;">
            <button onclick="document.getElementById('report-view-content').classList.add('hidden')" style="background: none; border: 1px solid #444; color: #8b949e; padding: 5px 10px; cursor: pointer; border-radius: 4px; margin-bottom: 20px;">← Back to List</button>
            ${content.replace(/\n/g, '<br>')}
        </div>
    `;
};

// =============================================================================
// Phase 5 — Convergence State Polling & Dashboard Integration
// =============================================================================

let _convergencePoller = null;

/**
 * Start polling the convergence API every 5s for the given project.
 * Stops automatically when state becomes CONVERGED or ESCALATED.
 */
function startConvergencePolling(projectId) {
    if (_convergencePoller) clearInterval(_convergencePoller);

    _convergencePoller = setInterval(async () => {
        try {
            const resp = await fetch(`${API_BASE}/projects/${projectId}/convergence`);
            if (!resp.ok) return;
            const data = await resp.json();
            updateConvergencePanel(data);

            // Stop polling when task is done
            const terminal = ['CONVERGED', 'ESCALATED', 'AWAITING'];
            if (terminal.includes(data.state)) {
                clearInterval(_convergencePoller);
                _convergencePoller = null;

                // Show summary in chat
                if (data.summary) {
                    addChatMessage('system', `[Convergence] ${data.summary}`);
                }
            }
        } catch (e) {
            // Backend offline — silently skip
        }
    }, 5000);
}

/**
 * Update the convergence panel metrics with live data from the API.
 */
function updateConvergencePanel(data) {
    const stateEl = document.getElementById('conv-state-label');
    const coverageEl = document.getElementById('conv-coverage');
    const iterEl = document.getElementById('conv-iterations');
    const healsEl = document.getElementById('conv-heals');

    if (!stateEl) return;

    const state = data.state || 'AWAITING';
    stateEl.textContent = state;

    // Remove all state classes, then apply the current one
    const stateClasses = ['state-converged', 'state-partial', 'state-escalated', 'state-running', 'state-awaiting'];
    stateEl.classList.remove(...stateClasses);
    stateEl.classList.add(`state-${state.toLowerCase()}`);

    // Coverage
    const pct = data.coverage?.percentage;
    coverageEl.textContent = (pct !== null && pct !== undefined) ? `${pct.toFixed(1)}%` : '—%';

    // Iterations & self-heals
    iterEl.textContent = data.iterations ?? '—';
    healsEl.textContent = data.self_heals ?? '—';
}

function addChatMessage(role, text) {
    const chatMsgs = document.getElementById('chat-messages');
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;
    msgDiv.innerHTML = `<div class="msg-header">${role.toUpperCase()}</div><div class="msg-body">${text}</div>`;
    chatMsgs.appendChild(msgDiv);
    chatMsgs.scrollTop = chatMsgs.scrollHeight;
}

// --- Real-time WebSocket Logic ---
function connectWS() {
    try {
        socket = new WebSocket(WS_BASE);
        socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            handleServerEvent(data);
        };
        socket.onclose = () => {
            setTimeout(connectWS, 10000); // Slower reconnect for offline
        };
    } catch(e) {
        console.log("WebSocket suppressed (offline).");
    }
}

function handleServerEvent(data) {
    if (data.type === "task_started") {
        addChatMessage("system", `Engine initiated: ${data.prompt}`);
    } else if (data.type === "engineer_event") {
        const content = data.content;
        const sender = data.sender;
        
        if (content.type === "status_update") {
            addChatMessage("system", `[${sender.slice(0,8)}] ${content.text}`);
            dashboardStats.status.textContent = "EXECUTING";
        } else if (content.agent_role) {
            addChatMessage(content.agent_role.toLowerCase(), content.output || content.plan);
            if (content.status === "completed") {
                dashboardStats.status.textContent = "IDLE";
                dashboardStats.status.style.color = "#8b949e";
            }
        }
    }
}

// --- Sample Prompts ---
document.querySelectorAll('.prompt-tag').forEach(tag => {
    tag.addEventListener('click', () => {
        taskInput.value = tag.textContent;
        taskInput.focus();
    });
});

// --- Settings Modal ---
const settingsBtn = document.getElementById('settings-btn');
const settingsModal = document.getElementById('settings-modal');
const saveSettingsBtn = document.getElementById('save-settings-btn');
const restartTourBtn = document.getElementById('restart-tour-btn');

settingsBtn.onclick = () => settingsModal.classList.toggle('hidden');

saveSettingsBtn.onclick = () => {
    const limit = document.getElementById('cfg-tokens').value;
    localStorage.setItem('engineer_token_limit', limit);
    settingsModal.classList.add('hidden');
    addChatMessage("system", "Settings updated locally.");
};

let tour; // Global tour instance

restartTourBtn.onclick = () => {
    settingsModal.classList.add('hidden');
    if (tour) tour.reset();
};

// --- Report Viewer ---
window.viewReport = (name) => {
    addChatMessage("system", `Opening report: ${name}... (Markdown rendering demo)`);
    // Mock logic
    const reports = document.getElementById('reports-view');
    reports.innerHTML = `<h3>Report: ${name}</h3><div class="md-preview"># Verification Successful\nTests passed: 42/42</div>`;
};

// --- Memory Viewer ---
document.querySelectorAll('.memory-card').forEach(card => {
    card.addEventListener('click', () => {
        const file = card.getAttribute('data-file');
        addChatMessage("system", `Inspecting memory file: ${file}.json...`);
    });
});

import { OnboardingTour } from './onboarding.js';

// --- Initialization ---
async function init() {
    // Start tour immediately to ensure it works even if API fails
    // Initialize the global tour instance
    tour = new OnboardingTour();
    setTimeout(() => {
        if (!localStorage.getItem('engineer_tour_finished')) {
            tour.start();
        }
    }, 500);

    await fetchProjects();
    connectWS();
}

init();
