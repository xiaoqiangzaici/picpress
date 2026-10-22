"""Protocol-level test client for the PicPress MCP server.

Spawns the server as a real MCP client would (stdio), performs the handshake,
lists tools and calls every one of them, then prints a PASS/FAIL report.

Usage:
    python scripts/test_mcp.py                  # auto: dist/picpress-mcp.exe
    python scripts/test_mcp.py --python         # run from source instead
    python scripts/test_mcp.py --exe <path-to-picpress-mcp.exe>
    python scripts/test_mcp.py --keep           # keep the sample/output files

Exit code 0 = all checks passed.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PIL import Image  # noqa: E402
from mcp import ClientSession, StdioServerParameters  # noqa: E402
from mcp.client.stdio import stdio_client  # noqa: E402


def make_sample(path: Path) -> Path:
    """Create a photo-like JPEG of a few MB."""
    w, h = 2400, 1600
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        g = int(70 + 100 * y / h)
        b = int(140 + 70 * y / h)
        for x in range(w):
            px[x, y] = (int(100 + 120 * x / w), g, min(255, b + int(40 * x / w)))
    img.save(path, "JPEG", quality=95)
    return path


def human(n: int | None) -> str:
    if not n:
        return "-"
    v = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if v < 1024 or unit == "GB":
            return f"{int(v)} B" if unit == "B" else f"{v:.1f} {unit}"
        v /= 1024
    return f"{v:.1f} GB"


class Report:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0
        self.lines: list[str] = []

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        if ok:
            self.passed += 1
            mark = "PASS"
        else:
            self.failed += 1
            mark = "FAIL"
        line = f"[{mark}] {name}"
        if detail:
            line += f"  —  {detail}"
        print(line)
        self.lines.append(line)


async def run(params: StdioServerParameters, work: Path, report: Report) -> None:
    sample = work / "sample_photo.jpg"
    if not sample.exists():
        make_sample(sample)

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            info = await session.initialize()
            # Field names differ between SDK generations (v1 camelCase, v2 snake_case).
            server_info = getattr(info, "server_info", None) or getattr(info, "serverInfo", None)
            server_name = getattr(server_info, "name", "") if server_info else ""
            protocol = (getattr(info, "protocol_version", None)
                        or getattr(info, "protocolVersion", ""))
            report.check("handshake (initialize)", bool(server_name),
                         f"server: {server_name}  protocol: {protocol}")

            tools = await session.list_tools()
            names = sorted(t.name for t in tools.tools)
            expected = {"compress_image", "batch_compress", "estimate_target",
                        "image_info_tool", "supported_formats"}
            report.check("tools/list", expected <= set(names), ", ".join(names))

            async def call(tool: str, args: dict) -> dict:
                res = await session.call_tool(tool, args)
                return json.loads(res.content[0].text)

            # --- supported_formats
            fmt = await call("supported_formats", {})
            report.check("supported_formats", len(fmt["input_extensions"]) >= 5,
                         f"{len(fmt['input_extensions'])} inputs, "
                         f"outputs={fmt['output_formats']}, units={fmt['units']}")

            # --- image_info
            meta = await call("image_info_tool", {"image_path": str(sample)})
            report.check("image_info_tool",
                         meta["width"] == 2400 and meta["height"] == 1600,
                         f"{meta['width']}x{meta['height']} {meta['format']} "
                         f"{human(meta['bytes'])}")

            # --- estimate_target
            orig = sample.stat().st_size
            target_kb = max(20, int(orig / 1024 / 4))
            est = await call("estimate_target", {
                "image_path": str(sample), "target_size": target_kb,
                "unit": "KB", "allow_resize": True})
            report.check("estimate_target", est["verdict"] in ("feasible", "unreachable"),
                         f"verdict={est['verdict']} min={est['min_size']}")

            # --- compress_image
            outdir = work / "out"
            res = await call("compress_image", {
                "image_path": str(sample), "target_size": target_kb, "unit": "KB",
                "output_dir": str(outdir), "output_format": "jpeg",
                "allow_resize": True})
            ok = (res["status"] == "ok"
                  and res["final_bytes"] <= target_kb * 1024
                  and Path(res["output_path"]).exists())
            report.check("compress_image",
                         ok, f"{human(res['original_bytes'])} -> "
                             f"{human(res['final_bytes'])} (target {target_kb} KB)"
                             + (f"  {Path(res['output_path']).name}"
                                if res.get("output_path") else ""))

            # --- naming: same target twice must not overwrite
            res2 = await call("compress_image", {
                "image_path": str(sample), "target_size": target_kb, "unit": "KB",
                "output_dir": str(outdir), "output_format": "jpeg",
                "allow_resize": True})
            distinct = (res2.get("output_path") != res.get("output_path")
                        and res2["status"] == "ok")
            report.check("naming (no overwrite)", distinct,
                         Path(res2["output_path"]).name if res2.get("output_path") else "-")

            # --- guard: target >= original must be refused
            guard = await call("compress_image",
                               {"image_path": str(sample), "target_size": 50,
                                "unit": "MB"})
            report.check("guard: target >= original",
                         guard["status"] == "target_too_large"
                         and guard["output_path"] is None,
                         guard["status"])

            # --- batch_compress
            batch = await call("batch_compress", {
                "image_paths": [str(sample)], "target_size": target_kb,
                "unit": "KB", "output_dir": str(work / "batch"),
                "allow_resize": True})
            summary = batch["summary"]
            report.check("batch_compress",
                         summary["compressed"] == 1,
                         f"compressed={summary['compressed']} "
                         f"saved={summary['saved_size']} "
                         f"(status={batch['results'][0]['status']})")


def main() -> int:
    ap = argparse.ArgumentParser(description="Test the PicPress MCP server")
    ap.add_argument("--exe", help="path to picpress-mcp.exe")
    ap.add_argument("--python", action="store_true",
                    help="run the server from source (python -m picpress.mcp_server)")
    ap.add_argument("--keep", action="store_true", help="keep sample/output files")
    args = ap.parse_args()

    if args.python:
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "picpress.mcp_server"],
            env={"PYTHONPATH": str(ROOT / "src")},
        )
        label = f"python -m picpress.mcp_server"
    else:
        exe = Path(args.exe) if args.exe else ROOT / "dist" / "picpress-mcp.exe"
        if not exe.exists():
            print(f"ERROR: {exe} not found.")
            print("Build it first:  python scripts/build.py mcp")
            print("Or test from source:  python scripts/test_mcp.py --python")
            return 2
        params = StdioServerParameters(command=str(exe), args=[])
        label = str(exe)

    work = Path(tempfile.mkdtemp(prefix="picpress-mcp-test_"))
    print(f"Server : {label}")
    print(f"Workdir: {work}")
    print("-" * 72)

    report = Report()
    try:
        asyncio.run(run(params, work, report))
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] client error: {type(exc).__name__}: {exc}")
        report.failed += 1

    print("-" * 72)
    print(f"RESULT: {report.passed} passed, {report.failed} failed")
    if report.failed == 0:
        print("MCP server works correctly. 可以正常连接使用了。")
    if args.keep:
        print(f"Files kept in: {work}")
    else:
        import shutil
        shutil.rmtree(work, ignore_errors=True)

    if sys.stdin and sys.stdin.isatty():
        try:
            input("\nPress Enter to exit / 按回车退出…")
        except EOFError:
            pass
    return 0 if report.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
