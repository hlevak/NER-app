import re
from typing import Any

from .logger import get_predict_logger

logger = get_predict_logger()

# ---------------------------------------------------------------------------
# DATE patterns
# ---------------------------------------------------------------------------

_DATE_GENITIVE = (
    r"(?:января|февраля|марта|апреля|мая|июня"
    r"|июля|августа|сентября|октября|ноября|декабря)"
)
_DATE_FLEX = (
    r"(?:январ[яеь]|феврал[яеь]|март[ае]?|апрел[яеь]|ма[яей]"
    r"|июн[яеь]|июл[яеь]|август[ае]?|сентябр[яеь]|октябр[яеь]"
    r"|ноябр[яеь]|декабр[яеь])"
)
_YEAR_SUFFIX = r"(?:\s+год[уа])?"

_DATE_PATTERNS: list[re.Pattern] = [
    # "15 марта 2024 года" / "15 марта 2024" / "15 марта"
    re.compile(
        r"\b(?:0?[1-9]|[12]\d|3[01])\s+" + _DATE_GENITIVE
        + r"(?:\s+\d{4}" + _YEAR_SUFFIX + r")?\b",
        re.IGNORECASE | re.UNICODE,
    ),
    # "в апреле 2023 года" / "марта 2024"
    re.compile(
        r"\b" + _DATE_FLEX + r"\s+\d{4}" + _YEAR_SUFFIX + r"\b",
        re.IGNORECASE | re.UNICODE,
    ),
    # "2020 году" / "2024 года"
    re.compile(r"\b(?:19|20)\d{2}\s+год[уа]\b", re.IGNORECASE | re.UNICODE),
    # "15.03.2024" / "15/03/2024" / "15-03-2024"
    re.compile(
        r"\b(?:0?[1-9]|[12]\d|3[01])[.\-/](?:0?[1-9]|1[0-2])[.\-/](?:19|20)\d{2}\b"
    ),
]

# ---------------------------------------------------------------------------
# ES patterns
# ---------------------------------------------------------------------------

_TLD = r"(?:ru|рф|com|net|org|io|gov|edu)"

# Name group for composite patterns: 1-3 words starting with uppercase/digit.
# Prevents generic words like "сайт", "канал", "группа" from being absorbed.
_NAME = r"(?P<name>[А-ЯЁA-Z0-9]\S*(?:\s+[А-ЯЁA-Z0-9]\S*){0,2})"

# Composite patterns compiled WITHOUT re.IGNORECASE so that the uppercase
# constraint on the name group ([А-ЯЁA-Z0-9]) is enforced at match time.
_ES_COMPOSITE: list[tuple[re.Pattern, bool]] = [
    # C1. "Яндекс (www.ya.ru)" / "Google Maps (https://maps.google.com)"
    (
        re.compile(
            _NAME + r"\s*"
            r"\((?P<id>https?://[^\s<>\"')]+|www\.[a-zA-Z0-9\-]+\.[a-zA-Z]{2,}[^\s<>\"')]*"
            r"|[a-zA-Z0-9\-]+\." + _TLD + r"[^\s<>\"')]*)\)",
            re.UNICODE,
        ),
        True,
    ),
    # C2. "Новости (@news_ru)" / "Support (@support_bot)"
    (
        re.compile(
            _NAME + r"\s*\((?P<id>@[a-zA-Z][a-zA-Z0-9_]{3,30})\)",
            re.UNICODE,
        ),
        True,
    ),
    # C3. "Помощь (t.me/help_chat)"
    (
        re.compile(
            _NAME + r"\s*\((?P<id>(?:https?://)?t(?:elegram)?\.me/[a-zA-Z0-9_/\-.]+)\)",
            re.UNICODE,
        ),
        True,
    ),
]

# Standalone patterns compiled with re.IGNORECASE.
_ES_STANDALONE: list[tuple[re.Pattern, bool]] = [
    # S1. Email (before @username — consumes the @ part)
    (re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", re.IGNORECASE), False),
    # S2. @username
    (re.compile(r"(?<!\w)@[a-zA-Z][a-zA-Z0-9_]{3,30}(?!\w)", re.IGNORECASE), False),
    # S3. t.me / telegram.me deep links
    (re.compile(r"(?:https?://)?t(?:elegram)?\.me/[a-zA-Z0-9_/\-.]+", re.IGNORECASE), False),
    # S4. URL (http/https) — before bare domain
    (re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE), False),
    # S5. www.domain
    (re.compile(r"\bwww\.[a-zA-Z0-9\-]+\.[a-zA-Z]{2,}[^\s<>\"']*", re.IGNORECASE), False),
    # S6. Bare domain with restricted TLD list
    (re.compile(r"\b[a-zA-Z0-9\-]+\." + _TLD + r"(?:/[^\s]*)?\b", re.IGNORECASE), False),
    # S7. IPv4
    (re.compile(
        r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
    ), False),
    # S8. IPv6 (full / compressed / loopback)
    (re.compile(
        r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b"
        r"|\b(?:[0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}\b"
        r"|\b::1\b",
        re.IGNORECASE,
    ), False),
    # S9. Russian phone: +7 (999) 123-45-67 / 8-999-123-45-67 / +79991234567
    (re.compile(
        r"(?<!\d)(?:\+7|8)[\s\-]?[\(\[]?\d{3}[\)\]]?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}(?!\d)"
    ), False),
    # S10. ETH wallet (before BTC — different charset)
    (re.compile(r"\b0x[0-9a-fA-F]{40}\b", re.IGNORECASE), False),
    # S11. BTC wallet (legacy P2PKH/P2SH + bech32)
    (re.compile(r"\b(?:[13][a-km-zA-HJ-NP-Z1-9]{24,33}|bc1[ac-hj-np-z02-9]{6,87})\b"), False),
    # S12. Bank card: 16 digits in groups of 4
    (re.compile(r"(?<!\d)\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}(?!\d)"), False),
    # S13. Russian bank account: exactly 20 digits
    (re.compile(r"(?<!\d)\d{20}(?!\d)"), False),
]

_ES_PATTERNS: list[tuple[re.Pattern, bool]] = _ES_COMPOSITE + _ES_STANDALONE


# ---------------------------------------------------------------------------
# Overlap resolution
# ---------------------------------------------------------------------------

def _resolve_overlaps(
    candidates: list[tuple[int, int, str, str, dict]],
) -> list[dict[str, Any]]:
    """Keep longest non-overlapping spans; ties broken by pattern-list order (index)."""
    # candidates: (start, end, label, text, extra_fields_dict, priority_index)
    # We store priority as a 6th element when building candidates below.
    # Here we receive (start, end, label, text, meta_or_empty, priority).
    sorted_cands = sorted(candidates, key=lambda c: (c[0], -(c[1] - c[0]), c[5]))
    result: list[dict[str, Any]] = []
    last_end = -1
    for start, end, label, text, meta, _priority in sorted_cands:
        if start >= last_end:
            ent: dict[str, Any] = {
                "start": start,
                "end": end,
                "label": label,
                "text": text,
                "score": 1.0,
                "source": "regex",
            }
            if meta:
                ent["meta"] = meta
            result.append(ent)
            last_end = end
    return result


# ---------------------------------------------------------------------------
# RegexNERProcessor
# ---------------------------------------------------------------------------

class RegexNERProcessor:
    """Deterministic NER using compiled regex patterns for DATE and ES entities."""

    def predict(self, text: str) -> list[dict[str, Any]]:
        candidates: list[tuple[int, int, str, str, dict, int]] = []
        priority = 0

        for pat in _DATE_PATTERNS:
            for m in pat.finditer(text):
                candidates.append((m.start(), m.end(), "DATE", m.group(0), {}, priority))
            priority += 1

        for pat, has_named in _ES_PATTERNS:
            for m in pat.finditer(text):
                if has_named:
                    name = (m.group("name") or "").strip()
                    identifier = (m.group("id") or "").strip()
                    meta: dict[str, str] = {}
                    if name:
                        meta["name"] = name
                    if identifier:
                        meta["identifier"] = identifier
                else:
                    meta = {"identifier": m.group(0)}
                candidates.append((m.start(), m.end(), "ES", m.group(0), meta, priority))
            priority += 1

        entities = _resolve_overlaps(candidates)
        logger.debug("RegexNER found %d entities in %d chars", len(entities), len(text))
        return entities
