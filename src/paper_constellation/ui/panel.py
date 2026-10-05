"""Side panel: what the selected paper is, where it stands, and its lineage."""
from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QPainter
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea,
                               QSizePolicy, QVBoxLayout, QWidget)

from .. import trend as trend_mod
from ..i18n import pick, tr
from ..model import STATUSES, Graph, Node, Trend
from . import theme


def _label(text: str = "", name: str = "", wrap: bool = True) -> QLabel:
    l = QLabel(text)
    if name:
        l.setObjectName(name)
    l.setWordWrap(wrap)
    l.setTextInteractionFlags(Qt.TextSelectableByMouse)
    return l


def _year(n: Node) -> str:
    if n.date:
        return n.date[:7].replace("-", ".")
    return str(int(n.year)) if n.year else ""


class ClickLabel(QLabel):
    """A wrapping, clickable row (QPushButton text cannot wrap)."""
    clicked = Signal()

    def __init__(self, text: str):
        super().__init__(text)
        self.setObjectName("rel")
        self.setWordWrap(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.rect().contains(e.position().toPoint()):
            self.clicked.emit()

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            self.clicked.emit()
        else:
            super().keyPressEvent(e)


class Sparkline(QWidget):
    """Citations per half-year, last bin emphasised."""

    def __init__(self, bins: list[tuple[str, int]]):
        super().__init__()
        self.bins = bins[-12:]
        self.setMinimumHeight(64)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def sizeHint(self):
        return QSize(240, 64)

    def paintEvent(self, e):
        if not self.bins:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height() - 16
        top = max(c for _, c in self.bins) or 1
        n = len(self.bins)
        bw = w / n
        for i, (key, c) in enumerate(self.bins):
            bh = max(2.0, (h - 4) * c / top)
            col = QColor(theme.FUTURE)
            col.setAlpha(255 if i == n - 1 else 120)
            p.setPen(Qt.NoPen)
            p.setBrush(col)
            p.drawRoundedRect(QRectF(i * bw + 2, h - bh, bw - 4, bh), 2, 2)
        p.setPen(theme.MUTED)
        f = p.font()
        f.setPointSizeF(8.5)
        p.setFont(f)
        p.drawText(QRectF(0, h + 2, w / 2, 14), Qt.AlignLeft, self.bins[0][0])
        p.drawText(QRectF(w / 2, h + 2, w / 2, 14), Qt.AlignRight, f"{self.bins[-1][0]} · {self.bins[-1][1]}")
        p.end()


class DetailPanel(QScrollArea):
    jumpTo = Signal(str)        # select another star
    expand = Signal(str)        # build a new constellation around this paper

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setMinimumWidth(300)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.graph: Graph | None = None
        self.current: str | None = None
        self._clear()

    def _clear(self):
        # a fresh body each time: the scroll area deletes the old one immediately
        self.body = QWidget()
        self.body.setObjectName("panelBody")
        self.lay = QVBoxLayout(self.body)
        self.lay.setContentsMargins(18, 18, 18, 18)
        self.lay.setSpacing(10)
        self.setWidget(self.body)

    def refresh(self) -> None:
        """Re-render what is shown (after a language switch)."""
        if self.graph and self.current:
            self.show_node(self.graph, self.current)
        else:
            self.show_overview(self.graph)

    # ---- overview when nothing is selected -----------------------------------
    def show_overview(self, g: Graph | None) -> None:
        self.graph, self.current = g, None
        self._clear()
        if not g:
            return
        self.lay.addWidget(_label(tr("panel.overview"), "section"))
        self.lay.addWidget(_label(pick(g.title, g.title_en) or tr("panel.untitled"), "title"))
        n_e = sum(1 for e in g.edges if e.solves)
        meta = tr("panel.meta", n=len(g.nodes), m=len(g.edges)) + (tr("panel.meta_notes", k=n_e) if n_e else "")
        self.lay.addWidget(_label(meta, "muted"))
        summary = pick(g.summary, g.summary_en)
        if summary:
            self.lay.addWidget(_label(summary))
        if g.center and g.trend and g.trend.bins:
            self._trend(g.trend)
        self.lay.addWidget(_label(tr("panel.hint"), "muted"))
        self.lay.addStretch(1)

    def _trend(self, t: Trend):
        verdict_text, detail = trend_mod.describe(t)
        self.lay.addWidget(_label(tr("trend.title"), "section"))
        row = QHBoxLayout()
        verdict = _label(verdict_text or "-", wrap=False)
        verdict.setStyleSheet(f"color:{theme.FUTURE.name()}; font-size:15px; font-weight:600;")
        row.addWidget(verdict)
        row.addStretch(1)
        self.lay.addLayout(row)
        self.lay.addWidget(Sparkline(t.bins))
        if detail:
            self.lay.addWidget(_label(detail, "muted"))

    # ---- one paper -----------------------------------------------------------
    def show_node(self, g: Graph, nid: str) -> None:
        self.graph, self.current = g, nid
        n = g.node(nid)
        self._clear()
        if not n:
            return
        cat = f"arXiv {n.arxiv}" if n.arxiv else (f"DOI {n.doi}" if n.doi else tr("panel.paper"))
        lane = next((pick(l.name, l.name_en) for l in g.lanes if l.key == n.lane), "")
        top = QHBoxLayout()
        top.addWidget(_label(cat, "muted", wrap=False))
        top.addStretch(1)
        if lane:
            top.addWidget(_label(lane, "muted", wrap=False))
        self.lay.addLayout(top)
        self.lay.addWidget(_label(n.display_label(), "title"))
        if n.title and n.title != n.display_label():
            self.lay.addWidget(_label(n.title))
        meta = " · ".join(x for x in [n.authors, n.venue, _year(n),
                                      tr("panel.citations", n=f"{n.citation_count:,}") if n.citation_count else ""] if x)
        if meta:
            self.lay.addWidget(_label(meta, "muted"))
        if n.status in STATUSES:
            chip = _label(tr(f"status.{n.status}"), wrap=False)
            c = theme.STATUS_COLORS.get(n.status, theme.MUTED)
            chip.setStyleSheet(f"color:{c.name()}; border:1px solid {c.name()}; border-radius:9px; padding:2px 8px;")
            row = QHBoxLayout()
            row.addWidget(chip)
            row.addStretch(1)
            self.lay.addLayout(row)
        text = pick(n.note, n.note_en) or n.tldr
        if text:
            self.lay.addWidget(_label(text))
        if nid == g.center and g.trend and g.trend.bins:
            self._trend(g.trend)
            summary = pick(g.summary, g.summary_en)
            if summary:
                self.lay.addWidget(_label(summary))

        links = QHBoxLayout()

        def link(text, url):
            b = QPushButton(text)
            b.setObjectName("link")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(url)))
            links.addWidget(b)
        if n.arxiv:
            link(tr("link.abstract"), f"https://arxiv.org/abs/{n.arxiv}")
            link(tr("link.pdf"), f"https://arxiv.org/pdf/{n.arxiv}")
        elif n.doi:
            link(tr("link.paper"), f"https://doi.org/{n.doi}")
        if n.url:
            link(tr("link.s2") if "semanticscholar" in n.url else tr("link.find"), n.url)
        links.addStretch(1)
        self.lay.addLayout(links)

        if nid != g.center:
            b = QPushButton(tr("btn.expand"))
            b.setObjectName("primary")
            b.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
            b.setToolTip(tr("btn.expand"))
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda: self.expand.emit(nid))
            self.lay.addWidget(b)

        self._relations(tr("rel.before"), theme.PAST,
                        [(e.src, pick(e.solves, e.solves_en)) for e in g.parents(nid)], g)
        self._relations(tr("rel.after"), theme.FUTURE,
                        [(e.dst, pick(e.solves, e.solves_en)) for e in g.children(nid)], g)
        if n.abstract:
            self.lay.addWidget(_label(tr("panel.abstract"), "section"))
            self.lay.addWidget(_label(n.abstract, "muted"))
        self.lay.addStretch(1)

    def _relations(self, title: str, color: QColor, items: list[tuple[str, str]], g: Graph):
        head = _label(f"<span style='color:{color.name()}'>●</span>&nbsp; {title}", "section")
        head.setTextFormat(Qt.RichText)
        self.lay.addWidget(head)
        by_id = g.by_id()
        items = [(i, s) for i, s in items if i in by_id]
        items.sort(key=lambda t: by_id[t[0]].year)
        if not items:
            self.lay.addWidget(_label(tr("rel.none"), "muted"))
            return
        box = QFrame()
        v = QVBoxLayout(box)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)
        for nid, solves in items:
            n = by_id[nid]
            text = f"{n.display_label()}   {_year(n)}" + (f"\n{solves}" if solves else "")
            b = ClickLabel(text)
            b.setToolTip(n.title)
            b.clicked.connect(lambda i=nid: self.jumpTo.emit(i))
            v.addWidget(b)
        self.lay.addWidget(box)
