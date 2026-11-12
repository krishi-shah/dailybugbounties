"""python -m dailybugbounties [--root .] [--sources algora,issuehunt,opire,labeled]"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import enrich, pipeline, render
from .github import GitHub
from .sources import github_search, opire

ALL = ["algora", "issuehunt", "opire", "labeled"]


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="dailybugbounties")
    p.add_argument("--root", default=".", help="repo root to write data/, docs/, README.md")
    p.add_argument("--sources", default=",".join(ALL))
    p.add_argument("--site-url", default=os.getenv("BB_SITE_URL", "https://krishi-shah.github.io/dailybugbounties/"))
    p.add_argument("-v", "--verbose", action="store_true")
    a = p.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    log = logging.getLogger("dailybugbounties")

    root = Path(a.root)
    gh = GitHub()
    wanted = [s.strip() for s in a.sources.split(",") if s.strip()]

    groups = []
    for s in wanted:
        if s == "opire":
            groups.append(opire.fetch())
        elif s in github_search.AMOUNT_ORDER:
            groups.append(github_search.fetch(gh, s))
        else:
            log.error("unknown source %s", s)

    merged = pipeline.merge_all(groups)
    log.info("%d unique issues before enrichment", len(merged))
    enrich.enrich(gh, merged)
    items, _ = pipeline.select(merged, gh.authed, pipeline.load_blocklist(root / "blocklist.txt"))

    if not items:
        # Never overwrite a good feed with an empty one because of an outage.
        log.error("no bounties survived; leaving the existing feed untouched")
        return 1

    now = datetime.now(timezone.utc)
    seen_path = root / "data" / "seen.json"
    seen = json.loads(seen_path.read_text()) if seen_path.exists() else {}
    seen = pipeline.stamp_first_seen(items, seen, now.date().isoformat())
    seen_path.parent.mkdir(exist_ok=True)
    seen_path.write_text(json.dumps(seen, indent=0, sort_keys=True))

    payload = render.write_all(root, items, now, a.site_url)
    log.info("wrote %d bounties worth $%s", payload["count"], f"{payload['total_usd']:,.0f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
