# Security

## Reporting a vulnerability

Please don't open a public issue. Use GitHub's private reporting instead:
**Security → Report a vulnerability** on this repo. You'll get a reply within a few days.

## What this project does to stay safe

* **Untrusted data is treated as untrusted.** Issue titles, bodies and listing fields come from third parties. Only `http(s)` links are ever written to the README, RSS feed or website. Text is escaped for Markdown, XML and HTML before it's shown.
* **Prompt injection and scams are filtered.** Issues that try to instruct AI agents, airdrop style scams and token "bounties" are dropped before publishing.
* **Least privilege CI.** Workflows are read only by default. Only the job that commits the feed can write to the repo, and it uses the short lived `GITHUB_TOKEN`. No other secrets are used.
* **No dependencies.** The pipeline uses only Python's standard library, so there's no third party package to compromise.
* **Bounded downloads.** Every fetch has a timeout and a size cap.
* **Automated checks.** CodeQL scans the Python, JavaScript and workflows weekly and on every change, and Dependabot keeps the GitHub Actions up to date.

## Not a bounty program

This repo lists other people's bounties. It doesn't run one, and it can't vouch for any listed payout. Always confirm a bounty on the original issue or platform before you start work.
