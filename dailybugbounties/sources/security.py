"""Security bug bounties: open programs (Immunefi) and time boxed audit contests
(Immunefi audit competitions, Sherlock).

These are not fixed price tasks. A program pays "up to" its max bounty for a valid
vulnerability, and a contest splits a prize pool among researchers. So they are kept
in their own list and never mixed into the task totals.
"""

import logging
import time
from datetime import datetime, timezone
from typing import List

from ..github import get_json
from ..models import Bounty

log = logging.getLogger(__name__)

IMMUNEFI = "https://immunefi.com/public-api/bounties.json"
SHERLOCK = "https://mainnet-contest.sherlock.xyz/contests?page={page}"
DOLLAR_TOKENS = {"USDC", "USDT", "DAI", "RLUSD", "USD", "USDS", "PYUSD", "USDG"}
CONTEST, PROGRAM = "Audit contest", "Bug bounty program"


def _get(url: str, timeout: int = 60):
    return get_json(url, timeout=timeout)


def _iso(ts) -> str:
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_immunefi(programs: list) -> List[Bounty]:
    out = []
    for p in programs or []:
        if p.get("isPaused") or p.get("inviteOnly"):
            continue
        amount = p.get("maxBounty")
        slug = p.get("slug")
        if not amount or not slug:
            continue
        name = (p.get("project") or slug).strip()
        contest = name.lower().startswith("audit competition") or bool(p.get("endDate"))
        kind = CONTEST if contest else PROGRAM
        name = name.split("|", 1)[1].strip() if "|" in name else name
        path = "audit-competition" if contest else "bug-bounty"
        out.append(Bounty(
            owner=name, repo="", number=0, kind="security",
            link=f"https://immunefi.com/{path}/{slug}/",
            owner_url=p.get("websiteUrl") or None,
            title=f"{name} {'audit competition' if contest else 'bug bounty'}",
            amount_usd=float(amount), sources=["immunefi"], labels=[kind],
            languages=list(p.get("language") or []),
            deadline=p.get("endDate"), created_at=p.get("launchDate"), updated_at=p.get("updatedDate"),
            kyc=bool(p.get("kyc")), state="OPEN", payout="crypto",
        ))
    return out


def parse_sherlock(contests: list, now: float = None) -> List[Bounty]:
    now = now or time.time()
    out = []
    for c in contests or []:
        if c.get("private") or (c.get("status") or "").upper() in ("FINISHED", "JUDGING", "ESCALATING", "SHERLOCK_JUDGING"):
            continue
        ends = c.get("ends_at")
        if not ends or int(ends) < now:
            continue
        token = (c.get("token") or "USDC").upper()
        amount = c.get("rewards") or c.get("prize_pool")
        if token not in DOLLAR_TOKENS or not amount:
            continue
        title = (c.get("title") or "").strip()
        out.append(Bounty(
            owner=title, repo="", number=0, kind="security",
            link=f"https://audits.sherlock.xyz/contests/{c['id']}",
            title=f"{title} audit contest", amount_usd=float(amount), sources=["sherlock"],
            labels=[CONTEST], deadline=_iso(ends),
            created_at=_iso(c["starts_at"]) if c.get("starts_at") else None,
            state="OPEN", payout="crypto",
        ))
    return out


def fetch_immunefi() -> List[Bounty]:
    try:
        data = _get(IMMUNEFI, timeout=90)
    except Exception as e:
        log.error("immunefi fetch failed: %s", e)
        return []
    out = parse_immunefi(data if isinstance(data, list) else data.get("bounties", []))
    log.info("immunefi: %d programs and contests", len(out))
    return out


def fetch_sherlock(max_pages: int = 40) -> List[Bounty]:
    """The API ignores status filters and sorts by prize pool, so read every page."""
    raw, page = [], 1
    while page and page <= max_pages:
        try:
            data = _get(SHERLOCK.format(page=page))
        except Exception as e:
            log.error("sherlock page %d failed: %s", page, e)
            break
        raw += data.get("items") or []
        page = data.get("next_page") if data.get("has_next") else None
    out = parse_sherlock(raw)
    log.info("sherlock: %d live contests out of %d", len(out), len(raw))
    return out


def fetch() -> List[Bounty]:
    return fetch_immunefi() + fetch_sherlock()


def select(items: List[Bounty]) -> List[Bounty]:
    """Live ones only, contests by soonest deadline first, then programs by max bounty."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    live = [b for b in items if not (b.deadline and b.deadline[:19] < now)]
    seen, out = set(), []
    for b in live:
        if b.key not in seen:
            seen.add(b.key)
            out.append(b)
    contests = sorted((b for b in out if CONTEST in b.labels), key=lambda b: b.deadline or "9")
    programs = sorted((b for b in out if CONTEST not in b.labels), key=lambda b: -(b.amount_usd or 0))
    return contests + programs
