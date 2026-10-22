"""PyInstaller entry stub for the GUI app."""

import sys
from pathlib import Path

# When frozen, the picpress package is bundled; when run from source the
# src layout is added to sys.path by the --paths build flag.
from picpress.gui import main

if __name__ == "__main__":
    sys.exit(main())
