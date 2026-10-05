"""Turn whatever the user pastes into a Semantic Scholar paper identifier."""
from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qs, unquote, urlparse

from .i18n import InputError, tr

_NEW_ARXIV = re.compile(r"(\d{4}\.\d{4,5})(v\d+)?")
_OLD_ARXIV = re.compile(r"([a-z\-]+(?:\.[A-Z]{2})?/\d{7})(v\d+)?")
_DOI = re.compile(r"(10\.\d{4,9}/[^\s?#]+)")
_S2_HEX = re.compile(r"\b([0-9a-f]{40})\b")


@dataclass(frozen=True)
class PaperRef:
    """`s2_id` is what the Semantic Scholar API accepts in /paper/{id};
    `query` is set instead when the input is a free-text title."""
    s2_id: str = ""
    query: str = ""
    display: str = ""


def parse(text: str) -> PaperRef:
    raw = (text or "").strip()
    if not raw:
        raise InputError("err.empty_input")

    # bare identifiers
    m = _NEW_ARXIV.fullmatch(raw) or _OLD_ARXIV.fullmatch(raw)
    if m:
        return PaperRef(s2_id=f"arXiv:{m.group(1)}", display=f"arXiv {m.group(1)}")
    if raw.lower().startswith("arxiv:"):
        return parse(raw.split(":", 1)[1])
    if raw.lower().startswith("doi:"):
        raw = raw.split(":", 1)[1].strip()
    m = _DOI.fullmatch(raw)
    if m:
        return PaperRef(s2_id=f"DOI:{m.group(1)}", display=f"DOI {m.group(1)}")
    if _S2_HEX.fullmatch(raw):
        return PaperRef(s2_id=raw, display="Semantic Scholar")

    # URLs
    url = raw if "://" in raw else ("https://" + raw if "/" in raw and "." in raw.split("/")[0] else "")
    if url:
        u = urlparse(url)
        host = u.netloc.lower().removeprefix("www.")
        path = unquote(u.path)
        if host.endswith("arxiv.org") or host.endswith("alphaxiv.org"):
            m = _NEW_ARXIV.search(path) or _OLD_ARXIV.search(path.lstrip("/").split("/", 1)[-1])
            if m:
                return PaperRef(s2_id=f"arXiv:{m.group(1)}", display=f"arXiv {m.group(1)}")
        if host.endswith("doi.org"):
            m = _DOI.search(path.lstrip("/"))
            if m:
                return PaperRef(s2_id=f"DOI:{m.group(1)}", display=f"DOI {m.group(1)}")
        if host.endswith("semanticscholar.org"):
            m = _S2_HEX.search(path)
            if m:
                return PaperRef(s2_id=m.group(1), display="Semantic Scholar")
        if host.endswith("openreview.net"):
            pid = parse_qs(u.query).get("id", [""])[0]
            if pid:
                return PaperRef(s2_id=f"URL:https://openreview.net/forum?id={pid}", display=f"OpenReview {pid}")
        if host.endswith("aclanthology.org"):
            slug = path.strip("/").removesuffix(".pdf")
            if slug:
                return PaperRef(s2_id=f"ACL:{slug}", display=f"ACL {slug}")
        m = _DOI.search(path)  # publisher pages often embed the DOI (ACM, IEEE, Springer)
        if m and host.endswith(("acm.org", "springer.com", "wiley.com", "ieee.org")):
            return PaperRef(s2_id=f"DOI:{m.group(1).removesuffix('.pdf')}", display=f"DOI {m.group(1)}")
        return PaperRef(s2_id=f"URL:{url}", display=host)

    # anything else: treat it as a title
    return PaperRef(query=raw, display=tr("ref.title_search", q=raw))
