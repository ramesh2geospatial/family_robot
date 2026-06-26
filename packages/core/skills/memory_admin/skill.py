"""
Memory admin skill – remember, recall, forget via MemoryPort.
"""

from __future__ import annotations

import logging

from packages.core.skills.base import BaseSkill, SkillContext, SkillResult

logger = logging.getLogger(__name__)


class MemoryAdminSkill(BaseSkill):
    """CRUD operations on the family memory store."""

    @property
    def name(self) -> str:
        return "memory_admin"

    @property
    def required_permissions(self) -> list[str]:
        return ["memory_write"]

    async def execute(self, ctx: SkillContext) -> SkillResult:
        memory = ctx.ports.get("memory")
        if memory is None:
            return SkillResult(spoken_response="Memory store is not available.", success=False)

        action = ctx.slots.get("action", "store")

        if action == "recall":
            return await self._recall(ctx, memory)
        if action == "forget":
            return await self._forget(ctx, memory)
        return await self._store(ctx, memory)

    async def _store(self, ctx: SkillContext, memory: object) -> SkillResult:
        fact = ctx.slots.get("fact", ctx.raw_text)
        meta = {"user_id": ctx.user_id, "source": "voice"}
        mem_id = await memory.store(fact, meta=meta)  # type: ignore[union-attr]
        logger.info("Stored memory %s for user %s", mem_id[:8], ctx.user_id)
        return SkillResult(
            spoken_response=f"Got it! I'll remember that.",
            memory_item=fact,
            memory_meta=meta,
        )

    async def _recall(self, ctx: SkillContext, memory: object) -> SkillResult:
        query = ctx.slots.get("query", ctx.raw_text)
        hits = await memory.search(query, k=3)  # type: ignore[union-attr]
        if not hits:
            return SkillResult(spoken_response="I don't have anything saved about that.")
        top = hits[0]
        text = top["text"]
        score = top.get("score", 0)
        if score < 0.3:
            return SkillResult(spoken_response="I'm not sure, but I found this: " + text)
        return SkillResult(spoken_response=text)

    async def _forget(self, ctx: SkillContext, memory: object) -> SkillResult:
        # For MVP, delete the most recent memory matching the query
        query = ctx.slots.get("query", ctx.raw_text)
        hits = await memory.search(query, k=1)  # type: ignore[union-attr]
        if not hits:
            return SkillResult(spoken_response="I couldn't find anything to forget.")
        mem_id = hits[0]["id"]
        deleted = await memory.delete(mem_id)  # type: ignore[union-attr]
        if deleted:
            return SkillResult(spoken_response="Done, I've forgotten that.")
        return SkillResult(spoken_response="I couldn't remove that memory.", success=False)
