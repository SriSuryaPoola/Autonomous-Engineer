"""
Test Execution Tools (Self-Healing QA Engine driver).
"""

from .cli_tools import CLITools

class TestTools:
    
    @staticmethod
    def run_pytest(test_path: str = "tests/", cwd: str = ".") -> dict:
        """
        Run pytest and return a structured dictionary containing success status and logs.
        """
        import subprocess
        try:
            result = subprocess.run(
                f"python -m pytest {test_path} -v --tb=short",
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            
            passed = result.returncode == 0
            
            return {
                "success": passed,
                "exit_code": result.returncode,
                "stdout": result.stdout[:5000],  # Truncate to save tokens
                "stderr": result.stderr[:5000],
                "message": "Tests passed" if passed else "Tests failed"
            }
        except Exception as e:
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "message": "Execution framework error"
            }
