"""
GitHub Tools — Real-world integration with GitHub for Phase 3.

Provides the ability to:
- Create Repositories & Branches
- Commit Code
- Open Pull Requests
- Comment on PRs
- Read CI/CD statuses from GitHub Actions
"""

import os
import subprocess
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class GitHubTools:
    """
    Interfaces with Git CLI and GitHub API (via `gh` CLI if installed or standard fallback).
    Requires a working shell and Git environment.
    """

    @staticmethod
    def _run_cmd(cmd: str, cwd: Optional[str] = None) -> tuple[int, str, str]:
        """Helper to run shell commands safely."""
        cwd = cwd or os.getcwd()
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            return -1, "", f"Command timed out: {cmd}"
        except Exception as e:
            return -1, "", f"Execution failed: {e}"

    @classmethod
    def create_branch(cls, branch_name: str, cwd: Optional[str] = None) -> str:
        code, out, err = cls._run_cmd(f"git checkout -b {branch_name}", cwd)
        if code == 0:
            return f"Branch {branch_name} created and checked out."
        return f"Failed to create branch: {err}"

    @classmethod
    def commit_all(cls, message: str, cwd: Optional[str] = None) -> str:
        """Stages all changes and commits them."""
        cls._run_cmd("git add .", cwd)
        # Handle double quotes in message
        safe_msg = message.replace('"', '\\"')
        code, out, err = cls._run_cmd(f'git commit -m "{safe_msg}"', cwd)
        if code == 0:
            return f"Successfully committed: {message}"
        elif "nothing to commit" in out or "nothing to commit" in err:
            return "No changes to commit."
        return f"Commit failed: {err}"

    @classmethod
    def push_branch(cls, branch_name: str, cwd: Optional[str] = None) -> str:
        code, out, err = cls._run_cmd(f"git push -u origin {branch_name}", cwd)
        if code == 0:
            return f"Pushed branch {branch_name} to origin."
        return f"Failed to push: {err}"

    @classmethod
    def create_pull_request(cls, title: str, body: str, cwd: Optional[str] = None) -> str:
        """
        Uses GitHub CLI (`gh`) to create a PR.
        If `gh` is not installed, it will return an error suggesting it to the agent.
        """
        code, out, err = cls._run_cmd("gh --version")
        if code != 0:
            return "GitHub CLI (gh) is not installed or authenticated. Cannot create PR automatically."

        safe_title = title.replace('"', '\\"')
        safe_body = body.replace('"', '\\"')
        cmd = f'gh pr create --title "{safe_title}" --body "{safe_body}"'
        
        code, out, err = cls._run_cmd(cmd, cwd)
        if code == 0:
            return f"Pull Request Created successfully: {out}"
        return f"Failed to create PR: {err}"

    @classmethod
    def comment_on_pr(cls, pr_number: str, comment: str, cwd: Optional[str] = None) -> str:
        safe_comment = comment.replace('"', '\\"')
        cmd = f'gh pr comment {pr_number} --body "{safe_comment}"'
        code, out, err = cls._run_cmd(cmd, cwd)
        if code == 0:
            return f"Commented on PR #{pr_number} successfully."
        return f"Failed to comment on PR: {err}"

    @classmethod
    def check_pr_status(cls, pr_number: str, cwd: Optional[str] = None) -> str:
        """Checks the CI status of a specific PR."""
        cmd = f"gh pr checks {pr_number}"
        code, out, err = cls._run_cmd(cmd, cwd)
        if code == 0:
            return f"PR Checks Status:\n{out}"
        return f"Failed to check PR status: {err}"
