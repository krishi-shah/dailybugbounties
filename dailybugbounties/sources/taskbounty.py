"""TaskBounty: funded GitHub issues ($10 to $100) listed at a public, unauthenticated endpoint."""

import json
import logging
import urllib.request
from typing import List

from ..github import UA
from ..models import Bounty, parse_issue_url

log = logging.getLogger(__name__)

URL = "https://www.task-bounty.com/api/v1/tasks"


def _amount(t: dict):
    for k in ("bounty_cents", "amount_cents", "reward_cents"):
        if t.get(k):
            return float(t[k]) / 100
    for k in ("bounty_usd", "amount_usd", "bounty", "amount", "reward"):
        v = t.get(k)
        if isinstance(v, (int, float)) and v > 0:
            return float(v)
    return None


def parse(tasks: list) -> List[Bounty]:
    out = []
    for t in tasks or []:
        url = t.get("github_issue_url") or t.get("issue_url") or t.get("url") or ""
        parsed = parse_issue_url(url)
        amount = _amount(t)
        if not parsed or not amount:
            continue
        owner, repo, number = parsed
        lang = t.get("language")
        out.append(Bounty(owner=owner, repo=repo, number=number, title=t.get("title") or "",
                          amount_usd=amount, sources=["taskbounty"],
                          languages=[lang] if lang else [], created_at=t.get("created_at")))
    return out


def fetch() -> List[Bounty]:
    try:
        req = urllib.request.Request(URL, headers={"User-Agent": UA, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
    except Exception as e:
        log.error("taskbounty fetch failed: %s", e)
        return []
    tasks = data.get("data") if isinstance(data, dict) else data
    out = parse(tasks)
    log.info("taskbounty: %d candidates", len(out))
    return out
