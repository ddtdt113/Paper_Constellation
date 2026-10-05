"""Graph data model and JSON (de)serialisation.

A constellation is a directed graph of papers. Every edge points from the
earlier paper (the one that was built upon) to the later one, and may carry a
short note on which problem the later paper solved.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

SCHEMA = "paper-constellation/1"

# Node kinds
CENTER = "center"          # the paper the user searched for
ANCESTOR = "ancestor"      # a paper the center (transitively) builds on
DESCENDANT = "descendant"  # a paper that (transitively) builds on the center
FOUNDATION = "foundation"  # curated graphs: bedrock papers
CORE = "core"              # curated graphs: the hub of the map
BRANCH = "branch"          # curated graphs: follow-up work
NEW = "new"                # curated graphs: freshly added from a digest

# Node status ("where does this paper stand today?"); display names live in i18n
STATUSES = ("foundation", "active", "superseded", "recent")


@dataclass
class Node:
    id: str
    title: str
    label: str = ""
    authors: str = ""
    year: float = 0.0          # fractional year, used for the time axis
    date: str = ""             # YYYY-MM-DD when known
    venue: str = ""
    arxiv: str = ""
    doi: str = ""
    url: str = ""
    abstract: str = ""
    tldr: str = ""
    citation_count: int = 0
    influential_count: int = 0
    lane: str = ""
    kind: str = BRANCH
    status: str = ""
    note: str = ""
    note_en: str = ""          # optional English translation (curated examples)

    def display_label(self) -> str:
        return self.label or short_label(self.title)


@dataclass
class Edge:
    src: str                   # earlier paper (built upon)
    dst: str                   # later paper (builds on src)
    solves: str = ""           # what problem dst solved relative to src
    influential: bool = False
    solves_en: str = ""        # optional English translation


@dataclass
class Lane:
    key: str
    name: str
    name_en: str = ""


@dataclass
class Trend:
    """Citation activity of the center paper."""
    bins: list[tuple[str, int]] = field(default_factory=list)  # ("2024H1", 12)
    verdict: str = ""          # accelerating | steady | slowing | rising | early
    detail: str = ""           # free text (older files); newer files use the numbers below
    last: int = 0              # citations in the last 12 months
    prev: int = 0              # citations in the 12 months before that
    first: str = ""            # date of the first dated citation
    capped: bool = False       # True when only the first 2000 citations were scanned


@dataclass
class Graph:
    title: str = ""
    title_en: str = ""
    center: str | None = None
    source: str = ""
    generated: str = ""
    summary: str = ""
    summary_en: str = ""
    lanes: list[Lane] = field(default_factory=list)
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    trend: Trend | None = None

    # ---- lookups -------------------------------------------------------
    def node(self, nid: str) -> Node | None:
        for n in self.nodes:
            if n.id == nid:
                return n
        return None

    def by_id(self) -> dict[str, Node]:
        return {n.id: n for n in self.nodes}

    def parents(self, nid: str) -> list[Edge]:
        return [e for e in self.edges if e.dst == nid]

    def children(self, nid: str) -> list[Edge]:
        return [e for e in self.edges if e.src == nid]

    def lineage(self, nid: str) -> tuple[set[str], set[str]]:
        """Transitive ancestors and descendants of a node."""
        up: dict[str, list[str]] = {}
        down: dict[str, list[str]] = {}
        for e in self.edges:
            up.setdefault(e.dst, []).append(e.src)
            down.setdefault(e.src, []).append(e.dst)
        return _walk(nid, up), _walk(nid, down)

    def validate(self) -> None:
        ids = [n.id for n in self.nodes]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate node ids")
        known = set(ids)
        self.edges = [e for e in self.edges if e.src in known and e.dst in known and e.src != e.dst]
        seen = set()
        uniq = []
        for e in self.edges:
            if (e.src, e.dst) not in seen:
                seen.add((e.src, e.dst))
                uniq.append(e)
        self.edges = uniq

    # ---- io ------------------------------------------------------------
    def to_dict(self) -> dict:
        d = {
            "schema": SCHEMA,
            "title": self.title,
            "title_en": self.title_en,
            "center": self.center,
            "source": self.source,
            "generated": self.generated,
            "summary": self.summary,
            "summary_en": self.summary_en,
            "lanes": [asdict(l) for l in self.lanes],
            "nodes": [asdict(n) for n in self.nodes],
            "edges": [asdict(e) for e in self.edges],
        }
        if self.trend:
            t = asdict(self.trend)
            t["bins"] = [list(b) for b in self.trend.bins]
            d["trend"] = t
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Graph":
        if d.get("schema") not in (SCHEMA, None):
            raise ValueError(f"unsupported schema: {d.get('schema')}")
        node_fields = Node.__dataclass_fields__.keys()
        edge_fields = Edge.__dataclass_fields__.keys()
        lane_fields = Lane.__dataclass_fields__.keys()
        g = cls(
            title=d.get("title", ""),
            title_en=d.get("title_en", ""),
            center=d.get("center"),
            source=d.get("source", ""),
            generated=d.get("generated", ""),
            summary=d.get("summary", ""),
            summary_en=d.get("summary_en", ""),
            lanes=[Lane(**{k: v for k, v in l.items() if k in lane_fields}) for l in d.get("lanes", [])],
            nodes=[Node(**{k: v for k, v in n.items() if k in node_fields}) for n in d.get("nodes", [])],
            edges=[Edge(**{k: v for k, v in e.items() if k in edge_fields}) for e in d.get("edges", [])],
        )
        t = d.get("trend")
        if t:
            g.trend = Trend(bins=[(str(a), int(b)) for a, b in t.get("bins", [])],
                            verdict=t.get("verdict", ""), detail=t.get("detail", ""),
                            last=int(t.get("last", 0)), prev=int(t.get("prev", 0)),
                            first=t.get("first", ""), capped=bool(t.get("capped", False)))
        g.validate()
        return g

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=1), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "Graph":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def _walk(start: str, adj: dict[str, list[str]]) -> set[str]:
    seen: set[str] = set()
    stack = [start]
    while stack:
        for nxt in adj.get(stack.pop(), []):
            if nxt not in seen and nxt != start:
                seen.add(nxt)
                stack.append(nxt)
    return seen


def short_label(title: str, limit: int = 28) -> str:
    """A compact star label: the part before a colon when it is short (the
    method name, by convention), otherwise the first few words."""
    title = " ".join(title.split())
    head = title.split(":", 1)[0].strip()
    if ":" in title and 0 < len(head) <= limit:
        return head
    words: list[str] = []
    for w in title.split():
        if len(" ".join(words + [w])) > limit:
            break
        words.append(w)
    return (" ".join(words) or title[:limit]) + ("…" if len(title) > len(" ".join(words)) else "")


def fractional_year(date: str | None, year: int | None) -> float:
    """'2023-08-08' -> 2023.598; falls back to mid-year when only a year is known."""
    if date:
        try:
            y, m, dd = (int(x) for x in date[:10].split("-"))
            import datetime as _dt
            doy = _dt.date(y, m, dd).timetuple().tm_yday
            return round(y + (doy - 1) / 366, 4)
        except (ValueError, TypeError):
            pass
    return float(year) + 0.5 if year else 0.0


def transitive_reduce(edges: Iterable[Edge], keep: set[str]) -> list[Edge]:
    """Drop an edge u->w when a longer path u->...->w exists, unless the edge
    touches a node in `keep` (the center keeps all of its direct links)."""
    edges = list(edges)
    adj: dict[str, set[str]] = {}
    for e in edges:
        adj.setdefault(e.src, set()).add(e.dst)

    def reachable_without(u: str, w: str) -> bool:
        stack = [v for v in adj.get(u, ()) if v != w]
        seen = set(stack)
        while stack:
            v = stack.pop()
            if v == w:
                return True
            for x in adj.get(v, ()):
                if x not in seen:
                    seen.add(x)
                    stack.append(x)
        return False

    out = []
    for e in edges:
        if e.src in keep or e.dst in keep or not reachable_without(e.src, e.dst):
            out.append(e)
    return out
