"""Tunable knobs. Everything that decides what makes the list lives here."""

import os

# Money sanity bounds (USD). Below MIN is noise; above MAX is almost always fake.
MIN_AMOUNT = float(os.getenv("BB_MIN_AMOUNT", 10))
MAX_AMOUNT = float(os.getenv("BB_MAX_AMOUNT", 50_000))

# The generic `bounty` label is spammy, so its repos must clear a star bar.
MIN_STARS_LABELED = int(os.getenv("BB_MIN_STARS_LABELED", 50))
# Big payouts from any source need a repo people actually use.
BIG_AMOUNT = 5_000
MIN_STARS_BIG_LABELED = 200
# A repo with this many labeled bounty issues is an issue farm unless it is popular.
FARM_THRESHOLD = 40
FARM_MIN_STARS = 500
# Platform sources (Algora, IssueHunt, Opire) are vetted by the platform already.
MIN_STARS_PLATFORM = int(os.getenv("BB_MIN_STARS_PLATFORM", 10))

# One repo can't flood the list.
PER_REPO_CAP = int(os.getenv("BB_PER_REPO_CAP", 5))

# GitHub search returns at most 1000 results per query.
SEARCH_MAX_RESULTS = int(os.getenv("BB_SEARCH_MAX_RESULTS", 1000))
GRAPHQL_BATCH = 25

README_TOP_N = 100
README_NEW_N = 10
RSS_TOP_N = 50

GITHUB_SEARCH_QUERIES = {
    "algora": 'label:"💎 Bounty" is:issue is:open',
    "issuehunt": (
        'label:"funded on IssueHunt",":dollar: Funded on Issuehunt",'
        '"💵 Funded on Issuehunt" is:issue is:open'
    ),
    "labeled": (
        'label:bounty,"💰 bounty","bounty 💰","cash bounty","💸 bounty","💵 bounty",'
        '"has bounty","bounty available","bounty-program" is:issue is:open'
    ),
    # Expensify pays per issue (usually $250) and puts the price in the title: "[$250] ..."
    "expensify": 'repo:Expensify/App label:"Help Wanted" is:issue is:open',
    # Bounties announced only in the title, e.g. "[Bounty $500] Add SSO".
    "title": 'bounty in:title is:issue is:open',
}

OPIRE_URL = "https://api.opire.dev/rewards"

# Generic label bounties with no activity for this long are treated as abandoned.
STALE_DAYS = int(os.getenv("BB_STALE_DAYS", 540))
