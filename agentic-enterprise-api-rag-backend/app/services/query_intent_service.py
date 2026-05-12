from __future__ import annotations

import re


INTENT_PATTERNS: dict[str, list[str]] = {
    "authentication_intent": [
        r"\bauth\b",
        r"\bauthentication\b",
        r"\btoken\b",
        r"\bbearer\b",
        r"\bjwt\b",
        r"\boauth\b",
        r"\bclient credentials\b",
        r"\brefresh token\b",
    ],
    "error_intent": [
        r"\binvalid\b",
        r"\berror\b",
        r"\bfailed\b",
        r"\bfailure\b",
        r"\bincorrect\b",
        r"\breturn code\b",
        r"\breturn message\b",
    ],
    "async_intent": [
        r"\basynchronous\b",
        r"\basync\b",
        r"\bcallback\b",
        r"\basynch\b",
    ],
    "api_lookup_intent": [
        r"\bwhich api\b",
        r"\bapi used\b",
        r"\bservice used\b",
    ],
    "parameter_intent": [
        r"\bmandatory\b",
        r"\bmandatory inputs?\b",
        r"\brequired\b",
        r"\brequired inputs?\b",
        r"\binput parameters?\b",
        r"\binput parameter\b",
        r"\brequest parameters?\b",
        r"\brequest parameter\b",
        r"\bresponse parameter\b",
        r"\bpayload\b",
        r"\bbody fields?\b",
        r"\bfield\b",
        r"\bfields\b",
    ],
    "response_field_intent": [
        r"\bsuccess response fields\b",
        r"\bresponse fields\b",
        r"\bresponse parameters\b",
        r"\bsuccessful response\b",
        r"\boutput response\b",
        r"\bwhat fields are returned\b",
        r"\bfields are returned\b",
        r"\breturned fields\b",
    ],
    "overview_intent": [
        r"\bpurpose\b",
        r"\bscope\b",
        r"\bintroduction\b",
        r"\bdocument\b",
    ],
    # Step 55 — semantic retrieval enrichment (headers / token expiry / request structure).
    "header_parameter_intent": [
        r"\bheaders?\s+(are\s+)?required\b",
        r"\brequired\s+headers?\b",
        r"\brequest\s+headers?\b",
        r"\bcalling\s+.*\bapi\b.*\bheader\b",
        r"\bauthorization\s+header\b",
        r"\btransactionid\b",
        r"\bheader\s+parameters\b",
        r"\bwhile\s+calling\b.*\bheader\b",
    ],
    "token_expiry_intent": [
        r"\baccess\s+tokens?\b.*\b(expir|expiry|expire)\b",
        r"\b(expir|expiry|expire)\b.*\baccess\s+tokens?\b",
        r"\bexpires_in\b",
        r"\b540\b.*\b(second|sec)s?\b",
        r"\b60\b.*\b(second|sec)s?\b",
        r"\bprod\b.*\b(non[\s-]*prod|uat|dev|lower)\b.*\b(expir|token|second)\b",
        r"\btokens?\b.*\b(prod|non[\s-]*prod)\b.*\b(expir|second)\b",
        r"\bexpiry\s+time\b.*\b(prod|non[\s-]*prod)\b",
        r"\bexpiry\s+time\b",
    ],
    "request_structure_intent": [
        r"\brequest\s+structure\b",
        r"\bexplain\s+the\s+request\s+structure\b",
        r"\bexplain\s+the\s+request\b",
        r"\brequest\s+body\b",
        r"\bjson\s+request\b",
        r"\brequest\s+payload\b",
        r"\bparameters\s+array\b",
        r"\bkey\s*/\s*value\b",
        r"\bkey\s+value\s+pairs\b",
    ],
}


def detect_query_intents(question: str) -> list[str]:
    text = (question or "").lower()
    intents: list[str] = []
    for intent, patterns in INTENT_PATTERNS.items():
        if any(re.search(pattern, text) for pattern in patterns):
            intents.append(intent)
    return intents
