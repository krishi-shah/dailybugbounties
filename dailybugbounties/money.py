"""Pull a USD amount out of free text like "$1,500", "$2k", "250 USD" or "300 USDC"."""

import re
from typing import Iterable, Optional

_NUM = r"(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d{1,2}))?"
_DOLLAR = re.compile(r"(?<![A-Za-z0-9])(?:US)?\$\s?" + _NUM + r"\s?([kK])?(?![A-Za-z0-9])")
_SUFFIX = re.compile(r"(?<![\w$])" + _NUM + r"\s?([kK])?\s?(?:USD[CT]?|dollars)\b", re.I)


def _to_float(whole: str, cents: Optional[str], k: Optional[str]) -> float:
    value = float(whole.replace(",", ""))
    if cents:
        value += float("0." + cents)
    if k:
        value *= 1000
    return value


def parse_amount(text: Optional[str]) -> Optional[float]:
    """Return the first plausible USD amount in text, or None."""
    if not text:
        return None
    hits = []
    for rx in (_DOLLAR, _SUFFIX):
        for m in rx.finditer(text):
            hits.append((m.start(), _to_float(m.group(1), m.group(2), m.group(3))))
    hits = [h for h in hits if h[1] > 0]
    if not hits:
        return None
    hits.sort()
    return hits[0][1]


def first_amount(texts: Iterable[Optional[str]]) -> Optional[float]:
    """First amount found, trying each text in priority order."""
    for t in texts:
        a = parse_amount(t)
        if a:
            return a
    return None
