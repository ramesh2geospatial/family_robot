import logging

from packages.core.skills.base import BaseSkill, SkillContext, SkillResult

logger = logging.getLogger(__name__)

# Simple unit conversions
_CONVERSIONS = {
    ("cup", "ml"): lambda x: x * 240,
    ("cup", "ounces"): lambda x: x * 8,
    ("kg", "g"): lambda x: x * 1000,
    ("tsp", "ml"): lambda x: x * 5,
    ("tbsp", "ml"): lambda x: x * 15,
}

# In-memory transient state for active recipe steps (since we don't persist active step to SQLite)
_ACTIVE_RECIPES: dict[str, list[str]] = {
    "paneer butter masala": [
        "Step 1: Saute onions, ginger, garlic, and tomatoes in butter until soft.",
        "Step 2: Blend the mixture into a smooth paste and return to the pan.",
        "Step 3: Add spices, cream, and paneer cubes. Simmer for 5 minutes.",
        "Step 4: Garnish with kasuri methi and serve hot!"
    ],
    "dal tadka": [
        "Step 1: Pressure cook dal with turmeric, salt, and water.",
        "Step 2: Heat ghee and temper cumin seeds, garlic, red chilies, and onions.",
        "Step 3: Pour the tempering over the cooked dal and stir.",
        "Step 4: Garnish with fresh coriander leaves and serve!"
    ]
}

# Current step pointer
_ACTIVE_STEP_INDEX = 0
_CURRENT_RECIPE = ""

class CookingSkill(BaseSkill):
    """
    Skill to help with recipes, conversion, and step-by-step reading.
    """

    @property
    def name(self) -> str:
        return "cooking"

    @property
    def required_permissions(self) -> list[str]:
        return ["general_info"]

    async def execute(self, ctx: SkillContext) -> SkillResult:
        global _ACTIVE_STEP_INDEX, _CURRENT_RECIPE

        intent_id = ctx.slots.get("intent_id", "cooking.recipe")

        if intent_id == "cooking.convert":
            amt_str = ctx.slots.get("amount")
            unit = ctx.slots.get("unit", "").lower().strip()
            target = ctx.slots.get("target_unit", "").lower().strip()

            try:
                amt = float(amt_str)
            except (ValueError, TypeError):
                return SkillResult(spoken_response="Please specify a valid amount to convert.", success=False)

            conv_key = (unit, target)
            if conv_key in _CONVERSIONS:
                res = _CONVERSIONS[conv_key](amt)
                return SkillResult(spoken_response=f"{amt} {unit} is equal to {res:.1f} {target}.", success=True)

            return SkillResult(
                spoken_response=f"Sorry, I don't know how to convert {unit} to {target}.",
                success=False
            )

        if intent_id == "cooking.next":
            if not _CURRENT_RECIPE or _CURRENT_RECIPE not in _ACTIVE_RECIPES:
                return SkillResult(spoken_response="No recipe has been started yet.", success=False)

            steps = _ACTIVE_RECIPES[_CURRENT_RECIPE]
            if _ACTIVE_STEP_INDEX >= len(steps):
                return SkillResult(spoken_response="The recipe is complete. Enjoy your meal!", success=True)

            step = steps[_ACTIVE_STEP_INDEX]
            _ACTIVE_STEP_INDEX += 1
            return SkillResult(spoken_response=step, success=True)

        # Start recipe
        recipe_name = ctx.slots.get("recipe", "").lower().strip()
        if not recipe_name:
            return SkillResult(spoken_response="Which recipe would you like to cook?", success=False)

        # Look up recipe
        if recipe_name in _ACTIVE_RECIPES:
            _CURRENT_RECIPE = recipe_name
            _ACTIVE_STEP_INDEX = 1
            first_step = _ACTIVE_RECIPES[recipe_name][0]
            return SkillResult(
                spoken_response=f"Let's make {_CURRENT_RECIPE}. Here is the first step: {first_step}",
                success=True
            )

        # Fallback to LLM to generate a recipe if llm is present
        llm = ctx.ports.get("llm")
        if llm:
            try:
                system = "You are a cooking chef. Give a short 3-step recipe for the requested dish. Keep it concise."
                recipe_text = await llm.generate(recipe_name, system=system, max_tokens=150)
                return SkillResult(spoken_response=recipe_text, success=True)
            except Exception as e:
                logger.warning(f"Cooking LLM fallback failed: {e}")

        return SkillResult(
            spoken_response=f"Sorry, I don't have a recipe for {recipe_name} and my online search is unavailable.",
            success=False
        )
