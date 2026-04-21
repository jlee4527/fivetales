"""System prompt builder and few-shot examples loader."""
import json
import logging
from pathlib import Path
from fivetales.schema import get_llm_schema

logger = logging.getLogger(__name__)

_EXEMPLARS_PATH = Path(__file__).parent.parent.parent / "prompts" / "exemplars.json"

_SYSTEM_PROMPT_TEMPLATE = """\
You are a children's story generator for kids ages 5 to 8.

You transform medical conditions into hero characters with simple, kind stories. \
Every word must be one a 5-year-old can understand. \
Every sentence must be short — no more than 15 words.

HARD RULES — follow these exactly:
1. NEVER use medical terms in origin_story, superpowers, flaws, or visual_description.
2. NEVER use the words "war", "battle", "attack", or "fight" for any condition. Use balance, learning, confusion, or teamwork instead.
3. The origin_story must make clear what the condition does to the body, in plain language.
4. ALL story fields must be non-empty.
5. Respond with ONLY a valid JSON object. No explanations. No markdown. No code fences.

The JSON object must match this exact schema:
{schema}

The "tone" field must be EXACTLY one of: brave, gentle, curious, playful, fierce
Choose the tone that best fits the condition:
- brave: body is actively working to get better (infections, fever)
- gentle: condition is confusing, scary, or long-lasting (leukemia, asthma)
- curious: condition has interesting biology to explore (flu, allergies)
- playful: condition is mild and non-threatening (minor rashes, common cold)
- fierce: condition requires real strength and resilience (sepsis, serious injuries)

The "confidence" field is your self-score from 0.0 to 1.0. Score below 0.6 means the story needs human review.
The "notes" field is an empty string unless you need to flag something.

/no_think"""


def _build_system_prompt() -> str:
    schema_str = json.dumps(get_llm_schema(), indent=2)
    return _SYSTEM_PROMPT_TEMPLATE.format(schema=schema_str)


def load_exemplars() -> list[dict]:
    """
    Load few-shot exemplar cards from prompts/exemplars.json.
    Returns empty list and logs WARNING if file is missing or empty.
    """
    if not _EXEMPLARS_PATH.exists():
        logger.warning("exemplars.json not found at %s — running without few-shot examples", _EXEMPLARS_PATH)
        return []
    try:
        data = json.loads(_EXEMPLARS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        logger.warning("exemplars.json is not valid JSON: %s — running without few-shot examples", exc)
        return []
    if not data:
        logger.warning("exemplars.json is empty — running without few-shot examples")
        return []
    return data


def build_messages(normalized_term: str, definition: str) -> list[dict]:
    """
    Build the full messages array for the LLM call.

    Structure:
      [system prompt]
      [user: exemplar input] [assistant: exemplar card JSON]  (repeated per exemplar)
      [user: real input]
    """
    messages: list[dict] = [{"role": "system", "content": _build_system_prompt()}]

    for ex in load_exemplars():
        user_content = ex.get("input_term", "")
        def_text = ex.get("input_definition", "")
        if def_text:
            user_content = f"{user_content}\n\nDefinition: {def_text}"
        messages.append({"role": "user", "content": user_content})
        messages.append({"role": "assistant", "content": json.dumps(ex.get("character_card", {}))})

    user_input = normalized_term
    if definition:
        user_input = f"{normalized_term}\n\nDefinition: {definition}"
    messages.append({"role": "user", "content": user_input})

    return messages
