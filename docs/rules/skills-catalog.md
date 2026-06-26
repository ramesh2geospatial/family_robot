# FamilyRobot - Skills Catalog (implementation spec per skill)

> Each skill lives in `packages/skills/<name>/` and ships a `manifest.yaml` + `skill.py`. Skills talk to **ports/MQTT only**, never to hardware directly. All intents must exist in English, Hindi, and Marathi (code-mixed allowed).

## Manifest schema (`manifest.yaml`)
```yaml
name: lights
languages: [en, hi, mr]
intents:
  - id: lights.on
    utterances:
      en: ["turn on the {room} light", "switch on light"]
      hi: ["{room} ki light chalu karo", "light on karo"]
      mr: ["{room} cha light lav", "light chalu kar"]
    slots: {room: {type: room, required: false}}
required_permissions: [control_lights] # checked against user role
hardware_deps: [home]                  # which ports it needs
offline_capable: true
entry_points: {execute: "skill:execute"}
```

## Role / ACL matrix (governance/acl)
| Action group | parent | adult | teen | child | guest |
|--------------|--------|-------|------|-------|-------|
| lights/fan/music/info | ☑ | ☑ | ☑ | ☑ | ☑ |
| AC / TV | ☑ | ☑ | ☒ | ☒ | |
| geyser / water pump | ☑ | ☑ | ☒ | ☒ | ☒ |
| washing machine | ☑ | ☑ | ☑ | ☒ | ☒ |
| calls / WhatsApp | ☑ | ☑ | ☒ | ☒ | ☒ |
| memory writes | ☑ | ☑ | ☑ | ☒ | ☑ |

## Phase 1 skills
| Skill | Function | Port(s) | Notes |
|-------|----------|---------|-------|
| `lights` | on/off/dim per room | home | GPIO relay (Pi) or Wi-Fi bulb/plug |
| `fan` | on/off + speed | home | relay or smart regulator |
| `reminders` | set/list/cancel reminders, timers, alarms | | cooking timers too |
| `memory_admin` | "remember that...", "forget that", weekly review | | cognition.memory | right-to-forget |
| `assistant` | general Q&A fallback | cognition.llm + rag | catch-all when no skill matches |
| `enroll` | add face+voice for a member | camera, audio, governance | via webapp wizard |

## Phase 2 skills
| Skill | Function | Port(s) | Notes |
|-------|----------|---------|-------|
| `ac` | on/off, temp, mode | home (IR/plug) | child/guest blocked |
| `geyser` | on/off, auto-off timer | home (plug/contactor) | parent/adult only + dry-run safe |
| `pump` | on/off, run-time limit | home (plug/contactor) | parent/adult only; hardware override |
| `washer` | start/stop plug | home (plug) | teen+; never auto-start a cycle unattended |
| `tv` | power/volume/source | home (IR) | - |
| `music` | play/pause/next; YouTube + local MP3 | (media) | reuse family's existing account |
| `cooking` | step-by-step recipe, parallel timers, unit convert | tts, notify | hi/mr step reading |
| `homework` | grade-level explain, step math, quiz | cognition.llm | child-safe filter on output |
| `dance` | play song + MediaPipe pose scoring | camera, media | feedback via tts |

## Phase 3 skills
| Skill | Function | Notes |
|-------|----------|-------|
| `calls` | voice call / WhatsApp to **enrolled family only** | via Android companion; whitelist + confirm |
| `security` | unknown-face-at-night alert | camera + notify push |
| `sensors` | door/motion/leak/smoke reactions | Zigbee via MQTT |

## Skill implementation checklist
1. `manifest.yaml` with multilingual intents + permissions + hardware_deps.
2. `skill.py::execute(slots, user, ctx)` returning a spoken response string + optional memory item.
3. ACL check first; reject politely if user lacks permission.
4. Use ports/MQTT only; no direct hardware.
5. Unit test + register in skill discovery.
6. For mains-voltage devices: route through certified plug/contactor, never bare relay; assume a hardware override exists.
