import logging

from packages.core.skills.base import BaseSkill, SkillContext, SkillResult

logger = logging.getLogger(__name__)

class HomeworkSkill(BaseSkill):
    """
    Skill to help children with homework (grade-appropriate concepts, math solvers, and quizzes).
    Uses the LLM port to generate answers and ensures output is clean and child-safe.
    """

    @property
    def name(self) -> str:
        return "homework"

    @property
    def required_permissions(self) -> list[str]:
        return ["general_info"]

    async def execute(self, ctx: SkillContext) -> SkillResult:
        llm = ctx.ports.get("llm")
        if llm is None:
            return SkillResult(
                spoken_response="Sorry, I need an active connection to my brain to solve homework problems.",
                success=False
            )

        intent_id = ctx.slots.get("intent_id", "homework.explain")

        if intent_id == "homework.explain":
            concept = ctx.slots.get("concept", "")
            grade = ctx.slots.get("grade", "5")
            if not concept:
                return SkillResult(spoken_response="What concept would you like me to explain?", success=False)

            prompt = f"Explain the concept of '{concept}' to a child in grade {grade}. Keep it simple, engaging, and under 100 words."
            system = "You are a friendly, child-safe school teacher tutor assistant."
            try:
                explanation = await llm.generate(prompt, system=system, max_tokens=150)
                return SkillResult(spoken_response=explanation, success=True)
            except Exception as e:
                logger.error(f"Homework explain failed: {e}")
                return SkillResult(spoken_response="Failed to generate explanation.", success=False)

        if intent_id == "homework.solve":
            problem = ctx.slots.get("problem", "")
            if not problem:
                return SkillResult(spoken_response="Which math problem would you like me to solve?", success=False)

            prompt = f"Solve this math problem: '{problem}'. Show the step-by-step working clearly and simply."
            system = "You are an encouraging math tutor. Provide a clean, step-by-step breakdown."
            try:
                solution = await llm.generate(prompt, system=system, max_tokens=200)
                return SkillResult(spoken_response=solution, success=True)
            except Exception as e:
                logger.error(f"Homework solve failed: {e}")
                return SkillResult(spoken_response="Failed to solve the math problem.", success=False)

        if intent_id == "homework.quiz":
            topic = ctx.slots.get("topic", "")
            if not topic:
                return SkillResult(spoken_response="Which topic would you like to be quizzed on?", success=False)

            prompt = f"Generate one multiple choice quiz question about '{topic}' for a school student. Include the question, options A, B, C, D, and state the correct answer at the very end."
            system = "You are a quiz master. Create a fun and educational school-level question."
            try:
                quiz_q = await llm.generate(prompt, system=system, max_tokens=200)
                return SkillResult(spoken_response=quiz_q, success=True)
            except Exception as e:
                logger.error(f"Homework quiz failed: {e}")
                return SkillResult(spoken_response="Failed to generate a quiz question.", success=False)

        return SkillResult(spoken_response="I didn't recognize that homework request.", success=False)
