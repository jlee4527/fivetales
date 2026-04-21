"""
Shared pytest fixtures for fivetales test suite.

Fixtures:
- sample_valid_llm_output: 8-field dict passing LLM_OUTPUT_SCHEMA
- sample_valid_card: 12-field dict passing CARD_SCHEMA
- mock_nlm_code_response: mocked NLM HTTP response for ICD-10 code lookup
- mock_nlm_term_response: mocked NLM HTTP response for free-text term search
- mock_nlm_no_match_response: mocked NLM HTTP response returning no results
- sample_nlm_result: NLMResult-compatible dict for pipeline integration tests
"""
import pytest


@pytest.fixture
def sample_valid_llm_output():
    """Complete 8-field dict that passes validation against LLM_OUTPUT_SCHEMA."""
    return {
        "character_name": "Blaze the Fever Knight",
        "origin_story": (
            "Blaze was born when your body got too hot. "
            "She runs through your blood to fight the bad bugs. "
            "She is strong and brave."
        ),
        "superpowers": "Makes your body very warm to scare away germs",
        "flaws": "Gets tired quickly and needs rest to recover",
        "visual_description": "A glowing orange knight with a flaming shield",
        "tone": "brave",
        "confidence": 0.9,
        "notes": "",
    }


@pytest.fixture
def sample_valid_card(sample_valid_llm_output):
    """Complete 12-field dict that passes validation against CARD_SCHEMA."""
    return {
        **sample_valid_llm_output,
        "original_input": "J45.909",
        "normalized_term": "Unspecified asthma, uncomplicated",
        "icd10_code": "J45.909",
        "source": "NLM+Qwen3-32B",
    }


@pytest.fixture
def mock_nlm_code_response():
    """Mocked NLM API HTTP response for a successful ICD-10 code lookup."""
    return {
        "codes": ["J45.909"],
        "display_names": ["Unspecified asthma, uncomplicated"],
        "MSH_Definition": "A form of bronchial disorder with no specific cause identified.",
        "NCI_Definition": "Asthma that has not been further specified.",
        "MEDLINEPLUS_Definition": (
            "Asthma is a disease that affects your lungs. "
            "It causes repeated episodes of wheezing, breathlessness, "
            "chest tightness, and nighttime or early morning coughing."
        ),
    }


@pytest.fixture
def mock_nlm_term_response():
    """Mocked NLM API HTTP response for a successful free-text term search."""
    return {
        "codes": ["R50.9"],
        "display_names": ["Fever, unspecified"],
        "MSH_Definition": "An abnormal elevation of body temperature.",
        "NCI_Definition": "A rise in body temperature above the normal range.",
        "MEDLINEPLUS_Definition": (
            "A fever is a body temperature that is higher than normal. "
            "A normal temperature is about 98.6 degrees Fahrenheit."
        ),
    }


@pytest.fixture
def mock_nlm_no_match_response():
    """Mocked NLM API HTTP response when no results are found."""
    return {
        "codes": [],
        "display_names": [],
        "MSH_Definition": "",
        "NCI_Definition": "",
        "MEDLINEPLUS_Definition": "",
    }


@pytest.fixture
def sample_nlm_result():
    """NLMResult-compatible dict for use in pipeline integration tests."""
    return {
        "icd10_code": "R50.9",
        "normalized_term": "Fever, unspecified",
        "best_definition": (
            "A fever is a body temperature that is higher than normal. "
            "A normal temperature is about 98.6 degrees Fahrenheit."
        ),
        "raw_response": {},
    }
