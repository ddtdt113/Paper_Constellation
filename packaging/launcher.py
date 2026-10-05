"""Entry point for the frozen app (PyInstaller needs a script, not a module)."""
import sys

from paper_constellation.ui.main import main

if __name__ == "__main__":
    sys.exit(main())
