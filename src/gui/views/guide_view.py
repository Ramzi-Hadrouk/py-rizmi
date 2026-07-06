"""Tab 5 — Integration Guide for PyQt6."""
import re
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextBrowser

class GuideView(QWidget):
    """View to display the integration guide using QTextBrowser markdown support."""
    
    def __init__(self, app=None):
        super().__init__()
        self.app = app
        self._build()
        
    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        # Using a custom stylesheet to make markdown look good in Qt
        self.browser.setStyleSheet("""
            QTextBrowser {
                background-color: transparent;
                border: none;
                font-size: 14px;
            }
        """)
        layout.addWidget(self.browser)
        
        self._load_markdown()
        
    def _load_markdown(self) -> None:
        readme_path = Path(__file__).resolve().parent.parent.parent.parent / "README.md"
        guide_md = "No guide found."
        
        if readme_path.exists():
            try:
                with open(readme_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Extract the API section
                match = re.search(r'## Python API / Backend Integration(.*?)(?:\n---|\n## )', content, re.DOTALL)
                if match:
                    guide_md = "## Python API / Backend Integration\n" + match.group(1).strip()
                else:
                    guide_md = "Could not find 'Python API / Backend Integration' section in README.md"
            except Exception as e:
                guide_md = f"Error reading README.md: {e}"
                
        self.browser.setMarkdown(guide_md)
