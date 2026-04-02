"""
CLI Execution Tools for Claude Flow.
"""

import subprocess

class CLITools:
    
    @staticmethod
    def run_command(command: str, cwd: str = ".") -> str:
        """Run a shell command and return stdout + stderr."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            out = result.stdout.strip()
            err = result.stderr.strip()
            
            output = []
            if out:
                output.append(f"STDOUT:\n{out}")
            if err:
                output.append(f"STDERR:\n{err}")
                
            return "\n\n".join(output) if output else f"Command completed with exit code {result.returncode} (No output)"
        except Exception as e:
            return f"Execution error: {e}"
