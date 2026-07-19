"""
Tool executor for local LLM function calling.

Parses tool-call JSON from LLM output, validates parameters,
enforces ACL, executes the tool handler, and optionally feeds
the result back to the LLM for a natural language summary.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from packages.core.cognition.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)

# Pattern to detect a tool call in LLM output
_TOOL_CALL_MARKERS = ('{"tool":', "{'tool':")


class ToolExecutor:
    """Execute tool calls from LLM output.

    Flow:
      1. Check if LLM response contains a tool-call JSON.
      2. Parse and validate the tool name and arguments.
      3. Check ACL permissions (if tool requires them).
      4. Execute the tool handler.
      5. Optionally re-prompt the LLM with the tool result for a
         natural language summary.
    """

    def __init__(
        self,
        registry: ToolRegistry,
        *,
        acl: Any = None,
        llm: Any = None,
    ) -> None:
        self._registry = registry
        self._acl = acl
        self._llm = llm

    def is_tool_call(self, llm_response: str) -> bool:
        """Return True if the LLM response looks like a tool call."""
        stripped = llm_response.strip()
        return any(stripped.startswith(m) for m in _TOOL_CALL_MARKERS)

    async def execute(
        self,
        llm_response: str,
        *,
        user_role: str = "unknown",
        user_id: str = "unknown",
        language: str = "en",
    ) -> str:
        """Parse and execute a tool call from the LLM's response.

        Returns:
            A human-readable result string (either raw tool output
            or an LLM-summarized version).
        """
        # 1. Parse the JSON
        try:
            cleaned = llm_response.strip()
            # Handle markdown fences
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            call = json.loads(cleaned)
            tool_name = call.get("tool", "").strip()
            args = call.get("args", {})

            if not isinstance(args, dict):
                args = {}

        except (json.JSONDecodeError, AttributeError, TypeError) as exc:
            logger.warning("Failed to parse tool call JSON: %s", exc)
            return "I tried to do something but got confused. Could you rephrase?"

        # 2. Look up the tool
        tool_def = self._registry.get(tool_name)
        if tool_def is None:
            logger.warning("LLM called unknown tool: %s", tool_name)
            return f"I don't have a tool called '{tool_name}'."

        # 3. ACL check
        if tool_def.requires_permission and self._acl:
            try:
                acl_result = self._acl.check_permission(user_role, tool_def.requires_permission)
                if not acl_result:
                    logger.info(
                        "ACL denied tool %s for user %s (role=%s)",
                        tool_name,
                        user_id,
                        user_role,
                    )
                    return "Sorry, you don't have permission to do that."
            except Exception:
                pass  # If ACL check fails, allow (fail-open for tools)

        # 4. Execute the tool
        try:
            logger.info(
                "Executing tool: %s(%s) for user %s",
                tool_name,
                args,
                user_id,
            )
            result = await tool_def.handler(**args)
            logger.info("Tool %s result: %s", tool_name, result[:100] if result else "")
            return result

        except Exception as exc:
            logger.error("Tool execution failed: %s(%s) → %s", tool_name, args, exc)
            return f"I tried to {tool_def.description.lower()} but encountered an error."
