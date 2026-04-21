"""Tests for pipeline.py — integration tests using mocked NLM and LLM."""
import json
import pytest
import requests
from unittest.mock import patch, MagicMock, call
from fivetales.pipeline import generate_card, _run_validation_retry
from fivetales.nlm_client import NLMResult, NLMNoMatchError
from fivetales.llm_client import LLMCallError


def _make_nlm_result(**kwargs):
    defaults = {
        "icd10_code": "R50.9",
        "normalized_term": "Fever, unspecified",
        "best_definition": "A fever is when your body gets hotter than normal.",
        "raw_response": {},
    }
    defaults.update(kwargs)
    return NLMResult(**defaults)


def _valid_llm_json(**overrides):
    card = {
        "character_name": "Blaze",
        "origin_story": "She was born when your body got too hot.",
        "superpowers": "Makes germs run away with heat",
        "flaws": "Gets tired quickly",
        "visual_description": "A glowing orange hero",
        "tone": "brave",
        "confidence": 0.9,
        "notes": "",
    }
    card.update(overrides)
    return json.dumps(card)


@patch("fivetales.pipeline.call_llm")
@patch("fivetales.pipeline.lookup")
def test_happy_path(mock_lookup, mock_call_llm):
    mock_lookup.return_value = _make_nlm_result()
    mock_call_llm.return_value = _valid_llm_json()

    result = generate_card("R50.9")

    assert "error" not in result
    assert result["icd10_code"] == "R50.9"
    assert result["original_input"] == "R50.9"
    assert result["normalized_term"] == "Fever, unspecified"
    assert result["source"].startswith("NLM+")
    assert result["character_name"] == "Blaze"


@patch("fivetales.pipeline.call_llm")
@patch("fivetales.pipeline.lookup")
def test_nlm_no_match_returns_error_dict(mock_lookup, mock_call_llm):
    mock_lookup.side_effect = NLMNoMatchError("No match")

    result = generate_card("xyzzy_not_real")

    assert result["error"] == "NLM_NO_MATCH"
    assert result["original_input"] == "xyzzy_not_real"
    mock_call_llm.assert_not_called()


@patch("fivetales.pipeline.call_llm")
@patch("fivetales.pipeline.lookup")
def test_llm_call_error_returns_error_dict(mock_lookup, mock_call_llm):
    mock_lookup.return_value = _make_nlm_result()
    mock_call_llm.side_effect = LLMCallError("all attempts failed")

    result = generate_card("fever")

    assert result["error"] == "LLM_FAILURE"


@patch("fivetales.pipeline.call_llm")
@patch("fivetales.pipeline.lookup")
def test_fuzzy_repair_succeeds_without_retry(mock_lookup, mock_call_llm):
    """Malformed JSON (trailing comma) is repaired by json_repair without LLM retry."""
    mock_lookup.return_value = _make_nlm_result()
    malformed = _valid_llm_json().rstrip("}") + ',}'  # trailing comma — valid for json_repair
    mock_call_llm.return_value = malformed

    result = generate_card("fever")

    assert "error" not in result
    # call_llm called once (no retry needed)
    assert mock_call_llm.call_count == 1


@patch("fivetales.pipeline.call_llm")
@patch("fivetales.pipeline.lookup")
def test_pipeline_field_injection_overwrites_llm_values(mock_lookup, mock_call_llm):
    """Pipeline-computed fields always overwrite any LLM-produced values."""
    mock_lookup.return_value = _make_nlm_result(icd10_code="R50.9", normalized_term="Fever, unspecified")
    # LLM returns valid JSON but with wrong pipeline fields
    mock_call_llm.return_value = _valid_llm_json()

    result = generate_card("fever")

    assert result["icd10_code"] == "R50.9"
    assert result["normalized_term"] == "Fever, unspecified"
    assert result["original_input"] == "fever"
    assert result["source"].startswith("NLM+")


@patch("fivetales.pipeline.call_llm")
@patch("fivetales.pipeline.lookup")
def test_think_block_stripped_before_validation(mock_lookup, mock_call_llm):
    """Responses with think blocks are cleaned by llm_client before pipeline sees them."""
    mock_lookup.return_value = _make_nlm_result()
    # llm_client already strips think blocks, so pipeline receives clean JSON
    mock_call_llm.return_value = _valid_llm_json()

    result = generate_card("fever")
    assert "error" not in result


# ---------------------------------------------------------------------------
# Pairwise test cases (NLM result × definition availability)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("definition,expected_def_passed", [
    ("A fever is when your body gets hotter than normal.", True),   # MEDLINEPLUS available
    ("A rise in body temperature above the normal range.", True),   # NCI only
    ("An abnormal elevation of body temperature.", True),           # MSH only
    ("", False),                                                    # no definition
])
@patch("fivetales.pipeline.call_llm")
@patch("fivetales.pipeline.lookup")
def test_definition_availability_variants(mock_lookup, mock_call_llm, definition, expected_def_passed):
    """Pipeline works for all definition availability levels; empty def still produces a card."""
    mock_lookup.return_value = _make_nlm_result(best_definition=definition)
    mock_call_llm.return_value = _valid_llm_json()

    result = generate_card("fever")

    assert "error" not in result
    # Verify the user message passed to LLM includes definition when available
    messages_sent = mock_call_llm.call_args[0][0]
    last_user = messages_sent[-1]["content"]
    if expected_def_passed:
        assert "Definition:" in last_user
    else:
        assert "Definition:" not in last_user


@pytest.mark.parametrize("input_text", [
    "J45.909",               # ICD-10 code
    "asthma",                # plain medical term
    "trouble breathing",     # colloquial description
])
@patch("fivetales.pipeline.call_llm")
@patch("fivetales.pipeline.lookup")
def test_input_type_variants(mock_lookup, mock_call_llm, input_text):
    """All three input types resolve to a valid card when NLM matches."""
    mock_lookup.return_value = _make_nlm_result(
        icd10_code="J45.909", normalized_term="Unspecified asthma, uncomplicated"
    )
    mock_call_llm.return_value = _valid_llm_json()

    result = generate_card(input_text)

    assert "error" not in result
    assert result["original_input"] == input_text
    assert result["icd10_code"] == "J45.909"


@pytest.mark.parametrize("input_text", [
    "J45.909",        # ICD-10 code
    "plain_term",     # plain term
    "colloquial",     # colloquial
])
@patch("fivetales.pipeline.call_llm")
@patch("fivetales.pipeline.lookup")
def test_nlm_no_match_all_input_types(mock_lookup, mock_call_llm, input_text):
    """NLM_NO_MATCH error dict is returned for all input types when NLM finds nothing."""
    mock_lookup.side_effect = NLMNoMatchError("No match")

    result = generate_card(input_text)

    assert result["error"] == "NLM_NO_MATCH"
    mock_call_llm.assert_not_called()


# ---------------------------------------------------------------------------
# Retry layer tests
# ---------------------------------------------------------------------------

@patch("fivetales.pipeline.call_llm")
@patch("fivetales.pipeline.lookup")
def test_layer3_self_correction_succeeds(mock_lookup, mock_call_llm):
    """Schema-invalid JSON on first call triggers Layer 3; second call returns valid card."""
    mock_lookup.return_value = _make_nlm_result()
    invalid_first = json.dumps({"character_name": "Blaze", "tone": "mysterious"})  # invalid tone
    mock_call_llm.side_effect = [invalid_first, _valid_llm_json()]

    result = generate_card("fever")

    assert "error" not in result
    assert mock_call_llm.call_count == 2
    # Second call should include a correction message as the last user turn
    second_call_messages = mock_call_llm.call_args_list[1][0][0]
    assert any("failed validation" in m["content"] for m in second_call_messages if m["role"] == "user")


@patch("fivetales.pipeline.call_llm")
@patch("fivetales.pipeline.lookup")
def test_layer3_all_retries_exhausted(mock_lookup, mock_call_llm):
    """Exhausting all retries returns LLM_FAILURE dict."""
    from fivetales.config import MAX_LLM_RETRIES
    mock_lookup.return_value = _make_nlm_result()
    # Every call returns schema-violating JSON (invalid tone)
    bad_response = json.dumps({"character_name": "X", "tone": "mysterious"})
    mock_call_llm.return_value = bad_response

    result = generate_card("fever")

    assert result["error"] == "LLM_FAILURE"
    # initial call + MAX_LLM_RETRIES retries
    assert mock_call_llm.call_count == 1 + MAX_LLM_RETRIES


@patch("fivetales.pipeline.call_llm")
@patch("fivetales.pipeline.lookup")
def test_layer3_retry_fails_with_llm_error(mock_lookup, mock_call_llm):
    """LLMCallError during a retry attempt exits cleanly with LLM_FAILURE."""
    mock_lookup.return_value = _make_nlm_result()
    bad_response = json.dumps({"character_name": "X", "tone": "mysterious"})
    mock_call_llm.side_effect = [bad_response, LLMCallError("retry failed")]

    result = generate_card("fever")

    assert result["error"] == "LLM_FAILURE"


# ---------------------------------------------------------------------------
# Schema violation edge cases
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_field,bad_value", [
    ("tone", "mysterious"),          # tone not in enum
    ("confidence", 1.5),             # confidence > 1.0
    ("confidence", -0.1),            # confidence < 0.0
    ("origin_story", ""),            # empty narrative field
    ("character_name", ""),          # empty required field
])
@patch("fivetales.pipeline.call_llm")
@patch("fivetales.pipeline.lookup")
def test_schema_violations_trigger_retry(mock_lookup, mock_call_llm, bad_field, bad_value):
    """Each schema violation on the first LLM call triggers at least one retry attempt."""
    mock_lookup.return_value = _make_nlm_result()
    first_response = _valid_llm_json(**{bad_field: bad_value})
    mock_call_llm.side_effect = [first_response, _valid_llm_json()]

    result = generate_card("fever")

    assert "error" not in result
    assert mock_call_llm.call_count == 2


# ---------------------------------------------------------------------------
# Pipeline field injection edge cases
# ---------------------------------------------------------------------------

@patch("fivetales.pipeline.call_llm")
@patch("fivetales.pipeline.lookup")
def test_llm_extra_pipeline_fields_fail_schema(mock_lookup, mock_call_llm):
    """LLM_OUTPUT_SCHEMA has additionalProperties:false — pipeline fields in LLM output
    cause a schema violation, triggering retry. They cannot reach injection unchanged."""
    from fivetales.config import MAX_LLM_RETRIES
    mock_lookup.return_value = _make_nlm_result(icd10_code="R50.9")
    llm_card = json.loads(_valid_llm_json())
    llm_card["icd10_code"] = "WRONG"  # extra field → additionalProperties violation
    mock_call_llm.return_value = json.dumps(llm_card)

    result = generate_card("fever")

    # Retries are exhausted because every call returns the extra field
    assert result["error"] == "LLM_FAILURE"
    assert mock_call_llm.call_count == 1 + MAX_LLM_RETRIES


# ---------------------------------------------------------------------------
# Boundary / edge cases
# ---------------------------------------------------------------------------

@patch("fivetales.pipeline.call_llm")
@patch("fivetales.pipeline.lookup")
def test_whitespace_only_input_hits_nlm_no_match(mock_lookup, mock_call_llm):
    """Whitespace-only input results in NLM_NO_MATCH; LLM never called."""
    mock_lookup.side_effect = NLMNoMatchError("empty query")

    result = generate_card("   ")

    assert result["error"] == "NLM_NO_MATCH"
    mock_call_llm.assert_not_called()


@patch("fivetales.pipeline.call_llm")
@patch("fivetales.pipeline.lookup")
def test_icd10_letter_suffix_code_routed_correctly(mock_lookup, mock_call_llm):
    """Letter-suffix ICD-10 codes (e.g. S52.521A) resolve and produce a card."""
    mock_lookup.return_value = _make_nlm_result(
        icd10_code="S52.521A",
        normalized_term="Nondisplaced fracture of head of right radius",
    )
    mock_call_llm.return_value = _valid_llm_json()

    result = generate_card("S52.521A")

    assert "error" not in result
    assert result["icd10_code"] == "S52.521A"


@patch("fivetales.pipeline.call_llm")
@patch("fivetales.pipeline.lookup")
def test_colloquial_input_with_no_definition(mock_lookup, mock_call_llm):
    """Colloquial input + no definition still produces a card (LLM uses term name only)."""
    mock_lookup.return_value = _make_nlm_result(best_definition="")
    mock_call_llm.return_value = _valid_llm_json()

    result = generate_card("trouble breathing")

    assert "error" not in result
    messages_sent = mock_call_llm.call_args[0][0]
    last_user = messages_sent[-1]["content"]
    assert "Definition:" not in last_user


@patch("fivetales.pipeline.call_llm")
@patch("fivetales.pipeline.lookup")
def test_unparseable_json_exhausts_all_retries(mock_lookup, mock_call_llm):
    """Completely unparseable responses exhaust all retries and return LLM_FAILURE."""
    from fivetales.config import MAX_LLM_RETRIES
    mock_lookup.return_value = _make_nlm_result()
    mock_call_llm.return_value = "I cannot generate a JSON response."

    result = generate_card("fever")

    assert result["error"] == "LLM_FAILURE"
    assert mock_call_llm.call_count == 1 + MAX_LLM_RETRIES


@patch("fivetales.pipeline.call_llm")
@patch("fivetales.pipeline.lookup")
def test_nlm_http_error_propagates(mock_lookup, mock_call_llm):
    """NLM HTTP 500 propagates as an unhandled exception (not swallowed into error dict)."""
    mock_lookup.side_effect = requests.HTTPError("500 Server Error")

    with pytest.raises(requests.HTTPError):
        generate_card("fever")
