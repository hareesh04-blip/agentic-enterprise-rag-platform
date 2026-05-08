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
        r"\brequired\b",
        r"\binput parameter\b",
        r"\bresponse parameter\b",
        r"\bfield\b",
    ],
    "overview_intent": [
        r"\bpurpose\b",
        r"\bscope\b",
        r"\bintroduction\b",
        r"\bdocument\b",
    ],
}


def detect_query_intents(question: str) -> list[str]:
    text = (question or "").lower()
    intents: list[str] = []
    for intent, patterns in INTENT_PATTERNS.items():
        if any(re.search(pattern, text) for pattern in patterns):
            intents.append(intent)
    return intents
