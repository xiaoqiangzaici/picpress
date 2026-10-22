"""Publish this repository to GitHub using the REST API.

Useful when `git push` cannot reach github.com directly (some networks allow
`api.github.com` but block the web/git endpoints).

Usage:
    set GITHUB_TOKEN=ghp_xxx            # Windows (or export on macOS/Linux)
    python scripts/publish_github.py <owner>/<repo> [--dry-run]

The token needs the `repo` scope, plus `workflow` if you want to publish the
GitHub Actions file (.github/workflows/build.yml). Classic tokens are created at
https://github.com/settings/tokens — revoke it when you are done.

What it does:
  1. creates the repo if it does not exist (public by default)
  2. sets the description and topics
  3. uploads every tracked project file as ONE commit on the target branch

Release assets (the zips) are NOT uploaded — do that on the Releases page, it is
both faster and more reliable for large binaries.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.github.com"

# Directories/files that are build output, caches or local scratch space.
EXCLUDE_DIRS = {
    ".git", "build", "dist", "release", "__pycache__", "_tmp", "_tmp_mcp",
    ".venv", "venv", "env", ".idea", ".vscode", ".ruff_cache", ".pytest_cache",
    "demo_photos", "demo_out",
}
EXCLUDE_SUFFIXES = (".spec", ".pyc", ".log", ".swp")

DEFAULT_DESCRIPTION = (
    "Compress photos to an exact target size (B/KB/MB) — desktop app + MCP server for AI agents"
)
DEFAULT_TOPICS = [
    "image-compression", "photo", "jpeg", "webp", "mcp", "mcp-server",
    "pyside6", "windows", "desktop-app", "python",
]


def api(method: str, path: str, token: str, payload: dict | None = None) -> tuple[int, dict | list | None]:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(f"{API}{path}", data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode()
            return resp.status, (json.loads(body) if body.strip() else None)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, {"message": body[:300]}
    except urllib.error.URLError as exc:
        print(f"\nNetwork error talking to api.github.com: {exc.reason}")
        sys.exit(1)


def collect_files() -> list[Path]:
    files: list[Path] = []
    for path in sorted(ROOT.rglob("*")):
        rel = path.relative_to(ROOT)
        if not path.is_file():
            continue
        if any(part in EXCLUDE_DIRS for part in rel.parts):
            continue
        if path.suffix.lower() in EXCLUDE_SUFFIXES:
            continue
        if rel.name in {"Thumbs.db", ".DS_Store", "demo_shot.png", "_combo_test.png"}:
            continue
        files.append(path)
    return files


def create_repo(owner: str, name: str, token: str, login: str, private: bool) -> bool:
    status, body = api("GET", f"/repos/{owner}/{name}", token)
    if status == 200:
        print(f"repo exists: {owner}/{name}")
        return False
    if status not in (404, 403):
        print(f"unexpected response while checking repo: {status} {body}")
    payload = {
        "name": name,
        "description": DEFAULT_DESCRIPTION,
        "private": private,
        "has_issues": True,
        "has_wiki": False,
        "has_projects": False,
        "auto_init": False,
    }
    path = "/user/repos" if owner == login else f"/orgs/{owner}/repos"
    status, body = api("POST", path, token, payload)
    if status not in (200, 201):
        print(f"failed to create repo: {status} {body}")
        sys.exit(1)
    print(f"created repo: {owner}/{name}")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Publish PicPress to GitHub via REST API")
    ap.add_argument("repository", help="owner/repo, e.g. xiaoqiang/picpress")
    ap.add_argument("--branch", default="main")
    ap.add_argument("--private", action="store_true", help="create a private repo")
    ap.add_argument("--dry-run", action="store_true", help="only list the files")
    ap.add_argument("--message", default="Initial commit: PicPress")
    args = ap.parse_args()

    files = collect_files()
    total = sum(f.stat().st_size for f in files)
    print(f"{len(files)} files, {total / 1024:.0f} KB to publish")
    if args.dry_run:
        for f in files:
            print("  ", f.relative_to(ROOT))
        return 0

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print("\nGITHUB_TOKEN is not set.")
        print("Create a token at https://github.com/settings/tokens (scopes: repo, workflow)")
        print("then:  set GITHUB_TOKEN=ghp_xxx   (Windows cmd)")
        return 2

    if "/" not in args.repository:
        print("repository must look like owner/repo")
        return 2
    owner, name = args.repository.split("/", 1)

    status, me = api("GET", "/user", token)
    if status != 200 or not isinstance(me, dict):
        print(f"token check failed: {status} {me}")
        return 1
    login = me.get("login", "")
    print(f"authenticated as {login}")

    create_repo(owner, name, token, login, args.private)

    # Repo metadata (best effort).
    api("PATCH", f"/repos/{owner}/{name}", token,
        {"description": DEFAULT_DESCRIPTION, "homepage": f"https://github.com/{owner}/{name}"})
    api("PUT", f"/repos/{owner}/{name}/topics", token, {"names": DEFAULT_TOPICS})

    # Current branch head, if any.
    status, ref = api("GET", f"/repos/{owner}/{name}/git/ref/heads/{args.branch}", token)
    parent_sha = ref["object"]["sha"] if status == 200 and isinstance(ref, dict) else None
    base_tree = None
    if parent_sha:
        status, commit = api("GET", f"/repos/{owner}/{name}/git/commits/{parent_sha}", token)
        if status == 200 and isinstance(commit, dict):
            base_tree = commit["tree"]["sha"]

    # Upload blobs (one call per file).
    entries = []
    for i, path in enumerate(files, 1):
        rel = path.relative_to(ROOT).as_posix()
        content = base64.b64encode(path.read_bytes()).decode()
        status, blob = api("POST", f"/repos/{owner}/{name}/git/blobs", token,
                           {"content": content, "encoding": "base64"})
        if status not in (200, 201) or not isinstance(blob, dict):
            hint = ""
            if rel.startswith(".github/workflows") and status in (403, 404):
                hint = "  → the token probably lacks the `workflow` scope"
            print(f"  failed: {rel} ({status}){hint}")
            return 1
        entries.append({"path": rel, "mode": "100644", "type": "blob", "sha": blob["sha"]})
        print(f"  [{i}/{len(files)}] {rel}")

    tree_payload: dict = {"tree": entries}
    if base_tree:
        tree_payload["base_tree"] = base_tree
    status, tree = api("POST", f"/repos/{owner}/{name}/git/trees", token, tree_payload)
    if status not in (200, 201):
        print(f"failed to create tree: {status} {tree}")
        return 1

    commit_payload = {"message": args.message, "tree": tree["sha"]}
    if parent_sha:
        commit_payload["parents"] = [parent_sha]
    status, commit = api("POST", f"/repos/{owner}/{name}/git/commits", token, commit_payload)
    if status not in (200, 201):
        print(f"failed to create commit: {status} {commit}")
        return 1

    if parent_sha:
        status, _ = api("PATCH", f"/repos/{owner}/{name}/git/refs/heads/{args.branch}", token,
                        {"sha": commit["sha"], "force": False})
    else:
        status, _ = api("POST", f"/repos/{owner}/{name}/git/refs", token,
                        {"ref": f"refs/heads/{args.branch}", "sha": commit["sha"]})
    if status not in (200, 201):
        print(f"failed to update branch: {status}")
        return 1

    print(f"\nPublished: https://github.com/{owner}/{name}")
    print("Next: create a release and upload the zips from dist/")
    print(f"      https://github.com/{owner}/{name}/releases/new")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
