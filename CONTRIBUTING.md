# Contributing to PicPress

Thanks for taking the time to contribute! This guide keeps things simple.

## Ways to help

- 🐛 **Report a bug** — open an issue with steps to reproduce and your Windows version
- 💡 **Suggest a feature** — describe the problem first, then the proposed solution
- 🌍 **Add a language** — copy one dict in `src/picpress/i18n.py` and translate the values
- 🧪 **Improve tests** — new edge cases are always welcome
- 📝 **Improve docs** — README (EN/zh-CN), screenshots, wording

## Development setup

```bash
git clone https://github.com/your-name/picpress.git
cd picpress
pip install -e ".[dev]"     # core + GUI + MCP + build tools

python -m picpress          # run the desktop app from source
python scripts/test_mcp.py --python   # exercise the MCP server
```

Requirements: Python 3.10+ (3.12/3.13 recommended), Windows for the GUI.

## Project layout

```
src/picpress/
├── core.py        # compression engine — UI-agnostic, used by both front-ends
├── i18n.py        # EN / zh-CN strings
├── gui.py         # PySide6 desktop app
├── mcp_server.py  # stdio MCP server (+ --selftest)
└── __main__.py    # python -m picpress → GUI
scripts/           # build / screenshots / MCP test client
tests/             # engine, MCP protocol, GUI smoke
```

**Keep `core.py` free of UI imports.** Both the GUI and the MCP server depend
on it; that separation is why the two front-ends stay in sync.

## Tests

```bash
python tests/test_core.py        # engine (19)
python tests/test_mcp_server.py  # MCP protocol (5)
python tests/test_gui_smoke.py   # GUI (4, needs a desktop session)
```

All three must pass before a PR is merged. CI runs them on Windows.

## Code style

- Standard library + Pillow + PySide6 + the MCP SDK; avoid new dependencies
  without discussion
- Type hints on public functions, docstrings on modules and public APIs
- UI text goes through `i18n.t()` — never hardcode user-facing strings
- Keep commits focused; conventional-ish prefixes (`feat:`, `fix:`, `docs:`) help

## Adding a language

1. Copy the `"en"` dict in `src/picpress/i18n.py`, rename the key (e.g. `"ja"`)
2. Translate every value (a test asserts both dicts share the same keys)
3. Add the button in `gui.py` → `_build_header()`'s language list
4. Add `<details>` screenshots to the README if you can

## Pull requests

1. Fork, create a branch (`feat/target-presets`)
2. Make the change, add/adjust tests
3. Run all three test files
4. Open the PR and describe the behaviour change

## License

By contributing you agree your work is released under the [MIT License](LICENSE).
