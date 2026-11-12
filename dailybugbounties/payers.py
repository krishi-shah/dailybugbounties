"""Who pays, and how.

`payout_method` says how a bounty gets paid (Stripe, Upwork, crypto, ...), from its source.
`collect_payers` finds evidence that a repo has paid bounties before:
  * Algora adds "💰 Rewarded" to an issue once its bounty is paid out.
  * DevPool closes a directory issue as completed once the task is done (payment is automatic).
  * Some maintainers mark paid bounty issues with a "paid" or "rewarded" label.
Evidence accumulates in data/payers.json, so the record keeps growing past GitHub's
1,000 results per search.
"""

import json
import logging
from datetime import date
from pathlib import Path
from typing import Dict, Iterable

from .github import GitHub
from .models import Bounty, parse_issue_url

log = logging.getLogger(__name__)

# How each source pays, best first when a bounty is listed in several places.
PAYOUT_BY_SOURCE = [
    ("algora", "stripe"), ("opire", "stripe"), ("expensify", "upwork"), ("devpool", "crypto"),
    ("superteam", "crypto"), ("taskbounty", "crypto"), ("issuehunt", "issuehunt"),
    ("labeled", "maintainer"), ("title", "maintainer"),
]
PAYOUT_NAMES = {"stripe": "Stripe", "upwork": "Upwork", "crypto": "Crypto wallet",
                "issuehunt": "IssueHunt", "maintainer": "Ask maintainer"}

# Company programs that pay every accepted contribution as a matter of policy.
PROGRAM_PAYERS = {"expensify/app": "Expensify pays every accepted Help Wanted fix through Upwork"}

EVIDENCE_QUERIES = {
    "algora_rewarded": 'label:"💰 Rewarded" is:issue',
    "devpool_completed": "repo:devpool-directory/devpool-directory is:issue is:closed reason:completed",
    "paid_label": 'label:bounty label:paid,"bounty paid",rewarded,"💸 Paid" is:issue is:closed',
}


def payout_method(b: Bounty) -> str:
    for source, method in PAYOUT_BY_SOURCE:
        if source in b.sources:
            return method
    return "maintainer"


def _repo_of(item: dict, kind: str):
    """The repo an evidence issue belongs to. DevPool directory issues point at the original."""
    if kind == "devpool_completed":
        body = (item.get("body") or "").strip().split()
        parsed = parse_issue_url(body[0]) if body else None
        if not parsed:
            return None
        return f"{parsed[0]}/{parsed[1]}".lower()
    parsed = parse_issue_url(item.get("html_url", ""))
    return f"{parsed[0]}/{parsed[1]}".lower() if parsed else None


def collect_payers(gh: GitHub, max_results: int = 1000) -> Dict[str, Dict[str, int]]:
    """repo -> {evidence kind: number of paid issues seen in this run}"""
    found: Dict[str, Dict[str, int]] = {}
    for kind, query in EVIDENCE_QUERIES.items():
        n = 0
        try:
            for item in gh.search_issues(query, max_results):
                repo = _repo_of(item, kind)
                if repo:
                    found.setdefault(repo, {}).setdefault(kind, 0)
                    found[repo][kind] += 1
                    n += 1
        except Exception as e:
            log.error("payer evidence %s failed after %d: %s", kind, n, e)
        log.info("payer evidence %s: %d issues", kind, n)
    return found


def merge_history(old: dict, new: Dict[str, Dict[str, int]], today: str) -> dict:
    """Keep the highest count ever seen per repo and kind. Counts never go down just
    because older paid issues fell outside this run's search window."""
    out = {k: dict(v) for k, v in old.items()}
    for repo, kinds in new.items():
        rec = out.setdefault(repo, {"first_seen": today})
        for kind, n in kinds.items():
            rec[kind] = max(rec.get(kind, 0), n)
        rec["last_seen"] = today
    return out


def paid_count(rec: dict) -> int:
    return sum(v for k, v in rec.items() if isinstance(v, int))


def apply(items: Iterable[Bounty], history: dict) -> None:
    for b in items:
        b.payout = payout_method(b)
        if not b.is_issue:
            continue
        repo = b.full_repo.lower()
        b.paid_before = paid_count(history.get(repo, {}))
        b.verified_payer = b.paid_before > 0 or repo in PROGRAM_PAYERS


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, ValueError):
        return {}


def save(path: Path, history: dict) -> None:
    path.write_text(json.dumps(history, indent=0, sort_keys=True, ensure_ascii=False))
