---
noteId: "f63a56003db111f1992167ecef4078b8"
tags: []

---

# fivetales Pipeline

A 3-stage Python pipeline that transforms any medical input — raw ICD-10 code, free-text medical term, or plain description — into a JSON "character card" for kids ages 5–8.

---

## Stage Breakdown

### Stage 1 — NLM Normalization (`nlm_client.py`)

Accepts any input format and hits the NLM ICD-10-CM API to resolve it to a canonical `{ icd10_code, normalized_term, best_definition }`. Handles both code lookups (`J45.909`) and free-text searches (`"asthma"`) via field-targeted queries. Picks the best available definition in priority order: MedlinePlus → NCI → MeSH.

### Stage 2 — LLM Generation (`llm_client.py` + `prompt.py`)

Feeds the normalized term + definition into Qwen3-32B on Cerebras (via Hugging Face `InferenceClient`). Uses a structured system prompt with hard rules (no medical jargon, no war language, ≤15-word sentences, 5-to-8-year-old vocabulary). Few-shot exemplars are loaded from `prompts/exemplars.json` — currently 5 hand-crafted examples (Bacteria, Vaccine, Leukemia, Fever, Influenza).

Three-tier structured output fallback:
1. `json_schema` strict mode (Cerebras fast path)
2. `json_object` mode
3. Plain text generation

### Stage 3 — Validation + Retry (`pipeline.py` + `schema.py`)

Four-layer recovery on bad output:
1. Direct `json.loads` + schema check
2. `json_repair` fuzzy fix
3. LLM self-correction prompt (up to 2 retries)
4. Return structured error dict

On success, pipeline injects the 4 ground-truth fields (`original_input`, `normalized_term`, `icd10_code`, `source`) — the LLM never owns those. Final full 12-field `CARD_SCHEMA` validation before returning.

---

## Output Format

```json
{
  "original_input": "J45.909",
  "normalized_term": "Unspecified asthma, uncomplicated",
  "icd10_code": "J45.909",
  "source": "NLM+Qwen3-32B",
  "character_name": "...",
  "origin_story": "...",
  "superpowers": "...",
  "flaws": "...",
  "visual_description": "...",
  "tone": "gentle",
  "confidence": 0.88,
  "notes": ""
}
```

`tone` is always one of: `brave | gentle | curious | playful | fierce` — enum-enforced.

---

## Integration

Single entry point:

```python
from fivetales.pipeline import generate_card

card = generate_card("J45.909")         # ICD-10 code
card = generate_card("asthma")          # free-text term
card = generate_card("acute leukemia")  # description
```

Returns a card dict on success, or an error dict with `"error": "NLM_NO_MATCH"` or `"error": "LLM_FAILURE"` on failure. No exceptions bubble up — the caller always gets a dict.

**Jerry (backend):** Wrap `generate_card()` in a FastAPI route (`POST /card`, body `{ "input": "..." }`). The 12-field schema is stable.

**Brendan (image gen):** Use `visual_description` as the image prompt — plain English, no medical terms.

**Jesse (PDF/frontend):** Full card dict is the payload. `confidence < 0.6` signals human review needed.

---

## Baseline Testing

`baseline/run_baseline.py` runs 4 test types × N conditions before any few-shot prompting:

| Test ID | What it measures |
|---|---|
| `raw_term` | Does the model understand plain medical terms unaided? |
| `raw_code` | Does the model decode ICD codes without pre-processing? |
| `norm_no_prompt` | Does NLM normalization alone improve output? |
| `norm_schema_only` | How much does adding the JSON schema instruction buy? |

```bash
uv run python baseline/run_baseline.py
# custom conditions:
uv run python baseline/run_baseline.py --conditions "sepsis" "J45.909" "diabetes"
```

Results land in `baseline/results/` as timestamped JSON + a summary with JSON parse rate, field completion rate, and tone enum adherence.

---

## Forward Plan

### Sprint 1 (now — Apr 23)
- [ ] Run baseline tests, log results to `baseline/results/`
- [ ] Finalize schema with Jae — any field additions before Sprint 2 starts
- [ ] Add 3–5 more exemplars to `prompts/exemplars.json` with Jae

### Sprint 2 — Prompt Engineering
- Tune temperature, retry limits, and tone assignment rules based on baseline results
- Add batch processing: accept a list of inputs, return a list of cards

### Sprint 3 — Streamlit Dashboard
- Left panel: raw input field
- Middle panel: NLM resolution preview (code + normalized term + definition)
- Right panel: character card JSON + story preview
- Hook into `generate_card()` directly — no backend needed for the prototype
- Toggle to swap between Qwen3-32B (primary) and Qwen3-8B (baseline/cheap) for live comparison

---

## Open Gaps

- `exemplars.json` has 5 examples — system prompt is wired and ready for more
- `confidence` is LLM self-reported — consider a secondary heuristic check in Sprint 2
- No rate-limit handling on NLM or HF calls yet — add before Sprint 3 demo
