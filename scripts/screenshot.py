"""Capture a screenshot of the PicPress window for docs (widget-only, no desktop)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from picpress.gui import MainWindow, QSS  # noqa: E402
from picpress.core import compress_to_target  # noqa: E402
from PIL import Image  # noqa: E402


def make_demo_photos(folder: Path) -> list[Path]:
    folder.mkdir(parents=True, exist_ok=True)
    paths = []
    specs = [
        ("sunset_beach.jpg", (1920, 1080), "JPEG"),
        ("city_night.jpg", (1600, 1200), "JPEG"),
        ("portrait_studio.jpg", (1400, 1800), "JPEG"),
    ]
    import random
    random.seed(7)
    for name, size, fmt in specs:
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
        img.save(p, fmt, quality=93)
        paths.append(p)
    return paths


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(QSS)
    win = MainWindow()
    win.resize(1180, 760)

    demo = make_demo_photos(Path(__file__).parent / "demo_photos")
    win.add_paths([str(p) for p in demo])

    # Simulate mixed results in the table for the screenshot
    outdir = Path(__file__).parent / "demo_out"
    outdir.mkdir(exist_ok=True)
    for row, p in enumerate(demo):
        r = compress_to_target(p, 500, "KB", output=outdir / p.name,
                               output_format="jpeg", allow_resize=True)
        win._on_file_done(row, r)
    win._on_all_done()

    win.show()
    app.processEvents()
    import time
    time.sleep(0.6)
    app.processEvents()

    pix = win.grab()  # widget-only capture, never the full desktop
    out = Path(__file__).parent / "demo_shot.png"
    pix.save(str(out))
    print("saved", out, pix.width(), pix.height())


if __name__ == "__main__":
    main()
