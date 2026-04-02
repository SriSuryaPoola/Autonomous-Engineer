"""
Git Tools for Claude Flow.
"""

from .cli_tools import CLITools

class GitTools:
    
    @staticmethod
    def init(cwd: str = ".") -> str:
        return CLITools.run_command("git init", cwd=cwd)

    @staticmethod
    def status(cwd: str = ".") -> str:
        return CLITools.run_command("git status -s", cwd=cwd)

    @staticmethod
    def add_all(cwd: str = ".") -> str:
        return CLITools.run_command("git add .", cwd=cwd)
        
    @staticmethod
    def commit(message: str, cwd: str = ".") -> str:
        safe_message = message.replace('"', '\\"')
        return CLITools.run_command(f'git commit -m "{safe_message}"', cwd=cwd)
        
    @staticmethod
    def diff(cwd: str = ".") -> str:
        return CLITools.run_command("git diff", cwd=cwd)

    @staticmethod
    def commit_and_push(files: list, message: str, cwd: str = ".") -> str:
        """
        Stage specific files, commit with message, and push to origin.
        Returns a result string indicating success or failure.
        """
        # Stage only specified files
        for f in files:
            stage_result = CLITools.run_command(f'git add "{f}"', cwd=cwd)
        
        # Commit
        safe_msg = message.replace('"', '\\"')
        commit_result = CLITools.run_command(f'git commit -m "{safe_msg}"', cwd=cwd)
        
        if "nothing to commit" in commit_result.lower():
            return "success: nothing to commit"
        if "error" in commit_result.lower() or "failed" in commit_result.lower():
            return f"commit failed: {commit_result}"
        
        # Push
        push_result = CLITools.run_command("git push origin HEAD", cwd=cwd)
        if "error" in push_result.lower() or "failed" in push_result.lower():
            return f"push failed: {push_result}"
        
        return f"success: pushed {len(files)} file(s). {push_result[:100]}"
