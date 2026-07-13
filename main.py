import sys
from PyQt6.QtWidgets import QApplication

from py_rizmi.gui.app import LicenseToolApp
from py_rizmi.gui.theme import apply_theme

def main():
    app = QApplication(sys.argv)
    apply_theme(app)

    window = LicenseToolApp()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
