"""
DevOps Engineer Worker — Advanced Phase 3 Agent.

Provides containerization generation, infrastructure setup,
deployment strategies, and real Git operations.
"""

from __future__ import annotations

import logging
import uuid
import os
from typing import Optional

from config.settings import WORKER_ROLES
from core.agent_base import WorkerAgent
from core.message import TaskSpec
from core.hiclaw_bridge import HiClawCoordinator
from core.memory import ProjectMemory
from core.tools.fs_tools import FileSystemTools
from core.tools.git_tools import GitTools

logger = logging.getLogger(__name__)

_ROLE_CONFIG = WORKER_ROLES["DEVOPS_ENGINEER"]


class DevOpsEngineer(WorkerAgent):
    def __init__(self, coordinator: Optional[HiClawCoordinator] = None, memory_dir: Optional[str] = None):
        super().__init__(
            agent_id=str(uuid.uuid4()),
            role="DEVOPS_ENGINEER",
            capabilities=_ROLE_CONFIG["capabilities"],
            coordinator=coordinator,
            memory_dir=memory_dir
        )
        self.project_memory = ProjectMemory(base_dir=memory_dir or "memory")

    async def _process_task(self, task: TaskSpec) -> dict:
        """
        Domain-specific processing: Write Dockerfiles, configure Git, deploy.
        """
        self._logger.info(f"⚓ Processing DevOps task: {task.title}")
        category = task.category.lower()
        desc = task.description.lower()
        
        deployed = False
        docker_file_created = False
        git_commit_logs = ""

        # Containerization Task
        if "docker" in desc or "container" in desc or "deploy" in desc:
            dockerfile = (
                "FROM python:3.9-slim\n"
                "WORKDIR /app\n"
                "COPY requirements.txt .\n"
                "RUN pip install --no-cache-dir -r requirements.txt\n"
                "COPY . .\n"
                "CMD [\"python\", \"main.py\"]\n"
            )
            FileSystemTools.write_file("Dockerfile", dockerfile)
            docker_file_created = True
            
            # Record deployment metric
            self.project_memory.add_deployment_history({
                "task_id": task.task_id,
                "strategy": "Docker Image",
                "timestamp": str(self.project_memory)
            })
            deployed = True
            self._logger.info("  Generated Dockerfile for containerization.")

        # Git Source Control Integration
        if "git" in desc or "commit" in desc or deployed:
            # Initialize Git if missing
            out = GitTools.init_repo()
            self._logger.info(f"  Git Init: {out}")

            # Extract user message constraint or default
            msg = f"Auto-commit: DevOps execution for {task.task_id[:8]}"
            commit_result = GitTools.commit_all(msg)
            git_commit_logs = commit_result
            self._logger.info(f"  Git Action: {commit_result}")

        result = {
            "domain": "devops",
            "task": task.title,
            "category": category,
            "action": "infrastructure_setup",
            "artifacts": {
                "dockerfile_created": docker_file_created,
                "git_commit": git_commit_logs,
                "deployment_ready": deployed
            },
            "status": "configured",
        }

        self.memory.store_output(task.title, result, tags=["devops_output", "infrastructure"])
        return result
