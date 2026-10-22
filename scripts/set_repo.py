"""Point the project at your own GitHub repo (replaces the placeholder URL).

Usage:
    python scripts/set_repo.py <owner>/<repo>

Rewrites README.md, README.zh-CN.md, pyproject.toml and the in-app GitHub
button constant in src/picpress/gui.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = "your-name/picpress"

TARGETS = [
    ROOT / "README.md",
    ROOT / "README.zh-CN.md",
    ROOT / "pyproject.toml",
    ROOT / "src" / "picpress" / "gui.py",
]


def main() -> int:
    if len(sys.argv) != 2 or "/" not in sys.argv[1]:
        print(__doc__)
        return 2
    new = sys.argv[1].strip().strip("/")

    changed = 0
    for path in TARGETS:
        if not path.exists():
            print(f"skip (missing): {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        if OLD not in text:
            print(f"skip (already set): {path.relative_to(ROOT)}")
            continue
        count = text.count(OLD)
        path.write_text(text.replace(OLD, new), encoding="utf-8")
        print(f"updated {path.relative_to(ROOT)}  ({count} occurrence(s))")
        changed += count

    if changed == 0:
        print("\nNothing to change — the repo URL may already be set.")
        return 0

    print(f"\nRepo set to: https://github.com/{new}")
    print("Rebuild the exe so the in-app GitHub button picks up the new URL:")
    print("    python scripts/build.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
