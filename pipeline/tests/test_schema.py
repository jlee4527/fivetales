"""Tests for schema.py."""
import pytest
from fivetales.schema import validate_card, get_llm_schema, get_card_schema


def test_valid_llm_output(sample_valid_llm_output):
    valid, errors = validate_card(sample_valid_llm_output, get_llm_schema())
    assert valid, errors


def test_valid_full_card(sample_valid_card):
    valid, errors = validate_card(sample_valid_card)
    assert valid, errors


def test_missing_required_field(sample_valid_card):
    del sample_valid_card["character_name"]
    valid, errors = validate_card(sample_valid_card)
    assert not valid
    assert errors


def test_invalid_tone_value(sample_valid_card):
    sample_valid_card["tone"] = "mysterious"
    valid, errors = validate_card(sample_valid_card)
    assert not valid


def test_confidence_too_high(sample_valid_card):
    sample_valid_card["confidence"] = 1.5
    valid, errors = validate_card(sample_valid_card)
    assert not valid


def test_confidence_too_low(sample_valid_card):
    sample_valid_card["confidence"] = -0.1
    valid, errors = validate_card(sample_valid_card)
    assert not valid


def test_empty_narrative_field_fails(sample_valid_card):
    sample_valid_card["origin_story"] = ""
    valid, errors = validate_card(sample_valid_card)
    assert not valid


def test_extra_fields_fail(sample_valid_card):
    sample_valid_card["unexpected_field"] = "oops"
    valid, errors = validate_card(sample_valid_card)
    assert not valid


def test_llm_schema_excludes_pipeline_fields():
    schema = get_llm_schema()
    for field in ("original_input", "normalized_term", "icd10_code", "source"):
        assert field not in schema["properties"]


def test_card_schema_includes_all_fields():
    schema = get_card_schema()
    for field in ("original_input", "normalized_term", "icd10_code", "source"):
        assert field in schema["properties"]
