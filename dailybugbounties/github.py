"""Tiny GitHub client on the stdlib: REST search with paging, GraphQL, rate limit aware."""

import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request

log = logging.getLogger(__name__)

API = "https://api.github.com"
UA = "dailybugbounties (+https://github.com/krishi-shah/dailybugbounties)"


class GitHub:
    def __init__(self, token=None, sleep=time.sleep):
        self.token = token if token is not None else os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        self._sleep = sleep

    @property
    def authed(self) -> bool:
        return bool(self.token)

    def _request(self, url, data=None, tries=4):
        headers = {"Accept": "application/vnd.github+json", "User-Agent": UA,
                   "X-GitHub-Api-Version": "2022-11-28"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        body = None
        if data is not None:
            body = json.dumps(data).encode()
            headers["Content-Type"] = "application/json"
        for attempt in range(tries):
            req = urllib.request.Request(url, data=body, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    return json.loads(r.read().decode())
            except urllib.error.HTTPError as e:
                if e.code in (403, 429) and attempt < tries - 1:
                    reset = e.headers.get("x-ratelimit-reset")
                    retry_after = e.headers.get("retry-after")
                    wait = int(retry_after) if retry_after else (
                        max(1, int(reset) - int(time.time())) if reset else 30)
                    wait = min(wait + 1, 120)
                    log.warning("rate limited on %s, sleeping %ss", url[:80], wait)
                    self._sleep(wait)
                    continue
                if e.code >= 500 and attempt < tries - 1:
                    self._sleep(2 ** attempt)
                    continue
                raise
            except urllib.error.URLError:
                if attempt < tries - 1:
                    self._sleep(2 ** attempt)
                    continue
                raise

    def search_issues(self, query, max_results=1000):
        """Yield raw issue items for a search query, newest updated first."""
        per_page = 100
        pages = max(1, min(10, -(-max_results // per_page)))
        for page in range(1, pages + 1):
            qs = urllib.parse.urlencode({"q": query, "sort": "updated", "order": "desc",
                                         "per_page": per_page, "page": page})
            data = self._request(f"{API}/search/issues?{qs}")
            items = data.get("items", [])
            yield from items
            if len(items) < per_page:
                return
            # Search is limited to 30 req/min authed, 10 unauthed.
            self._sleep(2.2 if self.authed else 6.5)

    def graphql(self, query):
        if not self.token:
            raise RuntimeError("GraphQL needs GITHUB_TOKEN")
        return self._request(f"{API}/graphql", data={"query": query})
