"""Convenience entry point for running the GUI directly with `python main.py`.

For the installed CLI command, use: rizmi gui
For production use, prefer: uv run rizmi gui

This file defers all PyQt6 imports so that a bare `import main` (or lint/analysis
tooling scanning the file) does not fail when the [gui] extra is not installed.
"""
import sys


def main() -> None:
    """Launch the py-Rizmi GUI, with a friendly error if [gui] extra is missing."""
    try:
        from PyQt6.QtWidgets import QApplication  # type: ignore[import]
        from py_rizmi.gui.app import LicenseToolApp  # type: ignore[import]
        from py_rizmi.gui.theme import apply_theme  # type: ignore[import]
    except ModuleNotFoundError as exc:
        print(
            f"\nError: GUI dependencies are not installed (missing: {exc.name}).\n"
            "Install them with:\n"
            "    pip install py-rizmi[gui]\n",
            file=sys.stderr,
        )
        sys.exit(1)

    app = QApplication(sys.argv)
    apply_theme(app)

    window = LicenseToolApp()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
