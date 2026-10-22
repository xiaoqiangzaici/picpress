"""Allow ``python -m picpress`` to launch the desktop app."""

from picpress.gui import main

if __name__ == "__main__":
    raise SystemExit(main())
