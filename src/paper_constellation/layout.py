"""Place papers on the chart: time runs left to right, branches are rows.

The time axis blends linear time with rank order, so a 1995 classic does not
push the crowded recent years into a corner.
"""
from __future__ import annotations

import bisect
import math
from dataclasses import dataclass, field

from .i18n import tr
from .model import ANCESTOR, CENTER, Graph, Lane

LANE_H = 92.0
SLOT = 24.0


@dataclass
class Layout:
    pos: dict[str, tuple[float, float]] = field(default_factory=dict)
    lanes: list[tuple[float, Lane]] = field(default_factory=list)   # (y, lane)
    ticks: list[tuple[float, str]] = field(default_factory=list)    # (x, label)
    width: float = 0.0

    def x_of_year(self, year: float) -> float:
        return _interp(year, self._yx_years, self._yx_xs)

    _yx_years: list[float] = field(default_factory=list)
    _yx_xs: list[float] = field(default_factory=list)


def _interp(v: float, xs: list[float], ys: list[float]) -> float:
    if not xs:
        return 0.0
    if len(xs) == 1:
        return ys[0]
    i = bisect.bisect_left(xs, v)
    if i <= 0:
        i = 1
    elif i >= len(xs):
        i = len(xs) - 1
    x0, x1, y0, y1 = xs[i - 1], xs[i], ys[i - 1], ys[i]
    if x1 == x0:
        return y0
    return y0 + (v - x0) * (y1 - y0) / (x1 - x0)


def label_width(text: str) -> float:
    # CJK glyphs are about twice as wide as Latin ones at the same size
    return sum(13 if ord(c) > 0x2E80 else 7 for c in text) + 22


def compute(g: Graph) -> Layout:
    lay = Layout()
    nodes = [n for n in g.nodes if n.year]
    if not nodes:
        return lay

    # ---- x: blend of linear time and rank --------------------------------
    years = sorted({round(n.year, 3) for n in nodes})
    span = max(years[-1] - years[0], 1e-6)
    width = max(900.0, 70.0 * len(years))
    xs = []
    for i, y in enumerate(years):
        lin = (y - years[0]) / span
        rank = i / max(len(years) - 1, 1)
        xs.append(width * (0.35 * lin + 0.65 * rank))
    lay._yx_years, lay._yx_xs, lay.width = years, xs, width

    # ---- rows -------------------------------------------------------------
    lanes = list(g.lanes)
    if lanes:
        known = {l.key for l in lanes}
        if any(n.lane not in known for n in nodes):
            lanes.append(Lane("other", tr("lane.other")))
        lane_of = {n.id: (n.lane if n.lane in known else "other") for n in nodes}
        expand_dir = {l.key: 0 for l in lanes}       # alternate up/down
    else:
        # no branches known: predecessors above the center, successors below
        lanes = [Lane("ancestors", tr("lane.ancestors")), Lane("center", tr("lane.center")),
                 Lane("descendants", tr("lane.descendants"))]
        lane_of = {n.id: ("center" if n.kind == CENTER or n.id == g.center
                          else "ancestors" if n.kind == ANCESTOR else "descendants") for n in nodes}
        expand_dir = {"ancestors": -1, "center": 0, "descendants": 1}

    # greedy slotting inside each lane so labels do not collide
    rows: dict[str, list[float]] = {}   # lane -> list of slot right edges
    offsets_of: dict[str, list[float]] = {}
    placed_y: dict[str, list[float]] = {}
    for n in sorted(nodes, key=lambda n: n.year):
        key = lane_of[n.id]
        x = lay.x_of_year(round(n.year, 3))
        w = label_width(n.display_label())
        ends = rows.setdefault(key, [])
        offs = offsets_of.setdefault(key, [])
        slot = next((i for i, e in enumerate(ends) if e < x - 8), None)
        if slot is None:
            slot = len(ends)
            ends.append(-math.inf)
            d = expand_dir[key]
            if d == 0:
                k = (slot + 1) // 2
                offs.append(0.0 if slot == 0 else (k * SLOT if slot % 2 else -k * SLOT))
            else:
                offs.append(d * slot * SLOT)
        ends[slot] = x + w
        lay.pos[n.id] = (x, offs[slot])
        placed_y.setdefault(key, []).append(offs[slot])

    # stack lanes, sizing each to its own spread
    prev_base = prev_bottom = None
    for lane in lanes:
        ys = placed_y.get(lane.key)
        if not ys:
            continue
        top, bottom = min(ys), max(ys)
        if prev_base is None:
            base = 0.0
        else:
            base = max(prev_base + LANE_H, prev_bottom + 0.55 * LANE_H - top)
        for nid, (x, oy) in list(lay.pos.items()):
            if lane_of.get(nid) == lane.key:
                lay.pos[nid] = (x, base + oy)
        lay.lanes.append((base, lane))
        prev_base, prev_bottom = base, base + bottom

    # ---- ticks: one per year (or half-year when there is room) -----------
    lo, hi = math.floor(years[0]), math.ceil(years[-1])
    cands = []
    for yr in range(lo, hi + 1):
        cands.append((float(yr), str(yr)))
        cands.append((yr + 0.5, f"{yr}.07"))
    for v, text in cands:
        if v < years[0] - 0.5 or v > years[-1] + 0.5:
            continue
        lay.ticks.append((lay.x_of_year(v), text))  # the view thins these out by on-screen spacing
    return lay
