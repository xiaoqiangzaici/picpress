# PicPress

**Compress photos to the exact size you choose.**
把照片压缩到你指定的体积 —— 精确到 B / KB / MB。

[English](README.md) · [简体中文](README.zh-CN.md)

---

PicPress is a focused image-compression tool: you pick a target file size
(e.g. `500 KB`), and PicPress re-encodes the photo to fit it — with the
**highest quality that meets the target**. If the target is *not* smaller
than the original file, PicPress refuses and tells you why. It never
"compresses" a file into a bigger one.

It ships in two forms:

| Form | What it is | Best for |
|---|---|---|
| **PicPress.exe** | Desktop app with a modern dark UI | Everyday use, sharing with friends |
| **picpress-mcp** | Local [MCP](https://modelcontextprotocol.io) server (stdio) | Letting AI agents compress photos for you |

## ✨ Features

- 🎯 **Exact target size** — type `500` and pick `B`, `KB` or `MB`; or use one-tap presets
- 🚫 **Compression only** — if the target ≥ original size, you get a clear warning instead of a bogus result
- 🔍 **Honest limits** — when a target is unreachable even at minimum quality, PicPress reports the smallest size it *can* achieve
- 🧠 **Smart encoding** — binary-searches JPEG/WebP/PNG quality (and, only if you allow it, a gentle downscale) to land under the target at the best visual quality
- 🈶 **Bilingual UI** — switch between English and 简体中文 instantly; the window rebuilds in place and keeps your files and settings
- 🏷 **Collision-free naming** — outputs carry the target size (`photo_500KB.jpg`, `photo_1MB.jpg`), and repeats get Explorer-style ` (2)` suffixes, so 100 KB and 200 KB runs never overwrite each other
- 🖼 **Explicit format control** — JPG (`.jpg`), JPEG (`.jpeg`), PNG, WebP, or Auto (picks WebP when the image has transparency)
- 🔒 **Privacy-friendly** — EXIF metadata (GPS, camera info) is stripped by default; opt in to keep it
- 📦 **Batch mode** — drop a folder of photos, compress them all to the same target
- 🤖 **MCP server** — five tools agents can call: `compress_image`, `batch_compress`, `estimate_target`, `image_info_tool`, `supported_formats`
- 🪟 **Portable exe** — single-file Windows builds, no installer, no Python required

## 📸 Screenshot

![PicPress UI](docs/assets/screenshot.png)

<details>
<summary>English UI / 英文界面</summary>

![PicPress UI in English](docs/assets/screenshot-en.png)

</details>

<details>
<summary>Warning dialog (light surface, dark text) / 警示弹窗</summary>

![PicPress warning dialog](docs/assets/screenshot-dialog.png)

</details>

## 🚀 Quick Start (desktop app)

1. Grab `PicPress.exe` from the [Releases](../../releases) page
2. Double-click it — that's it. No installation.
3. Drag photos in (or **Add files** / **Add folder**), set the target size, hit **Compress**

> Windows SmartScreen may warn about an unsigned exe — choose
> "More info → Run anyway". Builds are reproducible from source (see below).

### From source

```bash
git clone https://github.com/your-name/picpress.git
cd picpress
pip install -e ".[all]"        # core + GUI + MCP
python -m picpress             # launch the desktop app
```

## 🤖 MCP Server (for AI agents)

PicPress runs as a local [Model Context Protocol](https://modelcontextprotocol.io)
server over stdio. Agents can then compress photos on your machine with
precise size constraints.

### Option A — use the standalone exe

```json
{
  "mcpServers": {
    "picpress": {
      "command": "C:\\path\\to\\picpress-mcp.exe",
      "args": []
    }
  }
}
```

### Option B — run from source

```json
{
  "mcpServers": {
    "picpress": {
      "command": "python",
      "args": ["-m", "picpress.mcp_server"],
      "env": { "PYTHONPATH": "C:\\path\\to\\picpress\\src" }
    }
  }
}
```

Drop this into your client's MCP config (e.g. Claude Desktop's
`claude_desktop_config.json`, Cursor's `.cursor/mcp.json`, or WorkBuddy's
`~/.workbuddy/mcp.json`).

### Tools

| Tool | Purpose |
|---|---|
| `compress_image` | Compress one image to a target size |
| `batch_compress` | Compress many images to the same target |
| `estimate_target` | Check feasibility *before* compressing |
| `image_info_tool` | Dimensions / format / file size |
| `supported_formats` | List accepted inputs, outputs and units |

All results are structured JSON with a `status` field:
`ok` · `target_too_large` · `unreachable` · `error`.

## 📖 How it works

1. The target (e.g. `500 KB`) is converted to bytes
2. **Guard rail:** if target ≥ original file size → `target_too_large`, nothing is written
3. PicPress binary-searches encoder quality (highest quality whose output fits)
4. If quality alone can't reach it and you allowed downscaling, it searches for
   the *least* downscale that fits
5. If still unreachable → `unreachable`, with the smallest achievable size reported

You always get the best-looking file that fits your budget — never bigger,
never silently wrong.

## 🛠 Build the exes yourself

```bash
pip install -e ".[dev]"
python scripts/build.py
# → dist/PicPress.exe, dist/picpress-mcp.exe
```

## 🧩 Roadmap

- [ ] Resize-to-target-width helper
- [ ] Drag-in-place recompression history / undo
- [ ] macOS & Linux builds in CI
- [ ] Localized UI (EN/ZH switcher)

## 🤝 Contributing

Issues and PRs are welcome. Please keep the core engine (`src/picpress/core.py`)
UI-agnostic — both the desktop app and the MCP server depend on it.

```bash
python tests/test_core.py        # engine unit tests (19)
python tests/test_mcp_server.py  # MCP protocol tests (5)
python tests/test_gui_smoke.py   # GUI smoke tests (4, needs a desktop session)
```

## 📄 License

[MIT](LICENSE) — free for personal and commercial use.

---

*PicPress only compresses. If your target is bigger than the original file,
that's not compression — and PicPress will tell you so.* 
