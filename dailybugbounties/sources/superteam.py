"""Superteam Earn: a bounty board (mostly Solana companies) that pays in dollar stablecoins.

Its public listings API mixes dev work with content gigs (threads, videos) and has no
working category filter, so we keep a listing only when its title reads like building
software. Rewards in USDC/USDG count as dollars; other tokens are skipped.
"""

import json
import logging
import re
import urllib.parse
import urllib.request
from typing import List

from ..github import UA
from ..models import Bounty

log = logging.getLogger(__name__)

API = "https://superteam.fun/api/listings"
SITE = "https://superteam.fun/earn"
DOLLAR_TOKENS = {"USDC", "USDG", "USDT", "PYUSD", "USD"}

DEV = re.compile(
    r"\b(?:build|builds|building|develop\w*|dev|code|coding|engineer\w*|integrat\w*|sdk|api|"
    r"smart contracts?|programs?|bots?|agents?|apps?|dapps?|dashboards?|tools?|tooling|plugins?|"
    r"extensions?|cli|library|frontend|front end|backend|full ?stack|rust|anchor|typescript|"
    r"python|github|open ?source|deploy\w*|indexer|mcp|protocol|audit|hackathon)\b", re.I)
NOT_DEV = re.compile(
    r"\b(?:threads?|tweets?|videos?|content|memes?|articles?|blogs?|write|writing|writeup|"
    r"design|art|artwork|creators?|reels?|tiktok|youtube|translat\w*|trading competition|"
    r"community|ambassador|marketing|shill|raid|spaces?|podcast|newsletter)\b", re.I)


def is_dev(title: str) -> bool:
    return bool(DEV.search(title or "")) and not NOT_DEV.search(title or "")


def parse(listings: list) -> List[Bounty]:
    out = []
    for l in listings or []:
        if (l.get("status") or "OPEN") != "OPEN" or l.get("isWinnersAnnounced"):
            continue
        if l.get("isPro"):
            continue  # gated to paying members
        token = (l.get("token") or "").upper()
        amount = l.get("rewardAmount")
        if token not in DOLLAR_TOKENS or not amount:
            continue
        title = (l.get("title") or "").strip()
        if not is_dev(title):
            continue
        sponsor = l.get("sponsor") or {}
        kind = (l.get("type") or "bounty").lower()
        link = f"{SITE}/listing/{l.get('slug')}/"
        counts = l.get("_count") or {}
        out.append(Bounty(
            owner=(sponsor.get("name") or sponsor.get("slug") or "Superteam").strip(),
            repo="", number=0, kind="listing", link=link,
            owner_url=f"{SITE}/s/{sponsor['slug']}/" if sponsor.get("slug") else None,
            title=title, amount_usd=float(amount), sources=["superteam"],
            labels=[kind], deadline=l.get("deadline"),
            created_at=l.get("publishedAt") or l.get("createdAt"),
            updated_at=l.get("updatedAt"),
            submissions=counts.get("Submission", 0) or 0,
            comments=counts.get("Comments", 0) or 0,
            state="OPEN",
        ))
    return out


def _get(params: dict) -> list:
    url = f"{API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode())
    return data if isinstance(data, list) else data.get("listings") or data.get("data") or []


def fetch(max_pages: int = 10) -> List[Bounty]:
    """Page through every open listing. The API returns small pages and may ignore
    `type` and `take`, so we page with `skip` and stop when nothing new comes back."""
    by_slug = {}
    for kind in ("bounty", "project"):
        skip = 0
        for _ in range(max_pages):
            try:
                page = _get({"isWinnersAnnounced": "false", "take": 100, "skip": skip, "type": kind})
            except Exception as e:
                log.error("superteam %s fetch failed at skip=%d: %s", kind, skip, e)
                break
            new = [l for l in page if l.get("slug") and l["slug"] not in by_slug]
            for l in new:
                by_slug[l["slug"]] = l
            if not new:
                break
            skip += len(page)
    raw = list(by_slug.values())
    out = parse(raw)
    log.info("superteam: %d dev listings out of %d", len(out), len(raw))
    return out
