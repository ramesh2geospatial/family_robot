import logging
from packages.core.skills.base import BaseSkill, SkillContext, SkillResult

logger = logging.getLogger(__name__)

class EnrollSkill(BaseSkill):
    """
    Skill to direct users to the Companion webapp for face & voice enrollment.
    """

    @property
    def name(self) -> str:
        return "enroll"

    @property
    def required_permissions(self) -> list[str]:
        return ["general_info"]

    async def execute(self, ctx: SkillContext) -> SkillResult:
        logger.info("[EnrollSkill] Directing user to PWA for enrollment.")
        
        response = (
            "You can enroll new family members and capture their face and voice "
            "using the Family tab on the Companion web app at http://localhost:8080."
        )

        return SkillResult(
            spoken_response=response,
            success=True
        )
