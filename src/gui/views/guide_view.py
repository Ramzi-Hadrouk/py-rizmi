"""Tab 5 — Integration Guide for PyQt6."""
from pathlib import Path

import markdown as markdown_lib
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextBrowser

from ..theme import Color


MARKDOWN_CSS = f"""
<style>
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        font-size: 14px;
        line-height: 1.7;
        color: {Color.TEXT};
        background-color: transparent;
        padding: 0px;
    }}
    h1, h2, h3, h4 {{
        color: {Color.TEXT};
        font-weight: 700;
        margin-top: 1.4em;
        margin-bottom: 0.4em;
        line-height: 1.4;
    }}
    h1 {{ font-size: 1.55em; border-bottom: 1px solid {Color.BORDER}; padding-bottom: 0.3em; }}
    h2 {{ font-size: 1.3em; border-bottom: 1px solid {Color.BORDER}; padding-bottom: 0.25em; }}
    h3 {{ font-size: 1.1em; }}
    p {{ margin: 0.55em 0; }}
    a {{ color: {Color.ACCENT}; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    code {{
        font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
        font-size: 0.9em;
        background-color: {Color.PANEL_BG};
        padding: 0.15em 0.3em;
        border-radius: 4px;
        color: {Color.TEXT};
    }}
    pre {{
        background-color: {Color.PANEL_BG};
        border: 1px solid {Color.BORDER};
        border-radius: 8px;
        padding: 12px;
        overflow-x: auto;
        margin: 1em 0;
    }}
    pre code {{
        background: transparent;
        padding: 0;
        border-radius: 0;
        font-size: 0.85em;
        line-height: 1.5;
    }}
    blockquote {{
        border-left: 4px solid {Color.ACCENT};
        margin: 1em 0;
        padding: 0.5em 1em;
        background: {Color.PANEL_BG};
        border-radius: 0 8px 8px 0;
        color: {Color.TEXT};
    }}
    ul, ol {{ padding-left: 1.6em; margin: 0.55em 0; }}
    li {{ margin: 0.2em 0; }}
    hr {{ border: none; border-top: 1px solid {Color.BORDER}; margin: 1.4em 0; }}
    img {{ max-width: 100%; height: auto; border-radius: 8px; }}
</style>
"""


class GuideView(QWidget):
    """View to display the integration guide from markdown.md."""

    def __init__(self, app=None):
        super().__init__()
        self.app = app
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        self.browser.setStyleSheet("""
            QTextBrowser {
                background-color: transparent;
                border: none;
                font-size: 14px;
            }
        """)
        layout.addWidget(self.browser)

        self._load_guide()

    def _load_guide(self) -> None:
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        guide_path = project_root / "markdown.md"

        if not guide_path.exists():
            self.browser.setHtml(
                MARKDOWN_CSS + "<h2>Guide not found</h2>"
                "<p>Expected <code>markdown.md</code> in the project root.</p>"
            )
            return

        try:
            md_text = guide_path.read_text(encoding="utf-8")
        except Exception as exc:
            self.browser.setHtml(
                MARKDOWN_CSS + f"<h2>Error</h2><p>{exc}</p>"
            )
            return

        html_body = markdown_lib.markdown(
            md_text,
            extensions=["fenced_code", "codehilite", "tables", "toc"],
            extension_configs={"codehilite": {"css_class": "highlight"}},
        )

        full_html = f"<!DOCTYPE html><html><head><meta charset='utf-8'>{MARKDOWN_CSS}</head><body>{html_body}</body></html>"
        self.browser.setHtml(full_html)
