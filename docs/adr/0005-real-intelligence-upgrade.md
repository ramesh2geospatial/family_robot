# ADR 0005: Real Intelligence Upgrade — Local LLM Tool-Use, Context Engine, and Proactive Agency

## Status
Approved

## Context
FamilyRobot v1 (Steps 1-21) delivered a functional family companion with 20 keyword-matched skills, basic RAG memory, and conversation history. However, three intelligence gaps limited the user experience:

1. **Reactive-only behavior**: The robot only responds when spoken to, never proactively helps.
2. **Rigid intent classification**: Purely keyword-based; natural language variations like "dim the lights a bit" fail.
3. **No tool-use from chat**: The `general_chat` LLM fallback can only generate text, never take action (control devices, play music, set timers).
4. **Flat personality**: Same tone for children, elders, and guests.
5. **Silence gap**: 5-20 second CPU inference with no user feedback.

## Decision
Implement a 6-phase intelligence upgrade, all using the existing **local Llama 3.2 3B** model (no cloud dependency):

### Phase 1: Context Engine (`context_builder.py`)
- Unified, token-budgeted system prompt assembler.
- Injects identity (who is speaking, their role), time awareness (morning/night, day of week), active state (music playing, timers), RAG memories, and personality instructions.
- Replaces the scattered prompt construction in AssistantSkill.

### Phase 2: LLM-First Intent Classification (`intent_prompts.py`)
- Keyword rules remain as fast-path (zero LLM cost for exact matches).
- LLM fallback now returns **structured JSON** with both intent name AND extracted entities.
- Includes multilingual few-shot examples (Hindi, Marathi, English).
- Confidence calibration: JSON parse success → 0.75, plain text fallback → 0.6, parse failure → 0.4.

### Phase 3: Proactive Intelligence (`proactive_engine.py`)
- Background engine checked every 60s during idle.
- Time-based triggers: morning greetings (6-9 AM), bedtime reminders (10 PM+).
- State-based triggers: geyser-on warnings.
- Memory-based: surfaces relevant facts during greetings.
- Respects quiet hours (10 PM - 6 AM).
- Rate-limited (5 min minimum between suggestions).

### Phase 4: Tool-Use / Function Calling (`tool_registry.py`, `tool_executor.py`)
- Registry of callable tools (control_device, play_song, store/search_memory, get_time).
- Tool definitions injected into LLM system prompt during `general_chat`.
- LLM can respond with `{"tool": "name", "args": {...}}` JSON.
- ToolExecutor parses, validates, enforces ACL, executes, returns result.
- Guests cannot use tools.

### Phase 5: Personality (`personality.py`)
- Role-based persona profiles: child (encouraging, simple), teen (casual), elder (respectful, "ji"), guest (welcoming, no private info).
- Indian cultural calendar: festival greetings (Diwali, Holi, Ganesh Chaturthi, etc.).
- Injected into ContextBuilder system prompt.

### Phase 6: Latency Optimization
- Immediate acknowledgment phrase ("Let me think…" / "सोचने दो…" / "विचार करतो…") spoken before LLM inference.
- Translation merged into main LLM prompt (language instruction) — eliminates separate translation LLM call.
- Context window bumped from 2048 → 4096 tokens.

## Consequences

### Positive
- Natural language commands work ("dim the lights") via LLM classification.
- Robot can take action from free-form chat via tool-use.
- Proactive suggestions make the robot feel alive and helpful.
- Role-appropriate personality creates warmth.
- Acknowledgment eliminates awkward silence gap.
- All changes are local-first (no cloud dependency).

### Negative
- LLM intent classification adds ~2-5s latency for non-keyword commands.
- Tool-use in `general_chat` adds prompt size (~200 tokens for tool definitions).
- Proactive engine may occasionally suggest unwanted things (mitigated by quiet hours and rate limiting).
- Festival dates are approximate (hardcoded, not lunar-calendar-aware).

### Risks
- 3B model may not reliably produce valid JSON for tool calls. Mitigated by graceful fallback.
- Proactive geyser check requires HomePort.get_state() to work correctly for real devices.
