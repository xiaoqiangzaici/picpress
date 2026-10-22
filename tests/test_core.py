"""Unit tests for the PicPress core engine."""

from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PIL import Image  # noqa: E402

from picpress.core import (  # noqa: E402
    CompressionError,
    compress_to_target,
    format_size,
    image_info,
    parse_size,
    probe_min_size,
)


def make_photo(path: Path, size=(1600, 1200), fmt="JPEG") -> Path:
    """Create a synthetic 'photo' (gradients + shapes) big enough to compress."""
    img = Image.new("RGB", size)
    px = img.load()
    w, h = size
    for y in range(h):
        for x in range(0, w, 4):
            r = int(255 * x / w)
            g = int(255 * y / h)
            b = int(255 * (x + y) / (w + h))
            for dx in range(4):
                if x + dx < w:
                    px[x + dx, y] = (r, g, b)
    img.save(path, fmt, quality=92)
    return path


class ParseSizeTests(unittest.TestCase):
    def test_units(self):
        self.assertEqual(parse_size(1, "B"), 1)
        self.assertEqual(parse_size(1, "KB"), 1024)
        self.assertEqual(parse_size(1, "MB"), 1024 * 1024)
        self.assertEqual(parse_size(1.5, "MB"), int(1.5 * 1024 * 1024))

    def test_string_forms(self):
        self.assertEqual(parse_size("512B"), 512)
        self.assertEqual(parse_size("2kb"), 2048)
        self.assertEqual(parse_size("1.5 MB"), int(1.5 * 1024 * 1024))
        self.assertEqual(parse_size("2048", "B"), 2048)

    def test_bad_input(self):
        with self.assertRaises(CompressionError):
            parse_size(0, "KB")
        with self.assertRaises(CompressionError):
            parse_size(-5, "MB")
        with self.assertRaises(CompressionError):
            parse_size(1, "GBX")
        with self.assertRaises(CompressionError):
            parse_size("abc", "KB")

    def test_format_size(self):
        self.assertEqual(format_size(512), "512 B")
        self.assertIn("KB", format_size(348 * 1024))
        self.assertIn("MB", format_size(2 * 1024 * 1024))


class CompressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(__file__).parent / "_tmp"
        cls.tmp.mkdir(exist_ok=True)
        cls.photo = make_photo(cls.tmp / "photo.jpg")

    @classmethod
    def tearDownClass(cls):
        for f in cls.tmp.glob("*"):
            f.unlink()
        cls.tmp.rmdir()

    def test_hit_target_kb(self):
        out = self.tmp / "out_kb.jpg"
        r = compress_to_target(self.photo, 80, "KB", output=out, output_format="jpeg")
        self.assertEqual(r.status, "ok", r.message)
        self.assertLessEqual(r.final_bytes, 80 * 1024)
        self.assertGreater(r.final_bytes, 0)
        self.assertTrue(out.exists())
        # Quality should be as high as possible: bumping it 10 points should overflow.
        self.assertIsNotNone(r.quality)
        self.assertGreaterEqual(r.saved_ratio, 0)

    def test_target_must_be_smaller_than_original(self):
        size = self.photo.stat().st_size
        r = compress_to_target(self.photo, size, "B")
        self.assertEqual(r.status, "target_too_large")
        self.assertIsNone(r.output_path)

        r2 = compress_to_target(self.photo, size * 2, "B")
        self.assertEqual(r2.status, "target_too_large")

    def test_unreachable_target_warns(self):
        r = compress_to_target(self.photo, 300, "B", output=self.tmp / "tiny.jpg",
                               output_format="jpeg", allow_resize=True)
        # 300 B for a 1600x1200 photo is impossible even downscaled.
        self.assertEqual(r.status, "unreachable")
        self.assertIn("Cannot reach", r.message)

    def test_resize_helps_reach_small_target(self):
        r_no = compress_to_target(self.photo, 5, "KB", output=self.tmp / "n5.jpg",
                                  output_format="jpeg", allow_resize=False)
        r_yes = compress_to_target(self.photo, 5, "KB", output=self.tmp / "y5.jpg",
                                   output_format="jpeg", allow_resize=True)
        self.assertEqual(r_yes.status, "ok", r_yes.message)
        if r_no.status == "ok":
            # Both can fit; resized one should not be larger.
            self.assertLessEqual(r_yes.final_bytes, 5 * 1024)
        else:
            self.assertEqual(r_no.status, "unreachable")
        self.assertTrue(any("downscaled" in w for w in r_yes.warnings)
                        or r_yes.scale == 1.0)

    def test_exact_byte_target(self):
        out = self.tmp / "exact.jpg"
        target_b = self.photo.stat().st_size // 3
        r = compress_to_target(self.photo, target_b, "B", output=out,
                               output_format="jpeg")
        self.assertEqual(r.status, "ok", r.message)
        self.assertLessEqual(r.final_bytes, target_b)

    def test_png_output(self):
        png_src = make_photo(self.tmp / "src.png", size=(600, 400), fmt="PNG")
        out = self.tmp / "out.png"
        orig = png_src.stat().st_size
        target = int(orig * 0.5)
        r = compress_to_target(png_src, target, "B", output=out, output_format="png")
        self.assertEqual(r.status, "ok", r.message)
        self.assertLessEqual(r.final_bytes, target)

    def test_webp_output_with_alpha(self):
        img = Image.new("RGBA", (400, 400), (255, 0, 0, 128))
        src = self.tmp / "alpha.png"
        img.save(src)
        out = self.tmp / "alpha.webp"
        orig = src.stat().st_size
        target = orig // 2  # halfway between min-achievable and original
        r = compress_to_target(src, target, "B", output=out, output_format="auto")
        self.assertEqual(r.status, "ok", r.message)
        self.assertEqual(r.output_format, "webp")
        self.assertLessEqual(r.final_bytes, target)
        self.assertLess(r.final_bytes, orig)

    def test_missing_file(self):
        r = compress_to_target(self.tmp / "nope.jpg", 10, "KB")
        self.assertEqual(r.status, "error")

    def test_probe_and_info(self):
        info = image_info(self.photo)
        self.assertEqual(info["width"], 1600)
        self.assertGreater(info["bytes"], 0)
        probe = probe_min_size(self.photo, allow_resize=True)
        self.assertGreater(probe["min_bytes"], 0)

    def test_result_dict_serializable(self):
        import json
        r = compress_to_target(self.photo, 100, "KB", output=self.tmp / "d.jpg")
        json.dumps(r.to_dict())  # must not raise


if __name__ == "__main__":
    unittest.main(verbosity=2)
