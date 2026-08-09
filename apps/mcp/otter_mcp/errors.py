"""Structured errors for MCP tool responses."""
from __future__ import annotations

from typing import Any


class OtterMcpError(Exception):
    def __init__(self, code: str, message: str, next_action: str = "") -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.next_action = next_action

    def to_dict(self) -> dict[str, Any]:
        payload = {"error": self.code, "message": self.message}
        if self.next_action:
            payload["next_action"] = self.next_action
        return payload


def as_tool_error(error: Exception) -> dict[str, Any]:
    if isinstance(error, OtterMcpError):
        return error.to_dict()
    return {
        "error": "internal_error",
        "message": str(error),
        "next_action": "Retry with a valid repository_id or OTTER_REPO_ROOT.",
    }
