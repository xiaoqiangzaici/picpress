"""Build PicPress.exe (GUI) and picpress-mcp.exe (MCP server) with PyInstaller.

Usage:  python scripts/build.py
Output: dist/PicPress.exe, dist/picpress-mcp.exe
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
DIST = ROOT / "dist"
BUILD = ROOT / "build"
ASSETS = ROOT / "docs" / "assets"


def make_icon() -> Path | None:
    """Generate a multi-size .ico matching the in-app icon."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None

    icon_path = ASSETS / "picpress.ico"
    ASSETS.mkdir(parents=True, exist_ok=True)

    def render(size: int) -> Image.Image:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        # Gradient-ish tile: two overlapping rounded rects
        r = int(size * 0.22)
        d.rounded_rectangle([0, 0, size - 1, size - 1], radius=r,
                            fill=(109, 139, 255, 255))
        d.rounded_rectangle([size // 2, 0, size - 1, size - 1], radius=r,
                            fill=(155, 109, 255, 255))
        # Shrink arrow
        w = max(2, int(size * 0.07))
        cx = size // 2
        d.line([(cx, int(size * 0.24)), (cx, int(size * 0.52))],
               fill="white", width=w)
        d.polygon(
            [(int(cx - size * 0.13), int(size * 0.46)),
             (int(cx + size * 0.13), int(size * 0.46)),
             (cx, int(size * 0.60))],
            fill="white")
        d.line([(int(size * 0.26), int(size * 0.74)),
                (int(size * 0.74), int(size * 0.74))],
               fill="white", width=w)
        return img

    sizes = [16, 24, 32, 48, 64, 128, 256]
    render(256).save(icon_path, format="ICO",
                     sizes=[(s, s) for s in sizes])
    return icon_path


def run_pyinstaller(args: list[str]) -> None:
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", *args]
    print("\n>>>", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=ROOT)


def build(icon: Path | None, targets: set[str]) -> None:
    icon_args = ["--icon", str(icon)] if icon else []

    # --- GUI exe (windowed, single file) ---------------------------------
    # Standard PyInstaller PySide6 hooks pick up the needed Qt plugins;
    # --collect-all would bloat the exe to ~100 MB.
    if "gui" in targets:
        run_pyinstaller([
            "--onefile",
            "--windowed",
            "--name", "PicPress",
            *icon_args,
            "--paths", str(SRC),
            "--exclude-module", "tkinter",
            str(ROOT / "scripts" / "entry_gui.py"),
        ])

    # --- MCP server exe (console, single file) ---------------------------
    # NOTE: do NOT --collect-submodules mcp — mcp.cli calls sys.exit at
    # import time when the optional `typer` dep is missing. Plain import
    # analysis of mcp.server.mcpserver is sufficient.
    if "mcp" in targets:
        run_pyinstaller([
            "--onefile",
            "--console",
            "--name", "picpress-mcp",
            "--paths", str(SRC),
            "--exclude-module", "mcp.cli",
            "--hidden-import", "mcp.server.mcpserver",
            "--hidden-import", "pydantic.deprecated.decorator",
            str(ROOT / "scripts" / "entry_mcp.py"),
        ])


def smoke_test(targets: set[str]) -> None:
    """Quick sanity checks on the built binaries."""
    gui_exe = DIST / "PicPress.exe"
    mcp_exe = DIST / "picpress-mcp.exe"

    if "gui" in targets:
        if not gui_exe.exists():
            raise SystemExit(f"Missing build output: {gui_exe}")
        print(f"OK  {gui_exe.name}  {gui_exe.stat().st_size / 1024 / 1024:.1f} MB")

        # Launch smoke test: the windowed exe must stay alive for a few seconds.
        import time
        proc = subprocess.Popen([str(gui_exe)])
        time.sleep(6)
        alive = proc.poll() is None
        if alive:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
        else:
            raise SystemExit(f"PicPress.exe exited immediately (code {proc.returncode})")
        print("OK  PicPress.exe launches and stays alive")

    if "mcp" not in targets:
        return

    if not mcp_exe.exists():
        raise SystemExit(f"Missing build output: {mcp_exe}")
    print(f"OK  {mcp_exe.name}  {mcp_exe.stat().st_size / 1024 / 1024:.1f} MB")

    # MCP handshake smoke test against the packaged exe.
    sys.path.insert(0, str(SRC))
    import asyncio
    import json
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def probe():
        params = StdioServerParameters(command=str(mcp_exe), args=[])
        async with stdio_client(params) as (r, w):
            async with ClientSession(r, w) as s:
                await s.initialize()
                tools = await s.list_tools()
                return sorted(t.name for t in tools.tools)

    names = asyncio.run(probe())
    print("MCP tools from packaged exe:", names)
    assert "compress_image" in names, names


if __name__ == "__main__":
    args = [a.lower() for a in sys.argv[1:]]
    targets = {"gui", "mcp"} if not args or "all" in args else set(args) & {"gui", "mcp"}
    if not targets:
        raise SystemExit("usage: build.py [gui|mcp|all]")
    DIST.mkdir(exist_ok=True)
    BUILD.mkdir(exist_ok=True)
    icon = make_icon()
    print("icon:", icon, "| targets:", sorted(targets))
    build(icon, targets)
    smoke_test(targets)
    print("\nBuild complete:")
    for f in sorted(DIST.glob("*.exe")):
        print(f"  {f}  ({f.stat().st_size / 1024 / 1024:.1f} MB)")
