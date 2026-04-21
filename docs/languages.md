---
noteId: "24d0dd603d9711f1992167ecef4078b8"
tags: []

---

# Localization Strategy

## Goal

Ensure character card narratives resonate across cultures, prioritizing communities with the highest barriers to medical understanding.

---

## Phase 1: Core Languages

| Language | Priority | Rationale |
|----------|----------|-----------|
| **English** | Baseline | Primary development language |
| **Spanish** | High | Largest non-English clinical population in the U.S. |

---

## Phase 2: High-Impact Scaling

| Language | Target Population |
|----------|------------------|
| **Mandarin** | Large immigrant and international patient communities |
| **Vietnamese** | Significant U.S. Southeast Asian healthcare access gap |
| **Arabic** | Regional healthcare needs, diaspora populations |
| **Korean** | Specific regional and community health needs |

---

## Cultural Vetting Requirements

For every language, the hero metaphor must be culturally reviewed before deployment:

- A character that feels safe and heroic in one culture may carry fear or negative connotation in another.
- **Example:** A dragon is a protector in East Asian culture but a threat in Western folklore. The metaphor must swap to ensure the child feels safe — never scared.
- The five `tone` enum values (`brave`, `gentle`, `curious`, `playful`, `fierce`) carry cultural weight and may need reframing per language before being passed to the LLM.

---

## Technical Notes for Localization

- The `tone` field is currently constrained to five English enum values. Each language rollout requires:
  1. Culturally equivalent tone labels reviewed by a native speaker
  2. Updated `LLM_OUTPUT_SCHEMA` enum in `src/fivetales/schema.py`
  3. Localized few-shot exemplars in `prompts/exemplars_{lang}.json`
  4. System prompt translated and culturally adapted (not just machine-translated)
- The `normalized_term` from the NLM API is English-only. A separate medical terminology lookup layer will be needed for non-English pipelines.
