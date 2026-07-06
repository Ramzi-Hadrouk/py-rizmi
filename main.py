"""GUI entry point."""
from src.gui.app import LicenseToolApp


def main() -> None:
    app = LicenseToolApp()
    app.mainloop()


if __name__ == "__main__":
    main()
