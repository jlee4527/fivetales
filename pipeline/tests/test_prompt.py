"""Tests for prompt.py."""
import json
import pytest
from unittest.mock import patch
from fivetales.prompt import build_messages, load_exemplars
from fivetales.schema import get_llm_schema


def test_build_messages_no_exemplars(tmp_path, monkeypatch):
    empty_file = tmp_path / "exemplars.json"
    empty_file.write_text("[]")
    import fivetales.prompt as prompt_mod
    monkeypatch.setattr(prompt_mod, "_EXEMPLARS_PATH", empty_file)

    messages = build_messages("Fever", "Body temperature higher than normal.")
    assert messages[0]["role"] == "system"
    assert messages[-1]["role"] == "user"
    # system + 1 user = 2 messages with no exemplars
    assert len(messages) == 2


def test_build_messages_with_exemplars(tmp_path, monkeypatch):
    exemplar = {
        "input_term": "Fever",
        "input_definition": "High temperature.",
        "character_card": {
            "character_name": "Blaze",
            "origin_story": "She was born in fire.",
            "superpowers": "Makes you warm",
            "flaws": "Tires quickly",
            "visual_description": "Orange glow",
            "tone": "brave",
            "confidence": 0.9,
            "notes": "",
        },
    }
    exemplars_file = tmp_path / "exemplars.json"
    exemplars_file.write_text(json.dumps([exemplar]))

    import fivetales.prompt as prompt_mod
    monkeypatch.setattr(prompt_mod, "_EXEMPLARS_PATH", exemplars_file)

    messages = build_messages("Asthma", "Breathing difficulty.")
    # system + user/assistant pair + real user = 4 messages
    assert len(messages) == 4
    assert messages[1]["role"] == "user"
    assert messages[2]["role"] == "assistant"
    assert messages[3]["role"] == "user"


def test_system_prompt_contains_schema():
    messages = build_messages("Test", "Test definition.")
    system_content = messages[0]["content"]
    assert "character_name" in system_content
    assert "origin_story" in system_content
    assert "tone" in system_content


def test_user_message_format():
    messages = build_messages("Fever", "High body temperature.")
    last_user = messages[-1]["content"]
    assert "Fever" in last_user
    assert "Definition:" in last_user
    assert "High body temperature." in last_user


def test_load_exemplars_missing_file(tmp_path, monkeypatch):
    import fivetales.prompt as prompt_mod
    monkeypatch.setattr(prompt_mod, "_EXEMPLARS_PATH", tmp_path / "nonexistent.json")

    result = load_exemplars()
    assert result == []


def test_load_exemplars_empty_array(tmp_path, monkeypatch):
    empty_file = tmp_path / "exemplars.json"
    empty_file.write_text("[]")

    import fivetales.prompt as prompt_mod
    monkeypatch.setattr(prompt_mod, "_EXEMPLARS_PATH", empty_file)

    result = load_exemplars()
    assert result == []


def test_no_think_directive_in_system_prompt():
    messages = build_messages("Test", "")
    system_content = messages[0]["content"]
    assert "/no_think" in system_content
