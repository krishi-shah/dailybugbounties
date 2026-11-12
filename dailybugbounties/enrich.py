"""One GraphQL call per batch fills in state, stars, language, attempts and Algora amounts."""

import json
import logging
import re
from typing import Dict, List

from . import config
from .github import GitHub
from .models import Bounty
from .money import parse_amount

log = logging.getLogger(__name__)

ALGORA_BOT = re.compile(r"algora", re.I)

FIELDS = """
  stargazerCount isArchived primaryLanguage { name }
  issue(number: %d) {
    state title createdAt updatedAt
    labels(first: 20) { nodes { name } }
    comments(first: 40) { totalCount nodes { author { login } body } }
  }
"""


def build_query(batch: List[Bounty]) -> str:
    parts = []
    for i, b in enumerate(batch):
        parts.append("i%d: repository(owner: %s, name: %s) {%s}" % (
            i, json.dumps(b.owner), json.dumps(b.repo), FIELDS % b.number))
    return "query {\n" + "\n".join(parts) + "\n}"


def algora_amount(comments: List[dict]):
    for c in comments:
        login = ((c.get("author") or {}).get("login")) or ""
        if ALGORA_BOT.search(login):
            a = parse_amount(c.get("body"))
            if a:
                return a
    return None


def apply(b: Bounty, repo: dict) -> None:
    b.stars = repo.get("stargazerCount")
    b.archived = bool(repo.get("isArchived"))
    lang = (repo.get("primaryLanguage") or {}).get("name")
    if lang:
        b.language = lang
    issue = repo.get("issue")
    if not issue:
        b.state = "MISSING"
        return
    b.state = issue.get("state")
    b.title = issue.get("title") or b.title
    b.created_at = issue.get("createdAt") or b.created_at
    b.updated_at = issue.get("updatedAt") or b.updated_at
    b.labels = sorted({n["name"] for n in (issue.get("labels") or {}).get("nodes", [])} | set(b.labels))
    comments = (issue.get("comments") or {})
    nodes = comments.get("nodes") or []
    b.comments = comments.get("totalCount", b.comments)
    bodies = [(c.get("body") or "").strip().lower() for c in nodes]
    b.attempts = max(b.attempts, sum(1 for t in bodies if t.startswith("/attempt")))
    b.claims = max(b.claims, sum(1 for t in bodies if t.startswith("/claim")))
    if "algora" in b.sources:
        a = algora_amount(nodes)
        if a:
            b.amount_usd = max(a, b.amount_usd or 0)


def enrich(gh: GitHub, bounties: Dict[str, Bounty]) -> None:
    if not gh.authed:
        log.warning("no GITHUB_TOKEN: skipping enrichment (state, stars, Algora amounts)")
        return
    items = list(bounties.values())
    for start in range(0, len(items), config.GRAPHQL_BATCH):
        batch = items[start:start + config.GRAPHQL_BATCH]
        try:
            resp = gh.graphql(build_query(batch))
        except Exception as e:
            log.error("graphql batch %d failed: %s", start, e)
            continue
        data = resp.get("data") or {}
        for i, b in enumerate(batch):
            repo = data.get(f"i{i}")
            if repo is None:
                b.state = "MISSING"  # repo deleted, renamed or private
            else:
                apply(b, repo)
    log.info("enriched %d issues", len(items))
