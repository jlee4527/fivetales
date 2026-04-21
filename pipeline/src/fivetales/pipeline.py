"""Main pipeline orchestrator: generate_card()."""
import sys
import json
import logging
import time
from json_repair import repair_json
from fivetales.nlm_client import lookup, NLMNoMatchError
from fivetales.llm_client import call_llm, LLMCallError
from fivetales.prompt import build_messages
from fivetales.schema import validate_card, get_llm_schema
from fivetales.config import MAX_LLM_RETRIES, MODEL_PRIMARY

logger = logging.getLogger(__name__)

_CORRECTION_MESSAGE = (
    "Your previous response failed validation: {errors}. "
    "Respond ONLY with a corrected JSON object matching the schema. "
    "Do not include any explanations or text outside the JSON."
)


def _parse_and_validate(text: str) -> tuple[dict | None, list[str]]:
    """Attempt to parse text as JSON and validate against LLM_OUTPUT_SCHEMA."""
    try:
        card = json.loads(text)
    except json.JSONDecodeError:
        return None, [f"JSON parse error: {text[:120]}"]
    valid, errors = validate_card(card, get_llm_schema())
    if not valid:
        return card, errors
    return card, []


def _run_validation_retry(initial_response: str, messages: list[dict]) -> dict | None:
    """
    Four-layer retry strategy:
      Layer 1: direct json.loads + schema validation
      Layer 2: json_repair fuzzy fix
      Layer 3: prompted self-correction (up to MAX_LLM_RETRIES)
      Layer 4: return None (caller handles failure)
    """
    # Layer 1
    card, errors = _parse_and_validate(initial_response)
    if card is not None and not errors:
        return card

    # Layer 2: fuzzy repair
    repaired = repair_json(initial_response)
    card, errors = _parse_and_validate(repaired)
    if card is not None and not errors:
        logger.info("Layer 2 fuzzy repair succeeded")
        return card

    # Layer 3: prompted self-correction
    retry_messages = list(messages)
    # Append what the model returned as an assistant message
    retry_messages.append({"role": "assistant", "content": initial_response})

    for attempt in range(MAX_LLM_RETRIES):
        error_desc = "; ".join(errors) if errors else "invalid or unparseable JSON"
        correction = _CORRECTION_MESSAGE.format(errors=error_desc)
        retry_messages.append({"role": "user", "content": correction})
        logger.warning("Layer 3 retry %d/%d: %s", attempt + 1, MAX_LLM_RETRIES, error_desc)

        try:
            response = call_llm(retry_messages)
        except LLMCallError as exc:
            logger.error("LLM retry %d failed: %s", attempt + 1, exc)
            break

        card, errors = _parse_and_validate(response)
        if card is not None and not errors:
            logger.info("Layer 3 self-correction succeeded on attempt %d", attempt + 1)
            return card

        retry_messages.append({"role": "assistant", "content": response})

    # Layer 4: failure
    return None


def generate_card(input_text: str) -> dict:
    """
    Convert a raw medical input to a character card.

    Args:
        input_text: ICD-10 code (e.g. "J45.909"), medical term, or plain description

    Returns:
        On success: character card dict matching CARD_SCHEMA (12 fields)
        On NLM failure: {"error": "NLM_NO_MATCH", "original_input": ..., "message": ...}
        On LLM failure: {"error": "LLM_FAILURE", "original_input": ..., "message": ...}
    """
    start = time.monotonic()
    logger.info("generate_card: %r", input_text)

    # Step 1: NLM normalization
    try:
        nlm = lookup(input_text)
    except NLMNoMatchError as exc:
        logger.error("NLM no match for %r: %s", input_text, exc)
        return {"error": "NLM_NO_MATCH", "original_input": input_text, "message": str(exc)}

    # Step 2: Build messages
    messages = build_messages(nlm.normalized_term, nlm.best_definition)

    # Step 3: LLM call
    try:
        raw_response = call_llm(messages)
    except LLMCallError as exc:
        logger.error("LLM failure for %r: %s", input_text, exc)
        return {"error": "LLM_FAILURE", "original_input": input_text, "message": str(exc)}

    # Steps 4+: Validation and retry
    llm_card = _run_validation_retry(raw_response, messages)

    if llm_card is None:
        duration_ms = int((time.monotonic() - start) * 1000)
        logger.error(
            "generate_card FAILED | input=%r resolved=%s (%s) | duration=%dms",
            input_text, nlm.icd10_code, nlm.normalized_term, duration_ms,
        )
        return {"error": "LLM_FAILURE", "original_input": input_text, "message": "All validation retries exhausted"}

    # Step 5: Pipeline injection — always overwrites LLM-produced values for these fields
    card = {
        **llm_card,
        "original_input": input_text,
        "normalized_term": nlm.normalized_term,
        "icd10_code": nlm.icd10_code,
        "source": f"NLM+{MODEL_PRIMARY.split('/')[1].split(':')[0]}",
    }

    # Step 6: Final validation against full CARD_SCHEMA
    valid, errors = validate_card(card)
    if not valid:
        logger.error("Final card validation failed: %s", errors)
        return {"error": "LLM_FAILURE", "original_input": input_text, "message": f"Final validation failed: {errors}"}

    duration_ms = int((time.monotonic() - start) * 1000)
    logger.info(
        "generate_card OK | input=%r resolved=%s (%s) | duration=%dms",
        input_text, nlm.icd10_code, nlm.normalized_term, duration_ms,
    )
    return card


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Generate a fivetales character card")
    parser.add_argument("--input", required=True, help="ICD-10 code or medical term")
    args = parser.parse_args()

    result = generate_card(args.input)
    if "error" in result:
        print(json.dumps(result, indent=2))
        sys.exit(1)
    print(json.dumps(result, indent=2))
    sys.exit(0)
