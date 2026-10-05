"""Main window: a search bar for a paper address, the star chart, and the detail panel."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QLocale, QObject, QSettings, Qt, QThread, Signal
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog, QDialogButtonBox, QFileDialog,
                               QFormLayout, QLabel, QLineEdit, QMainWindow, QMessageBox,
                               QProgressBar, QPushButton, QSizePolicy, QSplitter, QToolBar,
                               QWidget)

from .. import __version__, annotate, examples, i18n, lineage
from ..i18n import pick, tr
from ..model import Graph
from ..s2 import S2Error, SemanticScholar
from . import theme
from .panel import DetailPanel
from .view import ConstellationView

ORG = APP = "paper-constellation"
EXAMPLES = examples.CATALOG
load_example = examples.load


def initial_language(settings: QSettings) -> str:
    """PC_LANG, then the saved choice, then the system language."""
    lang = os.environ.get("PC_LANG") or settings.value("lang", "")
    if lang in i18n.LANGUAGES:
        return lang
    return "ko" if QLocale.system().language() == QLocale.Korean else "en"


class Worker(QObject):
    progress = Signal(str)
    done = Signal(object, str)   # Graph, warning
    failed = Signal(str)

    def __init__(self, query: str, s2_key: str, llm_key: str, model: str, use_llm: bool):
        super().__init__()
        self.query, self.s2_key, self.llm_key, self.model, self.use_llm = query, s2_key, llm_key, model, use_llm

    def run(self):
        try:
            src = SemanticScholar(api_key=self.s2_key or None)
            g, contexts = lineage.build(self.query, src, progress=self.progress.emit)
            warning = ""
            if self.use_llm and self.llm_key:
                self.progress.emit(tr("progress.llm"))
                try:
                    g = annotate.annotate(g, contexts, api_key=self.llm_key, model=self.model or None)
                except (annotate.AnnotateError, ValueError) as e:
                    warning = tr("warn.llm_skipped", e=e)
            elif self.use_llm:
                warning = tr("warn.no_key")
            self.done.emit(g, warning)
        except (S2Error, ValueError) as e:
            self.failed.emit(str(e))
        except Exception as e:  # keep the UI alive on unexpected errors
            self.failed.emit(tr("err.unexpected", e=repr(e)))


class SettingsDialog(QDialog):
    def __init__(self, settings: QSettings, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("settings.title"))
        self.s = settings
        form = QFormLayout(self)
        self.s2 = QLineEdit(settings.value("s2_key", ""))
        self.s2.setEchoMode(QLineEdit.Password)
        self.s2.setPlaceholderText(tr("settings.s2_ph"))
        self.llm = QLineEdit(settings.value("anthropic_key", ""))
        self.llm.setEchoMode(QLineEdit.Password)
        self.llm.setPlaceholderText(tr("settings.llm_ph"))
        self.model = QLineEdit(settings.value("model", annotate.DEFAULT_MODEL))
        self.use_llm = QCheckBox(tr("settings.use_llm"))
        self.use_llm.setChecked(settings.value("use_llm", "true") == "true")
        form.addRow(tr("settings.s2"), self.s2)
        form.addRow(tr("settings.llm"), self.llm)
        form.addRow(tr("settings.model"), self.model)
        form.addRow(self.use_llm)
        note = QLabel(tr("settings.note"))
        note.setObjectName("muted")
        note.setWordWrap(True)
        form.addRow(note)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.save)
        bb.rejected.connect(self.reject)
        form.addRow(bb)
        self.resize(560, 0)

    def save(self):
        self.s.setValue("s2_key", self.s2.text().strip())
        self.s.setValue("anthropic_key", self.llm.text().strip())
        self.s.setValue("model", self.model.text().strip() or annotate.DEFAULT_MODEL)
        self.s.setValue("use_llm", "true" if self.use_llm.isChecked() else "false")
        self.accept()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(1360, 820)
        self.settings = QSettings(ORG, APP)
        i18n.set_language(initial_language(self.settings))
        self.graph: Graph | None = None
        self.thread: QThread | None = None
        self._status_key: str | None = "status.ready"   # re-translated on a language switch

        # toolbar: search, zoom, language
        tb = QToolBar()
        tb.setMovable(False)
        self.addToolBar(tb)
        self.search = QLineEdit()
        self.search.setClearButtonEnabled(True)
        self.search.returnPressed.connect(self.run_search)
        self.search.setMinimumWidth(380)
        self.go = QPushButton()
        self.go.setObjectName("primary")
        self.go.clicked.connect(self.run_search)
        self.fit_btn = QPushButton()
        self.fit_btn.clicked.connect(lambda: self.view.fit())
        self.zoom_out_btn = QPushButton("−")
        self.zoom_in_btn = QPushButton("+")
        for b in (self.zoom_out_btn, self.zoom_in_btn):
            b.setObjectName("zoom")
            b.setFixedWidth(36)
        self.zoom_label = QLabel("100%")
        self.zoom_label.setObjectName("muted")
        self.zoom_label.setFixedWidth(46)
        self.zoom_label.setAlignment(Qt.AlignCenter)
        self.lang_btn = QPushButton()
        self.lang_btn.setObjectName("lang")
        self.lang_btn.setCursor(Qt.PointingHandCursor)
        self.lang_btn.clicked.connect(self.toggle_language)
        tb.addWidget(self.search)
        tb.addWidget(self.go)
        tb.addSeparator()
        tb.addWidget(self.zoom_out_btn)
        tb.addWidget(self.zoom_label)
        tb.addWidget(self.zoom_in_btn)
        tb.addWidget(self.fit_btn)
        self.busy = QProgressBar()
        self.busy.setRange(0, 0)
        self.busy.setFixedWidth(120)
        self.busy.setVisible(False)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tb.addWidget(spacer)
        tb.addWidget(self.busy)
        tb.addWidget(self.lang_btn)

        # chart + panel
        self.view = ConstellationView()
        self.panel = DetailPanel()
        self.zoom_in_btn.clicked.connect(self.view.zoom_in)
        self.zoom_out_btn.clicked.connect(self.view.zoom_out)
        self.view.zoomChanged.connect(lambda z: self.zoom_label.setText(f"{z * 100:.0f}%"))
        split = QSplitter(Qt.Horizontal)
        split.addWidget(self.view)
        split.addWidget(self.panel)
        split.setStretchFactor(0, 1)
        split.setSizes([1000, 360])
        self.setCentralWidget(split)

        self.view.nodeSelected.connect(lambda nid: self.panel.show_node(self.graph, nid))
        self.view.cleared.connect(lambda: self.panel.show_overview(self.graph))
        self.view.nodeActivated.connect(self.expand_from)
        self.panel.jumpTo.connect(self.jump)
        self.panel.expand.connect(self.expand_from)

        self.retranslate()
        self.set_graph(load_example())

    # ---- language --------------------------------------------------------
    def retranslate(self) -> None:
        self.search.setPlaceholderText(tr("search.placeholder"))
        self.go.setText(tr("btn.draw"))
        self.fit_btn.setText(tr("btn.fit"))
        self.fit_btn.setToolTip(tr("tip.fit"))
        self.zoom_out_btn.setToolTip(tr("tip.zoom_out"))
        self.zoom_in_btn.setToolTip(tr("tip.zoom_in"))
        self.lang_btn.setText(tr("btn.lang"))
        self.lang_btn.setToolTip(tr("tip.lang"))
        self.menuBar().clear()
        self._menus()
        self._update_title()
        if self._status_key:
            self.statusBar().showMessage(tr(self._status_key))

    def toggle_language(self) -> None:
        self.set_language("en" if i18n.LANG == "ko" else "ko")

    def set_language(self, lang: str) -> None:
        i18n.set_language(lang)
        self.settings.setValue("lang", i18n.LANG)
        self.retranslate()
        self.view.relabel()
        self.panel.refresh()

    def _update_title(self) -> None:
        title = pick(self.graph.title, self.graph.title_en) if self.graph else ""
        self.setWindowTitle(f"{title} — Paper Constellation" if title else "Paper Constellation")

    def _menus(self):
        m = self.menuBar().addMenu(tr("menu.file"))
        m.addAction(QAction(tr("act.open"), self, shortcut=QKeySequence.Open, triggered=self.open_file))
        m.addAction(QAction(tr("act.save"), self, shortcut=QKeySequence.Save, triggered=self.save_file))
        ex = m.addMenu(tr("menu.examples"))
        for fname, (ko, en) in EXAMPLES.items():
            ex.addAction(QAction(pick(ko, en), self, triggered=lambda _=False, f=fname: self.set_graph(load_example(f))))
        m.addSeparator()
        m.addAction(QAction(tr("act.quit"), self, shortcut=QKeySequence.Quit, triggered=self.close))
        v = self.menuBar().addMenu(tr("menu.view"))
        zin = QAction(tr("act.zoom_in"), self, triggered=self.view.zoom_in)
        zin.setShortcuts([QKeySequence(QKeySequence.ZoomIn), QKeySequence("Ctrl+=")])
        v.addAction(zin)
        v.addAction(QAction(tr("act.zoom_out"), self, shortcut=QKeySequence.ZoomOut, triggered=self.view.zoom_out))
        v.addAction(QAction(tr("act.fit"), self, shortcut=QKeySequence("Ctrl+0"), triggered=lambda: self.view.fit()))
        v.addSeparator()
        v.addAction(QAction(tr("act.lang"), self, shortcut=QKeySequence("Ctrl+L"), triggered=self.toggle_language))
        s = self.menuBar().addMenu(tr("menu.settings"))
        s.addAction(QAction(tr("act.settings"), self, triggered=self.open_settings))
        h = self.menuBar().addMenu(tr("menu.help"))
        h.addAction(QAction(tr("act.about"), self, triggered=self.about))

    def _status(self, text: str, key: str | None = None) -> None:
        self._status_key = key
        self.statusBar().showMessage(text)

    # ---- graph -----------------------------------------------------------
    def set_graph(self, g: Graph):
        self.graph = g
        self.view.set_graph(g)
        self.panel.show_overview(g)
        self._update_title()
        if g.center:
            self.view.select(g.center)

    def jump(self, nid: str):
        self.view.select(nid)
        self.view.center_on_node(nid)

    def expand_from(self, nid: str):
        n = self.graph.node(nid) if self.graph else None
        if not n:
            return
        query = f"arXiv:{n.arxiv}" if n.arxiv else (f"DOI:{n.doi}" if n.doi else n.id if len(n.id) == 40 else n.title)
        self.search.setText(query)
        self.run_search()

    # ---- search ----------------------------------------------------------
    def run_search(self):
        q = self.search.text().strip()
        if not q or self.thread is not None:
            return
        s = self.settings
        self.go.setEnabled(False)
        self.busy.setVisible(True)
        self.thread = QThread(self)
        self.worker = Worker(q, s.value("s2_key", ""), s.value("anthropic_key", "") or os.environ.get("ANTHROPIC_API_KEY", ""),
                             s.value("model", ""), s.value("use_llm", "true") == "true")
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(lambda m: self._status(m))
        self.worker.done.connect(self._done)
        self.worker.failed.connect(self._failed)
        self.worker.done.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self._cleanup)
        self.thread.start()

    def _done(self, g: Graph, warning: str):
        self.set_graph(g)
        msg = tr("status.done", n=len(g.nodes), m=len(g.edges))
        self._status(msg + (f"  {warning}" if warning else ""))

    def _failed(self, msg: str):
        self._status(msg)
        QMessageBox.warning(self, tr("dlg.failed"), msg)

    def _cleanup(self):
        self.go.setEnabled(True)
        self.busy.setVisible(False)
        self.worker.deleteLater()
        self.thread.deleteLater()
        self.thread = None

    # ---- files -----------------------------------------------------------
    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, tr("dlg.open"), str(Path.home()), "Constellation (*.json)")
        if path:
            try:
                self.set_graph(Graph.load(path))
            except (OSError, ValueError, TypeError) as e:
                QMessageBox.warning(self, tr("dlg.open_fail_title"), tr("dlg.open_fail", e=e))

    def save_file(self):
        if not self.graph:
            return
        name = (pick(self.graph.title, self.graph.title_en) or "constellation").replace("/", "-") + ".json"
        path, _ = QFileDialog.getSaveFileName(self, tr("dlg.save"), str(Path.home() / name), "Constellation (*.json)")
        if path:
            self.graph.save(path)
            self._status(tr("status.saved", path=path))

    def open_settings(self):
        SettingsDialog(self.settings, self).exec()

    def about(self):
        QMessageBox.about(self, "Paper Constellation",
                          f"<b>Paper Constellation {__version__}</b><br>{tr('about.body')}")


def main(argv: list[str] | None = None) -> int:
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("Paper Constellation")
    app.setOrganizationName(ORG)
    app.setStyleSheet(theme.STYLESHEET)
    w = MainWindow()
    w.show()
    args = (argv if argv is not None else sys.argv)[1:]
    if args:
        w.search.setText(args[0])
        w.run_search()
    return app.exec()
