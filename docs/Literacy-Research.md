---
noteId: "23e852203d9711f1992167ecef4078b8"
tags: []

---

# Pediatric Literacy Research: The Anchor Five

**Status:** Active — Sprint 1  
**Owner:** @Jae (Product Designer)  
**Collaborators:** @Brendan (Visuals), @Terrance (AI)

---

## Goal

Bridge the gap between complex medical jargon and a child's understanding using action-oriented plain language and hero character metaphors. Target audience: children ages 5–8.

---

## The "Anchor Five" Framework

These five examples are the ground truth for the AI's tone and visual style. They directly populate `prompts/exemplars.json` as the few-shot examples baked into every LLM prompt.

| # | Medical Term | Plain Language Definition | Hero Metaphor | Tone |
|---|:---|:---|:---|:---|
| 1 | **Bacteria** | Tiny uninvited guests that try to take up space | The Grumble-Goblins — pesky creatures that leave toxins behind | `playful` |
| 2 | **Vaccine** | A "practice lesson" for the body's defenders | The Shield Map — a scroll that shows the Knights what Goblins look like | `brave` |
| 3 | **Leukemia** | When defenders get confused and grow too fast | The Clumsy Knights — protectors who have forgotten their jobs and are crowding the halls | `gentle` |
| 4 | **Fever** | The body turning up the heat to chase away bugs | The Fire Dragon's Hug — a friendly dragon warming the walls to help the Kingdom | `brave` |
| 5 | **Flu** | A big storm that makes the body tired while it cleans up | The Gray Mist — a heavy fog that settles while the Knights work hard | `curious` |

---

## Tone Vocabulary

Every character card must use exactly one tone value from this fixed set:

| Value | When to Use |
|-------|-------------|
| `brave` | Conditions where the body is actively fighting (fever, infections) |
| `gentle` | Conditions that are chronic, confusing, or scary (leukemia, asthma) |
| `curious` | Conditions with interesting biology the child can explore (flu, allergies) |
| `playful` | Conditions with a light, non-threatening framing (minor bacteria, rashes) |
| `fierce` | Conditions requiring strength and resilience (sepsis, serious injuries) |

---

## Hard Constraints for Story Generation

These rules are enforced in the AI system prompt and validated against the JSON schema:

- **Never use "war," "battle," or "attack" for Leukemia.** Frame it as balance, learning, and confusion — not combat.
- **No medical terms in story fields.** `origin_story`, `superpowers`, `flaws`, and `visual_description` must use plain language a 5-year-old can understand.
- **Short sentences only.** No sentence in a story field should exceed ~15 words.
- **Every story must convey the plain language definition.** The child should understand what the condition does to the body after reading the card, even if the word is never used.
- **`confidence` is AI self-scored (0.0–1.0).** A score below 0.6 should be flagged for human review.

---

## Exemplar File Location

Jae populates the five exemplar character cards in:

```
pipeline/prompts/exemplars.json
```

Each entry follows this format:

```json
{
  "input_term": "Fever",
  "input_definition": "A fever is a body temperature that is higher than normal...",
  "character_card": {
    "character_name": "...",
    "origin_story": "...",
    "superpowers": "...",
    "flaws": "...",
    "visual_description": "...",
    "tone": "brave",
    "confidence": 0.95,
    "notes": ""
  }
}
```

The pipeline loads these at runtime. An empty file is handled gracefully — the model will run with schema-only prompting until exemplars are added.

---

## Visual Direction (for Brendan)

- **The Clumsy Knights (Leukemia):** Harmless and confused — carrying too many shields, tripping over capes. Not scary.
- **The Fire Dragon (Fever):** Warm orange palette. Friendly, not threatening.
- **The Gray Mist (Flu):** Soft gray/blue. Avoid neon red or high-anxiety colors.
- **General rule:** No character should look like a threat to the child viewer.

---

> **Ethics note:** This research is grounded in pediatric literacy standards (CDC Clear Communication Index). We reframe the *experience* of illness — we do not misrepresent the *science*.
