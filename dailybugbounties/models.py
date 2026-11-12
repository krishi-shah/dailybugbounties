import re
from dataclasses import dataclass, field, asdict
from typing import List, Optional

ISSUE_RE = re.compile(r"github\.com/([^/\s]+)/([^/\s]+)/issues/(\d+)")


def parse_issue_url(url: str):
    m = ISSUE_RE.search(url or "")
    if not m:
        return None
    return m.group(1), m.group(2), int(m.group(3))


def canonical_url(owner: str, repo: str, number: int) -> str:
    return f"https://github.com/{owner}/{repo}/issues/{number}".lower()


@dataclass
class Bounty:
    owner: str
    repo: str
    number: int
    title: str = ""
    amount_usd: Optional[float] = None
    sources: List[str] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)
    body: str = ""
    language: Optional[str] = None
    languages: List[str] = field(default_factory=list)
    stars: Optional[int] = None
    state: Optional[str] = None  # OPEN / CLOSED, filled by enrichment
    archived: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    comments: int = 0
    attempts: int = 0
    claims: int = 0
    open_prs: int = 0
    older: bool = False  # issue opened more than MAX_AGE_DAYS ago
    first_seen: Optional[str] = None

    @property
    def key(self) -> str:
        return canonical_url(self.owner, self.repo, self.number)

    @property
    def url(self) -> str:
        return f"https://github.com/{self.owner}/{self.repo}/issues/{self.number}"

    @property
    def full_repo(self) -> str:
        return f"{self.owner}/{self.repo}"

    def merge(self, other: "Bounty") -> None:
        """Fold another sighting of the same issue into this one."""
        for s in other.sources:
            if s not in self.sources:
                self.sources.append(s)
        # Same money listed on two platforms is still the same money: keep the max.
        if other.amount_usd and (not self.amount_usd or other.amount_usd > self.amount_usd):
            self.amount_usd = other.amount_usd
        for attr in ("title", "body", "created_at", "updated_at", "language"):
            if not getattr(self, attr) and getattr(other, attr):
                setattr(self, attr, getattr(other, attr))
        self.labels = sorted(set(self.labels) | set(other.labels))
        self.languages = sorted(set(self.languages) | set(other.languages))
        self.attempts = max(self.attempts, other.attempts)
        self.claims = max(self.claims, other.claims)
        self.comments = max(self.comments, other.comments)
        self.open_prs = max(self.open_prs, other.open_prs)

    def to_public(self) -> dict:
        d = asdict(self)
        d.pop("body")
        d["url"] = self.url
        d["repo_full"] = self.full_repo
        return d
