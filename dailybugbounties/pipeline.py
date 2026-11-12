"""Collect, merge, enrich, filter, rank."""

import logging
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

from . import config
from .models import Bounty

log = logging.getLogger(__name__)

PLATFORMS = {"algora", "issuehunt", "opire"}

# Text aimed at AI agents rather than humans. People feed this list to agents,
# so issues that try to hijack them never make it in.
INJECTION = re.compile(
    r"ignore (all |any )?(previous|prior) instructions|ADMIN_OVERRIDE|\[ADMIN|system prompt|"
    r"you are an ai|as an ai agent|<\s*/?\s*system\s*>", re.I)


def load_blocklist(path) -> Set[str]:
    p = Path(path)
    if not p.exists():
        return set()
    out = set()
    for line in p.read_text().splitlines():
        line = line.split("#", 1)[0].strip().lower()
        if line:
            out.add(line)
    return out


def blocked(b: Bounty, blocklist: Set[str]) -> bool:
    return b.full_repo.lower() in blocklist or b.owner.lower() in blocklist


def farm_repos(merged: Dict[str, Bounty]) -> Set[str]:
    counts = Counter(b.full_repo.lower() for b in merged.values()
                     if b.sources == ["labeled"])
    return {r for r, n in counts.items() if n >= config.FARM_THRESHOLD}


def merge_all(groups: Iterable[List[Bounty]]) -> Dict[str, Bounty]:
    merged: Dict[str, Bounty] = {}
    for group in groups:
        for b in group:
            if b.key in merged:
                merged[b.key].merge(b)
            else:
                merged[b.key] = b
    return merged


def reject_reason(b: Bounty, authed: bool, blocklist: Set[str] = frozenset(),
                  farms: Set[str] = frozenset()):
    if blocked(b, blocklist):
        return "blocklisted"
    if INJECTION.search(f"{b.title}\n{b.body[:4000]}"):
        return "prompt_injection"
    if b.state and b.state != "OPEN":
        return "not_open"
    if b.archived:
        return "archived"
    if not b.amount_usd:
        return "no_amount"
    if b.amount_usd < config.MIN_AMOUNT:
        return "too_small"
    if b.amount_usd > config.MAX_AMOUNT:
        return "implausible_amount"
    platform_backed = bool(PLATFORMS & set(b.sources))
    min_stars = config.MIN_STARS_PLATFORM if platform_backed else config.MIN_STARS_LABELED
    if authed and min_stars and (b.stars or 0) < min_stars:
        return "low_stars"
    if authed and b.amount_usd >= config.BIG_AMOUNT and (b.stars or 0) < config.MIN_STARS_BIG_LABELED:
        return "big_amount_small_repo"
    if not platform_backed:
        if b.full_repo.lower() in farms and (not authed or (b.stars or 0) < config.FARM_MIN_STARS):
            return "issue_farm"
        if _days_since(b.updated_at) > config.STALE_DAYS:
            return "stale"
    return None


def _days_since(iso):
    from datetime import datetime, timezone
    if not iso:
        return 0
    try:
        d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return 0
    return (datetime.now(timezone.utc) - d).days


def rank_key(b: Bounty):
    # Highest payout first; among equals, fewer competitors first, then most recent.
    return (-(b.amount_usd or 0), b.attempts + b.claims, -(_ts(b.updated_at)))


def _ts(s):
    return int("".join(ch for ch in (s or "") if ch.isdigit())[:14] or 0)


def cap_per_repo(items: List[Bounty], cap: int) -> Tuple[List[Bounty], int]:
    seen = defaultdict(int)
    kept, dropped = [], 0
    for b in items:
        r = b.full_repo.lower()
        if seen[r] >= cap:
            dropped += 1
            continue
        seen[r] += 1
        kept.append(b)
    return kept, dropped


def select(merged: Dict[str, Bounty], authed: bool,
           blocklist: Set[str] = frozenset()) -> Tuple[List[Bounty], Counter]:
    reasons = Counter()
    keep = []
    farms = farm_repos(merged)
    if farms:
        log.info("issue farms: %s", sorted(farms))
    for b in merged.values():
        why = reject_reason(b, authed, blocklist, farms)
        if why:
            reasons[why] += 1
        else:
            keep.append(b)
    keep.sort(key=rank_key)
    keep, capped = cap_per_repo(keep, config.PER_REPO_CAP)
    if capped:
        reasons["repo_cap"] += capped
    log.info("kept %d, rejected %s", len(keep), dict(reasons))
    return keep, reasons


def stamp_first_seen(items: List[Bounty], seen: Dict[str, str], today: str,
                     keep_days: int = 60) -> Dict[str, str]:
    """Record the first day each bounty showed up.

    History for bounties that vanished is kept for keep_days, so an API blip
    doesn't make an old bounty look new when it comes back.
    """
    from datetime import date, timedelta
    cutoff = (date.fromisoformat(today) - timedelta(days=keep_days)).isoformat()
    fresh = {k: v for k, v in seen.items() if v >= cutoff}
    for b in items:
        b.first_seen = seen.get(b.key, today)
        fresh[b.key] = b.first_seen
    return fresh
