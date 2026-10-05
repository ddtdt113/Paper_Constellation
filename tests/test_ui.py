import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["PC_LANG"] = "ko"  # start in Korean regardless of the machine's saved choice
QtWidgets = pytest.importorskip("PySide6.QtWidgets")

from paper_constellation.ui import theme  # noqa: E402
from paper_constellation.ui.main import MainWindow  # noqa: E402


@pytest.fixture(scope="module")
def app():
    a = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    a.setStyleSheet(theme.STYLESHEET)
    return a


def test_window_opens_with_example(app, tmp_path):
    w = MainWindow()
    w.resize(1360, 820)
    w.show()
    app.processEvents()
    assert w.graph and len(w.view.stars) == 53
    # selecting a star highlights its lineage and fills the panel
    w.view.select("2dgs")
    app.processEvents()
    states = {i: s.state for i, s in w.view.stars.items()}
    assert states["2dgs"] == "selected" and states["3dgs"] == "anc" and states["pgsr"] == "desc"
    assert states["dreamgaussian"] == "dim"
    shot = os.environ.get("PC_SCREENSHOT")
    if shot:
        w.grab().save(shot)
    # zoom in and out around the view center, clamped to the allowed range
    w.view.fit()
    assert abs(w.view.zoom_level() - 1.0) < 1e-6
    w.view.zoom_in()
    assert abs(w.view.zoom_level() - 1.25) < 1e-6 and w.zoom_label.text() == "125%"
    for _ in range(40):
        w.view.zoom_in()
    assert w.view.zoom_level() <= w.view.MAX_ZOOM + 1e-6
    for _ in range(60):
        w.view.zoom_out()
    assert w.view.zoom_level() >= w.view.MIN_ZOOM - 1e-6
    w.view.fit()
    assert w.zoom_label.text() == "100%"
    w.view.select(None)
    app.processEvents()
    assert all(s.state == "normal" for s in w.view.stars.values())
    w.close()


def test_language_toggle(app):
    from paper_constellation import i18n
    w = MainWindow()
    w.resize(1360, 820)
    w.show()
    app.processEvents()
    assert i18n.LANG == "ko" and w.go.text() == "성도 그리기" and w.lang_btn.text() == "English"
    w.view.select("2dgs")
    w.view.zoom_in()
    zoom = w.view.zoom_level()
    w.toggle_language()
    app.processEvents()
    assert i18n.LANG == "en"
    assert w.go.text() == "Draw constellation" and w.lang_btn.text() == "한국어"
    assert w.menuBar().actions()[0].text() == "File"
    # the chart keeps its zoom and selection, and switches curated text to English
    assert abs(w.view.zoom_level() - zoom) < 1e-6 and w.view.selected == "2dgs"
    notes = [e.note.text() for a, b, e in w.view.edges if e.note is not None and (a, b) == ("3dgs", "2dgs")]
    assert notes and notes[0].startswith("3D ellipsoids")
    texts = [l.text() for l in w.panel.body.findChildren(QtWidgets.QLabel)]
    assert any("Before · what this paper builds on" in t for t in texts)
    assert any(t.startswith("Replaces 3D ellipsoids") for t in texts)
    shot = os.environ.get("PC_SCREENSHOT_EN")
    if shot:
        w.grab().save(shot)
    w.toggle_language()
    app.processEvents()
    assert i18n.LANG == "ko" and w.menuBar().actions()[0].text() == "파일"
    w.close()
