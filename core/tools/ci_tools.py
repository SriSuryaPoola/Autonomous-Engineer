"""
CI/CD Tools — Real-world integration with GitHub Actions / CI Pipelines.

Provides the ability to:
- Trigger pipelines
- Check pipeline run status
- Fetch failure logs for self-healing loops
"""

import os
import subprocess
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class CITools:
    """
    Interfaces with GitHub Actions (via `gh run`) to support dynamic CI/CD feedback loops.
    """

    @staticmethod
    def _run_cmd(cmd: str, cwd: Optional[str] = None) -> tuple[int, str, str]:
        cwd = cwd or os.getcwd()
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=45
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            return -1, "", f"Command timed out: {cmd}"
        except Exception as e:
            return -1, "", f"Execution failed: {e}"

    @classmethod
    def trigger_workflow(cls, workflow_name: str, ref: str = "main", cwd: Optional[str] = None) -> str:
        """Triggers a specific GitHub Actions workflow."""
        cmd = f'gh workflow run "{workflow_name}" --ref {ref}'
        code, out, err = cls._run_cmd(cmd, cwd)
        if code == 0:
            return f"Workflow '{workflow_name}' triggered successfully on ref '{ref}'."
        return f"Failed to trigger workflow: {err}"

    @classmethod
    def get_latest_run_status(cls, workflow_name: str, cwd: Optional[str] = None) -> Dict[str, Any]:
        """Gets the status of the latest run for a workflow."""
        cmd = f'gh run list --workflow="{workflow_name}" --limit 1 --json status,conclusion,url,databaseId'
        code, out, err = cls._run_cmd(cmd, cwd)
        
        if code != 0:
            return {"error": f"Failed to fetch run status: {err}"}
            
        import json
        try:
            data = json.loads(out)
            if not data:
                return {"error": "No runs found."}
            return data[0]
        except json.JSONDecodeError:
            return {"error": f"Failed to parse gh CLI output: {out}"}

    @classmethod
    def get_run_logs(cls, run_id: str, cwd: Optional[str] = None) -> str:
        """Fetches the logs of a specific failing run to feed back to Claude Flow for diagnosis."""
        cmd = f'gh run view {run_id} --log'
        code, out, err = cls._run_cmd(cmd, cwd)
        if code == 0:
            # Logs can be huge, return the last 100 lines for diagnosis
            lines = out.splitlines()
            if len(lines) > 100:
                out = "\n".join(lines[-100:])
            return f"Run Logs (last 100 lines):\n{out}"
        return f"Failed to fetch logs for run {run_id}: {err}"
