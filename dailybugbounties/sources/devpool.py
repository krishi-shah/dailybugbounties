"""Ubiquity DevPool: a directory repo that mirrors priced tasks from many repos.

Each directory issue's body is the URL of the original issue, and its labels carry the
price ("Price: 75 USD"). We report the original issue so links, state checks and
dedupe all use the real thing.
"""

import logging
import re
from typing import List

from ..github import GitHub
from ..models import Bounty, parse_issue_url
from ..money import parse_amount
from . import from_search_item

log = logging.getLogger(__name__)

QUERY = "repo:devpool-directory/devpool-directory is:issue is:open"
PRICE = re.compile(r"^price:\s*", re.I)


def from_item(item: dict):
    b = from_search_item(item, "devpool")
    if not b:
        return None
    prices = [parse_amount(l) for l in b.labels if PRICE.match(l)]
    prices = [p for p in prices if p]
    if not prices:
        return None
    original = parse_issue_url((b.body or "").strip().split()[0] if b.body else "")
    if original:
        b.owner, b.repo, b.number = original
    b.amount_usd = max(prices)
    b.body = ""  # the body is just the link
    return b


def fetch(gh: GitHub, max_results: int = 1000) -> List[Bounty]:
    out = []
    try:
        for item in gh.search_issues(QUERY, max_results):
            b = from_item(item)
            if b:
                out.append(b)
    except Exception as e:
        log.error("devpool search failed after %d items: %s", len(out), e)
    log.info("devpool: %d candidates", len(out))
    return out
