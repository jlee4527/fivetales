"""JSON schema definitions and validator — single source of truth for character card structure."""
from jsonschema import validate, ValidationError
from typing import Any

LLM_OUTPUT_SCHEMA: dict = {
    "type": "object",
    "title": "LLMOutput",
    "description": "The 8 fields the LLM is asked to produce.",
    "properties": {
        "character_name": {"type": "string", "minLength": 1},
        "origin_story": {"type": "string", "minLength": 1},
        "superpowers": {"type": "string", "minLength": 1},
        "flaws": {"type": "string", "minLength": 1},
        "visual_description": {"type": "string", "minLength": 1},
        "tone": {"type": "string", "enum": ["brave", "gentle", "curious", "playful", "fierce"]},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "notes": {"type": "string"},
    },
    "required": [
        "character_name",
        "origin_story",
        "superpowers",
        "flaws",
        "visual_description",
        "tone",
        "confidence",
        "notes",
    ],
    "additionalProperties": False,
}

CARD_SCHEMA: dict = {
    "type": "object",
    "title": "CharacterCard",
    "description": "All 12 fields of the final merged character card.",
    "properties": {
        **LLM_OUTPUT_SCHEMA["properties"],
        "original_input": {"type": "string"},
        "normalized_term": {"type": "string"},
        "icd10_code": {"type": "string"},
        "source": {"type": "string"},
    },
    "required": [
        *LLM_OUTPUT_SCHEMA["required"],
        "original_input",
        "normalized_term",
        "icd10_code",
        "source",
    ],
    "additionalProperties": False,
}


def get_llm_schema() -> dict:
    """Return LLM_OUTPUT_SCHEMA for use in response_format."""
    return LLM_OUTPUT_SCHEMA


def get_card_schema() -> dict:
    """Return CARD_SCHEMA for final card validation."""
    return CARD_SCHEMA


def validate_card(card: dict[str, Any], schema: dict | None = None) -> tuple[bool, list[str]]:
    """
    Validate a character card dict against the given schema.

    Defaults to CARD_SCHEMA. Pass get_llm_schema() to validate 8-field LLM output.
    Returns (is_valid, list_of_error_messages).
    """
    if schema is None:
        schema = CARD_SCHEMA
    errors: list[str] = []
    try:
        validate(instance=card, schema=schema)
    except ValidationError as exc:
        errors.append(exc.message)
        # Collect all sub-errors from anyOf/oneOf if present
        for sub in exc.context:
            errors.append(sub.message)
    return (len(errors) == 0, errors)
