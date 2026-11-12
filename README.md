# dailybugbounties

**Every paid open source issue in one list, sorted by payout. Updated daily.**

dailybugbounties collects open bounties from **Algora**, **IssueHunt**, **Opire** and GitHub issues labeled `bounty`, checks that each issue is still open, removes spam, and ranks what's left by how much it pays.

🌐 **Website:** https://krishi-shah.github.io/dailybugbounties/ (filter by language, payout, competition)
📡 **RSS:** [`docs/feed.xml`](docs/feed.xml) for new bounties as they appear
🧾 **JSON:** [`data/bounties.json`](data/bounties.json) if you want to build on it

⭐ Star the repo to keep it handy. It refreshes itself every day.

## Today's top bounties

<!-- FEED:START -->
The first run of the daily workflow fills this table.
<!-- FEED:END -->

## How it works

| Source | How we get it | Where the amount comes from |
|---|---|---|
| Opire | Public `api.opire.dev/rewards` endpoint | Opire's reward value |
| Algora | GitHub search for the `💎 Bounty` label | The Algora bot comment on the issue |
| IssueHunt | GitHub search for the "Funded on IssueHunt" labels | The funded total IssueHunt writes into the issue |
| Labeled | GitHub search for `bounty` and similar labels | A `$` amount in a label, the title or the body |

Then, once a day in GitHub Actions:

1. **Merge.** If one issue shows up on two platforms, it becomes one row. We keep the higher amount and never add the two together.
2. **Verify.** One GraphQL call for every 25 issues gets the open/closed state, repo stars, language, archive status and the `/attempt` and `/claim` comments.
3. **Filter.** We drop closed issues, archived repos, amounts under $10 or over $50k, and prompt injection bait. For the generic `bounty` label we also drop repos under 50 stars, payouts of $5k or more in repos under 200 stars, issue farms, and anything in [`blocklist.txt`](blocklist.txt).
4. **Rank.** Highest payout first. When two pay the same, the one with fewer people trying wins.
5. **Publish.** The run writes this README, the JSON, the RSS feed and the site data, then commits them if anything changed.

No paid APIs, no accounts, no dependencies. It uses Python's standard library and the built in `GITHUB_TOKEN`.

## Run it yourself

```bash
git clone https://github.com/krishi-shah/dailybugbounties && cd dailybugbounties
export GITHUB_TOKEN=ghp_...        # any token works; without one, verification is skipped
python -m dailybugbounties --root .      # writes README.md, data/, docs/
python -m dailybugbounties --sources opire,algora -v
python -m unittest discover -s tests
```

You can tune the filters with environment variables: `BB_MIN_AMOUNT`, `BB_MAX_AMOUNT`, `BB_MIN_STARS_LABELED`, `BB_PER_REPO_CAP`, `BB_SEARCH_MAX_RESULTS`. See [`dailybugbounties/config.py`](dailybugbounties/config.py).

## Contributing

* **Found spam or a fake payout?** Open a PR that adds the repo or owner to [`blocklist.txt`](blocklist.txt), with a link that shows why.
* **Know another bounty platform?** Add a module under `dailybugbounties/sources/` that returns `Bounty` objects, then add a test.
* **Amount parsed wrong?** Add the text to `tests/test_feed.py` and fix `dailybugbounties/money.py`.

## Before you start work on a bounty

Amounts come from each platform or from the issue text. Read the issue, check that the bounty is still active, and see who is already working on it. dailybugbounties is a discovery tool and has no connection to any of these platforms.

## License

MIT
