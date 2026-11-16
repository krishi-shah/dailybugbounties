"""Opire exposes every active reward at a public, unauthenticated endpoint."""

import logging
from typing import List

from .. import config
from ..github import get_json
from ..models import Bounty, parse_issue_url

log = logging.getLogger(__name__)


def parse(rewards: list) -> List[Bounty]:
    out = []
    for r in rewards or []:
        if (r.get("platform") or "GitHub") != "GitHub":
            continue
        if r.get("project", {}).get("isPublic") is False:
            continue
        parsed = parse_issue_url(r.get("url", ""))
        if not parsed:
            continue
        price = r.get("pendingPrice") or {}
        value = price.get("value") or 0
        unit = (price.get("unit") or "USD_CENT").upper()
        amount = value / 100 if unit == "USD_CENT" else float(value) if unit == "USD" else None
        owner, repo, number = parsed
        out.append(Bounty(
            owner=owner, repo=repo, number=number,
            title=r.get("title") or "",
            amount_usd=amount,
            sources=["opire"],
            languages=list(r.get("programmingLanguages") or []),
            attempts=len(r.get("tryingUsers") or []),
            claims=len(r.get("claimerUsers") or []),
        ))
    return out


def fetch(url: str = config.OPIRE_URL) -> List[Bounty]:
    try:
        data = get_json(url)
    except Exception as e:
        log.error("opire fetch failed: %s", e)
        return []
    if isinstance(data, dict):
        data = data.get("rewards") or data.get("data") or []
    out = parse(data)
    log.info("opire: %d candidates", len(out))
    return out
