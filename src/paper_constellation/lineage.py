"""Build a lineage constellation around one paper from citation data.

Selection is deliberately conservative: a constellation that shows 40 papers
that matter is more useful than one that shows 400 that were merely cited.
"""
from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass
from typing import Callable

from . import ids, trend
from .i18n import InputError, tr
from .model import (ANCESTOR, CENTER, DESCENDANT, Edge, Graph, Node, fractional_year,
                    short_label, transitive_reduce)
from .s2 import PaperSource

Progress = Callable[[str], None]


@dataclass
class Options:
    ancestors: int = 12          # direct predecessors kept
    descendants: int = 16        # direct successors kept
    expand: int = 5              # how many of those get their own neighbours fetched
    per_expand: int = 2          # neighbours kept per expanded paper
    citation_pages: int = 2000   # how many citing papers to scan for the center


def node_from_s2(p: dict) -> Node:
    ext = p.get("externalIds") or {}
    authors = [a.get("name", "") for a in (p.get("authors") or []) if a.get("name")]
    author = (authors[0] + (" et al." if len(authors) > 1 else "")) if authors else ""
    tldr = (p.get("tldr") or {}).get("text", "") if isinstance(p.get("tldr"), dict) else ""
    pid = p.get("paperId") or ""
    return Node(
        id=pid,
        title=" ".join((p.get("title") or "").split()),
        label=short_label(p.get("title") or ""),
        authors=author,
        year=fractional_year(p.get("publicationDate"), p.get("year")),
        date=p.get("publicationDate") or "",
        venue=p.get("venue") or "",
        arxiv=ext.get("ArXiv", "") or "",
        doi=ext.get("DOI", "") or "",
        url=p.get("url") or (f"https://www.semanticscholar.org/paper/{pid}" if pid else ""),
        abstract=p.get("abstract") or "",
        tldr=tldr,
        citation_count=int(p.get("citationCount") or 0),
        influential_count=int(p.get("influentialCitationCount") or 0),
    )


def _score(link: dict, recency_bonus: bool = False, today: float | None = None) -> float:
    p = link.get("paper") or {}
    s = math.log10(1 + (p.get("citationCount") or 0))
    s += 0.6 * math.log10(1 + (p.get("influentialCitationCount") or 0))
    if link.get("isInfluential"):
        s += 3.0
    intents = link.get("intents") or []
    if "methodology" in intents:
        s += 1.5
    s += 0.25 * min(len(link.get("contexts") or []), 6)
    if recency_bonus and today:
        y = fractional_year(p.get("publicationDate"), p.get("year"))
        if y and today - y < 1.5:  # young papers have not had time to collect citations
            s += 1.2
    return s


def _usable(link: dict) -> bool:
    p = link.get("paper") or {}
    return bool(p.get("paperId") and p.get("title") and (p.get("year") or p.get("publicationDate")))


def _top(links: list[dict], k: int, exclude: set[str], **kw) -> list[dict]:
    seen = set(exclude)
    out = []
    for l in sorted((l for l in links if _usable(l)), key=lambda l: _score(l, **kw), reverse=True):
        pid = l["paper"]["paperId"]
        if pid in seen:
            continue
        seen.add(pid)
        out.append(l)
        if len(out) == k:
            break
    return out


def build(query: str, source: PaperSource, progress: Progress = lambda m: None,
          opts: Options | None = None, today: dt.date | None = None) -> tuple[Graph, dict]:
    """Return the graph and the citation contexts per edge (src, dst) -> [sentences],
    which the optional LLM pass uses to explain each link."""
    opts = opts or Options()
    today = today or dt.date.today()
    now = fractional_year(today.isoformat(), None)
    ref = ids.parse(query)

    progress(tr("progress.finding", ref=ref.display))
    center_p = source.match_title(ref.query) if ref.query else source.paper(ref.s2_id)
    center = node_from_s2(center_p)
    if not center.id:
        raise InputError("err.unreadable")
    center.kind = CENTER
    cid = center.id

    nodes: dict[str, Node] = {cid: center}
    contexts: dict[tuple[str, str], list[str]] = {}
    influential: set[tuple[str, str]] = set()

    def add(link: dict, src: str, dst: str, kind: str) -> str:
        n = node_from_s2(link["paper"])
        n.kind = kind
        nodes.setdefault(n.id, n)
        if link.get("contexts"):
            contexts[(src, dst)] = [c for c in link["contexts"] if c][:4]
        if link.get("isInfluential"):
            influential.add((src, dst))
        return n.id

    progress(tr("progress.refs"))
    refs = source.references(cid)
    anc = _top(refs, opts.ancestors, {cid})
    anc_ids = [add(l, l["paper"]["paperId"], cid, ANCESTOR) for l in anc]

    for i, aid in enumerate(anc_ids[:opts.expand]):
        progress(tr("progress.roots", i=i + 1, n=min(opts.expand, len(anc_ids))))
        for l in _top(source.references(aid, 500), opts.per_expand, set(nodes)):
            add(l, l["paper"]["paperId"], aid, ANCESTOR)

    progress(tr("progress.cites"))
    cites = source.citations(cid, opts.citation_pages)
    t = trend.compute(cites, today)
    desc = _top(cites, opts.descendants, set(nodes), recency_bonus=True, today=now)
    desc_ids = [add(l, cid, l["paper"]["paperId"], DESCENDANT) for l in desc]

    for i, did in enumerate(desc_ids[:opts.expand]):
        progress(tr("progress.desc", i=i + 1, n=min(opts.expand, len(desc_ids))))
        for l in _top(source.citations(did, 500), opts.per_expand, set(nodes), recency_bonus=True, today=now):
            add(l, did, l["paper"]["paperId"], DESCENDANT)

    progress(tr("progress.links"))
    ref_map = source.reference_ids(list(nodes))
    edges: dict[tuple[str, str], Edge] = {}
    for dst, srcs in ref_map.items():
        for src in srcs:
            if src in nodes and src != dst:
                edges[(src, dst)] = Edge(src, dst, influential=(src, dst) in influential)
    for (src, dst) in list(contexts) + list(influential):  # links we saw directly
        edges.setdefault((src, dst), Edge(src, dst, influential=(src, dst) in influential))
    for aid in anc_ids:
        edges.setdefault((aid, cid), Edge(aid, cid, influential=(aid, cid) in influential))
    for did in desc_ids:
        edges.setdefault((cid, did), Edge(cid, did, influential=(cid, did) in influential))

    # citations point backwards in time; drop anything that would point forwards
    elist = [e for e in edges.values() if nodes[e.src].year <= nodes[e.dst].year + 0.25]
    elist = transitive_reduce(elist, keep={cid})

    connected = {e.src for e in elist} | {e.dst for e in elist} | {cid}
    g = Graph(
        title=center.display_label(),
        center=cid,
        source="semantic-scholar",
        generated=dt.datetime.now().isoformat(timespec="seconds"),
        nodes=[n for n in nodes.values() if n.id in connected],
        edges=elist,
        trend=t,
    )
    up, down = g.lineage(cid)
    for n in g.nodes:
        if n.id == cid:
            continue
        n.kind = ANCESTOR if n.id in up else DESCENDANT if n.id in down else (ANCESTOR if n.year < center.year else DESCENDANT)
        n.status = heuristic_status(n, now)
    center.status = heuristic_status(center, now, t)
    g.validate()
    return g, contexts


def heuristic_status(n: Node, now: float, t: "trend.Trend | None" = None) -> str:
    age = now - n.year if n.year else 99
    if age < 1.0:
        return "recent"
    if t is not None and t.verdict in ("accelerating", "steady", "rising"):
        return "active"
    if n.citation_count >= 1500 or (n.kind == ANCESTOR and n.influential_count >= 150):
        return "foundation"
    return ""
