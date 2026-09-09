# [AGC:FILE] tool=Cc author=fangkun date=2026-08-24
"""Agent1 工具集：文件操作和命令执行。"""
# [AGC:START] tool=Cc author=fangkun
from __future__ import annotations

import os
import subprocess
from typing import Annotated

from langchain_core.tools import tool


@tool
def read_file(
    path: Annotated[str, "File path relative to workspace"]
) -> str:
    """Read content from a file in the workspace.

    Args:
        path: File path relative to workspace directory.

    Returns:
        File content as string, or error message if file not found.
    """
    workspace = os.environ.get("WORKSPACE_DIR", "./workspace")
    full_path = os.path.join(workspace, path)

    if not os.path.exists(full_path):
        return f"Error: File not found: {path}"

    try:
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"


@tool
def write_file(
    path: Annotated[str, "File path relative to workspace"],
    content: Annotated[str, "Content to write to the file"]
) -> str:
    """Write content to a file in the workspace. Creates parent directories if needed.

    Args:
        path: File path relative to workspace directory.
        content: Content to write.

    Returns:
        Success message or error message.
    """
    workspace = os.environ.get("WORKSPACE_DIR", "./workspace")
    full_path = os.path.join(workspace, path)

    try:
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Error writing file: {e}"


@tool
def edit_file(
    path: Annotated[str, "File path relative to workspace"],
    old_text: Annotated[str, "Text to replace"],
    new_text: Annotated[str, "Replacement text"]
) -> str:
    """Replace specific text in a file.

    Args:
        path: File path relative to workspace directory.
        old_text: Exact text to find and replace.
        new_text: Text to replace with.

    Returns:
        Success message or error message.
    """
    workspace = os.environ.get("WORKSPACE_DIR", "./workspace")
    full_path = os.path.join(workspace, path)

    if not os.path.exists(full_path):
        return f"Error: File not found: {path}"

    try:
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()

        if old_text not in content:
            return f"Error: Text not found in file {path}"

        new_content = content.replace(old_text, new_text, 1)

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        return f"Successfully edited {path}"
    except Exception as e:
        return f"Error editing file: {e}"


@tool
def run_command(
    command: Annotated[str, "Shell command to execute"]
) -> str:
    """Execute a shell command in the workspace directory.

    Used for running linters (ruff, mypy), tests (pytest), etc.

    Args:
        command: Shell command to execute.

    Returns:
        Command output (stdout + stderr), or error message.
    """
    workspace = os.environ.get("WORKSPACE_DIR", "./workspace")

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=60
        )

        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += "\n" + result.stderr

        return output if output else f"Command completed with exit code {result.returncode}"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out (60s limit)"
    except Exception as e:
        return f"Error executing command: {e}"
# [AGC:END]
