import logging

from packages.core.governance.identity import UNKNOWN_USER
from packages.core.skills.base import BaseSkill, SkillContext, SkillResult

logger = logging.getLogger(__name__)


class SecuritySkill(BaseSkill):
    """
    Skill to perform nighttime security camera checks and trigger alerts.
    """

    @property
    def name(self) -> str:
        return "security"

    @property
    def required_permissions(self) -> list[str]:
        return ["general_info"]

    async def execute(self, ctx: SkillContext) -> SkillResult:
        camera = ctx.ports.get("camera")
        notify = ctx.ports.get("notify")
        identity_store = ctx.ports.get("identity_store")

        if not camera or not notify or not identity_store:
            return SkillResult(
                spoken_response="Security components are currently unavailable.",
                success=False,
            )

        # 1. Capture image frame
        await camera.open()
        try:
            frame = await camera.capture()
        finally:
            await camera.close()

        if frame is None:
            return SkillResult(
                spoken_response="Failed to obtain image from security camera.",
                success=False,
            )

        # 2. Match face (Simulate detecting an unknown face for night alerts)
        # On production, InsightFace embeddings are extracted from `frame` and compared.
        # For Desktop MVP/test we default to triggering alert if a face is detected.
        # We simulate detecting UNKNOWN_USER to test alert pushes.
        detected_user = UNKNOWN_USER

        if detected_user == UNKNOWN_USER:
            # Trigger high-priority notify push to parent
            await notify.push(
                user_id="parent_default",
                title="SECURITY ALERT",
                body="Unknown face detected at night!",
            )
            return SkillResult(
                spoken_response="Alert! I detected an unknown face outside and pushed a high-priority notification to Ramesh.",
                success=True,
                memory_item="Security alert: unknown face detected.",
            )
        else:
            return SkillResult(
                spoken_response=f"Security check clear. I saw {detected_user.name}.",
                success=True,
            )
