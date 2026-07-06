"""Tab 2 — Keypair Management for PyQt6."""
import os
import tempfile
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTextEdit, QComboBox, QFileDialog, QScrollArea, QFrame,
    QStackedWidget, QMessageBox, QApplication, QLineEdit
)
from PyQt6.QtCore import Qt

from ...core.keypair import KeyPairManager
from ..theme import Color
from ..widgets.step_card import StepCard

class KeyManagerTab(QWidget):
    """Manage RSA keypairs — generate, load, and validate."""
    
    def __init__(self, app=None):
        super().__init__()
        self.app = app
        self._temp_files = []
        self._active_source = "generate"
        self._build()
        
    def _build(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background-color: transparent;")
        
        content = QWidget()
        content.setStyleSheet("background-color: transparent;")
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(20)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        scroll.setWidget(content)
        main_layout.addWidget(scroll)
        
        self._build_source_card()
        self._build_validate_card()
        
    def _build_source_card(self) -> None:
        card = StepCard(step=1, title="Key Source")
        self.content_layout.addWidget(card)
        
        # Segmented switcher logic
        switcher = QFrame()
        switcher_layout = QHBoxLayout(switcher)
        switcher_layout.setContentsMargins(0, 0, 0, 14)
        
        self.btn_gen_mode = QPushButton("⚙  Generate New Keypair")
        self.btn_load_mode = QPushButton("📂  Load Existing Keys")
        
        # Style as segmented buttons
        style = f"""
            QPushButton {{
                background-color: {Color.PANEL_BG};
                border: 1px solid {Color.BORDER};
                padding: 8px;
                font-weight: bold;
                color: {Color.FG_MUTED};
            }}
            QPushButton:checked {{
                background-color: {Color.ACCENT};
                color: white;
            }}
        """
        
        self.btn_gen_mode.setStyleSheet(style + "border-top-left-radius: 6px; border-bottom-left-radius: 6px;")
        self.btn_load_mode.setStyleSheet(style + "border-top-right-radius: 6px; border-bottom-right-radius: 6px;")
        
        self.btn_gen_mode.setCheckable(True)
        self.btn_load_mode.setCheckable(True)
        self.btn_gen_mode.setChecked(True)
        
        switcher_layout.addWidget(self.btn_gen_mode)
        switcher_layout.addWidget(self.btn_load_mode)
        card.body_layout.addWidget(switcher)
        
        self.stack = QStackedWidget()
        card.body_layout.addWidget(self.stack)
        
        # Connect switcher
        self.btn_gen_mode.clicked.connect(lambda: self._set_mode("generate"))
        self.btn_load_mode.clicked.connect(lambda: self._set_mode("load"))
        
        self._build_generate_panel()
        self._build_load_panel()
        
    def _set_mode(self, mode: str):
        self._active_source = mode
        if mode == "generate":
            self.btn_gen_mode.setChecked(True)
            self.btn_load_mode.setChecked(False)
            self.stack.setCurrentIndex(0)
        else:
            self.btn_gen_mode.setChecked(False)
            self.btn_load_mode.setChecked(True)
            self.stack.setCurrentIndex(1)
            
    def _build_generate_panel(self) -> None:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Controls
        ctrl = QHBoxLayout()
        lbl_size = QLabel("Key Size:")
        lbl_size.setStyleSheet(f"font-weight: bold; color: {Color.FG_MUTED};")
        ctrl.addWidget(lbl_size)
        
        self.combo_size = QComboBox()
        self.combo_size.addItems([str(s) for s in KeyPairManager.KEY_SIZES])
        self.combo_size.setCurrentText(str(KeyPairManager.DEFAULT_KEY_SIZE))
        ctrl.addWidget(self.combo_size)
        
        btn_gen = QPushButton("⚙  Generate Keypair")
        btn_gen.setStyleSheet(f"background-color: {Color.ACCENT}; color: white; font-weight: bold;")
        btn_gen.clicked.connect(self._on_generate)
        ctrl.addWidget(btn_gen)
        
        self.lbl_gen_info = QLabel("")
        ctrl.addWidget(self.lbl_gen_info)
        ctrl.addStretch()
        layout.addLayout(ctrl)
        
        # PEM Side-by-side
        pem_layout = QHBoxLayout()
        layout.addLayout(pem_layout)
        
        def _make_pem_card(title, icon):
            frm = QFrame()
            frm.setObjectName("Panel")
            l = QVBoxLayout(frm)
            
            hdr = QHBoxLayout()
            lbl_ico = QLabel(icon)
            lbl_title = QLabel(title)
            lbl_title.setStyleSheet("font-weight: bold;")
            hdr.addWidget(lbl_ico)
            hdr.addWidget(lbl_title)
            hdr.addStretch()
            l.addLayout(hdr)
            
            txt = QTextEdit()
            txt.setReadOnly(True)
            txt.setStyleSheet("font-family: monospace; font-size: 11px;")
            txt.setFixedHeight(140)
            l.addWidget(txt)
            
            btns = QHBoxLayout()
            btns.setAlignment(Qt.AlignmentFlag.AlignLeft)
            btn_save = QPushButton("💾  Save")
            btn_copy = QPushButton("📋  Copy")
            btns.addWidget(btn_save)
            btns.addWidget(btn_copy)
            l.addLayout(btns)
            
            return frm, txt, btn_save, btn_copy
            
        p_frm, self.txt_priv, p_save, p_copy = _make_pem_card("Private Key", "🔒")
        p_save.setStyleSheet(f"background-color: {Color.WARNING};")
        p_save.clicked.connect(self._save_private)
        p_copy.clicked.connect(self._copy_private)
        pem_layout.addWidget(p_frm)
        
        u_frm, self.txt_pub, u_save, u_copy = _make_pem_card("Public Key", "🔓")
        u_save.clicked.connect(self._save_public)
        u_copy.clicked.connect(self._copy_public)
        pem_layout.addWidget(u_frm)
        
        self.stack.addWidget(panel)
        
    def _build_load_panel(self) -> None:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        
        lbl_tip = QLabel("Browse for .pem files on disk, or paste PEM content directly from clipboard.")
        lbl_tip.setStyleSheet(f"color: {Color.FG_MUTED};")
        layout.addWidget(lbl_tip)
        
        def _make_load_row(title, attr_prefix):
            lbl = QLabel(title)
            lbl.setStyleSheet("font-weight: bold;")
            layout.addWidget(lbl)
            
            row = QHBoxLayout()
            entry = QLineEdit()
            entry.setReadOnly(True)
            setattr(self, f"{attr_prefix}_entry", entry)
            row.addWidget(entry)
            
            btn_browse = QPushButton("Browse…")
            btn_paste = QPushButton("Paste")
            row.addWidget(btn_browse)
            row.addWidget(btn_paste)
            
            setattr(self, f"{attr_prefix}_btn_browse", btn_browse)
            setattr(self, f"{attr_prefix}_btn_paste", btn_paste)
            layout.addLayout(row)
            
        _make_load_row("🔒  Private Key File:", "priv")
        
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background-color: {Color.BORDER};")
        layout.addWidget(div)
        
        _make_load_row("🔓  Public Key File:", "pub")
        
        self.priv_btn_browse.clicked.connect(self._browse_priv)
        self.pub_btn_browse.clicked.connect(self._browse_pub)
        self.priv_btn_paste.clicked.connect(self._paste_priv)
        self.pub_btn_paste.clicked.connect(self._paste_pub)
        
        self.stack.addWidget(panel)
        
    def _build_validate_card(self) -> None:
        card = StepCard(step=2, title="Validate Keypair")
        self.content_layout.addWidget(card)
        
        lbl_desc = QLabel("Confirm that the private and public keys belong to the same RSA keypair.")
        lbl_desc.setStyleSheet(f"color: {Color.FG_MUTED};")
        card.body_layout.addWidget(lbl_desc)
        
        act_row = QHBoxLayout()
        act_row.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        btn_val = QPushButton("✅  Validate Keypair")
        btn_val.setFixedSize(180, 40)
        btn_val.setStyleSheet("font-weight: bold; font-size: 13px;")
        btn_val.clicked.connect(self._on_validate)
        act_row.addWidget(btn_val)
        
        self.lbl_val_res = QLabel("")
        self.lbl_val_res.setStyleSheet("font-weight: bold; font-size: 13px;")
        act_row.addWidget(self.lbl_val_res)
        
        card.body_layout.addLayout(act_row)
        
    # Helpers
    
    def _get_private_pem(self) -> str:
        return self.txt_priv.toPlainText().strip()

    def _get_public_pem(self) -> str:
        return self.txt_pub.toPlainText().strip()
        
    def _read_file(self, path: str) -> str:
        if not path:
            return ""
        try:
            with open(path) as f:
                return f.read().strip()
        except Exception:
            return ""

    def _write_temp_pem(self, content: str) -> str | None:
        if "BEGIN " not in content:
            QMessageBox.warning(self, "Warning", "Clipboard does not appear to contain a PEM key.")
            return None
        try:
            tmp = tempfile.NamedTemporaryFile(suffix=".pem", delete=False, mode="w")
            tmp.write(content)
            tmp.close()
            self._temp_files.append(tmp.name)
            return tmp.name
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to write temp key:\n{exc}")
            return None
            
    # Actions
    
    def _on_generate(self) -> None:
        key_size = int(self.combo_size.currentText())
        try:
            priv_pem, pub_pem = KeyPairManager.generate_keypair(key_size)
            self.txt_priv.setPlainText(priv_pem)
            self.txt_pub.setPlainText(pub_pem)
            self.lbl_gen_info.setText(f"✅  {key_size}-bit RSA keypair ready")
            self.lbl_gen_info.setStyleSheet(f"color: {Color.SUCCESS};")
            self.lbl_val_res.setText("")
            if self.app:
                self.app.status(f"{key_size}-bit keypair generated", "success")
        except Exception as exc:
            self.lbl_gen_info.setText(f"❌  {exc}")
            self.lbl_gen_info.setStyleSheet(f"color: {Color.ERROR};")
            if self.app:
                self.app.status("Keypair generation failed", "error")

    def _save_private(self) -> None:
        pem = self._get_private_pem()
        if not pem:
            QMessageBox.warning(self, "Warning", "Generate a keypair first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Private Key", "", "PEM files (*.pem);;All files (*.*)")
        if path:
            with open(path, "w") as f:
                f.write(pem)
            if self.app:
                self.app.status(f"Private key saved → {path}", "success")
                
    def _save_public(self) -> None:
        pem = self._get_public_pem()
        if not pem:
            QMessageBox.warning(self, "Warning", "Generate a keypair first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Public Key", "", "PEM files (*.pem);;All files (*.*)")
        if path:
            with open(path, "w") as f:
                f.write(pem)
            if self.app:
                self.app.status(f"Public key saved → {path}", "success")
                
    def _copy_private(self) -> None:
        pem = self._get_private_pem()
        if pem:
            QApplication.clipboard().setText(pem)
            self.lbl_gen_info.setText("📋  Private key copied")
            self.lbl_gen_info.setStyleSheet(f"color: {Color.SUCCESS};")
        else:
            QMessageBox.warning(self, "Warning", "Generate a keypair first.")
            
    def _copy_public(self) -> None:
        pem = self._get_public_pem()
        if pem:
            QApplication.clipboard().setText(pem)
            self.lbl_gen_info.setText("📋  Public key copied")
            self.lbl_gen_info.setStyleSheet(f"color: {Color.SUCCESS};")
        else:
            QMessageBox.warning(self, "Warning", "Generate a keypair first.")
            
    def _browse_priv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Private Key", "", "PEM files (*.pem);;All files (*.*)")
        if path:
            self.priv_entry.setText(path)
            
    def _browse_pub(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Public Key", "", "PEM files (*.pem);;All files (*.*)")
        if path:
            self.pub_entry.setText(path)
            
    def _paste_priv(self) -> None:
        clip = QApplication.clipboard().text().strip()
        if not clip:
            QMessageBox.warning(self, "Warning", "Clipboard is empty.")
            return
        tmp = self._write_temp_pem(clip)
        if tmp:
            self.priv_entry.setText(tmp)
            
    def _paste_pub(self) -> None:
        clip = QApplication.clipboard().text().strip()
        if not clip:
            QMessageBox.warning(self, "Warning", "Clipboard is empty.")
            return
        tmp = self._write_temp_pem(clip)
        if tmp:
            self.pub_entry.setText(tmp)
            
    def _on_validate(self) -> None:
        if self._active_source == "generate":
            priv_pem = self._get_private_pem()
            pub_pem = self._get_public_pem()
        else:
            priv_pem = self._read_file(self.priv_entry.text())
            pub_pem = self._read_file(self.pub_entry.text())

        if not priv_pem or not pub_pem:
            self._set_result("⚠  No keys available in active panel", Color.WARNING)
            return

        priv_ok = KeyPairManager.validate_private_key(priv_pem)
        pub_ok = KeyPairManager.validate_public_key(pub_pem)

        if not priv_ok and not pub_ok:
            self._set_result("❌  Both keys are invalid PEM", Color.ERROR)
            return
        if not priv_ok:
            self._set_result("❌  Private key is invalid PEM", Color.ERROR)
            return
        if not pub_ok:
            self._set_result("❌  Public key is invalid PEM", Color.ERROR)
            return

        if KeyPairManager.verify_keypair(priv_pem, pub_pem):
            size = KeyPairManager.get_key_size(priv_pem)
            self._set_result(f"✅  Keys match — {size}-bit RSA pair", Color.SUCCESS)
            if self.app:
                self.app.status(f"Keys validated: {size}-bit pair", "success")
        else:
            self._set_result("❌  Keys do NOT match — different keypairs", Color.ERROR)
            if self.app:
                self.app.status("Keypair mismatch detected", "error")

    def _set_result(self, text: str, color: str) -> None:
        self.lbl_val_res.setText(text)
        self.lbl_val_res.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 13px;")
