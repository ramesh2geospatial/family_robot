"""
Journey Audit skill - provides voice-first diagnostics and transparency.
Allows family members to verify what was heard, why an action was denied,
and what commands were recently executed.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from packages.core.skills.base import BaseSkill, SkillContext, SkillResult

logger = logging.getLogger(__name__)

class JourneyAuditSkill(BaseSkill):
    """Voice-first diagnostics for the AI user journey."""

    @property
    def name(self) -> str:
        return "journey_audit"

    @property
    def required_permissions(self) -> list[str]:
        return ["general_info"]

    async def execute(self, ctx: SkillContext) -> SkillResult:
        logger.info("[JourneyAuditSkill] Executing voice audit diagnostics.")

        raw_text = (ctx.raw_text or "").lower()
        lang = ctx.language or "en"

        # Determine sub-intent from query text
        is_hear_query = any(k in raw_text for k in ["hear", "सुना", "ऐकले"])
        is_deny_query = any(k in raw_text for k in ["deny", "denied", "अस्वीकार", "नाकारली"])
        is_command_query = any(k in raw_text for k in ["command", "action", "कमांड", "क्रिया"])

        if is_hear_query:
            return await self._handle_hear_query(ctx, lang)
        elif is_deny_query:
            return await self._handle_deny_query(ctx, lang)
        elif is_command_query:
            return await self._handle_command_query(ctx, lang)
        else:
            # Fallback default general response
            if lang == "hi":
                response = "मैं हाल की बातचीत और कमांड की जांच कर सकती हूँ। आप पूछ सकते हैं: मैंने क्या सुना, या मुझे क्यों मना किया गया।"
            elif lang == "mr":
                response = "मी अलीकडील संभाषणे आणि कमांड तपासू शकते. आपण विचारू शकता: मी काय ऐकले, किंवा मला का नाकारले गेले."
            else:
                response = "I can inspect recent conversations and commands. You can ask: 'what did you hear', 'why was I denied', or 'show my recent commands'."
            return SkillResult(spoken_response=response, success=True)

    async def _handle_hear_query(self, ctx: SkillContext, lang: str) -> SkillResult:
        conv_logger = ctx.ports.get("conversation_logger")
        if not conv_logger:
            return SkillResult(
                spoken_response="I'm sorry, conversation logging is not available right now." if lang == "en" else "माफ कीजिये, बातचीत का इतिहास उपलब्ध नहीं है।",
                success=False
            )

        # Get recent interactions
        recent = conv_logger.get_recent(50)
        if not recent:
            if lang == "hi":
                return SkillResult(spoken_response="मुझे कोई हालिया रिकॉर्ड नहीं मिला।", success=True)
            elif lang == "mr":
                return SkillResult(spoken_response="मला कोणताही अलीकडील रेकॉर्ड आढळला नाही.", success=True)
            return SkillResult(spoken_response="I couldn't find any recent conversations in my log.", success=True)

        # The current turn is the last entry in the log or currently executing.
        # So we search backwards starting from the second-to-last entry to find the previous user query.
        previous_query: Optional[str] = None
        user_id = ctx.user_id or "unknown"

        # Search backwards
        for entry in reversed(recent):
            input_text = entry.get("input_text", "")
            # Skip the current audit query itself
            if any(k in input_text.lower() for k in ["hear", "सुना", "ऐकले", "journey_audit"]):
                continue
            if entry.get("user_id") == user_id or user_id == "unknown" or entry.get("user_id") == "unknown":
                if input_text and not input_text.startswith("<"):
                    previous_query = input_text
                    break

        if not previous_query:
            # Fallback to the absolute last query that is not this one
            for entry in reversed(recent):
                input_text = entry.get("input_text", "")
                if input_text and not any(k in input_text.lower() for k in ["hear", "सुना", "ऐकले"]):
                    previous_query = input_text
                    break

        if previous_query:
            if lang == "hi":
                response = f"पिछली बार मैंने सुना: {previous_query}"
            elif lang == "mr":
                response = f"गेल्या वेळी मी ऐकले: {previous_query}"
            else:
                response = f"Before this, I heard you say: {previous_query}"
        else:
            if lang == "hi":
                response = "मुझे कोई पिछली बातचीत नहीं मिली।"
            elif lang == "mr":
                response = "मला कोणतेही मागील संभाषण आढळले नाही."
            else:
                response = "I couldn't find any previous queries in my logs."

        return SkillResult(spoken_response=response, success=True)

    async def _handle_deny_query(self, ctx: SkillContext, lang: str) -> SkillResult:
        audit_log = ctx.ports.get("audit_log")
        if not audit_log:
            return SkillResult(
                spoken_response="I'm sorry, the audit log is not available right now." if lang == "en" else "माफ कीजिये, ऑडिट लॉग उपलब्ध नहीं है।",
                success=False
            )

        recent = audit_log.read_recent(50)
        user_id = ctx.user_id or "unknown"

        # Search for the last denied event for this user or any user
        last_denied: Optional[dict] = None
        for entry in reversed(recent):
            if entry.get("allowed") is False:
                # If checking specific user, match user_id
                if user_id == "unknown" or entry.get("user_id") == user_id or entry.get("user_id") == "unknown":
                    last_denied = entry
                    break

        if last_denied:
            details = last_denied.get("details") or {}
            intent_name = details.get("intent", "unknown")
            user_role = last_denied.get("user_role", "guest")

            # Try to make intent name readable
            friendly_intent = intent_name.replace("control_", "").replace("_", " ")

            if lang == "hi":
                response = f"आपका '{friendly_intent}' कमांड चलाने का अनुरोध अस्वीकार कर दिया गया था क्योंकि आपकी भूमिका '{user_role}' है।"
            elif lang == "mr":
                response = f"तुमचे '{friendly_intent}' कमांड चालवण्याची विनंती नाकारण्यात आली कारण तुमची भूमिका '{user_role}' आहे."
            else:
                response = f"Your request to run '{friendly_intent}' was denied because your role is '{user_role}', which does not have permission for that action."
        else:
            if lang == "hi":
                response = "मुझे आपकी हालिया गतिविधियों में कोई अस्वीकृत कमांड नहीं मिला।"
            elif lang == "mr":
                response = "मला आपल्या अलीकडील क्रियाकलापांमध्ये कोणतीही नाकारलेली कमांड आढळली नाही."
            else:
                response = "I couldn't find any recently denied requests in my audit logs."

        return SkillResult(spoken_response=response, success=True)

    async def _handle_command_query(self, ctx: SkillContext, lang: str) -> SkillResult:
        audit_log = ctx.ports.get("audit_log")
        if not audit_log:
            return SkillResult(
                spoken_response="I'm sorry, the audit log is not available right now." if lang == "en" else "माफ कीजिये, ऑडिट लॉग उपलब्ध नहीं है।",
                success=False
            )

        recent = audit_log.read_recent(50)
        user_id = ctx.user_id or "unknown"

        # Collect recent successful commands/actions
        actions: list[str] = []
        for entry in reversed(recent):
            event = entry.get("event") or ""
            allowed = entry.get("allowed")
            # Only count successful webapp commands or intent execution checks
            if allowed is True and event in ("webapp_device_command", "acl_check"):
                details = entry.get("details") or {}
                # Filter out system audits/general chat falling back
                intent = details.get("intent") or ""
                device_id = details.get("device_id") or ""
                action = details.get("action") or ""

                if event == "webapp_device_command" and device_id:
                    actions.append(f"{action} {device_id}")
                elif intent and intent not in ("general_chat", "assistant.chat", "journey_audit.check"):
                    friendly_intent = intent.replace("control_", "").replace("_", " ")
                    actions.append(friendly_intent)

                if len(actions) >= 3:
                    break

        if actions:
            action_list = ", ".join(actions)
            if lang == "hi":
                response = f"हाल ही में किए गए सफल कमांड हैं: {action_list}।"
            elif lang == "mr":
                response = f"अलीकडे यशस्वी झालेल्या कमांड्स आहेत: {action_list}."
            else:
                response = f"The recent successful actions recorded are: {action_list}."
        else:
            if lang == "hi":
                response = "मुझे कोई हालिया कमांड नहीं मिला।"
            elif lang == "mr":
                response = "मला कोणतीही अलीकडील कमांड आढळली नाही."
            else:
                response = "I couldn't find any recent successful actions in my audit logs."

        return SkillResult(spoken_response=response, success=True)
