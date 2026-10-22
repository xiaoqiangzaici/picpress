"""PicPress desktop app — a polished PySide6 GUI for target-size photo compression.

UI text is fully routed through :mod:`picpress.i18n` so the whole window can be
rebuilt in another language at runtime (EN / 简体中文).
"""

from __future__ import annotations

import atexit
import os
import sys
import tempfile
from pathlib import Path

from PIL import Image as PILImage, ImageDraw

from PySide6.QtCore import QPointF, Qt, QThread, QUrl, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QDesktopServices,
    QFont,
    QIcon,
    QLinearGradient,
    QPainter,
    QPen,
    QPixmap,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .core import (
    SUPPORTED_INPUT,
    UNIT_CHOICES,
    CompressResult,
    CompressionError,
    compress_to_target,
    format_size,
    parse_size,
)
from .i18n import DEFAULT_LANG, t

APP_NAME = "PicPress"
APP_VERSION = "0.2.0"
GITHUB_URL = "https://github.com/your-name/picpress"

# Output format choices: key -> (engine format, preferred extension)
FORMAT_CHOICES: list[tuple[str, str, str | None]] = [
    ("auto", "auto", None),
    ("jpg", "jpeg", ".jpg"),
    ("jpeg", "jpeg", ".jpeg"),
    ("png", "png", ".png"),
    ("webp", "webp", ".webp"),
]

# ------------------------------------------------------------------ palette

C_BG = "#0E1017"
C_CARD = "#171B26"
C_CARD_ALT = "#1D2230"
C_BORDER = "#2A3042"
C_TEXT = "#E8EAF2"
C_MUTED = "#8A92A8"
C_ACCENT = "#6D8BFF"
C_ACCENT_2 = "#9B6DFF"
C_SUCCESS = "#3ECF8E"
C_WARNING = "#F5B83D"
C_DANGER = "#FF6B6B"


def _sweep_stale_chevrons() -> None:
    """Delete chevron PNGs left behind by a previous crashed/killed run.

    Only files older than an hour are touched, so a second running instance
    (which needs its own file for the QSS) is never affected.
    """
    import time

    temp_dir = Path(tempfile.gettempdir())
    cutoff = time.time() - 3600
    for pattern in ("picpress_chevron_*.png", "picpress_chevron_v1.png"):
        for stale in temp_dir.glob(pattern):
            try:
                if stale.stat().st_mtime < cutoff:
                    stale.unlink(missing_ok=True)
            except OSError:
                pass


def _chevron_image_path() -> str:
    """Draw a small down-chevron PNG and return its path for use in QSS.

    Qt renders CSS border-triangles as boxes, and the native arrow is
    invisible on a dark surface, so we ship a generated icon instead. The
    file is per-process and deleted on exit, leaving nothing behind.
    """
    _sweep_stale_chevrons()
    path = Path(tempfile.gettempdir()) / f"picpress_chevron_{os.getpid()}.png"
    scale = 4
    size = 11 * scale
    img = PILImage.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    w = 1.8 * scale
    draw.line([(1.6 * scale, 3.4 * scale), (5.5 * scale, 7.4 * scale)],
              fill=(138, 146, 168, 255), width=int(w))
    draw.line([(5.5 * scale, 7.4 * scale), (9.4 * scale, 3.4 * scale)],
              fill=(138, 146, 168, 255), width=int(w))
    img = img.resize((11, 11), PILImage.Resampling.LANCZOS)
    img.save(path)
    atexit.register(lambda p=path: p.unlink(missing_ok=True))
    return path.as_posix()


CHEVRON = _chevron_image_path()

QSS = f"""
* {{
    font-family: 'Segoe UI', 'Microsoft YaHei UI', sans-serif;
    color: {C_TEXT};
    outline: none;
}}
QMainWindow, QWidget#root {{
    background-color: {C_BG};
}}
QFrame#card {{
    background-color: {C_CARD};
    border: 1px solid {C_BORDER};
    border-radius: 14px;
}}
QLabel#title {{
    font-size: 26px;
    font-weight: 700;
    letter-spacing: 1px;
    color: {C_TEXT};
}}
QLabel#subtitle {{
    font-size: 13px;
    color: {C_MUTED};
}}
QLabel#section {{
    font-size: 12px;
    font-weight: 700;
    color: {C_MUTED};
    letter-spacing: 1.5px;
}}
QLabel#hint {{
    font-size: 12px;
    color: {C_MUTED};
}}
QPushButton {{
    background-color: {C_CARD_ALT};
    border: 1px solid {C_BORDER};
    border-radius: 9px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
}}
QPushButton:hover {{
    background-color: #242B3D;
    border-color: #3A4258;
}}
QPushButton:pressed {{
    background-color: #1B2130;
}}
QPushButton:disabled {{
    color: {C_MUTED};
    background-color: {C_CARD};
}}
QPushButton#primary {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {C_ACCENT}, stop:1 {C_ACCENT_2});
    border: none;
    color: white;
    font-size: 15px;
    font-weight: 700;
    padding: 13px 22px;
    border-radius: 11px;
}}
QPushButton#primary:hover {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #7E99FF, stop:1 #A97DFF);
}}
QPushButton#primary:pressed {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #5C7AEF, stop:1 #8A5EEB);
}}
QPushButton#primary:disabled {{
    background-color: #333A4D;
    color: {C_MUTED};
}}
QPushButton#ghost {{
    background: transparent;
    border: none;
    color: {C_MUTED};
    font-weight: 600;
    padding: 6px 10px;
}}
QPushButton#ghost:hover {{
    color: {C_TEXT};
}}
QPushButton#chip {{
    background-color: {C_CARD_ALT};
    border: 1px solid {C_BORDER};
    border-radius: 12px;
    padding: 6px 13px;
    font-size: 12px;
}}
QPushButton#chip:hover {{
    border-color: {C_ACCENT};
    color: {C_ACCENT};
}}
QPushButton#chip:checked {{
    background-color: rgba(109, 139, 255, 35);
    border-color: {C_ACCENT};
    color: {C_ACCENT};
}}
QPushButton#lang {{
    background-color: {C_CARD_ALT};
    border: 1px solid {C_BORDER};
    border-radius: 8px;
    padding: 5px 12px;
    font-size: 12px;
    font-weight: 600;
    color: {C_MUTED};
}}
QPushButton#lang:hover {{
    color: {C_TEXT};
    border-color: #3A4258;
}}
QPushButton#lang:checked {{
    background-color: rgba(109, 139, 255, 40);
    border-color: {C_ACCENT};
    color: {C_ACCENT};
}}
QLineEdit, QDoubleSpinBox, QComboBox {{
    background-color: #121622;
    border: 1px solid {C_BORDER};
    border-radius: 9px;
    padding: 8px 12px;
    font-size: 14px;
    selection-background-color: {C_ACCENT};
}}
QLineEdit:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border-color: {C_ACCENT};
}}
QComboBox::drop-down {{
    border: none;
    width: 30px;
}}
QComboBox::down-arrow {{
    image: url("{CHEVRON}");
    width: 11px;
    height: 11px;
    margin-right: 10px;
}}
QComboBox QAbstractItemView {{
    background-color: {C_CARD};
    border: 1px solid {C_BORDER};
    border-radius: 8px;
    selection-background-color: {C_ACCENT};
    selection-color: white;
    padding: 4px;
}}
QCheckBox {{
    spacing: 9px;
    font-size: 13px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1.5px solid {C_BORDER};
    background: #121622;
}}
QCheckBox::indicator:checked {{
    background-color: {C_ACCENT};
    border-color: {C_ACCENT};
}}
QTableWidget {{
    background-color: transparent;
    alternate-background-color: rgba(255, 255, 255, 4%);
    border: none;
    gridline-color: transparent;
    font-size: 13px;
}}
QTableWidget::item {{
    padding: 6px 10px;
    border: none;
}}
QTableWidget::item:selected {{
    background-color: rgba(109, 139, 255, 30);
    color: {C_TEXT};
}}
QHeaderView {{
    background-color: transparent;
}}
QHeaderView::section {{
    background-color: {C_CARD};
    border: none;
    border-bottom: 1px solid {C_BORDER};
    color: {C_MUTED};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    padding: 8px 10px;
}}
QProgressBar {{
    background-color: #121622;
    border: 1px solid {C_BORDER};
    border-radius: 8px;
    height: 14px;
    text-align: center;
    font-size: 11px;
    color: {C_TEXT};
}}
QProgressBar::chunk {{
    border-radius: 7px;
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {C_ACCENT}, stop:1 {C_ACCENT_2});
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #2E3547;
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
}}
QScrollBar::handle:horizontal {{
    background: #2E3547;
    border-radius: 5px;
    min-width: 30px;
}}
QStatusBar {{
    background: transparent;
    color: {C_MUTED};
    font-size: 12px;
}}
QToolTip {{
    background-color: {C_CARD};
    color: {C_TEXT};
    border: 1px solid {C_BORDER};
    padding: 6px 10px;
    border-radius: 6px;
}}
"""

# Message boxes are their own light window: light surface + dark text keeps
# warnings perfectly readable. Dark-theme light text must NOT leak in here.
DIALOG_QSS = """
QMessageBox {
    background-color: #FFFFFF;
}
QMessageBox QLabel {
    color: #14161F;
    font-size: 13px;
    font-family: 'Segoe UI', 'Microsoft YaHei UI', sans-serif;
}
QMessageBox QPushButton {
    background-color: #EDF0F6;
    color: #14161F;
    border: 1px solid #D6DBE6;
    border-radius: 8px;
    padding: 7px 22px;
    min-width: 68px;
    font-size: 13px;
    font-weight: 600;
}
QMessageBox QPushButton:hover {
    background-color: #E2E7F1;
}
QMessageBox QPushButton:default {
    background-color: #4C74F0;
    color: #FFFFFF;
    border: none;
}
QMessageBox QPushButton:default:hover {
    background-color: #3F66E2;
}
"""


# ------------------------------------------------------------------ helpers


def make_icon(size: int = 256) -> QIcon:
    """Programmatic app icon: gradient tile + shrink arrow motif."""
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)

    grad = QLinearGradient(0, 0, size, size)
    grad.setColorAt(0, QColor(C_ACCENT))
    grad.setColorAt(1, QColor(C_ACCENT_2))
    p.setBrush(QBrush(grad))
    p.setPen(Qt.NoPen)
    r = int(size * 0.22)
    p.drawRoundedRect(0, 0, size, size, r, r)

    pen = QPen(QColor("white"), int(size * 0.07), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    cx = size / 2
    p.drawLine(QPointF(cx, size * 0.24), QPointF(cx, size * 0.52))
    head = QPolygonF([
        QPointF(cx - size * 0.12, size * 0.44),
        QPointF(cx, size * 0.58),
        QPointF(cx + size * 0.12, size * 0.44),
    ])
    p.setBrush(QColor("white"))
    p.drawPolygon(head)
    p.drawLine(QPointF(size * 0.26, size * 0.72), QPointF(size * 0.74, size * 0.72))
    p.end()
    return QIcon(pix)


def status_color(status: str) -> str:
    return {
        "ok": C_SUCCESS,
        "target_too_large": C_WARNING,
        "unreachable": C_WARNING,
        "error": C_DANGER,
    }.get(status, C_MUTED)


# ------------------------------------------------------------------ worker


class CompressWorker(QThread):
    progress_changed = Signal(int, int, str)
    file_finished = Signal(int, object)
    all_finished = Signal()

    def __init__(self, rows, target_value, unit, output_format, output_ext,
                 allow_resize, keep_metadata, output_dir,
                 include_target_in_name, size_label):
        super().__init__()
        self.rows = rows
        self.target_value = target_value
        self.unit = unit
        self.output_format = output_format
        self.output_ext = output_ext
        self.allow_resize = allow_resize
        self.keep_metadata = keep_metadata
        self.output_dir = output_dir
        self.include_target_in_name = include_target_in_name
        self.size_label = size_label
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        total = len(self.rows)
        for idx, item in enumerate(self.rows):
            if self._cancelled:
                break
            path = Path(item["path"])
            self.progress_changed.emit(idx + 1, total, path.name)
            result: CompressResult = compress_to_target(
                path, self.target_value, self.unit,
                output_dir=self.output_dir,
                output_format=self.output_format,
                output_ext=self.output_ext,
                allow_resize=self.allow_resize,
                keep_metadata=self.keep_metadata,
                include_target_in_name=self.include_target_in_name,
                size_label=self.size_label,
            )
            self.file_finished.emit(item["row"], result)
        self.all_finished.emit()


# ------------------------------------------------------------------ window


class MainWindow(QMainWindow):
    def __init__(self, lang: str = DEFAULT_LANG):
        super().__init__()
        self.lang = lang
        self.setMinimumSize(1080, 710)
        self.resize(1180, 770)
        self.setWindowIcon(make_icon())
        self.setAcceptDrops(True)
        self.worker: CompressWorker | None = None
        self.row_results: dict[int, CompressResult] = {}
        self._build_ui()
        self._apply_stats()

    def tr(self, key: str, **kwargs) -> str:
        return t(self.lang, key, **kwargs)

    # ----- UI construction

    def _build_ui(self):
        root = QWidget(objectName="root")
        self.setCentralWidget(root)
        # Dark chrome applied to the main window's own tree (not the app), so
        # light message boxes keep their own look.
        self.setStyleSheet(QSS)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(22, 18, 22, 16)
        outer.setSpacing(14)

        outer.addWidget(self._build_header())

        body = QHBoxLayout()
        body.setSpacing(14)
        body.addWidget(self._build_files_card(), stretch=6)
        body.addWidget(self._build_settings_card(), stretch=4)
        outer.addLayout(body, stretch=1)

        outer.addWidget(self._build_footer())
        self.statusBar().showMessage(self.tr("status.ready"))

    def _build_header(self) -> QWidget:
        card = QFrame(objectName="card")
        lay = QHBoxLayout(card)
        lay.setContentsMargins(22, 16, 18, 16)

        logo = QLabel()
        logo.setPixmap(make_icon(52).pixmap(52, 52))
        lay.addWidget(logo)

        text_box = QVBoxLayout()
        text_box.setSpacing(1)
        text_box.addWidget(QLabel(APP_NAME, objectName="title"))
        text_box.addWidget(QLabel(self.tr("app.tagline"), objectName="subtitle"))
        lay.addLayout(text_box)
        lay.addStretch()

        # Language switch: 中文 | EN
        self.lang_buttons: dict[str, QPushButton] = {}
        lang_box = QHBoxLayout()
        lang_box.setSpacing(4)
        for code, label in (("zh", "中文"), ("en", "EN")):
            b = QPushButton(label, objectName="lang")
            b.setCheckable(True)
            b.setChecked(code == self.lang)
            b.setCursor(Qt.PointingHandCursor)
            b.setToolTip(self.tr("app.lang_tip"))
            b.clicked.connect(lambda _=False, c=code: self.set_language(c))
            lang_box.addWidget(b)
            self.lang_buttons[code] = b
        lay.addLayout(lang_box)

        ver = QLabel(f"v{APP_VERSION}")
        ver.setStyleSheet(f"color: {C_MUTED}; font-size: 12px; padding: 0 6px;")
        lay.addWidget(ver)

        gh = QPushButton("GitHub", objectName="ghost")
        gh.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(GITHUB_URL)))
        lay.addWidget(gh)
        return card

    def _build_files_card(self) -> QWidget:
        card = QFrame(objectName="card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(10)

        head = QHBoxLayout()
        head.addWidget(QLabel(self.tr("photos.section"), objectName="section"))
        head.addStretch()
        self.stats_label = QLabel("", objectName="hint")
        self.stats_label.setAlignment(Qt.AlignRight)
        head.addWidget(self.stats_label)
        lay.addLayout(head)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            self.tr("col.file"), self.tr("col.original"), self.tr("col.target"),
            self.tr("col.result"), self.tr("col.status"),
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for col, w in ((1, 100), (2, 100), (3, 150), (4, 175)):
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.Fixed)
            self.table.setColumnWidth(col, w)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        lay.addWidget(self.table, stretch=1)

        self.drop_hint = QLabel(self.tr("photos.drop"), objectName="hint",
                                alignment=Qt.AlignCenter)
        self.drop_hint.setFixedHeight(52)
        self.drop_hint.setStyleSheet(
            f"border: 1.5px dashed {C_BORDER}; border-radius: 10px; color: {C_MUTED};")
        lay.addWidget(self.drop_hint)

        btns = QHBoxLayout()
        self.btn_add = QPushButton(self.tr("photos.add"))
        self.btn_add.clicked.connect(self.pick_files)
        self.btn_folder = QPushButton(self.tr("photos.add_folder"))
        self.btn_folder.clicked.connect(self.pick_folder)
        self.btn_remove = QPushButton(self.tr("photos.remove"))
        self.btn_remove.clicked.connect(self.remove_selected)
        self.btn_clear = QPushButton(self.tr("photos.clear"), objectName="ghost")
        self.btn_clear.clicked.connect(self.clear_files)
        for b in (self.btn_add, self.btn_folder, self.btn_remove, self.btn_clear):
            btns.addWidget(b)
        btns.addStretch()
        lay.addLayout(btns)
        return card

    def _build_settings_card(self) -> QWidget:
        card = QFrame(objectName="card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(12)

        lay.addWidget(QLabel(self.tr("settings.target"), objectName="section"))

        row = QHBoxLayout()
        row.setSpacing(8)
        self.size_spin = QDoubleSpinBox()
        self.size_spin.setDecimals(1)
        self.size_spin.setRange(0.1, 99999)
        self.size_spin.setValue(500)
        self.size_spin.setMinimumWidth(110)
        self.size_spin.valueChanged.connect(self._apply_stats)
        row.addWidget(self.size_spin, stretch=1)

        self.unit_combo = QComboBox()
        self.unit_combo.addItems(list(UNIT_CHOICES))
        self.unit_combo.setCurrentText("KB")
        self.unit_combo.setFixedWidth(86)
        self.unit_combo.currentTextChanged.connect(self._apply_stats)
        row.addWidget(self.unit_combo)
        lay.addLayout(row)

        chips = QGridLayout()
        chips.setHorizontalSpacing(8)
        chips.setVerticalSpacing(8)
        presets = [(50, "B"), (100, "KB"), (200, "KB"), (500, "KB"),
                   (1, "MB"), (2, "MB"), (5, "MB"), (10, "MB")]
        self.chip_buttons: list[QPushButton] = []
        for i, (val, unit) in enumerate(presets):
            b = QPushButton(f"{val} {unit}", objectName="chip")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, v=val, u=unit: self._apply_preset(v, u))
            chips.addWidget(b, i // 4, i % 4)
            self.chip_buttons.append(b)
        lay.addLayout(chips)

        self.target_preview = QLabel("", objectName="hint")
        self.target_preview.setWordWrap(True)
        lay.addWidget(self.target_preview)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"color: {C_BORDER}; max-height: 1px;")
        lay.addWidget(line)

        lay.addWidget(QLabel(self.tr("settings.output"), objectName="section"))

        fmt_row = QHBoxLayout()
        fmt_row.addWidget(QLabel(self.tr("settings.format"), objectName="hint"))
        self.fmt_combo = QComboBox()
        for key, _engine_fmt, _ext in FORMAT_CHOICES:
            self.fmt_combo.addItem(self.tr(f"fmt.{key}"), key)
        fmt_row.addWidget(self.fmt_combo, stretch=1)
        lay.addLayout(fmt_row)

        self.chk_nametag = QCheckBox(self.tr("settings.nametag"))
        self.chk_nametag.setChecked(True)
        self.chk_nametag.setToolTip(self.tr("settings.nametag_tip"))
        lay.addWidget(self.chk_nametag)

        self.chk_resize = QCheckBox(self.tr("settings.resize"))
        self.chk_resize.setChecked(True)
        self.chk_resize.setToolTip(self.tr("settings.resize_tip"))
        lay.addWidget(self.chk_resize)

        self.chk_meta = QCheckBox(self.tr("settings.meta"))
        self.chk_meta.setToolTip(self.tr("settings.meta_tip"))
        lay.addWidget(self.chk_meta)

        dir_row = QHBoxLayout()
        self.out_dir_edit = QLineEdit()
        self.out_dir_edit.setPlaceholderText(self.tr("settings.placeholder"))
        self.out_dir_edit.setReadOnly(True)
        dir_row.addWidget(self.out_dir_edit, stretch=1)
        browse = QPushButton(self.tr("settings.browse"))
        browse.clicked.connect(self.pick_output_dir)
        dir_row.addWidget(browse)
        lay.addLayout(dir_row)

        lay.addStretch()

        self.btn_go = QPushButton(self.tr("btn.compress"), objectName="primary")
        self.btn_go.setCursor(Qt.PointingHandCursor)
        self.btn_go.clicked.connect(self.start_compression)
        lay.addWidget(self.btn_go)

        self.btn_cancel = QPushButton(self.tr("btn.cancel"), objectName="ghost")
        self.btn_cancel.clicked.connect(self.cancel_compression)
        self.btn_cancel.hide()
        lay.addWidget(self.btn_cancel, alignment=Qt.AlignCenter)
        return card

    def _build_footer(self) -> QWidget:
        card = QFrame(objectName="card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(18, 12, 18, 12)
        lay.setSpacing(8)

        top = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFixedHeight(16)
        self.progress.setFormat("%p%")
        top.addWidget(self.progress, stretch=1)

        self.btn_open_out = QPushButton(self.tr("footer.open"), objectName="ghost")
        self.btn_open_out.clicked.connect(self.open_output_folder)
        top.addWidget(self.btn_open_out)
        lay.addLayout(top)

        self.summary = QLabel(self.tr("footer.idle"), objectName="hint")
        lay.addWidget(self.summary)
        return card

    # ----- language switching

    def _snapshot_state(self) -> dict:
        return {
            "paths": [self.table.item(r, 0).data(Qt.UserRole)
                      for r in range(self.table.rowCount())],
            "results": dict(self.row_results),
            "size": self.size_spin.value(),
            "unit": self.unit_combo.currentText(),
            "fmt": self.fmt_combo.currentData(),
            "resize": self.chk_resize.isChecked(),
            "meta": self.chk_meta.isChecked(),
            "nametag": self.chk_nametag.isChecked(),
            "outdir": self.out_dir_edit.text(),
            "summary": self.summary.text(),
            "progress": self.progress.value(),
        }

    def _restore_state(self, snap: dict) -> None:
        self.size_spin.blockSignals(True)
        self.size_spin.setValue(snap["size"])
        self.size_spin.blockSignals(False)
        self.unit_combo.setCurrentText(snap["unit"])
        idx = self.fmt_combo.findData(snap["fmt"])
        if idx >= 0:
            self.fmt_combo.setCurrentIndex(idx)
        self.chk_resize.setChecked(snap["resize"])
        self.chk_meta.setChecked(snap["meta"])
        self.chk_nametag.setChecked(snap["nametag"])
        self.out_dir_edit.setText(snap["outdir"])

        self.add_paths(snap["paths"])
        for row, result in snap["results"].items():
            if row < self.table.rowCount():
                self.row_results[row] = result
                self._render_result(row, result)
        # Regenerate (do not restore) so wording follows the new language.
        if self.row_results:
            self._update_summary()
        else:
            self.summary.setText(self.tr("footer.idle"))
        self.progress.setValue(snap["progress"])
        self._apply_stats()

    def set_language(self, lang: str) -> None:
        if lang == self.lang:
            return
        if self.worker and self.worker.isRunning():
            self.statusBar().showMessage(self.tr("status.lang_busy"))
            self.lang_buttons[self.lang].setChecked(True)
            self.lang_buttons[lang].setChecked(False)
            return
        snap = self._snapshot_state()
        self.lang = lang
        self._build_ui()
        self._restore_state(snap)
        self.statusBar().showMessage(self.tr("status.ready"))

    # ----- message boxes (light surface, dark text)

    def _message(self, kind: str, title: str, text: str,
                 detail: str | None = None) -> None:
        # No parent: keeps this dialog out of the dark stylesheet's scope.
        box = QMessageBox()
        box.setWindowIcon(make_icon())
        box.setWindowTitle(title)
        box.setIcon({
            "info": QMessageBox.Icon.Information,
            "warn": QMessageBox.Icon.Warning,
            "error": QMessageBox.Icon.Critical,
        }[kind])
        box.setText(text)
        if detail:
            box.setInformativeText(detail)
        box.setStyleSheet(DIALOG_QSS)
        box.addButton(self.tr("btn.ok"), QMessageBox.ButtonRole.AcceptRole)
        box.exec()

    # ----- file management

    def pick_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Choose photos", "",
            "Images (*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff *.gif)")
        self.add_paths(paths)

    def pick_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose a folder")
        if folder:
            paths = sorted(
                str(p) for p in Path(folder).iterdir()
                if p.suffix.lower() in SUPPORTED_INPUT)
            self.add_paths(paths)

    def pick_output_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Output folder")
        if folder:
            self.out_dir_edit.setText(folder)
            self._apply_stats()

    def add_paths(self, paths):
        existing = {self.table.item(r, 0).data(Qt.UserRole)
                    for r in range(self.table.rowCount())}
        added = 0
        for p in paths:
            p = str(Path(p))
            if p in existing or Path(p).suffix.lower() not in SUPPORTED_INPUT:
                continue
            row = self.table.rowCount()
            self.table.insertRow(row)
            name_item = QTableWidgetItem(Path(p).name)
            name_item.setData(Qt.UserRole, p)
            name_item.setToolTip(p)
            self.table.setItem(row, 0, name_item)
            size = Path(p).stat().st_size
            self.table.setItem(row, 1, QTableWidgetItem(format_size(size)))
            self.table.setItem(row, 2, QTableWidgetItem("—"))
            self.table.setItem(row, 3, QTableWidgetItem("—"))
            self.table.setItem(row, 4, QTableWidgetItem(self.tr("status.pending")))
            existing.add(p)
            added += 1
        if added:
            self.drop_hint.hide()
        self._apply_stats()
        if added:
            self.statusBar().showMessage(self.tr("status.added", n=added))

    def remove_selected(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True)
        for r in rows:
            self.table.removeRow(r)
        # Row indices shift; results are keyed by row, so clear them.
        self.row_results.clear()
        self._apply_stats()

    def clear_files(self):
        self.table.setRowCount(0)
        self.row_results.clear()
        self._apply_stats()
        self.summary.setText(self.tr("footer.idle"))
        self.progress.setValue(0)

    def existing_paths(self) -> list[str]:
        return [self.table.item(r, 0).data(Qt.UserRole)
                for r in range(self.table.rowCount())]

    # ----- drag & drop

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = [u.toLocalFile() for u in event.mimeData().urls()]
        self.add_paths(paths)

    # ----- settings glue

    def _apply_preset(self, value, unit):
        self.size_spin.blockSignals(True)
        self.size_spin.setValue(value)
        self.size_spin.blockSignals(False)
        self.unit_combo.setCurrentText(unit)
        self._apply_stats()

    def _target_bytes(self) -> int:
        return parse_size(self.size_spin.value(), self.unit_combo.currentText())

    def _size_label(self) -> str:
        return f"{self.size_spin.value():g}{self.unit_combo.currentText()}"

    def _apply_stats(self):
        for b in self.chip_buttons:
            b.setChecked(False)
        try:
            target = self._target_bytes()
        except (CompressionError, ValueError):
            self.target_preview.setText("")
            return
        self.target_preview.setText(
            self.tr("settings.preview", size=format_size(target)))
        paths = self.existing_paths()
        total = sum(Path(p).stat().st_size for p in paths if Path(p).is_file())
        over = sum(1 for p in paths
                   if Path(p).is_file() and Path(p).stat().st_size <= target)
        msg = self.tr("photos.stats", n=len(paths), size=format_size(total))
        if over:
            msg += "   ⚠  " + self.tr("photos.skip", n=over)
        self.stats_label.setText(msg)
        self._refresh_target_column()

    def _refresh_target_column(self):
        try:
            target = self._target_bytes()
        except (CompressionError, ValueError):
            return
        for r in range(self.table.rowCount()):
            path = Path(self.table.item(r, 0).data(Qt.UserRole))
            if not path.is_file():
                continue
            cell = self.table.item(r, 2)
            if path.stat().st_size <= target:
                cell.setText(self.tr("status.skip"))
                cell.setForeground(QColor(C_WARNING))
            else:
                cell.setText(format_size(target))
                cell.setForeground(QColor(C_MUTED))

    # ----- compression

    def start_compression(self):
        if self.worker and self.worker.isRunning():
            return
        paths = self.existing_paths()
        if not paths:
            self._message("info", APP_NAME, self.tr("dlg.no_files"))
            return

        try:
            self._target_bytes()
        except (CompressionError, ValueError) as exc:
            self._message("warn", APP_NAME, str(exc))
            return

        fmt_key = self.fmt_combo.currentData()
        engine_fmt, out_ext = next(
            (f, e) for k, f, e in FORMAT_CHOICES if k == fmt_key)
        rows = [{"path": p, "row": r} for r, p in enumerate(paths)]
        self.row_results.clear()
        self.worker = CompressWorker(
            rows, self.size_spin.value(), self.unit_combo.currentText(),
            engine_fmt, out_ext,
            self.chk_resize.isChecked(), self.chk_meta.isChecked(),
            self.out_dir_edit.text().strip() or None,
            self.chk_nametag.isChecked(), self._size_label(),
        )
        self.worker.progress_changed.connect(self._on_progress)
        self.worker.file_finished.connect(self._on_file_done)
        self.worker.all_finished.connect(self._on_all_done)

        self.btn_go.setEnabled(False)
        self.btn_cancel.show()
        self.progress.setValue(0)
        self.summary.setText(self.tr("footer.compressing"))
        self.worker.start()

    def cancel_compression(self):
        if self.worker:
            self.worker.cancel()
            self.statusBar().showMessage(self.tr("status.cancelling"))

    def _on_progress(self, current, total, name):
        self.progress.setValue(int(current / max(total, 1) * 100))
        self.statusBar().showMessage(
            self.tr("status.compressing", name=name, i=current, n=total))

    def _on_file_done(self, row, result: CompressResult):
        self.row_results[row] = result
        self._render_result(row, result)
        self._update_summary()

    def _render_result(self, row: int, result: CompressResult):
        if result.status == "ok":
            status_text = self.tr("status.ok", pct=result.saved_ratio * 100)
            item = QTableWidgetItem(
                f"{format_size(result.original_bytes)} → {format_size(result.final_bytes)}")
            item.setForeground(QColor(C_SUCCESS))
            self.table.setItem(row, 3, item)
        else:
            status_text = {
                "target_too_large": self.tr("status.too_large"),
                "unreachable": self.tr("status.unreachable"),
                "error": self.tr("status.error"),
            }.get(result.status, self.tr("status.error"))
            self.table.setItem(row, 3, QTableWidgetItem("—"))

        st = QTableWidgetItem(status_text)
        st.setForeground(QColor(status_color(result.status)))
        st.setToolTip(result.message or result.output_path or "")
        self.table.setItem(row, 4, st)

    def _update_summary(self):
        results = list(self.row_results.values())
        if not results:
            return
        ok = [r for r in results if r.ok]
        warn = [r for r in results if r.status in ("target_too_large", "unreachable")]
        err = [r for r in results if r.status == "error"]
        saved_total = sum(r.saved_bytes for r in ok)

        parts = [self.tr("summary.compressed", n=len(ok))]
        if saved_total:
            parts.append(self.tr("summary.saved", size=format_size(saved_total)))
        if warn:
            parts.append(self.tr("summary.warned", n=len(warn)))
        if err:
            parts.append(self.tr("summary.failed", n=len(err)))
        self.summary.setText("  ·  ".join(parts))

    def _on_all_done(self):
        self.btn_go.setEnabled(True)
        self.btn_cancel.hide()
        self.progress.setValue(100)
        results = list(self.row_results.values())
        warn = [r for r in results if r.status in ("target_too_large", "unreachable")]
        err = [r for r in results if r.status == "error"]
        self._update_summary()
        self.statusBar().showMessage(self.tr("status.done"))

        if warn:
            lines = []
            for r in warn[:12]:
                name = Path(r.source_path).name
                if r.status == "target_too_large":
                    lines.append(self.tr(
                        "dlg.warn_too_large", name=name,
                        size=format_size(r.original_bytes)))
                else:
                    lines.append(self.tr(
                        "dlg.warn_unreachable", name=name,
                        target=format_size(r.target_bytes),
                        min=format_size(r.final_bytes or 0)))
            if len(warn) > 12:
                lines.append(self.tr("dlg.more", n=len(warn) - 12))
            self._message(
                "warn", self.tr("dlg.warn_title"),
                self.tr("dlg.warn_intro"),
                "\n".join(lines) + "\n\n" + self.tr("dlg.warn_footer"))

        if err:
            self._message(
                "error", self.tr("dlg.err_title"),
                "\n".join(f"• {Path(r.source_path).name}: {r.message}"
                          for r in err[:12]))

    def open_output_folder(self):
        out = self.out_dir_edit.text().strip()
        if not out:
            paths = self.existing_paths()
            out = str(Path(paths[0]).parent) if paths else None
        if out:
            QDesktopServices.openUrl(QUrl.fromLocalFile(out))


# ------------------------------------------------------------------ entry


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setFont(QFont("Segoe UI", 10))
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
