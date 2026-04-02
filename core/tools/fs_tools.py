"""
File System Tools for Claude Flow Execution.
"""

import os
import shutil

class FileSystemTools:
    
    @staticmethod
    def read_file(filepath: str) -> str:
        """Read text from a file."""
        if not os.path.exists(filepath):
            return f"Error: File {filepath} does not exist."
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {e}"

    @staticmethod
    def write_file(filepath: str, content: str) -> str:
        """Write text to a file, creating directories if needed."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Success: Wrote to {filepath}"
        except Exception as e:
            return f"Error writing file: {e}"

    @staticmethod
    def list_dir(directory: str) -> str:
        """List contents of a directory."""
        if not os.path.exists(directory):
            return f"Error: Directory {directory} does not exist."
        try:
            return "\n".join(os.listdir(directory))
        except Exception as e:
            return f"Error listing directory: {e}"

    @staticmethod
    def delete_file(filepath: str) -> str:
        """Delete a file."""
        if not os.path.exists(filepath):
            return f"Error: File {filepath} does not exist."
        try:
            os.remove(filepath)
            return f"Success: Deleted {filepath}"
        except Exception as e:
            return f"Error deleting file: {e}"
