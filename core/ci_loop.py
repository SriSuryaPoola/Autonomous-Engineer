"""
CI Feedback Loop — Wraps ci_tools.py into a polling async loop.

After local QA converges, the orchestrator calls this module to:
  1. Commit the generated test files
  2. Trigger the GitHub Actions workflow
  3. Poll until completion
  4. On failure: feed logs back to QAEngineer for one more patch cycle

This connects the final 'last mile' between local test convergence
and production CI/CD pipeline validation as described in ArXiv 2601.02454.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

from core.tools.ci_tools import CITools
from core.tools.git_tools import GitTools

logger = logging.getLogger(__name__)


@dataclass
class CIResult:
    success: bool
    run_url: str = ""
    logs: str = ""
    status: str = ""       # "success" | "failure" | "timeout" | "skipped"
    conclusion: str = ""


class CIFeedbackLoop:
    """
    Async CI/CD feedback loop. Triggers a workflow and polls for result.
    
    Usage:
        loop = CIFeedbackLoop()
        result = await loop.trigger_and_wait("run-tests.yml", project_path=".")
        if not result.success:
            # Feed result.logs back to QAEngineer for correction
    """

    POLL_INTERVAL_SECS = 15
    MAX_POLL_ATTEMPTS = 20  # 5 minutes max

    def __init__(self, project_path: str = "."):
        self.project_path = project_path

    async def trigger_and_wait(
        self,
        workflow_name: str,
        ref: str = "main",
        timeout: int = 300
    ) -> CIResult:
        """
        Trigger a GitHub Actions workflow and poll until completion.
        
        Args:
            workflow_name: Name of the workflow file (e.g., "run-tests.yml")
            ref: Git ref to run on (branch/tag)
            timeout: Maximum seconds to wait
            
        Returns:
            CIResult with success, logs, and run URL
        """
        logger.info(f"[CI] Triggering workflow: {workflow_name} on {ref}")

        # Step 1: Trigger
        trigger_msg = CITools.trigger_workflow(workflow_name, ref, cwd=self.project_path)
        logger.info(f"[CI] Trigger result: {trigger_msg}")

        if "Failed" in trigger_msg:
            return CIResult(
                success=False,
                status="skipped",
                logs=trigger_msg,
                conclusion="Workflow trigger failed — check gh CLI authentication"
            )

        # Step 2: Poll for completion
        polls = min(self.MAX_POLL_ATTEMPTS, timeout // self.POLL_INTERVAL_SECS)
        for attempt in range(int(polls)):
            await asyncio.sleep(self.POLL_INTERVAL_SECS)
            status_data = CITools.get_latest_run_status(workflow_name, cwd=self.project_path)

            if "error" in status_data:
                logger.warning(f"[CI] Poll error: {status_data['error']}")
                continue

            run_status = status_data.get("status", "")
            conclusion = status_data.get("conclusion", "")
            run_url = status_data.get("url", "")
            run_id = str(status_data.get("databaseId", ""))

            logger.info(f"[CI] Poll {attempt+1}: status={run_status} conclusion={conclusion}")

            if run_status == "completed":
                success = conclusion == "success"
                logs = ""

                if not success and run_id:
                    logs = CITools.get_run_logs(run_id, cwd=self.project_path)

                return CIResult(
                    success=success,
                    run_url=run_url,
                    logs=logs,
                    status=run_status,
                    conclusion=conclusion
                )

        # Step 3: Timeout
        logger.warning(f"[CI] Workflow did not complete within {timeout}s")
        return CIResult(
            success=False,
            status="timeout",
            logs=f"Workflow '{workflow_name}' did not complete within {timeout} seconds.",
            conclusion="timeout"
        )

    async def commit_tests_and_push(
        self,
        test_files: list,
        commit_message: str = "chore: add auto-generated tests [ai-engineer]"
    ) -> bool:
        """
        Commit generated test files and push to remote.
        Returns True if push was successful.
        """
        logger.info(f"[CI] Committing {len(test_files)} test file(s)...")
        result = GitTools.commit_and_push(
            files=test_files,
            message=commit_message,
            cwd=self.project_path
        )
        success = "success" in result.lower() or "pushed" in result.lower()
        logger.info(f"[CI] Git push result: {result}")
        return success
