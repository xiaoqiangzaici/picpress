"""Build PicPress with PyInstaller.

Usage:
    python scripts/build.py                 # all targets, portable folder (default)
    python scripts/build.py gui             # desktop app only
    python scripts/build.py mcp             # MCP server only
    python scripts/build.py all --onefile   # opt-in single-file build

Output (portable folder, default):
    dist/PicPress/PicPress.exe              GUI +_internal/ (zip the folder to share)
    dist/picpress-mcp/picpress-mcp.exe      MCP server +_internal/

Output (--onefile):
    dist/PicPress.exe                       single-file GUI (~55 MB); extracts
                                            ~134 MB to %TEMP% on every launch
    dist/picpress-mcp.exe                   single-file MCP server
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import time
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

    def render(size: int) -> "Image.Image":
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        r = int(size * 0.22)
        d.rounded_rectangle([0, 0, size - 1, size - 1], radius=r,
                            fill=(109, 139, 255, 255))
        d.rounded_rectangle([size // 2, 0, size - 1, size - 1], radius=r,
                            fill=(155, 109, 255, 255))
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

    render(256).save(icon_path, format="ICO",
                     sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
    return icon_path


def run_pyinstaller(args: list[str]) -> None:
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", *args]
    print("\n>>>", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=ROOT)


def build(icon: Path | None, targets: set[str], portable: bool) -> None:
    icon_args = ["--icon", str(icon)] if icon else []
    mode = "--onedir" if portable else "--onefile"

    # --- GUI app ---------------------------------------------------------
    # Standard PySide6 hooks pick up the needed Qt plugins; --collect-all
    # would bloat the exe to ~100 MB.
    if "gui" in targets:
        run_pyinstaller([
            mode,
            "--windowed",
            "--name", "PicPress",
            *icon_args,
            "--paths", str(SRC),
            "--exclude-module", "tkinter",
            str(ROOT / "scripts" / "entry_gui.py"),
        ])

    # --- MCP server ------------------------------------------------------
    # NOTE: do NOT --collect-submodules mcp — mcp.cli calls sys.exit at
    # import time when the optional `typer` dep is missing. Plain import
    # analysis of mcp.server.mcpserver is sufficient.
    if "mcp" in targets:
        run_pyinstaller([
            mode,
            "--console",
            "--name", "picpress-mcp",
            "--paths", str(SRC),
            "--exclude-module", "mcp.cli",
            "--hidden-import", "mcp.server.mcpserver",
            "--hidden-import", "pydantic.deprecated.decorator",
            str(ROOT / "scripts" / "entry_mcp.py"),
        ])


def _mei_dirs() -> set[Path]:
    """PyInstaller onefile extraction dirs currently in %TEMP%."""
    return set(Path(tempfile.gettempdir()).glob("_MEI*"))


def _gui_exe(portable: bool, name: str = "PicPress") -> Path:
    return DIST / name / f"{name}.exe" if portable else DIST / f"{name}.exe"


def smoke_test(targets: set[str], portable: bool) -> None:
    """Quick sanity checks on the built binaries."""
    gui_exe = _gui_exe(portable)
    mcp_exe = _gui_exe(portable, "picpress-mcp")

    if "gui" in targets:
        if not gui_exe.exists():
            raise SystemExit(f"Missing build output: {gui_exe}")
        size = (sum(f.stat().st_size for f in gui_exe.parent.rglob("*") if f.is_file())
                if portable else gui_exe.stat().st_size)
        print(f"OK  {gui_exe}  {size / 1024 / 1024:.1f} MB")

        before = _mei_dirs()
        proc = subprocess.Popen([str(gui_exe)])
        time.sleep(7)
        alive = proc.poll() is None
        # Close it: force-kill every PicPress process, then drop any temp
        # extraction dir this run created (keeps the dev machine clean).
        subprocess.run(["taskkill", "/IM", gui_exe.name, "/F"],
                       capture_output=True) if sys.platform == "win32" else proc.kill()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        time.sleep(1)
        created = _mei_dirs() - before
        for d in created:
            shutil.rmtree(d, ignore_errors=True)

        if not alive:
            raise SystemExit(f"{gui_exe.name} exited immediately (code {proc.returncode})")
        print(f"OK  {gui_exe.name} launches and stays alive"
              f"  ({len(created)} temp dir(s) created, cleaned up)")

    if "mcp" not in targets:
        return

    if not mcp_exe.exists():
        raise SystemExit(f"Missing build output: {mcp_exe}")
    print(f"OK  {mcp_exe}  {mcp_exe.stat().st_size / 1024 / 1024:.1f} MB")

    # MCP handshake smoke test against the packaged exe.
    sys.path.insert(0, str(SRC))
    import asyncio
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
    argv = [a.lower() for a in sys.argv[1:]]
    portable = "--onefile" not in argv  # portable folder is the default
    argv = [a for a in argv if not a.startswith("--")]
    targets = ({"gui", "mcp"} if not argv or "all" in argv
               else set(argv) & {"gui", "mcp"})
    if not targets:
        raise SystemExit("usage: build.py [gui|mcp|all] [--onefile]")

    DIST.mkdir(exist_ok=True)
    BUILD.mkdir(exist_ok=True)
    icon = make_icon()
    print(f"icon: {icon} | targets: {sorted(targets)} | "
          f"mode: {'portable folder' if portable else 'single file'}")
    build(icon, targets, portable)
    smoke_test(targets, portable)
    print("\nBuild complete:")
    for exe in sorted(DIST.glob("*.exe")) + sorted(DIST.glob("*/*.exe")):
        print(f"  {exe}")
