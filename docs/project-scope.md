---
noteId: "24582af03d9711f1992167ecef4078b8"
tags: []

---

# fivetales — Project Scope & Data Schema

## What We're Building

A pediatric health literacy platform that transforms clinical medical data (ICD-10 codes and medical terms) into child-friendly hero narratives called **character cards**. Each card reframes a medical condition as a hero story a child ages 5–8 can understand.

---

## Pipeline Overview

```
User Input (ICD-10 code or medical term)
        ↓
NLM ICD-10-CM API lookup
        ↓
Resolved: { code, name, best_definition }
        ↓
Few-shot LLM Prompt (Qwen3-32B via Hugging Face)
        ↓
Character Card JSON — validated against schema
        ↓
Frontend / Streamlit Dashboard
```

---

## Character Card Schema (12 fields)

This is the canonical output format. All LLM outputs are validated against this schema before saving or displaying. Invalid outputs are retried automatically.

```json
{
  "original_input":     "J45.909",
  "normalized_term":    "Unspecified asthma, uncomplicated",
  "icd10_code":         "J45.909",
  "character_name":     "Name of the hero character",
  "origin_story":       "How the character came to be — plain language, ages 5–8",
  "superpowers":        "What the condition does that can be framed as a strength",
  "flaws":              "The challenge or limitation the hero faces",
  "visual_description": "What the character looks like",
  "tone":               "brave | gentle | curious | playful | fierce",
  "source":             "NLM+Qwen3-32B",
  "confidence":         0.0,
  "notes":              ""
}
```

**Field rules:**
- `original_input`, `icd10_code`, `normalized_term`, `source` — set by the pipeline, never by the LLM
- `tone` — must be exactly one of the five enum values
- `confidence` — LLM self-score 0.0–1.0; flag for human review if below 0.6
- `notes` — optional; empty string if unused
- All narrative fields (`origin_story`, `superpowers`, `flaws`, `visual_description`) must be non-empty and use no medical terminology

---

## Narrative Framework

The character card maps to a hero story structure:

| Card Field | Story Role |
|---|---|
| `character_name` | The hero |
| `origin_story` | How the condition became part of the body's world |
| `superpowers` | What the condition does — reframed as a strength or interesting trait |
| `flaws` | The challenge the hero (and child) must navigate |
| `visual_description` | Art direction for Brendan's image generation |

---

## Clinical Input Fields (for Jerry's backend)

When ingesting from the MedSiML dataset or a clinical record, the pipeline accepts:

| Field | Example |
|---|---|
| `symptom` | `"Acute Inflammation"` |
| `icd10_code` | `"J45.909"` |
| `caregiver_note` | `"Scared of the needle"` *(optional — not yet in pipeline)* |

The NLM API resolves the code or symptom term to a normalized name and definition before the LLM is called.

---

## Team

| Member | Role | Scope |
|--------|------|-------|
| Jae | Product Lead & UX | JSON schema, exemplar cards, GitHub/sprint board |
| Terrance | AI Architect | LLM pipeline, prompt engineering, Streamlit dashboard |
| Jerry | Data Wrangler | Dataset cleaning, backend API |
| Brendan | Creative Technologist | Image generation, text-to-speech |
| Jesse | DevOps & Security | API key security, hosting, PDF export |

---

## Sprint Roadmap

| Sprint | Focus | Dates |
|--------|-------|-------|
| Sprint 1 — Blueprint & Data | NLM pipeline, baseline tests, JSON schema finalization, exemplar writing | Apr 10–Apr 23 |
| Sprint 2 — Prompt Engineering | Few-shot pipeline, scale testing, schema enforcement | Apr 24–May 7 |
| Sprint 3 — Dashboard | Streamlit UI, interactive generation, team demo | May 8–May 21 |
