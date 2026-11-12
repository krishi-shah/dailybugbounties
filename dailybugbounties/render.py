"""Write the feed: JSON, README table, RSS, and the data file for the Pages site."""

import json
import re
from collections import Counter
from datetime import date, datetime, timezone
from email.utils import format_datetime
from html import escape
from pathlib import Path
from typing import List

from . import config
from .models import Bounty

START, END = "<!-- FEED:START -->", "<!-- FEED:END -->"
SOURCE_NAMES = {"algora": "Algora", "issuehunt": "IssueHunt", "opire": "Opire", "labeled": "Label"}


def money(v: float) -> str:
    return f"${v:,.0f}" if v == int(v) else f"${v:,.2f}"


def age_days(iso, today: date) -> str:
    if not iso:
        return ""
    try:
        d = datetime.fromisoformat(iso.replace("Z", "+00:00")).date()
    except ValueError:
        return ""
    n = (today - d).days
    return f"{n}d" if n < 365 else f"{n // 365}y"


def md_escape(s: str) -> str:
    s = re.sub(r"\s+", " ", s or "").strip()
    s = s.replace("|", "\\|").replace("[", "\\[").replace("]", "\\]").replace("<", "&lt;")
    return s[:80] + ("…" if len(s) > 80 else "")


def build_payload(items: List[Bounty], generated_at: datetime) -> dict:
    by_source = Counter(s for b in items for s in b.sources)
    return {
        "generated_at": generated_at.isoformat(timespec="seconds"),
        "count": len(items),
        "total_usd": round(sum(b.amount_usd or 0 for b in items), 2),
        "by_source": dict(by_source),
        "bounties": [b.to_public() for b in items],
    }


def readme_block(items: List[Bounty], payload: dict, today: date) -> str:
    new_today = sum(1 for b in items if b.first_seen == today.isoformat())
    src = " · ".join(f"{SOURCE_NAMES.get(k, k)} {v}" for k, v in sorted(payload["by_source"].items()))
    lines = [
        START,
        f"**{payload['count']} open bounties worth ${payload['total_usd']:,.0f}** "
        f"· {new_today} new today · updated {payload['generated_at'][:16].replace('T', ' ')} UTC",
        "",
        f"Sources: {src}",
        "",
        "| Payout | Issue | Repo | ★ | Lang | Source | Tries | Age |",
        "|---:|---|---|---:|---|---|---:|---:|",
    ]
    for b in items[:config.README_TOP_N]:
        new = " 🆕" if b.first_seen == today.isoformat() else ""
        lang = b.language or (b.languages[0] if b.languages else "")
        lines.append(
            f"| **{money(b.amount_usd)}** | [{md_escape(b.title)}]({b.url}){new} "
            f"| [{b.full_repo}](https://github.com/{b.full_repo}) | {b.stars if b.stars is not None else ''} "
            f"| {lang} | {', '.join(SOURCE_NAMES.get(s, s) for s in b.sources)} "
            f"| {b.attempts + b.claims} | {age_days(b.created_at, today)} |"
        )
    if len(items) > config.README_TOP_N:
        lines += ["", f"Showing the top {config.README_TOP_N}. The full list of {len(items)} is in "
                      "[`data/bounties.json`](data/bounties.json) and on the website."]
    lines.append(END)
    return "\n".join(lines)


def update_readme(path: Path, block: str) -> None:
    text = path.read_text() if path.exists() else f"# dailybugbounties\n\n{START}\n{END}\n"
    if START not in text:
        text += f"\n{START}\n{END}\n"
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    path.write_text(pattern.sub(lambda _: block, text))


def rss(items: List[Bounty], generated_at: datetime, site_url: str) -> str:
    newest = sorted(items, key=lambda b: (b.first_seen or "", b.amount_usd or 0), reverse=True)
    out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0"><channel>',
        "<title>dailybugbounties: paid open source issues</title>",
        f"<link>{escape(site_url)}</link>",
        "<description>New open source bounties from Algora, IssueHunt, Opire and GitHub, daily.</description>",
        f"<lastBuildDate>{format_datetime(generated_at)}</lastBuildDate>",
    ]
    for b in newest[:config.RSS_TOP_N]:
        seen = datetime.fromisoformat(b.first_seen).replace(tzinfo=timezone.utc) if b.first_seen else generated_at
        out += [
            "<item>",
            f"<title>{escape(money(b.amount_usd))} · {escape(b.full_repo)} · {escape(b.title)}</title>",
            f"<link>{escape(b.url)}</link>",
            f'<guid isPermaLink="true">{escape(b.url)}</guid>',
            f"<pubDate>{format_datetime(seen)}</pubDate>",
            f"<description>{escape(', '.join(b.sources))} · {b.attempts + b.claims} tries · "
            f"{escape(b.language or '')}</description>",
            "</item>",
        ]
    out.append("</channel></rss>")
    return "\n".join(out)


def write_all(root: Path, items: List[Bounty], generated_at: datetime, site_url: str) -> dict:
    today = generated_at.date()
    payload = build_payload(items, generated_at)
    blob = json.dumps(payload, indent=1, ensure_ascii=False)
    (root / "data").mkdir(exist_ok=True)
    (root / "docs").mkdir(exist_ok=True)
    (root / "data" / "bounties.json").write_text(blob)
    (root / "docs" / "bounties.json").write_text(blob)
    (root / "docs" / "feed.xml").write_text(rss(items, generated_at, site_url))
    update_readme(root / "README.md", readme_block(items, payload, today))
    return payload
