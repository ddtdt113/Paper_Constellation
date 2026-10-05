"""Night-sky palette shared by the chart and the side panel."""
from PySide6.QtGui import QColor

SKY = QColor("#0a0f1f")
SKY_RAISED = QColor("#111930")
LINE = QColor(160, 176, 220, 40)
INK = QColor("#d7dcec")
MUTED = QColor("#8a93b3")
STAR = QColor("#f5f1e4")
PAST = QColor("#eab676")     # ancestors of the selected star
FUTURE = QColor("#82d3e6")   # descendants of the selected star
NOVA = QColor("#f4a6c3")     # freshly added / recent papers
FOCUS = QColor("#ffffff")

STATUS_COLORS = {
    "foundation": QColor("#c9b88a"),
    "active": QColor("#8fd6a8"),
    "superseded": QColor("#9a9fb4"),
    "recent": NOVA,
}

STYLESHEET = f"""
QMainWindow, QWidget#panelBody {{ background: {SKY.name()}; color: {INK.name()}; }}
QToolBar {{ background: {SKY.name()}; border: 0; padding: 8px 10px; spacing: 8px; }}
QLineEdit {{ background: {SKY_RAISED.name()}; color: {INK.name()}; border: 1px solid #2a3557;
            border-radius: 8px; padding: 7px 10px; font-size: 13px; selection-background-color: #2f4a6b; }}
QLineEdit:focus {{ border-color: {FUTURE.name()}; }}
QPushButton {{ background: {SKY_RAISED.name()}; color: {INK.name()}; border: 1px solid #2a3557;
              border-radius: 8px; padding: 7px 12px; }}
QPushButton:hover {{ border-color: #4a5a85; }}
QPushButton:focus {{ border-color: {FUTURE.name()}; }}
QPushButton#primary {{ background: #1d3a4a; border-color: #2f6077; color: #e9f7fb; }}
QPushButton:disabled {{ color: #5b6483; }}
QToolBar::separator {{ background: #2a3557; width: 1px; margin: 8px 6px; }}
QPushButton#lang {{ border-radius: 13px; padding: 5px 14px; color: #e9f7fb; }}
QPushButton#zoom {{ padding: 5px 0; font-size: 16px; }}
QLabel#rel {{ padding: 6px 8px; border-radius: 6px; }}
QLabel#rel:hover, QLabel#rel:focus {{ background: #18223d; }}
QPushButton#link {{ border-radius: 12px; padding: 4px 10px; color: {FUTURE.name()}; border-color: #2c5563; }}
QScrollArea {{ border: 0; background: {SKY.name()}; }}
QSplitter::handle {{ background: #182140; width: 1px; }}
QStatusBar {{ background: {SKY.name()}; color: {MUTED.name()}; }}
QLabel {{ color: {INK.name()}; }}
QLabel#muted {{ color: {MUTED.name()}; }}
QLabel#title {{ color: {STAR.name()}; font-size: 18px; font-weight: 600; }}
QLabel#section {{ color: {MUTED.name()}; font-size: 11px; font-weight: 600; letter-spacing: 1px; }}
QMenuBar, QMenu {{ background: {SKY_RAISED.name()}; color: {INK.name()}; }}
QMenu::item:selected {{ background: #22304f; }}
QDialog {{ background: {SKY_RAISED.name()}; color: {INK.name()}; }}
QCheckBox {{ color: {INK.name()}; }}
QProgressBar {{ background: {SKY_RAISED.name()}; border: 0; border-radius: 3px; max-height: 6px; }}
QProgressBar::chunk {{ background: {FUTURE.name()}; border-radius: 3px; }}
"""
