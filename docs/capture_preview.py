"""Regenerate the README previews from the bundled Gaussian Splatting example.

    QT_QPA_PLATFORM=offscreen QT_SCALE_FACTOR=2 PC_LANG=ko python docs/capture_preview.py   # docs/preview.png
    QT_QPA_PLATFORM=offscreen QT_SCALE_FACTOR=2 PC_LANG=en python docs/capture_preview.py   # docs/preview-en.png
"""
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from paper_constellation import i18n
from paper_constellation.i18n import pick
from paper_constellation.ui import theme
from paper_constellation.ui.main import MainWindow


def main(selected: str = "2dgs") -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(theme.STYLESHEET)
    w = MainWindow()
    w.resize(1600, 940)
    w.show()
    app.processEvents()
    w.view.fit()
    w.view.select(selected)
    w.statusBar().showMessage(pick("예제: Gaussian Splatting 성도 · 별을 누르면 계보가 이어집니다",
                                   "Example: Gaussian Splatting constellation · click a star to trace its lineage"))
    app.processEvents()
    out = Path(__file__).with_name("preview.png" if i18n.LANG == "ko" else "preview-en.png")
    w.grab().save(str(out))
    print(f"saved {out}")


if __name__ == "__main__":
    main(*sys.argv[1:])
