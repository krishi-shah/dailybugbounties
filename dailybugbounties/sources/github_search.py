"""Algora, IssueHunt and generic `bounty` labels all live on GitHub, so one module covers them."""

import logging
from typing import List

from .. import config
from ..github import GitHub
from . import amount_from_issue, from_search_item

log = logging.getLogger(__name__)

# Where to look for the amount first, per source.
AMOUNT_ORDER = {
    # Algora's real amount is in its bot comment; enrichment fills it in.
    "algora": (),
    # IssueHunt writes the funded total into the issue body.
    "issuehunt": ("body", "labels", "title"),
    # Generic labels: maintainers usually put "$200" in a label or the title.
    "labeled": ("labels", "title", "body"),
}


def fetch(gh: GitHub, source: str) -> List:
    query = config.GITHUB_SEARCH_QUERIES[source]
    out = []
    try:
        for item in gh.search_issues(query, config.SEARCH_MAX_RESULTS):
            b = from_search_item(item, source)
            if not b:
                continue
            order = AMOUNT_ORDER[source]
            if order:
                b.amount_usd = amount_from_issue(b, order)
            out.append(b)
    except Exception as e:  # one bad source never kills the feed
        log.error("%s search failed after %d items: %s", source, len(out), e)
    log.info("%s: %d candidates", source, len(out))
    return out
