"""Capture PicPress window/dialog screenshots for docs (widget-only, no desktop).

Produces:
  docs/assets/screenshot.png            (Chinese UI, mixed results)
  docs/assets/screenshot-en.png         (English UI)
  docs/assets/screenshot-dialog.png     (warning dialog: light bg, dark text)
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PIL import Image  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from picpress.core import compress_to_target  # noqa: E402
from picpress.gui import DIALOG_QSS, MainWindow, make_icon  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "assets"


def make_demo_photos(folder: Path) -> list[Path]:
    import random
    folder.mkdir(parents=True, exist_ok=True)
    random.seed(7)
    specs = [
        ("sunset_beach.jpg", (1920, 1080)),
        ("city_night.jpg", (1600, 1200)),
        ("portrait_studio.jpg", (1400, 1800)),
        ("tiny_preview.jpg", (600, 400)),
    ]
    paths = []
    for name, size in specs:
        img = Image.new("RGB", size)
        px = img.load()
        w, h = size
        for y in range(h):
            for x in range(0, w, 3):
                r = int(120 + 100 * x / w + random.randint(-20, 20))
                g = int(80 + 90 * y / h + random.randint(-20, 20))
                b = int(150 + 60 * (x + y) / (w + h) + random.randint(-20, 20))
                c = (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))
                for dx in range(3):
                    if x + dx < w:
                        px[x + dx, y] = c
        p = folder / name
        img.save(p, "JPEG", quality=93)
        paths.append(p)
    return paths


def populate(win: MainWindow, photos: list[Path], outdir: Path) -> None:
    win.add_paths([str(p) for p in photos])
    for row, p in enumerate(photos):
        # Same 500 KB target for all: the tiny last photo is already smaller,
        # so it lands in the "target >= original" warning row.
        r = compress_to_target(p, 500, "KB", output_dir=outdir,
                               output_format="jpeg", allow_resize=True,
                               size_label="500KB")
        win._on_file_done(row, r)
    win._update_summary()
    win.progress.setValue(100)


def grab(win: MainWindow, name: str) -> Path:
    win.show()
    QApplication.processEvents()
    time.sleep(0.5)
    QApplication.processEvents()
    win.repaint()  # force a full repaint so the grab sees current strings
    QApplication.processEvents()
    pix = win.grab()  # widget-only capture, never the full desktop
    out = ASSETS / name
    pix.save(str(out))
    print("saved", out, pix.width(), pix.height())
    return out


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    app = QApplication(sys.argv)

    photos = make_demo_photos(ROOT / "scripts" / "demo_photos")
    outdir = ROOT / "scripts" / "demo_out"
    # Fresh output dir so duplicate-name suffixes don't accumulate across runs.
    import shutil
    shutil.rmtree(outdir, ignore_errors=True)
    outdir.mkdir(exist_ok=True)

    # --- Chinese UI
    win = MainWindow(lang="zh")
    win.resize(1180, 770)
    populate(win, photos, outdir)
    grab(win, "screenshot.png")

    # --- English UI (exercises the runtime language switch + state restore)
    win.set_language("en")
    QApplication.processEvents()
    grab(win, "screenshot-en.png")
    win.close()

    # --- Warning dialog (light surface, dark text)
    box = QMessageBox()
    box.setWindowIcon(make_icon())
    box.setWindowTitle("部分照片未压缩")
    box.setIcon(QMessageBox.Icon.Warning)
    box.setText("PicPress 只做压缩，绝不会把文件变大。")
    box.setInformativeText(
        "• tiny_preview.jpg：目标体积不小于原文件（99.1 KB）\n"
        "• portrait_studio.jpg：无法达到 30KB（最小可达 41KB）\n\n"
        "请选择更小的目标体积后重试。")
    box.setStyleSheet(DIALOG_QSS)
    box.addButton("确定", QMessageBox.ButtonRole.AcceptRole)
    box.show()
    QApplication.processEvents()
    time.sleep(0.5)
    QApplication.processEvents()
    box.grab().save(str(ASSETS / "screenshot-dialog.png"))
    print("saved dialog")
    box.close()


if __name__ == "__main__":
    main()
