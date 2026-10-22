"""Integration test: spawn the MCP server over stdio and exercise its tools."""

from __future__ import annotations

import asyncio
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PIL import Image  # noqa: E402
from mcp import ClientSession, StdioServerParameters  # noqa: E402
from mcp.client.stdio import stdio_client  # noqa: E402

PY = sys.executable
ROOT = Path(__file__).resolve().parents[1]
TMP = Path(__file__).parent / "_tmp_mcp"


def make_photo(path: Path) -> Path:
    import random
    random.seed(11)
    img = Image.new("RGB", (1600, 1200))
    px = img.load()
    for y in range(1200):
        for x in range(1600):
            r = int(120 + 100 * x / 1600 + random.randint(-40, 40))
            g = int(80 + 90 * y / 1200 + random.randint(-40, 40))
            b = int(150 + 60 * (x + y) / 2800 + random.randint(-40, 40))
            px[x, y] = (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))
    img.save(path, "JPEG", quality=95)
    return path


class McpServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        TMP.mkdir(exist_ok=True)
        cls.photo = make_photo(TMP / "photo.jpg")
        cls.params = StdioServerParameters(
            command=PY,
            args=["-m", "picpress.mcp_server"],
            cwd=str(ROOT),
            env={"PYTHONPATH": str(ROOT / "src")},
        )

    @classmethod
    def tearDownClass(cls):
        import shutil
        shutil.rmtree(TMP, ignore_errors=True)

    def _session_run(self, coro):
        async def wrapper():
            async with stdio_client(self.params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    return await coro(session)
        return asyncio.run(wrapper())

    def test_list_tools(self):
        async def go(session):
            tools = await session.list_tools()
            return {t.name for t in tools.tools}
        names = self._session_run(go)
        self.assertLessEqual(
            {"compress_image", "batch_compress", "estimate_target",
             "image_info_tool", "supported_formats"}, names)

    def test_compress_to_target(self):
        out = TMP / "out.jpg"
        orig = self.photo.stat().st_size
        target_kb = max(20, (orig // 2) // 1024)  # halfway down, in KB

        async def go(session):
            return await session.call_tool("compress_image", {
                "image_path": str(self.photo),
                "target_size": target_kb,
                "unit": "KB",
                "output_path": str(out),
                "output_format": "jpeg",
            })
        result = self._session_run(go)
        payload = json.loads(result.content[0].text)
        self.assertEqual(payload["status"], "ok", payload)
        self.assertTrue(out.exists())
        self.assertLessEqual(out.stat().st_size, target_kb * 1024)
        self.assertLess(out.stat().st_size, orig)

    def test_target_too_large_warning(self):
        async def go(session):
            return await session.call_tool("compress_image", {
                "image_path": str(self.photo),
                "target_size": 50,
                "unit": "MB",  # absurdly large
            })
        result = self._session_run(go)
        payload = json.loads(result.content[0].text)
        self.assertEqual(payload["status"], "target_too_large")
        self.assertIn("not smaller", payload["message"])
        self.assertIsNone(payload["output_path"])

    def test_estimate_target(self):
        async def go(session):
            return await session.call_tool("estimate_target", {
                "image_path": str(self.photo),
                "target_size": 1024,
                "unit": "B",
                "allow_resize": True,
            })
        result = self._session_run(go)
        payload = json.loads(result.content[0].text)
        self.assertIn(payload["verdict"], ("unreachable", "feasible"))
        self.assertIn("advice", payload)

    def test_batch_compress(self):
        outdir = TMP / "batch"
        orig = self.photo.stat().st_size
        target_kb = max(20, (orig // 2) // 1024)

        async def go(session):
            return await session.call_tool("batch_compress", {
                "image_paths": [str(self.photo)],
                "target_size": target_kb,
                "unit": "KB",
                "output_dir": str(outdir),
            })
        result = self._session_run(go)
        payload = json.loads(result.content[0].text)
        self.assertEqual(payload["summary"]["total"], 1)
        self.assertEqual(payload["summary"]["compressed"], 1)
        produced = list(outdir.glob("*.jpg"))
        self.assertEqual(len(produced), 1, produced)
        self.assertIn(f"{target_kb}KB", produced[0].name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
