"""PicPress desktop app — a polished PySide6 GUI for target-size photo compression.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QFont, QIcon, QPainter, QPixmap
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
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .core import (
    SUPPORTED_INPUT,
    UNIT_CHOICES,
    CompressResult,
    compress_to_target,
    format_size,
    parse_size,
)

APP_NAME = "PicPress"
APP_VERSION = "0.1.0"
GITHUB_URL = "https://github.com/your-name/picpress"

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
QFrame#cardAlt {{
    background-color: {C_CARD_ALT};
    border: 1px solid {C_BORDER};
    border-radius: 10px;
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
QLabel#statBig {{
    font-size: 15px;
    font-weight: 600;
    color: {C_TEXT};
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
    width: 28px;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {C_MUTED};
    margin-right: 12px;
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


# ------------------------------------------------------------------ helpers


def make_icon(size: int = 256) -> QIcon:
    """Programmatic app icon: gradient tile + shrink arrow motif."""
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    from PySide6.QtGui import QBrush, QLinearGradient, QPen, QPolygonF
    from PySide6.QtCore import QPointF

    grad = QLinearGradient(0, 0, size, size)
    grad.setColorAt(0, QColor(C_ACCENT))
    grad.setColorAt(1, QColor(C_ACCENT_2))
    p.setBrush(QBrush(grad))
    p.setPen(Qt.NoPen)
    r = int(size * 0.22)
    p.drawRoundedRect(0, 0, size, size, r, r)

    # Down arrow into a tray = "compress to size".
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

    def __init__(self, rows, target_value, unit, output_format,
                 allow_resize, keep_metadata, output_dir):
        super().__init__()
        self.rows = rows
        self.target_value = target_value
        self.unit = unit
        self.output_format = output_format
        self.allow_resize = allow_resize
        self.keep_metadata = keep_metadata
        self.output_dir = output_dir
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
            out = None
            if self.output_dir:
                suffix = {"jpeg": ".jpg", "webp": ".webp", "png": ".png"}
                out = Path(self.output_dir) / path.name
                if self.output_format != "auto":
                    out = out.with_suffix(suffix[self.output_format])
            result: CompressResult = compress_to_target(
                path, self.target_value, self.unit,
                output=out,
                output_format=self.output_format,
                allow_resize=self.allow_resize,
                keep_metadata=self.keep_metadata,
            )
            self.file_finished.emit(item["row"], result)
        self.all_finished.emit()


# ------------------------------------------------------------------ window


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} — Photo Compressor")
        self.setMinimumSize(1080, 700)
        self.resize(1180, 760)
        self.setWindowIcon(make_icon())
        self.setAcceptDrops(True)
        self.worker: CompressWorker | None = None
        self._results: list[CompressResult] = []
        self._expected_target = 0
        self._build_ui()
        self._apply_stats()

    # ----- UI construction

    def _build_ui(self):
        root = QWidget(objectName="root")
        self.setCentralWidget(root)
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

        self.statusBar().showMessage("Ready · drop photos here or click Add files")

    def _build_header(self) -> QWidget:
        card = QFrame(objectName="card")
        lay = QHBoxLayout(card)
        lay.setContentsMargins(22, 16, 18, 16)

        logo = QLabel()
        logo.setPixmap(make_icon(52).pixmap(52, 52))
        lay.addWidget(logo)

        text_box = QVBoxLayout()
        text_box.setSpacing(1)
        title = QLabel(f"{APP_NAME}", objectName="title")
        sub = QLabel("Compress photos to the exact size you choose · 把照片压到你指定的体积",
                     objectName="subtitle")
        text_box.addWidget(title)
        text_box.addWidget(sub)
        lay.addLayout(text_box)
        lay.addStretch()

        ver = QLabel(f"v{APP_VERSION}", objectName="hint")
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
        lbl = QLabel("PHOTOS", objectName="section")
        head.addWidget(lbl)
        head.addStretch()
        self.stats_label = QLabel("", objectName="hint")
        head.addWidget(self.stats_label)
        lay.addLayout(head)

        # drop / list area
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["FILE", "ORIGINAL", "TARGET", "RESULT", "STATUS"])
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

        self.drop_hint = QLabel(
            "Drag & drop photos here   ·   JPG / PNG / WebP / BMP / TIFF",
            objectName="hint", alignment=Qt.AlignCenter)
        self.drop_hint.setFixedHeight(52)
        self.drop_hint.setStyleSheet(
            f"border: 1.5px dashed {C_BORDER}; border-radius: 10px; color: {C_MUTED};")
        lay.addWidget(self.drop_hint)

        btns = QHBoxLayout()
        self.btn_add = QPushButton("+  Add files")
        self.btn_add.clicked.connect(self.pick_files)
        self.btn_folder = QPushButton("Add folder")
        self.btn_folder.clicked.connect(self.pick_folder)
        self.btn_remove = QPushButton("−  Remove selected")
        self.btn_remove.clicked.connect(self.remove_selected)
        self.btn_clear = QPushButton("Clear all", objectName="ghost")
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

        lay.addWidget(QLabel("TARGET SIZE", objectName="section"))

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
        self.unit_combo.currentTextChanged.connect(self._unit_changed)
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

        lay.addWidget(QLabel("OUTPUT", objectName="section"))
        fmt_row = QHBoxLayout()
        fmt_row.addWidget(QLabel("Format", objectName="hint"))
        self.fmt_combo = QComboBox()
        self.fmt_combo.addItems(["Auto (recommended)", "JPEG", "WebP", "PNG"])
        fmt_row.addWidget(self.fmt_combo, stretch=1)
        lay.addLayout(fmt_row)

        self.chk_resize = QCheckBox("Allow downscaling to reach target")
        self.chk_resize.setChecked(True)
        self.chk_resize.setToolTip(
            "When quality alone cannot reach the target, PicPress gently\n"
            "reduces resolution as a last resort.")
        lay.addWidget(self.chk_resize)

        self.chk_meta = QCheckBox("Keep EXIF metadata")
        self.chk_meta.setToolTip(
            "Off by default: stripping metadata makes files smaller and\n"
            "protects privacy (GPS location etc.).")
        lay.addWidget(self.chk_meta)

        dir_row = QHBoxLayout()
        self.out_dir_edit = QLineEdit()
        self.out_dir_edit.setPlaceholderText("Same folder as source (default)")
        self.out_dir_edit.setReadOnly(True)
        dir_row.addWidget(self.out_dir_edit, stretch=1)
        browse = QPushButton("Browse")
        browse.clicked.connect(self.pick_output_dir)
        dir_row.addWidget(browse)
        lay.addLayout(dir_row)

        lay.addStretch()

        self.btn_go = QPushButton("Compress  →", objectName="primary")
        self.btn_go.setCursor(Qt.PointingHandCursor)
        self.btn_go.clicked.connect(self.start_compression)
        lay.addWidget(self.btn_go)

        self.btn_cancel = QPushButton("Cancel", objectName="ghost")
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

        self.btn_open_out = QPushButton("Open output folder", objectName="ghost")
        self.btn_open_out.clicked.connect(self.open_output_folder)
        top.addWidget(self.btn_open_out)
        lay.addLayout(top)

        self.summary = QLabel("Nothing compressed yet.", objectName="hint")
        lay.addWidget(self.summary)
        return card

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
            self.table.setItem(row, 4, QTableWidgetItem("Pending"))
            added += 1
        if added:
            self.drop_hint.hide()
        self._apply_stats()
        self.statusBar().showMessage(f"{added} photo(s) added")

    def remove_selected(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True)
        for r in rows:
            self.table.removeRow(r)
        self._apply_stats()

    def clear_files(self):
        self.table.setRowCount(0)
        self._apply_stats()
        self.summary.setText("Nothing compressed yet.")
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

    def _unit_changed(self):
        # Keep the numeric meaning sane when switching units (500 B vs 500 MB).
        self._apply_stats()

    def _apply_preset(self, value, unit):
        self.size_spin.blockSignals(True)
        self.size_spin.setValue(value)
        self.size_spin.blockSignals(False)
        self.unit_combo.setCurrentText(unit)
        self._apply_stats()

    def _target_bytes(self) -> int:
        return parse_size(self.size_spin.value(), self.unit_combo.currentText())

    def _apply_stats(self):
        for b in self.chip_buttons:
            b.setChecked(False)
        try:
            target = self._target_bytes()
        except Exception:
            self.target_preview.setText("")
            return
        self.target_preview.setText(
            f"Every photo will be compressed to ≤ {format_size(target)}")
        paths = self.existing_paths()
        total = sum(Path(p).stat().st_size for p in paths if Path(p).is_file())
        over = sum(1 for p in paths
                   if Path(p).is_file() and Path(p).stat().st_size <= target)
        msg = f"{len(paths)} photo(s) · {format_size(total)} total"
        if over:
            msg += f"   ⚠  {over} already ≤ target (will be skipped)"
        self.stats_label.setText(msg)
        self._refresh_target_column()

    def _refresh_target_column(self):
        try:
            target = self._target_bytes()
        except Exception:
            return
        for r in range(self.table.rowCount()):
            path = Path(self.table.item(r, 0).data(Qt.UserRole))
            if not path.is_file():
                continue
            size = path.stat().st_size
            cell = self.table.item(r, 2)
            if size <= target:
                cell.setText("— (skip)")
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
            QMessageBox.information(self, APP_NAME, "Add at least one photo first.")
            return

        try:
            target = self._target_bytes()
        except Exception as exc:
            QMessageBox.warning(self, APP_NAME, str(exc))
            return

        fmt_map = {"Auto (recommended)": "auto", "JPEG": "jpeg",
                   "WebP": "webp", "PNG": "png"}
        rows = [{"path": p, "row": r} for r, p in enumerate(paths)]
        self.worker = CompressWorker(
            rows, self.size_spin.value(), self.unit_combo.currentText(),
            fmt_map[self.fmt_combo.currentText()],
            self.chk_resize.isChecked(), self.chk_meta.isChecked(),
            self.out_dir_edit.text().strip() or None,
        )
        self.worker.progress_changed.connect(self._on_progress)
        self.worker.file_finished.connect(self._on_file_done)
        self.worker.all_finished.connect(self._on_all_done)
        self._results: list[CompressResult] = []
        self._expected_target = target

        self.btn_go.setEnabled(False)
        self.btn_cancel.show()
        self.progress.setValue(0)
        self.summary.setText("Compressing…")
        self.worker.start()

    def cancel_compression(self):
        if self.worker:
            self.worker.cancel()
            self.statusBar().showMessage("Cancelling…")

    def _on_progress(self, current, total, name):
        self.progress.setValue(int(current / max(total, 1) * 100))
        self.statusBar().showMessage(f"Compressing {name}  ({current}/{total})")

    def _on_file_done(self, row, result: CompressResult):
        self._results.append(result)
        color = QColor(status_color(result.status))

        if result.status == "target_too_large":
            status = "⚠ Target ≥ original — cannot compress"
            self.table.setItem(row, 3, QTableWidgetItem("—"))
        elif result.status == "unreachable":
            status = "⚠ Unreachable — see message"
            self.table.setItem(row, 3, QTableWidgetItem("—"))
        elif result.status == "error":
            status = "✗ Error"
            self.table.setItem(row, 3, QTableWidgetItem("—"))
        else:
            saved = result.saved_ratio * 100
            status = f"✓  −{saved:.1f}%"
            item = QTableWidgetItem(
                f"{format_size(result.original_bytes)} → {format_size(result.final_bytes)}")
            item.setForeground(QColor(C_SUCCESS))
            self.table.setItem(row, 3, item)

        st = QTableWidgetItem(status)
        st.setForeground(color)
        st.setToolTip(result.message)
        self.table.setItem(row, 4, st)

    def _on_all_done(self):
        self.btn_go.setEnabled(True)
        self.btn_cancel.hide()
        self.progress.setValue(100)
        results = getattr(self, "_results", [])
        ok = [r for r in results if r.ok]
        warn = [r for r in results if r.status in ("target_too_large", "unreachable")]
        err = [r for r in results if r.status == "error"]

        saved_total = sum(r.saved_bytes for r in ok)
        parts = [f"{len(ok)} compressed"]
        if saved_total:
            parts.append(f"saved {format_size(saved_total)}")
        if warn:
            parts.append(f"{len(warn)} skipped/warned")
        if err:
            parts.append(f"{len(err)} failed")
        self.summary.setText("  ·  ".join(parts) + ".")
        self.statusBar().showMessage("Done")

        if warn:
            lines = []
            for r in warn:
                name = Path(r.source_path).name
                if r.status == "target_too_large":
                    lines.append(f"• {name}: target size is not smaller than the "
                                 f"original file ({format_size(r.original_bytes)})")
                else:
                    lines.append(f"• {name}: {r.message}")
            QMessageBox.warning(
                self, "Some photos were not compressed",
                "PicPress only compresses — it never enlarges a file.\n\n"
                + "\n".join(lines[:12])
                + ("\n…" if len(lines) > 12 else "")
                + "\n\nPlease choose a smaller target size and try again.")

        if err:
            QMessageBox.critical(
                self, "Errors",
                "\n".join(f"• {Path(r.source_path).name}: {r.message}" for r in err[:12]))

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
    app.setStyleSheet(QSS)
    app.setFont(QFont("Segoe UI", 10))
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
