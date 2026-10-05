"""Render a scripted demo of Paper Constellation to MP4 (offscreen, frame by frame).

    QT_QPA_PLATFORM=offscreen QT_SCALE_FACTOR=1.5 PC_LANG=ko python docs/make_demo.py demo-ko.mp4

Needs ffmpeg on PATH.
"""
import math, os, subprocess, sys
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QImage
from PySide6.QtWidgets import QApplication
from paper_constellation import i18n
from paper_constellation.ui import theme
from paper_constellation.ui.main import MainWindow
from paper_constellation.ui.panel import ClickLabel

FPS = 30
OUT = sys.argv[1]
app = QApplication([])
app.setStyleSheet(theme.STYLESHEET)
w = MainWindow()
w.resize(1280, 760)
w.show()
app.processEvents()
w.view.fit()
w.view.select(None)
w.statusBar().showMessage("")
app.processEvents()

first = w.grab()
W, H = first.width(), first.height()
scale = W / w.width()
ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                       "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                       "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)

cursor = QPointF(w.width() * 0.75, w.height() * 0.55)
caption = ""
ripple = []      # (pos, age)
pinch = None     # (center, spread)


def win_pt(widget, p=None):
    p = p if p is not None else widget.rect().center()
    return QPointF(widget.mapTo(w, p))


def star_pt(nid):
    s = w.view.stars[nid]
    vp = w.view.mapFromScene(s.pos())
    return QPointF(w.view.viewport().mapTo(w, vp))


def ease(t):
    return 0.5 - 0.5 * math.cos(math.pi * max(0, min(1, t)))


def frame():
    app.processEvents()
    img = w.grab().toImage().convertToFormat(QImage.Format_RGB888)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    # caption pill
    if caption:
        f = QFont(); f.setPointSizeF(15); f.setBold(True)
        p.setFont(f)
        tw = p.fontMetrics().horizontalAdvance(caption) + 44
        r = QRectF((w.width() - tw) / 2, w.height() - 98, tw, 44)
        p.setPen(Qt.NoPen); p.setBrush(QColor(10, 15, 31, 225)); p.drawRoundedRect(r, 22, 22)
        p.setPen(QPen(QColor(130, 211, 230, 160), 1.2)); p.setBrush(Qt.NoBrush); p.drawRoundedRect(r, 22, 22)
        p.setPen(QColor("#f5f1e4")); p.drawText(r, Qt.AlignCenter, caption)
    # click ripples
    for pos, age in ripple:
        a = max(0, 1 - age / 12)
        p.setPen(QPen(QColor(255, 255, 255, int(220 * a)), 2)); p.setBrush(Qt.NoBrush)
        p.drawEllipse(pos, 6 + age * 2.2, 6 + age * 2.2)
    # pinch fingers
    if pinch:
        c, s = pinch
        for d in (-1, 1):
            q = QPointF(c.x() + d * s * 0.7, c.y() + d * s * 0.7)
            p.setPen(QPen(QColor(255, 255, 255, 200), 2)); p.setBrush(QColor(255, 255, 255, 70))
            p.drawEllipse(q, 13, 13)
    # arrow cursor
    x, y = cursor.x(), cursor.y()
    path = QPainterPath(QPointF(x, y))
    for dx, dy in [(0, 21), (5, 16), (9, 25), (12.5, 23.5), (8.5, 15), (15, 15)]:
        path.lineTo(x + dx, y + dy)
    path.closeSubpath()
    p.setPen(QPen(QColor(10, 15, 31), 1.6)); p.setBrush(QColor(255, 255, 255)); p.drawPath(path)
    p.end()
    ff.stdin.write(bytes(img.constBits()) if img.bytesPerLine() == W * 3 else
                   b"".join(bytes(img.constScanLine(i))[:W * 3] for i in range(H)))
    for r in ripple:
        r[1] += 1
    ripple[:] = [r for r in ripple if r[1] < 12]


def hold(sec):
    for _ in range(int(sec * FPS)):
        frame()


def move(target_fn, sec):
    global cursor
    a = QPointF(cursor)
    n = int(sec * FPS)
    for i in range(1, n + 1):
        b = target_fn()
        t = ease(i / n)
        cursor = QPointF(a.x() + (b.x() - a.x()) * t, a.y() + (b.y() - a.y()) * t)
        frame()


def click(action):
    ripple.append([QPointF(cursor), 0])
    action()


def zoom(total, sec, anchor_fn):
    global pinch
    n = int(sec * FPS)
    step = total ** (1 / n)
    for i in range(n):
        c = anchor_fn()
        pinch = (c, 18 + 40 * (i / n) if total > 1 else 58 - 40 * (i / n))
        vp = w.view.viewport().mapFrom(w, c.toPoint())
        w.view.zoom_by(step, vp)
        frame()
    pinch = None


def glide_to(nid, sec):
    v = w.view
    start = v.mapToScene(v.viewport().rect().center())
    end = v.stars[nid].pos()
    n = int(sec * FPS)
    for i in range(1, n + 1):
        t = ease(i / n)
        v.centerOn(QPointF(start.x() + (end.x() - start.x()) * t, start.y() + (end.y() - start.y()) * t))
        v._declutter()
        frame()


ko = i18n.LANG == "ko"
T = (lambda k, e: k if ko else e)

# 1. overview
caption = T("Gaussian Splatting 계보 53편, 한 장의 성도로", "53 Gaussian Splatting papers, one constellation")
hold(1.6)
# 2. click 3DGS
move(lambda: star_pt("3dgs"), 1.0)
click(lambda: w.view.select("3dgs"))
caption = T("별을 누르면: 딛고 선 연구는 주황, 뻗어 나간 연구는 하늘색", "Click a star: what it builds on in amber, what grew from it in cyan")
hold(2.0)
# 3. click 2DGS
move(lambda: star_pt("2dgs"), 0.9)
click(lambda: w.view.select("2dgs"))
caption = T("연결선마다 '무엇을 해결했나'가 적혀 있어요", "Every link says what the later paper solved")
hold(2.2)
# 4. pinch zoom around 2DGS
caption = T("핀치로 확대", "Pinch to zoom")
zoom(2.1, 1.4, lambda: star_pt("2dgs"))
hold(1.4)
# 5. jump via panel to SuGaR
row = next(l for l in w.panel.body.findChildren(ClickLabel) if l.text().startswith("SuGaR"))
move(lambda: win_pt(row), 0.9)
caption = T("패널에서 앞뒤 논문으로 바로 이동", "Jump along the lineage from the side panel")
click(lambda: w.view.select("sugar"))
glide_to("sugar", 0.8)
hold(1.6)
# 6. back to the whole map
caption = ""
fit_btn = w.fit_btn
move(lambda: win_pt(fit_btn), 0.8)
click(lambda: (w.view.fit(), w.view.select("3dgs")))
caption = T("전체 보기로 다시 한눈에", "Fit all to see the whole map again")
hold(1.8)
# 7. language toggle
move(lambda: win_pt(w.lang_btn), 0.9)
click(w.toggle_language)
caption = T("한국어 / English", "한국어 / English")
hold(2.2)
ff.stdin.close()
ff.wait()
print("done", W, H)
