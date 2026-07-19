"""
Structured intent classification prompts for the local LLM.

Used by IntentRouter when keyword rules don't match. The LLM returns
a JSON object with both intent name and extracted entities.
"""

INTENT_CLASSIFICATION_SYSTEM = """\
You are an intent classifier for a family home assistant robot.
Given a user command, classify it into exactly ONE intent and extract any entities.

Return ONLY valid JSON in this exact format (no markdown, no explanation):
{"intent": "<intent_name>", "entities": {<extracted_key_value_pairs>}}

Valid intents and their entity schemas:

| Intent | When to use | Entities |
|--------|-------------|----------|
| home_control | Control lights, appliances generically | {"devices": ["light","fan",...], "action": "on"|"off"} |
| control_ac | AC/air conditioner commands | {"action": "on"|"off", "temp": 24, "mode": "cool"|"heat"|"dry"|"fan"} |
| control_tv | TV/television commands | {"action": "on"|"off"|"volume_up"|"volume_down", "source": "hdmi1"} |
| control_geyser | Water heater/geyser commands | {"action": "on"|"off"} |
| control_pump | Water pump commands | {"action": "on"|"off"} |
| control_washer | Washing machine commands | {"action": "on"|"off"} |
| control_fan | Fan speed/on/off | {"action": "on"|"off", "speed": 1-5} |
| play_music | Play/pause/stop/next music | {"action": "play"|"pause"|"stop"|"next", "song": "song name"} |
| cooking | Recipes, cooking help, unit conversion | {"intent_id": "cooking.recipe"|"cooking.convert"|"cooking.next", "recipe": "dish name"} |
| homework | Study help, math, quizzes | {"intent_id": "homework.explain"|"homework.solve"|"homework.quiz", "concept": "topic", "grade": "5"} |
| dance | Dance requests | {"song": "song name"} |
| enroll | Register new user/face/voice | {} |
| memory_store | Save/remember a fact | {} |
| memory_recall | Recall/query a saved fact | {} |
| timer | Set a countdown timer | {"duration": {"minutes": 5}} |
| reminder | Set a reminder for later | {} |
| calls | Make a phone call | {"contact": "person name"} |
| security | Security check/alerts | {} |
| sensors | Check door/sensor status | {} |
| audit_journey | Ask what robot heard/did | {} |
| general_chat | Everything else (conversation, questions, jokes) | {} |

Examples:
User: "Can you dim the lights a little?"
{"intent": "control_fan", "entities": {"action": "on", "speed": 2}}

User: "What's the recipe for dal tadka?"
{"intent": "cooking", "entities": {"intent_id": "cooking.recipe", "recipe": "dal tadka"}}

User: "बत्ती बंद कर" (Turn off the light)
{"intent": "home_control", "entities": {"devices": ["light"], "action": "off"}}

User: "Set a timer for 10 minutes"
{"intent": "timer", "entities": {"duration": {"minutes": 10}}}

User: "How are you today?"
{"intent": "general_chat", "entities": {}}

User: "पंखा चालू कर और स्पीड ३ रख" (Turn on fan and set speed 3)
{"intent": "control_fan", "entities": {"action": "on", "speed": 3}}

User: "Arijit Singh चे गाणे लाव" (Play Arijit Singh's song)
{"intent": "play_music", "entities": {"action": "play", "song": "Arijit Singh"}}

Now classify this user command:
"""
