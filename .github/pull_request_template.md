<!-- Thanks for the PR! A few things that make review fast: -->

## What does this change?

<!-- One or two sentences. Link the issue if there is one: Fixes #12 -->

## Which part?

- [ ] Core engine (`src/picpress/core.py`)
- [ ] Desktop UI (`gui.py` / `i18n.py`)
- [ ] MCP server (`mcp_server.py`)
- [ ] Build / CI / docs

## Checklist

- [ ] `python tests/test_core.py` passes
- [ ] `python tests/test_mcp_server.py` passes
- [ ] `python tests/test_gui_smoke.py` passes (if UI touched)
- [ ] If UI text changed: added to **both** `en` and `zh` dicts in `i18n.py`
- [ ] If behaviour changed: updated `CHANGELOG.md`
- [ ] Core engine stays free of UI imports

## Screenshots (if UI changed)

<!-- Before / after helps a lot. -->
