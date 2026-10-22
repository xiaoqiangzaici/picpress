"""GUI smoke tests: language switch, format mapping, output naming.

Needs a desktop session (Qt widgets render for real). Run with:
    python tests/test_gui_smoke.py
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PIL import Image  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from picpress.gui import FORMAT_CHOICES, CompressWorker, MainWindow  # noqa: E402
from picpress.i18n import STRINGS  # noqa: E402

APP = QApplication.instance() or QApplication(sys.argv)


def make_photo(path: Path, size=(900, 600)) -> Path:
    img = Image.new("RGB", size)
    px = img.load()
    for y in range(size[1]):
        for x in range(size[0]):
            px[x, y] = (x % 256, y % 256, (x + y) % 256)
    img.save(path, "JPEG", quality=92)
    return path


class GuiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="picpress_gui_"))
        cls.photo = make_photo(cls.tmp / "sample.jpg")

    @classmethod
    def tearDownClass(cls):
        import shutil
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        self.win = MainWindow(lang="zh")
        self.win.add_paths([str(self.photo)])

    def tearDown(self):
        self.win.close()

    def test_language_switch_updates_strings(self):
        self.assertEqual(self.win.btn_go.text(), STRINGS["zh"]["btn.compress"])
        self.win.set_language("en")
        self.assertEqual(self.win.lang, "en")
        self.assertEqual(self.win.btn_go.text(), STRINGS["en"]["btn.compress"])
        self.assertEqual(self.win.table.horizontalHeaderItem(0).text(),
                         STRINGS["en"]["col.file"])
        # Settings survive the rebuild
        self.assertEqual(self.win.unit_combo.currentText(), "KB")
        self.assertEqual(self.win.table.rowCount(), 1)
        self.win.set_language("zh")
        self.assertEqual(self.win.btn_go.text(), STRINGS["zh"]["btn.compress"])

    def test_language_keys_have_matching_coverage(self):
        self.assertEqual(set(STRINGS["en"]), set(STRINGS["zh"]))
        self.assertTrue(all(STRINGS["en"][k] for k in STRINGS["en"]))

    def test_format_choices_include_jpg_and_jpeg(self):
        keys = [k for k, _f, _e in FORMAT_CHOICES]
        self.assertIn("jpg", keys)
        self.assertIn("jpeg", keys)
        exts = {k: e for k, _f, e in FORMAT_CHOICES}
        self.assertEqual(exts["jpg"], ".jpg")
        self.assertEqual(exts["jpeg"], ".jpeg")
        self.assertIsNone(exts["auto"])

    def test_worker_writes_jpeg_extension_and_unique_names(self):
        outdir = self.tmp / "gui_out"
        self.win.out_dir_edit.setText(str(outdir))
        idx = self.win.fmt_combo.findData("jpeg")
        self.win.fmt_combo.setCurrentIndex(idx)
        self.win.size_spin.setValue(30)
        self.win.unit_combo.setCurrentText("KB")

        rows = [{"path": str(self.photo), "row": 0}]
        # Run the worker synchronously (no event loop needed).
        worker = CompressWorker(
            rows, 30, "KB", "jpeg", ".jpeg",
            True, False, str(outdir), True, "30KB",
        )
        results = []
        worker.file_finished.connect(lambda row, res: results.append(res))
        worker.run()

        self.assertEqual(len(results), 1, results)
        res = results[0]
        self.assertEqual(res.status, "ok", res.message)
        self.assertTrue(res.output_path.endswith(".jpeg"), res.output_path)
        self.assertIn("30KB", Path(res.output_path).name)

        # Re-run: must not overwrite, must add " (2)"
        worker2 = CompressWorker(
            rows, 30, "KB", "jpeg", ".jpeg",
            True, False, str(outdir), True, "30KB",
        )
        results2 = []
        worker2.file_finished.connect(lambda row, res: results2.append(res))
        worker2.run()
        self.assertIn("(2)", Path(results2[0].output_path).name)
        self.assertNotEqual(res.output_path, results2[0].output_path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
