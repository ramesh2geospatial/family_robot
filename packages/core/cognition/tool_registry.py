"""
Tool registry for local LLM function calling.

Defines a set of tools that the LLM can invoke during general_chat,
allowing it to take actions (control devices, play music, set timers)
from free-form conversation without needing exact keyword matches.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Optional

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    """Schema for a callable tool."""

    name: str
    description: str
    parameters: dict  # JSON Schema dict
    handler: Callable[..., Coroutine[Any, Any, str]]
    requires_permission: Optional[str] = None


class ToolRegistry:
    """Registry of tools available to the LLM for function calling."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        """Register a tool definition."""
        self._tools[tool.name] = tool
        logger.debug("Registered tool: %s", tool.name)

    def get(self, name: str) -> Optional[ToolDefinition]:
        """Look up a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[ToolDefinition]:
        """Return all registered tools."""
        return list(self._tools.values())

    def get_tool_prompt_block(self) -> str:
        """Generate a prompt block describing all available tools for the LLM.

        This is injected into the system prompt so the LLM knows what
        tools it can call.
        """
        if not self._tools:
            return ""

        lines = [
            "\n\nYou have access to these tools. To use a tool, respond with "
            "ONLY a JSON object in this format:",
            '{"tool": "<tool_name>", "args": {<parameters>}}',
            "",
            "Available tools:",
        ]
        for tool in self._tools.values():
            params = ", ".join(
                f'{k}: {v.get("type", "string")}'
                for k, v in tool.parameters.get("properties", {}).items()
            )
            lines.append(f"- {tool.name}({params}): {tool.description}")

        lines.append(
            "\nIf no tool is needed, respond with normal text (no JSON)."
        )
        return "\n".join(lines)


def build_default_tools(ports: dict) -> ToolRegistry:
    """Create and populate a ToolRegistry with the standard FamilyRobot tools.

    Args:
        ports: Dict of available ports (home, memory, media_player, etc.)
    """
    registry = ToolRegistry()

    # ── control_device ──
    home = ports.get("home")
    if home:

        async def _control_device(device: str, action: str = "on", **kw: Any) -> str:
            on = action.lower() in ("on", "true", "1")
            ok = await home.set_switch(device, on)
            state = "on" if on else "off"
            if ok:
                return f"Done! Turned {state} the {device}."
            return f"Sorry, I couldn't control the {device}."

        registry.register(
            ToolDefinition(
                name="control_device",
                description="Turn a home device on or off",
                parameters={
                    "properties": {
                        "device": {"type": "string", "description": "Device name (light, fan, geyser, pump, etc.)"},
                        "action": {"type": "string", "description": "on or off"},
                    },
                    "required": ["device", "action"],
                },
                handler=_control_device,
                requires_permission="home_control",
            )
        )

    # ── play_song ──
    media = ports.get("media_player")
    if media:

        async def _play_song(song: str = "", **kw: Any) -> str:
            if not song:
                return "What would you like me to play?"
            try:
                await media.play(song)
                return f"Playing \"{song}\" now."
            except Exception as e:
                return f"Sorry, I couldn't play that: {e}"

        registry.register(
            ToolDefinition(
                name="play_song",
                description="Search for and play a song or music",
                parameters={
                    "properties": {
                        "song": {"type": "string", "description": "Song name or search query"},
                    },
                    "required": ["song"],
                },
                handler=_play_song,
                requires_permission="play_music",
            )
        )

    # ── store_memory ──
    memory = ports.get("memory")
    if memory:

        async def _store_memory(fact: str, **kw: Any) -> str:
            mem_id = await memory.store(fact)
            return f"I'll remember that. (saved as {mem_id[:8]})"

        registry.register(
            ToolDefinition(
                name="store_memory",
                description="Remember/save a fact for later recall",
                parameters={
                    "properties": {
                        "fact": {"type": "string", "description": "The fact to remember"},
                    },
                    "required": ["fact"],
                },
                handler=_store_memory,
                requires_permission="memory_write",
            )
        )

        async def _search_memory(query: str, **kw: Any) -> str:
            hits = await memory.search(query, k=3)
            if hits:
                facts = [h["text"] for h in hits[:3]]
                return "Here's what I remember: " + "; ".join(facts)
            return "I don't have anything saved about that."

        registry.register(
            ToolDefinition(
                name="search_memory",
                description="Search saved memories/facts",
                parameters={
                    "properties": {
                        "query": {"type": "string", "description": "What to search for"},
                    },
                    "required": ["query"],
                },
                handler=_search_memory,
            )
        )

    # ── get_time ──
    async def _get_time(**kw: Any) -> str:
        from datetime import datetime

        now = datetime.now()
        return f"It's {now.strftime('%I:%M %p')} on {now.strftime('%A, %B %d, %Y')}."

    registry.register(
        ToolDefinition(
            name="get_time",
            description="Get the current date and time",
            parameters={"properties": {}},
            handler=_get_time,
        )
    )

    return registry
