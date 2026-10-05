"""Optional LLM pass: explain each link and group papers into research branches.

Uses the Anthropic Messages API over plain HTTPS (no SDK dependency). Without an
API key the constellation still works; links simply carry no explanation.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

from . import i18n
from .i18n import LocalizedError
from .net import ssl_context
from .model import Graph, Lane, STATUSES

API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-sonnet-5-5"


class AnnotateError(LocalizedError):
    pass


SYSTEM = """You map the intellectual lineage of research papers for researchers.
You receive one CENTER paper, candidate papers around it (title, year, abstract)
and the citation links between them, sometimes with the sentence in which the
later paper cites the earlier one.

Your job:
1. Keep only papers that are a real methodological step in the lineage. Drop
   datasets, generic tools and papers cited only in passing. Never drop CENTER.
   Keep at most 40 papers.
2. For every kept link (src = earlier paper, dst = later paper) write `solves`:
   the problem dst fixed or the capability it added on top of src, in {LANG},
   at most 45 characters, concrete (e.g. "{EXAMPLE}").
   Drop links that are not a real "builds on" relation.
3. Group papers into 3-8 research branches (`lanes`) with short {LANG} names,
   ordered so related branches sit next to each other; put CENTER's branch in
   the middle.
4. For each kept paper give: a short `label` (the method name if it has one,
   max 24 chars), `lane`, `status` (one of foundation | active | superseded |
   recent | "" when unsure; superseded means later work in this graph solves
   the same problem better and has replaced it), and `note`: one {LANG}
   sentence on its key idea.
5. `summary`: 2-3 {LANG} sentences on where CENTER stands today: what problem
   it answered, which branches grew from it, and which are most active.

Answer with JSON only, no prose:
{"lanes":[{"key":"...","name":"..."}],
 "papers":[{"id":"...","label":"...","lane":"...","status":"...","note":"..."}],
 "links":[{"src":"...","dst":"...","solves":"..."}],
 "summary":"..."}"""


def system_prompt(lang: str | None = None) -> str:
    """The instructions, asking for output in the UI language."""
    lang = lang or i18n.LANG
    if lang == "ko":
        return SYSTEM.replace("{LANG}", "Korean").replace("{EXAMPLE}", "느린 광선 행진 렌더링을 래스터화로 대체")
    return SYSTEM.replace("{LANG}", "English").replace("{EXAMPLE}", "replaces slow ray marching with rasterisation")


def _payload(g: Graph, contexts: dict[tuple[str, str], list[str]]) -> str:
    papers = []
    for n in g.nodes:
        papers.append({
            "id": n.id,
            "role": "CENTER" if n.id == g.center else n.kind,
            "title": n.title,
            "year": int(n.year) if n.year else None,
            "citations": n.citation_count,
            "abstract": (n.tldr or n.abstract or "")[:550],
        })
    links = []
    for e in g.edges:
        item = {"src": e.src, "dst": e.dst}
        ctx = contexts.get((e.src, e.dst))
        if ctx:
            item["context"] = " | ".join(c[:220] for c in ctx[:2])
        links.append(item)
    return json.dumps({"papers": papers, "links": links}, ensure_ascii=False)


def _extract_json(text: str) -> dict:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    if fence:
        text = fence.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < 0:
        raise AnnotateError("llm.no_json")
    return json.loads(text[start:end + 1])


def call_claude(system: str, user: str, api_key: str, model: str, timeout: float = 180) -> str:
    body = json.dumps({
        "model": model,
        "max_tokens": 8000,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }).encode()
    req = urllib.request.Request(API_URL, data=body, method="POST", headers={
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_context()) as r:
            out = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        if e.code == 401:
            raise AnnotateError("llm.bad_key") from None
        raise AnnotateError("llm.http", code=e.code, detail=detail) from None
    except urllib.error.URLError as e:
        raise AnnotateError("llm.connect", reason=e.reason) from None
    return "".join(b.get("text", "") for b in out.get("content", []) if b.get("type") == "text")


def annotate(g: Graph, contexts: dict[tuple[str, str], list[str]], api_key: str | None = None,
             model: str | None = None, caller=call_claude) -> Graph:
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise AnnotateError("llm.no_key")
    model = model or os.environ.get("PC_MODEL") or DEFAULT_MODEL
    data = _extract_json(caller(system_prompt(), _payload(g, contexts), api_key, model))
    return apply(g, data)


def apply(g: Graph, data: dict) -> Graph:
    """Merge an LLM answer into the graph, trusting only ids that exist."""
    by_id = g.by_id()
    papers = {p.get("id"): p for p in data.get("papers", []) if p.get("id") in by_id}
    if g.center:
        papers.setdefault(g.center, {"id": g.center})
    if len(papers) >= 3:  # an answer that keeps almost nothing is a failed answer
        g.nodes = [n for n in g.nodes if n.id in papers]

    lanes = [Lane(str(l["key"]), str(l["name"])) for l in data.get("lanes", []) if l.get("key") and l.get("name")]
    lane_keys = {l.key for l in lanes}
    for n in g.nodes:
        p = papers.get(n.id, {})
        if p.get("label"):
            n.label = str(p["label"])[:40]
        if p.get("lane") in lane_keys:
            n.lane = p["lane"]
        if p.get("status") in STATUSES or p.get("status") == "":
            n.status = p.get("status") or n.status
        if p.get("note"):
            n.note = str(p["note"])
    if lanes:
        g.lanes = lanes
        center_lane = next((n.lane for n in g.nodes if n.id == g.center), "")
        for n in g.nodes:
            if not n.lane:
                n.lane = center_lane or lanes[0].key

    keep = {n.id for n in g.nodes}
    solves = {(l.get("src"), l.get("dst")): str(l.get("solves", ""))[:80] for l in data.get("links", [])}
    edges = []
    for e in g.edges:
        if e.src not in keep or e.dst not in keep:
            continue
        if solves and (e.src, e.dst) not in solves and g.center not in (e.src, e.dst):
            continue  # the model judged this link incidental
        e.solves = solves.get((e.src, e.dst), e.solves)
        edges.append(e)
    g.edges = edges
    linked = {e.src for e in edges} | {e.dst for e in edges} | {g.center}
    g.nodes = [n for n in g.nodes if n.id in linked]
    if data.get("summary"):
        g.summary = str(data["summary"])
    g.source = g.source + "+llm" if g.source and "+llm" not in g.source else g.source
    g.validate()
    return g
