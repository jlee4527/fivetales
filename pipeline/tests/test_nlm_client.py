"""Tests for nlm_client.py — uses mocked HTTP responses."""
import pytest
import requests
from fivetales.nlm_client import lookup, NLMNoMatchError, NLMResult


def _make_nlm_response(codes, display_names, defs=None):
    """Build a minimal NLM API response list."""
    extra = {}
    if defs:
        extra = {
            "MSH_Definition": [defs.get("MSH")],
            "NCI_Definition": [defs.get("NCI")],
            "MEDLINEPLUS_Definition": [defs.get("MEDLINEPLUS")],
        }
    return [
        len(codes),
        codes,
        extra if extra else None,
        [[c, n] for c, n in zip(codes, display_names)],
    ]


def test_icd10_code_lookup(mocker):
    payload = _make_nlm_response(["J45.909"], ["Unspecified asthma, uncomplicated"])
    mock_resp = mocker.MagicMock()
    mock_resp.json.return_value = payload
    mock_resp.raise_for_status.return_value = None
    mocker.patch("fivetales.nlm_client.requests.get", return_value=mock_resp)

    result = lookup("J45.909")
    assert result.icd10_code == "J45.909"
    assert result.normalized_term == "Unspecified asthma, uncomplicated"


def test_letter_suffix_code_detected_as_code(mocker):
    payload = _make_nlm_response(["S52.521A"], ["Nondisplaced fracture of head of right radius"])
    mock_resp = mocker.MagicMock()
    mock_resp.json.return_value = payload
    mock_resp.raise_for_status.return_value = None
    mock_get = mocker.patch("fivetales.nlm_client.requests.get", return_value=mock_resp)

    lookup("S52.521A")
    call_params = mock_get.call_args[1]["params"]
    assert call_params["sf"] == "code"


def test_free_text_term_lookup(mocker):
    payload = _make_nlm_response(["R50.9"], ["Fever, unspecified"])
    mock_resp = mocker.MagicMock()
    mock_resp.json.return_value = payload
    mock_resp.raise_for_status.return_value = None
    mocker.patch("fivetales.nlm_client.requests.get", return_value=mock_resp)

    result = lookup("fever")
    assert result.icd10_code == "R50.9"
    assert result.normalized_term == "Fever, unspecified"


def test_plain_term_not_detected_as_code(mocker):
    payload = _make_nlm_response(["R50.9"], ["Fever, unspecified"])
    mock_resp = mocker.MagicMock()
    mock_resp.json.return_value = payload
    mock_resp.raise_for_status.return_value = None
    mock_get = mocker.patch("fivetales.nlm_client.requests.get", return_value=mock_resp)

    lookup("fever")
    call_params = mock_get.call_args[1]["params"]
    assert call_params["sf"] == "code,name"


def test_definition_priority_medlineplus_preferred(mocker):
    payload = _make_nlm_response(
        ["J45.909"], ["Unspecified asthma, uncomplicated"],
        defs={"MSH": "MSH def", "NCI": "NCI def", "MEDLINEPLUS": "MedlinePlus def"},
    )
    mock_resp = mocker.MagicMock()
    mock_resp.json.return_value = payload
    mock_resp.raise_for_status.return_value = None
    mocker.patch("fivetales.nlm_client.requests.get", return_value=mock_resp)

    result = lookup("J45.909")
    assert result.best_definition == "MedlinePlus def"


def test_definition_priority_only_msh(mocker):
    payload = _make_nlm_response(
        ["J45.909"], ["Unspecified asthma, uncomplicated"],
        defs={"MSH": "MSH only", "NCI": None, "MEDLINEPLUS": None},
    )
    mock_resp = mocker.MagicMock()
    mock_resp.json.return_value = payload
    mock_resp.raise_for_status.return_value = None
    mocker.patch("fivetales.nlm_client.requests.get", return_value=mock_resp)

    result = lookup("J45.909")
    assert result.best_definition == "MSH only"


def test_no_match_raises_error(mocker):
    payload = [0, [], None, []]
    mock_resp = mocker.MagicMock()
    mock_resp.json.return_value = payload
    mock_resp.raise_for_status.return_value = None
    mocker.patch("fivetales.nlm_client.requests.get", return_value=mock_resp)

    with pytest.raises(NLMNoMatchError):
        lookup("xyzzy_not_real")


def test_network_error_propagates(mocker):
    mocker.patch("fivetales.nlm_client.requests.get", side_effect=requests.ConnectionError("network error"))

    with pytest.raises(requests.ConnectionError):
        lookup("J45.909")
