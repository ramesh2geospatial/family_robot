import logging

from packages.core.skills.base import BaseSkill, SkillContext, SkillResult

logger = logging.getLogger(__name__)


class CallsSkill(BaseSkill):
    """
    Skill to make phone calls or send messages to whitelisted family members.
    """

    @property
    def name(self) -> str:
        return "calls"

    @property
    def required_permissions(self) -> list[str]:
        return ["make_calls"]

    async def execute(self, ctx: SkillContext) -> SkillResult:
        contact_name = ctx.slots.get("contact", "")
        if not contact_name:
            return SkillResult(
                spoken_response="Who would you like to call?", success=False
            )

        # Retrieve identity store and look up contact
        identity_store = ctx.ports.get("identity_store")
        target_member = None
        if identity_store:
            for member in identity_store.list_members():
                if member.name.lower() == contact_name.lower():
                    target_member = member
                    break

        if not target_member:
            logger.warning(
                f"Call request blocked: '{contact_name}' is not in the family whitelist."
            )
            return SkillResult(
                spoken_response=f"Sorry, for safety reasons I can only call enrolled family members. {contact_name} is not enrolled.",
                success=False,
            )

        telephony = ctx.ports.get("telephony")
        if not telephony:
            return SkillResult(
                spoken_response="Telephony service is not available.", success=False
            )

        phone_number = getattr(target_member, "phone_number", "+919876543210")
        ok = await telephony.make_call(phone_number)
        if ok:
            return SkillResult(
                spoken_response=f"Sure, calling {target_member.name} now.",
                success=True,
                memory_item=f"Initiated voice call to {target_member.name}.",
            )
        else:
            return SkillResult(
                spoken_response=f"Sorry, I failed to initiate the call to {target_member.name}.",
                success=False,
            )
