"""Request-scoped redaction of text sent to an external model."""
from __future__ import annotations

import re
from urllib.parse import urlsplit

CATEGORIES = ("registration", "business", "card", "email", "phone", "account", "ip", "url_query", "api_key")

_PATTERNS = {
    "registration": re.compile(r"(?<!\d)\d{6}[- ]?[1-8]\d{6}(?!\d)"),
    "business": re.compile(r"(?<!\d)\d{3}-?\d{2}-?\d{5}(?!\d)"),
    "card": re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)"),
    "email": re.compile(r"(?<![\w.+-])[A-Z0-9._%+-]+@[A-Z0-9-]+(?:\.[A-Z0-9-]*)+(?![A-Za-z0-9_.-])", re.IGNORECASE),
    "phone": re.compile(r"(?<!\d)(?:\+82[- ]?0?|0)(?:1[016789]|2|[3-6][1-5])[- ]?\d{3,4}[- ]?\d{4}(?!\d)"),
    "account": re.compile(r"(?<!\d)\d{2,6}(?:-\d{2,6}){2,4}(?!\d)"),
    "ip": re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])"),
    "api_key": re.compile(r"(?<![\w])(?:sk[_-](?:test[_-]|live[_-])?|AKIA|gh[pousr]_|AIza)[A-Za-z0-9_-]{20,}(?![\w])"),
}
_URL = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
_QUERY_SECRET = re.compile(r"(?:token|key|secret|password|auth|signature|credential|access_token|api_key)", re.IGNORECASE)
_GENERIC_TOKEN = re.compile(r"(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{32,}(?![A-Za-z0-9_-])")


class MaskingSession:
    """Ephemeral token table; create once per judgment and never persist it."""

    def __init__(self):
        self._tokens: dict[tuple[str, str], str] = {}
        self.input_chars = 0
        self.output_chars = 0
        self.count = 0
        self.calls = 0

    def token(self, category: str, value: str) -> str:
        key = (category, value)
        if key not in self._tokens:
            self._tokens[key] = f"[MASKED_{category.upper()}_{len(self._tokens) + 1}]"
        self.count += 1
        return self._tokens[key]


def _luhn(value: str) -> bool:
    digits = [int(char) for char in value if char.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    total = 0
    for index, digit in enumerate(reversed(digits)):
        if index % 2:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def _ip(value: str) -> bool:
    return all(int(part) <= 255 for part in value.split("."))


def mask_for_external(text: str, policy: dict) -> str:
    """Mask configured categories while preserving all surrounding text."""
    if not isinstance(text, str):
        raise TypeError("external text must be a string")
    config = policy.get("masking", {})
    if not config.get("enabled", True):
        return text
    categories = set(config.get("categories", CATEGORIES))
    session = policy.get("_masking_session") or MaskingSession()
    session.calls += 1
    session.input_chars += len(text)
    spans: list[tuple[int, int, str, str]] = []
    for category in CATEGORIES:
        if category == "url_query":
            if category in categories:
                for match in _URL.finditer(text):
                    url = match.group()
                    try:
                        query = urlsplit(url).query
                    except ValueError:
                        continue
                    if query and _QUERY_SECRET.search(query):
                        spans.append((match.start(), match.end(), category, url))
            continue
        if category not in categories:
            continue
        for match in _PATTERNS[category].finditer(text):
            value = match.group()
            if category == "card" and not _luhn(value):
                continue
            if category == "ip" and not _ip(value):
                continue
            if category == "account" and not (10 <= len(value.replace("-", "")) <= 16):
                continue
            spans.append((match.start(), match.end(), category, value))
    if "api_key" in categories:
        for match in _GENERIC_TOKEN.finditer(text):
            value = match.group()
            if any(char.isdigit() for char in value) and any(char.isalpha() for char in value):
                spans.append((match.start(), match.end(), "api_key", value))
    # First category wins for overlapping spans; replacement never changes unit IDs.
    spans.sort(key=lambda item: (item[0], CATEGORIES.index(item[2]), -(item[1] - item[0])))
    output = []
    cursor = 0
    for start, end, category, value in spans:
        if start < cursor:
            continue
        output.append(text[cursor:start])
        output.append(session.token(category, value))
        cursor = end
    output.append(text[cursor:])
    masked = "".join(output)
    session.output_chars += len(masked)
    return masked
