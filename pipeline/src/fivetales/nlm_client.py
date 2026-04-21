"""NLM ICD-10-CM API wrapper.

API response format: [total, code_list, extra_fields_dict_or_null, display_list]
  - code_list: ["J45.909", ...]
  - display_list: [["J45.909", "Unspecified asthma, uncomplicated"], ...]
  - extra_fields_dict: {"MSH_Definition": [val_or_null, ...], ...} — often null values

For free-text queries, NLM returns results ordered by relevance; we take the first hit.
"""
import re
import logging
from dataclasses import dataclass
import requests
from fivetales.config import NLM_API_KEY, HTTP_TIMEOUT

logger = logging.getLogger(__name__)

_NLM_BASE_URL = "https://clinicaltables.nlm.nih.gov/api/icd10cm/v3/search"
# Anchored regex handles plain codes (J45.909) and letter-suffix codes (S52.521A, M1A.0110)
_ICD10_PATTERN = re.compile(r"^[A-Z]\d{2}(\.[A-Z0-9]{1,4})?$")


class NLMNoMatchError(Exception):
    """Raised when the NLM API returns no match for the given input."""


@dataclass
class NLMResult:
    icd10_code: str
    normalized_term: str
    best_definition: str
    raw_response: dict


def _select_best_definition(extra: dict, idx: int = 0) -> str:
    """Pick the best non-null definition from the extra_fields dict at list position idx."""
    for key in ("MEDLINEPLUS_Definition", "NCI_Definition", "MSH_Definition"):
        values = extra.get(key)
        if isinstance(values, list) and idx < len(values):
            val = values[idx]
            if isinstance(val, str) and val.strip():
                return val.strip()
    return ""


def lookup(input_text: str) -> NLMResult:
    """
    Resolve a raw medical input to a normalized term and definition.

    Detects ICD-10 codes via anchored regex (handles letter suffixes like S52.521A).
    Falls back to free-text search for plain medical terms.
    Raises NLMNoMatchError if no match is found.
    """
    text = input_text.strip()
    is_code = bool(_ICD10_PATTERN.match(text))

    # sf=code searches by code field; sf=code,name searches both code and name
    search_field = "code" if is_code else "code,name"
    params: dict = {
        "terms": text,
        "sf": search_field,
        "df": "code,name",
        "ef": "MSH_Definition,NCI_Definition,MEDLINEPLUS_Definition",
        "maxList": 1,
    }
    if NLM_API_KEY:
        params["apiKey"] = NLM_API_KEY

    logger.info("NLM lookup: %r (is_code=%s)", text, is_code)
    response = requests.get(_NLM_BASE_URL, params=params, timeout=HTTP_TIMEOUT)
    response.raise_for_status()
    raw = response.json()

    # raw = [total, code_list, extra_dict_or_null, display_list]
    code_list = raw[1] if len(raw) > 1 and raw[1] else []
    extra = raw[2] if len(raw) > 2 and isinstance(raw[2], dict) else {}
    display_list = raw[3] if len(raw) > 3 and raw[3] else []

    if not code_list:
        raise NLMNoMatchError(f"No NLM match for: {text!r}")

    icd10_code: str = code_list[0]
    normalized_term: str = display_list[0][1] if display_list and len(display_list[0]) > 1 else text
    best_def: str = _select_best_definition(extra, idx=0)

    logger.info("NLM resolved: %r → %r (%r)", text, icd10_code, normalized_term)
    return NLMResult(
        icd10_code=icd10_code,
        normalized_term=normalized_term,
        best_definition=best_def,
        raw_response={"total": raw[0] if raw else 0, "code_list": code_list, "display_list": display_list},
    )
