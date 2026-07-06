import customtkinter as ctk
import re

class GuideView(ctk.CTkFrame):
    """View to display the integration guide using native CTk widgets."""

    def __init__(self, parent, app=None):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkLabel(self, text="Integration Guide", font=ctk.CTkFont(size=24, weight="bold"))
        header.grid(row=0, column=0, sticky="w", pady=(0, 20))

        # Scrollable Content Area
        self.scroll = ctk.CTkScrollableFrame(self, fg_color=("gray95", "gray13"))
        self.scroll.grid(row=1, column=0, sticky="nsew")
        self.scroll.grid_columnconfigure(0, weight=1)

        self._render_guide()

    def _render_guide(self):
        from pathlib import Path
        import re

        readme_path = Path(__file__).resolve().parent.parent.parent.parent.parent / "README.md"
        guide_md = "No guide found."

        if readme_path.exists():
            with open(readme_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Extract the API section
            match = re.search(r'## Python API / Backend Integration(.*?)(?:\n---|\n## )', content, re.DOTALL)
            if match:
                guide_md = "## Python API / Backend Integration\n" + match.group(1).strip()
            else:
                guide_md = "Could not find 'Python API / Backend Integration' section in README.md"
        
        # Simple Markdown parser to CTk widgets

        lines = guide_md.split('\n')
        row = 0
        in_code_block = False
        code_content = []

        for line in lines:
            if line.startswith('```'):
                if in_code_block:
                    # Render code block
                    code_box = ctk.CTkTextbox(self.scroll, height=150, font=ctk.CTkFont(family="Courier", size=13), fg_color=("gray90", "gray10"))
                    code_box.insert("1.0", "\n".join(code_content))
                    code_box.configure(state="disabled")
                    code_box.grid(row=row, column=0, sticky="ew", pady=(10, 20), padx=10)
                    row += 1
                    in_code_block = False
                    code_content = []
                else:
                    in_code_block = True
                continue
            
            if in_code_block:
                code_content.append(line)
                continue
            
            if not line.strip():
                continue

            if line.startswith('# '):
                lbl = ctk.CTkLabel(self.scroll, text=line[2:], font=ctk.CTkFont(size=22, weight="bold"), anchor="w", justify="left")
                lbl.grid(row=row, column=0, sticky="w", pady=(20, 10), padx=10)
            elif line.startswith('## '):
                lbl = ctk.CTkLabel(self.scroll, text=line[3:], font=ctk.CTkFont(size=18, weight="bold"), anchor="w", justify="left")
                lbl.grid(row=row, column=0, sticky="w", pady=(15, 5), padx=10)
            elif line.startswith('- '):
                # Handle bold text in bullets
                text = line[2:]
                text = re.sub(r'\*\*(.*?)\*\*', r'\1', text) # Strip bold for now as CTkLabel doesn't support inline rich text easily
                lbl = ctk.CTkLabel(self.scroll, text="\u2022 " + text, font=ctk.CTkFont(size=14), anchor="w", justify="left", wraplength=600)
                lbl.grid(row=row, column=0, sticky="w", pady=2, padx=20)
            else:
                lbl = ctk.CTkLabel(self.scroll, text=line, font=ctk.CTkFont(size=14), anchor="w", justify="left", wraplength=600)
                lbl.grid(row=row, column=0, sticky="w", pady=5, padx=10)
            
            row += 1
