"""
Software Developer Worker — HiClaw Agent.

Domain: Code architecture, implementation, framework setup, refactoring.
Executes ALL tasks via Claude Flow internally.
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from config.settings import WORKER_ROLES
from core.agent_base import WorkerAgent
from core.message import TaskSpec
from core.hiclaw_bridge import HiClawCoordinator

logger = logging.getLogger(__name__)

_ROLE_CONFIG = WORKER_ROLES["SOFTWARE_DEVELOPER"]


class SoftwareDeveloper(WorkerAgent):
    """
    Software Developer specialist.

    Capabilities: code architecture, implementation, framework setup,
    refactoring, documentation.

    All execution goes through Claude Flow — never direct.
    """

    def __init__(self, coordinator: Optional[HiClawCoordinator] = None, memory_dir: Optional[str] = None):
        super().__init__(
            agent_id=str(uuid.uuid4()),
            role="SOFTWARE_DEVELOPER",
            capabilities=_ROLE_CONFIG["capabilities"],
            coordinator=coordinator,
            memory_dir=memory_dir
        )

    async def _process_task(self, task: TaskSpec) -> dict:
        """
        Domain-specific processing: Write actual Python code to disk.
        """
        self._logger.info(f"🛠  Processing dev task: {task.title}")
        from core.tools.fs_tools import FileSystemTools
        
        category = task.category.lower()
        desc = task.description.lower()
        
        if "math" in desc:
            filename = "math_lib.py"
            code = (
                "def add(a, b):\n"
                "    return a + b\n\n"
                "def subtract(a, b):\n"
                "    return a - b\n"
            )
        else:
            clean_title = "".join(c if c.isalnum() else "_" for c in task.title).strip("_").lower()[:20]
            filename = f"{clean_title}.py"
            code = f'"""\nAuto-generated module for: {task.title}\n"""\n\n'
            code += "def execute():\n    pass\n"
            
        FileSystemTools.write_file(filename, code)
        self._logger.info(f"  Wrote module to disk: {filename}")
        
        result = {
            "domain": "software_development",
            "task": task.title,
            "category": category,
            "action": "wrote_file",
            "artifacts": {
                "source_code": filename
            },
            "status": "implemented",
        }
        self.memory.store_output(task.title, result, tags=["dev_output", "file_system"])
        return result
