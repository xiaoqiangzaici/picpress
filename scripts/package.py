"""Zip the portable build folders for distribution.

Usage:
    python scripts/build.py        # build folders first
    python scripts/package.py      # → dist/PicPress-portable.zip,
                                   #   dist/picpress-mcp-portable.zip,
                                   #   dist/SHA256SUMS.txt
"""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
TARGETS = [("PicPress", "PicPress-portable.zip"),
           ("picpress-mcp", "picpress-mcp-portable.zip")]


def zip_folder(folder: Path, out: Path) -> None:
    if not folder.is_dir():
        raise SystemExit(f"Missing build output: {folder}  (run scripts/build.py first)")
    out.unlink(missing_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for f in sorted(folder.rglob("*")):
            if f.is_file():
                zf.write(f, f.relative_to(folder.parent))
    size = out.stat().st_size / 1024 / 1024
    print(f"{out.name}  {size:.1f} MB")


def main() -> None:
    lines: list[str] = []
    for folder_name, zip_name in TARGETS:
        out = DIST / zip_name
        zip_folder(DIST / folder_name, out)
        digest = hashlib.sha256(out.read_bytes()).hexdigest()
        lines.append(f"{digest}  {zip_name}")

    sums = DIST / "SHA256SUMS.txt"
    sums.write_text("\n".join(lines) + "\n", encoding="ascii")
    print(f"\n{sums.name}:")
    for line in lines:
        print(f"  {line}")


if __name__ == "__main__":
    main()
