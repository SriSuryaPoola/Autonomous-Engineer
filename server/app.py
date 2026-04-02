import asyncio
import json
import os
import uuid
from typing import List, Dict, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime

# Import core system (adjust paths if needed)
# from core.orchestrator import Orchestrator
# from core.message import AgentMessage

app = FastAPI(title="AI Autonomous Engineer | Advanced Engineering Platform")

# CORS for Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Data Models ---

class ProjectCreate(BaseModel):
    name: str
    description: str
    repository_url: Optional[str] = None

class Project(BaseModel):
    id: str
    name: str
    description: str
    repository_url: Optional[str] = None
    created_at: str
    memory_path: str

class TaskRequest(BaseModel):
    project_id: str
    prompt: str

# --- Persistence ---

PROJECTS_FILE = "memory/web_projects.json"

def load_projects() -> List[Dict]:
    if os.path.exists(PROJECTS_FILE):
        with open(PROJECTS_FILE, "r") as f:
            return json.load(f)
    return []

def save_projects(projects: List[Dict]):
    os.makedirs(os.path.dirname(PROJECTS_FILE), exist_ok=True)
    with open(PROJECTS_FILE, "w") as f:
        json.dump(projects, f, indent=2)

# --- WebSocket Manager ---

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

from orchestrator import Orchestrator
from core.message import AgentMessage, TaskSpec

# --- Global State ---
class SystemState:
    def __init__(self):
        self.orchestrators: Dict[str, Orchestrator] = {}

state = SystemState()

# --- Helpers ---

async def engineer_event_listener(msg: dict):
    """Callback for all Engineering room messages — broadcasts to WebSockets."""
    payload = {
        "type": "engineer_event",
        "sender": msg.get("sender_id", "system"),
        "room_id": msg.get("room_id"),
        "content": msg.get("content"),
        "timestamp": msg.get("timestamp")
    }
    await manager.broadcast(payload)

def get_orchestrator(project_id: str) -> Orchestrator:
    if project_id not in state.orchestrators:
        projects = load_projects()
        project = next((p for p in projects if p["id"] == project_id), None)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Initialize Orchestrator with isolated memory path
        orch = Orchestrator(memory_dir=project["memory_path"])
        
        # Register the web-socket broadcast listener on all standard rooms
        orch.coordinator.messenger.on_message(orch.coordinator.status_room.room_id, engineer_event_listener)
        orch.coordinator.messenger.on_message(orch.coordinator.broadcast_room.room_id, engineer_event_listener)
        orch.coordinator.messenger.on_message(orch.coordinator.review_room.room_id, engineer_event_listener)
        
        state.orchestrators[project_id] = orch
    return state.orchestrators[project_id]

# --- Endpoints ---

@app.get("/api/projects")
async def get_projects():
    return load_projects()

@app.post("/api/projects")
async def create_project(req: ProjectCreate):
    projects = load_projects()
    project_id = str(uuid.uuid4())[:8]
    memory_path = f"memory/projects/{project_id}"
    
    new_project = {
        "id": project_id,
        "name": req.name,
        "description": req.description,
        "repository_url": req.repository_url,
        "created_at": datetime.now().isoformat(),
        "memory_path": memory_path
    }
    
    projects.append(new_project)
    save_projects(projects)
    os.makedirs(memory_path, exist_ok=True)
    return new_project

@app.post("/api/tasks")
async def start_task(req: TaskRequest):
    try:
        orch = get_orchestrator(req.project_id)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"Orchestrator init failed: {e}\n{tb}")
        raise HTTPException(status_code=500, detail=f"Orchestrator init failed: {str(e)}")
    
    async def run_with_error_handling():
        try:
            await orch.run(req.prompt, use_dashboard=False)
        except Exception as e:
            import traceback
            logger.error(f"Task execution failed: {e}\n{traceback.format_exc()}")
            await manager.broadcast({
                "type": "engineer_event",
                "sender": "system",
                "content": {"text": f"⚠️ Task error: {str(e)}", "error": True},
                "timestamp": datetime.now().isoformat()
            })
    
    asyncio.create_task(run_with_error_handling())
    return {"status": "started", "project_id": req.project_id}

# --- Phase 5: Convergence & Coverage Endpoints ---

@app.get("/api/projects/{project_id}/convergence")
async def get_convergence(project_id: str):
    """
    Returns the latest ConvergenceReport for a project.
    Used by the live dashboard to display state, coverage, and iteration metrics.
    """
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from core.convergence_engine import ConvergenceEngine
        engine = ConvergenceEngine(memory_dir="memory/projects")
        report = engine.get_latest(project_id)
        if report:
            return report.to_dict()
        return {
            "project_id": project_id,
            "state": "AWAITING",
            "summary": "No tasks executed yet.",
            "iterations": 0,
            "self_heals": 0,
            "coverage": {"percentage": 0.0, "threshold": 70.0, "met": False},
            "ci": {"enabled": False, "success": None, "url": ""}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/projects/{project_id}/coverage")
async def get_coverage(project_id: str):
    """
    Returns the latest coverage percentage and trend for a project.
    """
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from core.coverage_tracker import CoverageTracker
        tracker = CoverageTracker(base_dir="memory/projects")
        trend = tracker.get_trend(project_id)
        history = tracker.get_history_summary(project_id)
        return {
            "current": trend["current"],
            "trend": trend["trend"],
            "direction": trend["direction"],
            "delta": trend["delta"],
            "history": history
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- WebSocket ---

@app.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle manual commands if needed
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
