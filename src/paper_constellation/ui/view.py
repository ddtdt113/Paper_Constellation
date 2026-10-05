"""The star chart: a QGraphicsView where papers are stars and lineage is drawn as arcs."""
from __future__ import annotations

import datetime as dt
import random

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (QBrush, QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen,
                           QRadialGradient)
from PySide6.QtWidgets import (QGraphicsItem, QGraphicsObject, QGraphicsPathItem,
                               QGraphicsScene, QGraphicsSimpleTextItem, QGraphicsView)

from .. import layout as layout_mod
from ..i18n import pick, tr
from ..model import CENTER, CORE, FOUNDATION, NEW, Graph, Node, fractional_year
from . import theme

BRIGHT = (CENTER, CORE, FOUNDATION)


def radius_for(n: Node, is_center: bool) -> float:
    if is_center or n.kind == CORE:
        return 8.5
    if n.kind == FOUNDATION:
        return 6.0
    if n.kind == NEW or n.status == "recent":
        return 5.0
    # brighter stars for more-cited papers
    c = n.citation_count
    return 4.2 + (1.2 if c > 1000 else 0.6 if c > 200 else 0)


class StarItem(QGraphicsObject):
    clicked = Signal(str)
    activated = Signal(str)

    def __init__(self, node: Node, is_center: bool):
        super().__init__()
        self.node = node
        self.is_center = is_center
        self.r = radius_for(node, is_center)
        self.color = theme.NOVA if (node.kind == NEW or node.status == "recent") else theme.STAR
        self.state = "normal"
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setZValue(2)
        tip = node.title + (f"\n{node.authors}" if node.authors else "") + (f" · {int(node.year)}" if node.year else "")
        self.setToolTip(tip)
        self.label = QGraphicsSimpleTextItem(node.display_label(), self)
        f = QFont()
        f.setPointSizeF(10.5 if not (is_center or node.kind == CORE) else 12.5)
        f.setBold(is_center or node.kind == CORE)
        self.label.setFont(f)
        self.label.setPos(self.r + 6, -self.label.boundingRect().height() / 2)
        self.hovered = False
        self._apply()

    def boundingRect(self) -> QRectF:
        R = self.r * 5
        return QRectF(-R, -R, 2 * R, 2 * R)

    def set_state(self, state: str) -> None:
        if state != self.state:
            self.state = state
            self._apply()
            self.update()

    def _apply(self):
        c = {"selected": theme.FOCUS, "anc": theme.PAST, "desc": theme.FUTURE}.get(self.state, self.color)
        self._draw_color = c
        dim = self.state == "dim"
        self.setOpacity(0.2 if dim else 1.0)
        self.label.setBrush(QBrush(theme.FOCUS if self.state == "selected" else theme.INK))

    def paint(self, p: QPainter, opt, widget=None):
        c = QColor(self._draw_color)
        g = QRadialGradient(QPointF(0, 0), self.r * 4.2)
        glow = QColor(c)
        glow.setAlpha(110 if self.state in ("selected", "anc", "desc") else 70)
        g.setColorAt(0, glow)
        g.setColorAt(1, QColor(0, 0, 0, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(g)
        p.drawEllipse(QPointF(0, 0), self.r * 4.2, self.r * 4.2)
        p.setBrush(c)
        p.drawEllipse(QPointF(0, 0), self.r, self.r)
        if self.is_center or self.node.kind in BRIGHT:
            spike = QColor(c)
            spike.setAlpha(150)
            p.setPen(QPen(spike, 0.9))
            L = self.r * (3.4 if self.is_center or self.node.kind == CORE else 2.4)
            p.drawLine(QPointF(-L, 0), QPointF(L, 0))
            p.drawLine(QPointF(0, -L), QPointF(0, L))
        if self.hovered or self.state == "selected":
            p.setPen(QPen(theme.FOCUS, 1))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QPointF(0, 0), self.r + 5, self.r + 5)

    def hoverEnterEvent(self, e):
        self.hovered = True
        self.update()

    def hoverLeaveEvent(self, e):
        self.hovered = False
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit(self.node.id)
            e.accept()
        else:
            super().mousePressEvent(e)

    def mouseDoubleClickEvent(self, e):
        self.activated.emit(self.node.id)


class EdgeItem(QGraphicsPathItem):
    def __init__(self, src: QPointF, dst: QPointF, solves: str):
        super().__init__()
        path = QPainterPath(src)
        mx = (src.x() + dst.x()) / 2
        path.cubicTo(QPointF(mx, src.y()), QPointF(mx, dst.y()), dst)
        self.setPath(path)
        self.setZValue(0)
        self.mid = path.pointAtPercent(0.5)
        if solves:
            self.setToolTip(solves)
        self.note = None
        self.wants_note = False
        if solves:
            self.note = QGraphicsSimpleTextItem(solves)
            self.note.setFlag(QGraphicsItem.ItemIgnoresTransformations)
            f = QFont()
            f.setPointSizeF(9.5)
            self.note.setFont(f)
            self.note.setZValue(3)
            self.note.setVisible(False)
        self.set_state("normal")

    def set_state(self, state: str, show_note: bool = False) -> None:
        if state == "anc":
            pen = QPen(theme.PAST, 1.7)
        elif state == "desc":
            pen = QPen(theme.FUTURE, 1.7)
        elif state == "dim":
            pen = QPen(QColor(190, 200, 235, 12), 1)
        else:
            pen = QPen(QColor(190, 200, 235, 46), 1)
        pen.setCosmetic(True)
        self.setPen(pen)
        self.wants_note = show_note
        if self.note is not None:
            self.note.setVisible(show_note)
            self.note.setBrush(QBrush(pen.color().lighter(110) if state in ("anc", "desc") else theme.MUTED))


class ConstellationView(QGraphicsView):
    nodeSelected = Signal(str)
    nodeActivated = Signal(str)
    cleared = Signal()
    zoomChanged = Signal(float)   # zoom relative to "fit all", 1.0 = 100%

    MIN_ZOOM, MAX_ZOOM = 0.25, 12.0
    MAX_NOTES = 8   # show "what it solved" on the map only for stars with at most this many links

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QGraphicsView.NoFrame)
        self.setBackgroundBrush(theme.SKY)
        self.graph: Graph | None = None
        self.lay: layout_mod.Layout | None = None
        self.stars: dict[str, StarItem] = {}
        self.edges: list[tuple[str, str, EdgeItem]] = []
        self.selected: str | None = None
        self._press = None
        self._auto_fit = True
        self._fit_k = 1.0
        rnd = random.Random(7)
        self.viewport().grabGesture(Qt.PinchGesture)
        self._bg = [(rnd.random(), rnd.random(), rnd.random() * 1.1 + 0.3, rnd.randint(30, 140)) for _ in range(420)]

    # ---- building --------------------------------------------------------
    def set_graph(self, g: Graph) -> None:
        sc = self.scene()
        sc.clear()
        self.stars.clear()
        self.edges.clear()
        self.selected = None
        self.graph = g
        self.lay = layout_mod.compute(g)
        pos = self.lay.pos
        for e in g.edges:
            if e.src in pos and e.dst in pos:
                item = EdgeItem(QPointF(*pos[e.src]), QPointF(*pos[e.dst]), pick(e.solves, e.solves_en))
                sc.addItem(item)
                if item.note is not None:
                    sc.addItem(item.note)
                    item.note.setPos(item.mid)
                self.edges.append((e.src, e.dst, item))
        for n in g.nodes:
            if n.id not in pos:
                continue
            s = StarItem(n, n.id == g.center)
            s.setPos(*pos[n.id])
            s.clicked.connect(self.select)
            s.activated.connect(self.nodeActivated)
            sc.addItem(s)
            self.stars[n.id] = s
        r = self._content_rect()
        sc.setSceneRect(r.adjusted(-4000, -4000, 4000, 4000))
        self._auto_fit = True
        self.fit()

    def _content_rect(self) -> QRectF:
        if not self.lay or not self.lay.pos:
            return QRectF(0, 0, 100, 100)
        xs = [p[0] for p in self.lay.pos.values()]
        ys = [p[1] for p in self.lay.pos.values()]
        return QRectF(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)

    def fit(self) -> None:
        r = self._content_rect()
        vw, vh = max(self.viewport().width(), 200), max(self.viewport().height(), 200)
        # leave room for the pinned lane names (left), labels (right) and year ticks (bottom)
        # leave room for the pinned lane names, whose width depends on the language
        f = QFont()
        f.setPointSizeF(9.5)
        fm = QFontMetrics(f)
        names = [pick(l.name, l.name_en) for _, l in self.lay.lanes] if self.lay else []
        left = max([200] + [fm.horizontalAdvance(n) + 60 for n in names])
        right, top, bottom = 170, 40, 60
        # stars and labels keep their pixel size, so the axes may scale independently:
        # time fills the width, branches fill the height
        kx = (vw - left - right) / max(r.width(), 1)
        ky = (vh - top - bottom) / max(r.height(), 1)
        kx = max(0.1, min(kx, 1.6))
        ky = max(0.1, min(ky, kx * 2.5, 2.2))
        self.resetTransform()
        self.scale(kx, ky)
        self._fit_k = kx
        cx = r.center().x() + (right - left) / 2 / kx
        cy = r.center().y() + (bottom - top) / 2 / ky
        self.centerOn(cx, cy)
        self._declutter()
        self.zoomChanged.emit(1.0)

    # ---- zoom ------------------------------------------------------------
    def zoom_level(self) -> float:
        return self.transform().m11() / self._fit_k if self._fit_k else 1.0

    def zoom_by(self, factor: float, anchor=None) -> None:
        """Zoom by `factor` around `anchor` (a viewport point), or the view center."""
        level = self.zoom_level()
        factor = max(self.MIN_ZOOM / level, min(factor, self.MAX_ZOOM / level))
        if abs(factor - 1.0) < 1e-4:
            return
        if anchor is None:
            anchor = self.viewport().rect().center()
        before = self.mapToScene(anchor)
        old = self.transformationAnchor()
        self.setTransformationAnchor(QGraphicsView.NoAnchor)
        self.scale(factor, factor)
        after = self.mapToScene(anchor)
        d = after - before
        self.translate(d.x(), d.y())
        self.setTransformationAnchor(old)
        self._auto_fit = False
        self._declutter()
        self.zoomChanged.emit(self.zoom_level())

    def zoom_in(self) -> None:
        self.zoom_by(1.25)

    def zoom_out(self) -> None:
        self.zoom_by(0.8)

    def viewportEvent(self, e):
        if e.type() == QEvent.Gesture:
            g = e.gesture(Qt.PinchGesture)
            if g is not None:
                # other platforms' touch pinch
                c = self.viewport().mapFromGlobal(g.centerPoint().toPoint())
                self.zoom_by(g.scaleFactor(), c)
                return True
        if e.type() == QEvent.NativeGesture and e.gestureType() == Qt.ZoomNativeGesture:
            # macOS trackpad pinch
            self.zoom_by(1.0 + e.value(), e.position().toPoint())
            return True
        return super().viewportEvent(e)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self._auto_fit:
            self.fit()
        else:
            self._declutter()

    def showEvent(self, e):
        super().showEvent(e)
        if self._auto_fit:
            self.fit()

    def _priority(self, nid: str) -> float:
        s = self.stars[nid]
        n = s.node
        if nid == self.selected:
            return 0
        if s.state in ("anc", "desc"):
            base = 10
        elif s.state == "dim":
            base = 1000
        else:
            base = 100
        if s.is_center or n.kind in ("core",):
            return base + 1
        if n.kind == "foundation":
            return base + 2
        if n.kind == "new" or n.status == "recent":
            return base + 3
        return base + 10 - min(n.citation_count, 100000) / 20000

    def _declutter(self) -> None:
        """Hide labels that would overlap a more important one at the current zoom."""
        placed: list = []

        def free(r):
            return not any(r.intersects(q) for q in placed)

        def place_star(nid):
            s = self.stars[nid]
            vp = self.mapFromScene(s.pos())
            br = s.label.boundingRect()
            r = QRectF(vp.x() + s.r + 6, vp.y() - br.height() / 2, br.width(), br.height()).adjusted(-2, -1, 2, 1)
            ok = nid == self.selected or free(r)
            s.label.setVisible(ok)
            if ok:
                placed.append(r)

        order = sorted(self.stars, key=self._priority)
        focus = [i for i in order if self._priority(i) < 100]
        rest = [i for i in order if self._priority(i) >= 100]
        for nid in focus:
            place_star(nid)
        # "what it solved" notes on the selected star's links outrank unrelated labels
        for a, b, e in self.edges:
            if e.note is None or not e.wants_note:
                continue
            br = e.note.boundingRect()
            mid = self.mapFromScene(e.mid)
            ok = False
            for k in (-1, 1, -2, 2, -3, 3):
                dy = (k * (br.height() + 4)) - (br.height() / 2 if k < 0 else -4)
                r = QRectF(mid.x() - br.width() / 2, mid.y() + dy - (br.height() if k < 0 else 0) / 2,
                           br.width(), br.height())
                if free(r):
                    ok = True
                    break
            e.note.setVisible(ok)
            if ok:
                e.note.setPos(self.mapToScene(r.topLeft().toPoint()))
                placed.append(r)
        for nid in rest:
            place_star(nid)

    def relabel(self) -> None:
        """Redraw after a language switch, keeping the zoom, position and selection."""
        if not self.graph:
            return
        keep_fit = self._auto_fit
        t = self.transform()
        c = self.mapToScene(self.viewport().rect().center())
        sel = self.selected
        fit_k = self._fit_k
        self.set_graph(self.graph)
        if not keep_fit:
            self._fit_k = fit_k
            self.setTransform(t)
            self.centerOn(c)
            self._auto_fit = False
        self.select(sel)
        self.zoomChanged.emit(self.zoom_level())

    def center_on_node(self, nid: str) -> None:
        if nid in self.stars:
            self.centerOn(self.stars[nid].pos())

    # ---- selection -------------------------------------------------------
    def select(self, nid: str | None) -> None:
        if not self.graph:
            return
        self.selected = nid if nid in self.stars else None
        if self.selected is None:
            for s in self.stars.values():
                s.set_state("normal")
            for _, _, e in self.edges:
                e.set_state("normal")
            self._declutter()
            self.cleared.emit()
            return
        up, down = self.graph.lineage(self.selected)
        # a hub paper (3DGS itself) has dozens of links: label them in the panel, not on the map
        adjacent = sum(1 for a, b, _ in self.edges if self.selected in (a, b))
        notes_on = adjacent <= self.MAX_NOTES
        for i, s in self.stars.items():
            s.set_state("selected" if i == self.selected else "anc" if i in up else "desc" if i in down else "dim")
        for a, b, e in self.edges:
            if (b == self.selected or b in up) and a in up:
                st = "anc"
            elif (a == self.selected or a in down) and b in down:
                st = "desc"
            else:
                st = "dim"
            e.set_state(st, show_note=notes_on and self.selected in (a, b))
        self._declutter()
        self.nodeSelected.emit(self.selected)

    # ---- interaction -----------------------------------------------------
    def wheelEvent(self, e):
        mods = e.modifiers()
        zoom_mod = bool(mods & (Qt.ControlModifier | Qt.MetaModifier))
        trackpad = not e.pixelDelta().isNull()
        if trackpad and not zoom_mod:
            # two-finger scroll on a trackpad pans, like a map; pinch or Cmd/Ctrl+scroll zooms
            d = e.pixelDelta()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - d.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - d.y())
            self._auto_fit = False
            return
        dy = e.angleDelta().y() or e.angleDelta().x()
        if dy:
            self.zoom_by(1.0015 ** dy, e.position().toPoint())

    def mousePressEvent(self, e):
        self._press = e.position()
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        super().mouseReleaseEvent(e)
        if self._press is not None and (e.position() - self._press).manhattanLength() >= 4:
            self._auto_fit = False
        if self._press is not None and (e.position() - self._press).manhattanLength() < 4:
            if not isinstance(self.itemAt(e.position().toPoint()), (StarItem, QGraphicsSimpleTextItem)):
                self.select(None)
        self._press = None

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.select(None)
        elif e.key() in (Qt.Key_Plus, Qt.Key_Equal):
            self.zoom_in()
        elif e.key() in (Qt.Key_Minus, Qt.Key_Underscore):
            self.zoom_out()
        else:
            super().keyPressEvent(e)

    # ---- painting --------------------------------------------------------
    def drawBackground(self, p: QPainter, rect: QRectF):
        p.fillRect(rect, theme.SKY)
        p.save()
        p.resetTransform()
        w, h = self.viewport().width(), self.viewport().height()
        p.setPen(Qt.NoPen)
        for x, y, r, a in self._bg:
            c = QColor(theme.STAR)
            c.setAlpha(a)
            p.setBrush(c)
            p.drawEllipse(QPointF(x * w, y * h), r, r)
        p.restore()
        if self.lay:
            pen = QPen(QColor(160, 176, 220, 20), 1)
            pen.setCosmetic(True)
            p.setPen(pen)
            for x, _ in self.lay.ticks:
                p.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
            for y, _ in self.lay.lanes:
                p.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))

    def drawForeground(self, p: QPainter, rect: QRectF):
        if not self.lay:
            return
        p.save()
        p.resetTransform()
        w, h = self.viewport().width(), self.viewport().height()
        f = QFont()
        f.setPointSizeF(9.5)
        p.setFont(f)
        fm = p.fontMetrics()
        # today marker
        today = fractional_year(dt.date.today().isoformat(), None)
        if self.lay._yx_years and today >= self.lay._yx_years[0]:
            tx = self.mapFromScene(QPointF(self.lay.x_of_year(today), 0)).x()
            if 0 <= tx <= w:
                pen = QPen(theme.NOVA, 1, Qt.DashLine)
                c = QColor(theme.NOVA)
                c.setAlpha(110)
                pen.setColor(c)
                p.setPen(pen)
                p.drawLine(QPointF(tx, 0), QPointF(tx, h - 34))
                p.setPen(theme.NOVA)
                today_txt = tr("view.today")
                p.drawText(QPointF(tx - fm.horizontalAdvance(today_txt) / 2, h - 30), today_txt)
        # year ticks along the bottom
        p.setPen(theme.MUTED)
        last = -1e9
        for x, text in self.lay.ticks:
            vx = self.mapFromScene(QPointF(x, 0)).x()
            gap = fm.horizontalAdvance(text) + (36 if text.endswith(".07") else 18)
            if -40 < vx < w + 40 and vx - last >= gap:
                p.drawText(QPointF(vx - fm.horizontalAdvance(text) / 2, h - 12), text)
                last = vx
        # lane names pinned to the left edge
        for y, lane in self.lay.lanes:
            vy = self.mapFromScene(QPointF(0, y)).y()
            if 20 < vy < h - 40:
                name = pick(lane.name, lane.name_en)
                tw = fm.horizontalAdvance(name) + 16
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(10, 15, 31, 215))
                p.drawRoundedRect(QRectF(10, vy - 11, tw, 22), 11, 11)
                is_center_lane = self.graph and any(
                    n.id == self.graph.center and n.lane == lane.key for n in self.graph.nodes)
                p.setPen(theme.STAR if is_center_lane or lane.key == "center" else theme.MUTED)
                p.drawText(QPointF(18, vy + fm.ascent() / 2 - 1), name)
        p.restore()
