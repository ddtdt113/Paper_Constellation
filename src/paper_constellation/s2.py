"""Minimal Semantic Scholar Graph API client (stdlib only, disk-cached).

Docs: https://api.semanticscholar.org/api-docs/graph
Works without a key (shared rate limit); set S2_API_KEY for a personal one.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Protocol

from .i18n import LocalizedError
from .net import ssl_context

BASE = "https://api.semanticscholar.org/graph/v1"
PAPER_FIELDS = ("paperId,externalIds,title,abstract,year,publicationDate,venue,authors,"
                "citationCount,influentialCitationCount,tldr,url")
LINK_FIELDS = ("contexts,intents,isInfluential,paperId,externalIds,title,abstract,year,"
               "publicationDate,venue,authors,citationCount,influentialCitationCount")
CACHE_TTL = 7 * 24 * 3600


class S2Error(LocalizedError):
    pass


class PaperSource(Protocol):
    def paper(self, pid: str) -> dict: ...
    def match_title(self, query: str) -> dict: ...
    def references(self, pid: str, limit: int = 1000) -> list[dict]: ...
    def citations(self, pid: str, limit: int = 2000) -> list[dict]: ...
    def reference_ids(self, pids: list[str]) -> dict[str, set[str]]: ...


def default_cache_dir() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "paper-constellation" / "s2"


class SemanticScholar:
    def __init__(self, api_key: str | None = None, cache_dir: Path | None = None,
                 min_interval: float = 1.05, timeout: float = 30.0):
        self.api_key = api_key if api_key is not None else os.environ.get("S2_API_KEY", "")
        self.cache_dir = cache_dir or default_cache_dir()
        self.min_interval = min_interval
        self.timeout = timeout
        self._last = 0.0

    # ---- transport -----------------------------------------------------
    def _request(self, method: str, path: str, params: dict | None = None, body: Any = None) -> Any:
        url = BASE + path + ("?" + urllib.parse.urlencode(params) if params else "")
        key = hashlib.sha1((method + url + json.dumps(body, sort_keys=True)).encode()).hexdigest()
        cpath = self.cache_dir / f"{key}.json"
        if cpath.exists() and time.time() - cpath.stat().st_mtime < CACHE_TTL:
            try:
                return json.loads(cpath.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                pass

        headers = {"User-Agent": "paper-constellation (+https://github.com/)", "Accept": "application/json"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"

        delay = 2.0
        for attempt in range(6):
            wait = self.min_interval - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=self.timeout, context=ssl_context()) as r:
                    out = json.loads(r.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    raise S2Error("s2.not_found") from None
                if e.code in (429, 500, 502, 503, 504) and attempt < 5:
                    time.sleep(delay)
                    delay *= 2
                    continue
                if e.code == 429:
                    raise S2Error("s2.rate_limited") from None
                detail = e.read().decode("utf-8", "replace")[:200]
                raise S2Error("s2.http", code=e.code, detail=detail) from None
            except urllib.error.URLError as e:
                if attempt < 2:
                    time.sleep(delay)
                    continue
                raise S2Error("s2.connect", reason=e.reason) from None
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            cpath.write_text(json.dumps(out), encoding="utf-8")
        except OSError:
            pass
        return out

    # ---- endpoints -----------------------------------------------------
    def paper(self, pid: str) -> dict:
        return self._request("GET", f"/paper/{urllib.parse.quote(pid, safe=':/')}", {"fields": PAPER_FIELDS})

    def match_title(self, query: str) -> dict:
        out = self._request("GET", "/paper/search/match", {"query": query, "fields": PAPER_FIELDS})
        data = out.get("data") or []
        if not data:
            raise S2Error("s2.no_title_match")
        return data[0]

    def _links(self, pid: str, kind: str, limit: int) -> list[dict]:
        items: list[dict] = []
        offset = 0
        page = min(1000, limit)
        while offset < limit:
            out = self._request("GET", f"/paper/{urllib.parse.quote(pid, safe=':/')}/{kind}",
                                {"fields": LINK_FIELDS, "limit": page, "offset": offset})
            data = out.get("data") or []
            items.extend(data)
            nxt = out.get("next")
            if not data or nxt is None or offset + page >= 9999:
                break
            offset = nxt
        return items[:limit]

    def references(self, pid: str, limit: int = 1000) -> list[dict]:
        return [{**x, "paper": x.get("citedPaper") or {}} for x in self._links(pid, "references", limit)]

    def citations(self, pid: str, limit: int = 2000) -> list[dict]:
        return [{**x, "paper": x.get("citingPaper") or {}} for x in self._links(pid, "citations", limit)]

    def reference_ids(self, pids: list[str]) -> dict[str, set[str]]:
        """paperId -> ids of the papers it references, for many papers at once."""
        result: dict[str, set[str]] = {}
        for i in range(0, len(pids), 400):
            chunk = pids[i:i + 400]
            try:
                out = self._request("POST", "/paper/batch", {"fields": "paperId,references.paperId"}, {"ids": chunk})
                for pid, p in zip(chunk, out):
                    if p:
                        result[pid] = {r["paperId"] for r in p.get("references") or [] if r.get("paperId")}
            except S2Error:
                for pid in chunk:  # slower fallback: one request per paper
                    result[pid] = {r["paper"].get("paperId") for r in self.references(pid, 1000)
                                   if r["paper"].get("paperId")}
        return result
