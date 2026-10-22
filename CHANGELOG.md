# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.0] — 2026-10-22

### Added
- **Bilingual UI** — switch between English and 简体中文 at runtime; the window
  rebuilds in place and keeps the file list, results and settings
- **Format options split by extension** — Auto / JPG (`.jpg`) / JPEG (`.jpeg`) /
  PNG (`.png`) / WebP (`.webp`)
- **Collision-free output naming** — files are named `<source>_<target>.<ext>`
  (e.g. `photo_500KB.jpg`); repeats get Explorer-style ` (2)` suffixes, so
  100 KB and 200 KB runs into one folder never overwrite each other
- `--selftest` for the MCP server: six checks without any client, no Python needed
- `scripts/test_mcp.py`: real stdio MCP test client (9 checks, PASS/FAIL output)
- `--onedir` build mode: portable folder, starts faster and writes nothing to `%TEMP%`
- GUI smoke tests; 28 tests total
- Screenshots for the Chinese UI, English UI and the warning dialog

### Fixed
- Warning/info dialogs were unreadable: dark-theme light text leaked onto the
  light dialog surface. Dialogs now use their own light style with dark text
- Combo-box arrows rendered as boxes; replaced with a generated chevron icon
  that is deleted when the app exits
- Language switch left stale summary/status text in the previous language

### Changed
- Dark theme stylesheet is scoped to the main window instead of the whole app

## [0.1.0] — 2026-10-22

### Added
- Core engine: binary-search encoder quality (and optional downscale) to hit an
  exact target size in B / KB / MB
- Guard rail: refuses targets that are not smaller than the original file
  (`target_too_large`), and reports the smallest achievable size otherwise
  (`unreachable`)
- PySide6 desktop app with drag & drop, batch mode, presets, progress and
  before/after comparison
- MCP server (stdio) with `compress_image`, `batch_compress`, `estimate_target`,
  `image_info_tool`, `supported_formats`
- PyInstaller builds (`PicPress.exe`, `picpress-mcp.exe`), MIT license,
  GitHub Actions build workflow, EN/zh-CN READMEs
