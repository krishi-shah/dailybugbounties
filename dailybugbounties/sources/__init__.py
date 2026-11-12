"""Each source turns one platform into a list of Bounty candidates."""

from typing import Optional

from ..models import Bounty, parse_issue_url
from ..money import first_amount


def from_search_item(item: dict, source: str) -> Optional[Bounty]:
    if "pull_request" in item:
        return None
    parsed = parse_issue_url(item.get("html_url", ""))
    if not parsed:
        return None
    owner, repo, number = parsed
    return Bounty(
        owner=owner, repo=repo, number=number,
        title=item.get("title") or "",
        sources=[source],
        labels=[l["name"] for l in item.get("labels", [])],
        body=item.get("body") or "",
        state=(item.get("state") or "").upper() or None,
        created_at=item.get("created_at"),
        updated_at=item.get("updated_at"),
        comments=item.get("comments", 0),
    )


def amount_from_issue(b: Bounty, order=("labels", "title", "body")) -> Optional[float]:
    texts = []
    for part in order:
        if part == "labels":
            texts.extend(b.labels)
        else:
            texts.append(getattr(b, part))
    return first_amount(texts)
