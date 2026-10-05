"""Citation activity of a paper: is it trending, steady or fading?"""
from __future__ import annotations

import datetime as dt

from .model import Trend


def _date_of(p: dict) -> dt.date | None:
    d = p.get("publicationDate")
    if d:
        try:
            return dt.date.fromisoformat(d[:10])
        except ValueError:
            return None
    return None


def compute(citations: list[dict], today: dt.date) -> Trend:
    """`citations` are link dicts with a "paper" key (the citing paper)."""
    dated = [d for d in (_date_of(c.get("paper") or {}) for c in citations) if d and d <= today]
    counts: dict[str, int] = {}
    for d in dated:
        key = f"{d.year}H{1 if d.month <= 6 else 2}"
        counts[key] = counts.get(key, 0) + 1

    bins: list[tuple[str, int]] = []
    if dated:
        y, h = min(dated).year, 1 if min(dated).month <= 6 else 2
        end = (today.year, 1 if today.month <= 6 else 2)
        while (y, h) <= end:
            bins.append((f"{y}H{h}", counts.get(f"{y}H{h}", 0)))
            y, h = (y, 2) if h == 1 else (y + 1, 1)

    one_year = dt.timedelta(days=365)
    last = sum(1 for d in dated if today - one_year < d <= today)
    prev = sum(1 for d in dated if today - 2 * one_year < d <= today - one_year)
    first = min(dated) if dated else None
    young = first is not None and (today - first).days < 540

    if not dated:
        verdict = ""
    elif young:
        verdict = "rising" if last >= 20 else "early"
    else:
        ratio = last / prev if prev else float("inf")
        verdict = "accelerating" if ratio > 1.3 else "steady" if ratio >= 0.8 else "slowing"
    return Trend(bins=bins, verdict=verdict, last=last, prev=prev,
                 first=first.isoformat() if first else "", capped=len(citations) >= 2000)


def describe(t: Trend) -> tuple[str, str]:
    """(verdict, detail) in the current UI language."""
    from .i18n import STRINGS, tr
    verdict = tr(f"verdict.{t.verdict}") if f"verdict.{t.verdict}" in STRINGS else t.verdict
    if not t.bins and not t.detail:
        return verdict, tr("trend.none")
    if t.detail and not (t.last or t.prev or t.first):
        return verdict, t.detail              # written by an older version
    if t.verdict in ("rising", "early"):
        detail = tr("trend.young", last=t.last, first=t.first)
    else:
        detail = tr("trend.detail", last=t.last, prev=t.prev)
    return verdict, detail + (tr("trend.capped") if t.capped else "")
