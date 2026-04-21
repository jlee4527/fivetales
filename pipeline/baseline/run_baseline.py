"""
Standalone baseline test runner.

Runs 4 test types × N conditions to document raw LLM behavior before few-shot prompting.
Results saved to baseline/results/ as timestamped JSON files — committed to repo.

Usage:
    uv run python baseline/run_baseline.py
    uv run python baseline/run_baseline.py --conditions fever asthma
"""
import sys
import json
import logging
import argparse
from datetime import datetime
from pathlib import Path

# Allow running from repo root without install
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fivetales.nlm_client import lookup, NLMNoMatchError
from fivetales.llm_client import call_llm, LLMCallError
from fivetales.schema import get_llm_schema, validate_card
from fivetales.config import MODEL_BASELINE, TEMPERATURE_BASELINE

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

RESULTS_DIR = Path(__file__).parent / "results"

DEFAULT_CONDITIONS = [
    "fever",
    "gastroenteritis",
    "urinary tract infection",
    "sepsis",
    "acute lymphoblastic leukemia",
]

_SCHEMA_ONLY_SYSTEM = (
    "Respond with ONLY a valid JSON object matching this schema. No explanations.\n\n"
    + json.dumps(get_llm_schema(), indent=2)
)

TEST_TYPES = [
    {
        "id": "raw_term",
        "description": "Plain medical term, no system prompt",
        "use_system": False,
        "use_normalized": False,
    },
    {
        "id": "raw_code",
        "description": "ICD-10 code string, no system prompt",
        "use_system": False,
        "use_normalized": False,
        "use_code_as_input": True,
    },
    {
        "id": "norm_no_prompt",
        "description": "NLM-normalized term + definition, no system prompt",
        "use_system": False,
        "use_normalized": True,
    },
    {
        "id": "norm_schema_only",
        "description": "NLM-normalized term + definition, schema-only system prompt",
        "use_system": True,
        "use_normalized": True,
    },
]


def _run_one(condition: str, test: dict, nlm_cache: dict) -> dict:
    """Run one test type for one condition. Returns a result record."""
    record: dict = {
        "condition": condition,
        "test_id": test["id"],
        "model": MODEL_BASELINE,
        "temperature": TEMPERATURE_BASELINE,
        "timestamp": datetime.utcnow().isoformat(),
        "input_sent": None,
        "system_prompt_used": None,
        "raw_response": None,
        "parse_success": False,
        "fields_present": [],
        "fields_missing": [],
        "tone_value": None,
        "token_usage": {},
        "error": None,
    }

    try:
        # Resolve ICD-10 code if needed
        if condition not in nlm_cache:
            try:
                nlm_cache[condition] = lookup(condition)
            except NLMNoMatchError:
                nlm_cache[condition] = None

        nlm = nlm_cache[condition]

        # Build input
        if test.get("use_code_as_input") and nlm:
            user_input = nlm.icd10_code
        elif test.get("use_normalized") and nlm:
            definition = nlm.best_definition
            user_input = nlm.normalized_term
            if definition:
                user_input = f"{nlm.normalized_term}\n\nDefinition: {definition}"
        else:
            user_input = condition

        record["input_sent"] = user_input

        # Build messages
        messages: list[dict] = []
        if test.get("use_system"):
            messages.append({"role": "system", "content": _SCHEMA_ONLY_SYSTEM})
            record["system_prompt_used"] = "schema_only"
        messages.append({"role": "user", "content": user_input})

        # Call LLM
        raw = call_llm(
            messages,
            temperature=TEMPERATURE_BASELINE,
            model=MODEL_BASELINE,
            response_format=None,
        )
        record["raw_response"] = raw

        # Analyze response
        try:
            parsed = json.loads(raw)
            record["parse_success"] = True
            schema_fields = list(get_llm_schema()["properties"].keys())
            record["fields_present"] = [f for f in schema_fields if f in parsed and parsed[f] not in (None, "")]
            record["fields_missing"] = [f for f in schema_fields if f not in parsed or parsed[f] in (None, "")]
            record["tone_value"] = parsed.get("tone")
        except json.JSONDecodeError:
            record["parse_success"] = False

    except LLMCallError as exc:
        record["error"] = f"LLM error: {exc}"
        logger.error("LLM error for %s / %s: %s", condition, test["id"], exc)
    except Exception as exc:
        record["error"] = f"Unexpected error: {exc}"
        logger.error("Unexpected error for %s / %s: %s", condition, test["id"], exc)

    return record


def run_baseline(conditions: list[str]) -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    all_results: list[dict] = []
    nlm_cache: dict = {}

    total = len(conditions) * len(TEST_TYPES)
    done = 0

    for condition in conditions:
        for test in TEST_TYPES:
            logger.info("[%d/%d] %s / %s", done + 1, total, condition, test["id"])
            record = _run_one(condition, test, nlm_cache)
            all_results.append(record)

            # Save individual result
            fname = f"{timestamp}_{condition.replace(' ', '_')}_{test['id']}.json"
            (RESULTS_DIR / fname).write_text(json.dumps(record, indent=2))
            done += 1

    # Summary stats
    parse_rate = sum(1 for r in all_results if r["parse_success"]) / len(all_results)
    schema_fields = list(get_llm_schema()["properties"].keys())
    avg_field_rate = (
        sum(len(r["fields_present"]) / len(schema_fields) for r in all_results if r["parse_success"])
        / max(1, sum(1 for r in all_results if r["parse_success"]))
    )
    tone_enum_values = {"brave", "gentle", "curious", "playful", "fierce"}
    tone_adherence = sum(
        1 for r in all_results if r.get("tone_value") in tone_enum_values
    ) / max(1, sum(1 for r in all_results if r["parse_success"]))

    summary = {
        "timestamp": timestamp,
        "model": MODEL_BASELINE,
        "conditions_tested": conditions,
        "total_runs": len(all_results),
        "json_parse_success_rate": round(parse_rate, 3),
        "avg_field_completion_rate": round(avg_field_rate, 3),
        "tone_enum_adherence_rate": round(tone_adherence, 3),
    }

    summary_file = RESULTS_DIR / f"{timestamp}_summary.json"
    summary_file.write_text(json.dumps(summary, indent=2))

    print("\n=== Baseline Summary ===")
    print(json.dumps(summary, indent=2))
    print(f"\nAll results saved to {RESULTS_DIR}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run fivetales baseline LLM tests")
    parser.add_argument(
        "--conditions",
        nargs="+",
        default=DEFAULT_CONDITIONS,
        help="Medical terms or ICD-10 codes to test (default: 5 exemplar conditions)",
    )
    args = parser.parse_args()
    run_baseline(args.conditions)
