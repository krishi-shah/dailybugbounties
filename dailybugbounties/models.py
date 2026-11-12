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
    """A paid task. Most are GitHub issues; listings from boards like Superteam
    Earn set `link` instead and use `owner` for the sponsor name."""
    owner: str
    repo: str
    number: int
    kind: str = "issue"           # "issue" (GitHub) or "listing" (bounty board)
    link: Optional[str] = None    # listing page, for non GitHub bounties
    owner_url: Optional[str] = None
    deadline: Optional[str] = None
    submissions: int = 0
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
    payout: str = "maintainer"     # how it gets paid: stripe, upwork, crypto, issuehunt, maintainer
    paid_before: int = 0           # paid bounties seen in this repo before
    verified_payer: bool = False
    first_seen: Optional[str] = None

    @property
    def is_issue(self) -> bool:
        return self.kind == "issue"

    @property
    def key(self) -> str:
        if not self.is_issue:
            return (self.link or "").lower()
        return canonical_url(self.owner, self.repo, self.number)

    @property
    def url(self) -> str:
        if not self.is_issue:
            return self.link or ""
        return f"https://github.com/{self.owner}/{self.repo}/issues/{self.number}"

    @property
    def full_repo(self) -> str:
        """owner/repo for issues; the sponsor name for listings."""
        return f"{self.owner}/{self.repo}" if self.is_issue else self.owner

    @property
    def home_url(self) -> Optional[str]:
        return f"https://github.com/{self.full_repo}" if self.is_issue else self.owner_url

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
        self.submissions = max(self.submissions, other.submissions)

    def to_public(self) -> dict:
        d = asdict(self)
        d.pop("body")
        d["url"] = self.url
        d["repo_full"] = self.full_repo
        d["home_url"] = self.home_url
        return d
