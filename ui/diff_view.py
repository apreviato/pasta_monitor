from __future__ import annotations

import difflib
import re
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QFrame, QSplitter,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QTextCharFormat, QTextCursor

_HUNK_RE = re.compile(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")


class DiffPanel(QWidget):
    """Full-height panel that shows a unified diff for a single file."""

    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("diffPanel")
        self._setup_ui()

    # ── UI setup ───────────────────────────────────────────────────────────

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Header ─────────────────────────────────────────────────────────
        header = QWidget()
        header.setObjectName("diffHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 10, 12, 10)
        header_layout.setSpacing(10)

        back_btn = QPushButton("← Voltar")
        back_btn.setObjectName("iconBtnClose")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.clicked.connect(self.closed.emit)
        header_layout.addWidget(back_btn)

        self._file_lbl = QLabel("Diff")
        self._file_lbl.setObjectName("diffFileName")
        header_layout.addWidget(self._file_lbl, 1)

        # Legend
        legend = QLabel(
            '<span style="color:#f14c4c">─ removido</span>'
            '&nbsp;&nbsp;&nbsp;'
            '<span style="color:#89d185">─ adicionado</span>'
        )
        legend.setTextFormat(Qt.TextFormat.RichText)
        legend.setStyleSheet("font-size: 11px;")
        header_layout.addWidget(legend)

        layout.addWidget(header)

        # ── Info bar ────────────────────────────────────────────────────────
        info_bar = QWidget()
        info_bar.setObjectName("diffInfoBar")
        info_layout = QHBoxLayout(info_bar)
        info_layout.setContentsMargins(16, 6, 16, 6)
        self._old_lbl = QLabel("")
        self._old_lbl.setObjectName("diffInfoText")
        self._new_lbl = QLabel("")
        self._new_lbl.setObjectName("diffInfoText")
        info_layout.addWidget(self._old_lbl)
        info_layout.addStretch()
        info_layout.addWidget(self._new_lbl)
        layout.addWidget(info_bar)

        # ── Diff text ───────────────────────────────────────────────────────
        self._text = QTextEdit()
        self._text.setObjectName("diffText")
        self._text.setReadOnly(True)
        mono = QFont("Cascadia Code", 10)
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self._text.setFont(mono)
        layout.addWidget(self._text, 1)

        # ── Status bar ──────────────────────────────────────────────────────
        self._status = QLabel("")
        self._status.setObjectName("diffStatusBar")
        self._status.setFixedHeight(26)
        self._status.setStyleSheet(
            "background-color: #007acc; color: white; "
            "font-size: 11px; padding: 0 10px;"
        )
        layout.addWidget(self._status)

    # ── Public API ─────────────────────────────────────────────────────────

    def load(self, folder: str, rel_path: str, checkpoint_dir: str | None) -> None:
        """Load and display the diff for the given file."""
        self._file_lbl.setText(f"📄  {rel_path}")

        folder_p = Path(folder)
        current = folder_p / rel_path
        cp_file = (Path(checkpoint_dir) / rel_path) if checkpoint_dir else None

        cp_label = str(cp_file) if cp_file else "sem checkpoint"
        self._old_lbl.setText(f"checkpoint  →  {cp_label}")
        self._new_lbl.setText(f"atual  →  {current}")

        old_lines = self._read(cp_file)
        new_lines = self._read(current)

        if isinstance(old_lines, str) or isinstance(new_lines, str):
            msg = old_lines if isinstance(old_lines, str) else new_lines
            self._show_message(msg or "Não foi possível gerar diff.")
            return

        if old_lines is None and new_lines is None:
            self._show_message("Arquivo não encontrado em nenhuma das versões.")
            return

        old_lines = old_lines or []
        new_lines = new_lines or []

        diff = list(difflib.unified_diff(
            old_lines, new_lines,
            fromfile=f"checkpoint/{rel_path}",
            tofile=f"atual/{rel_path}",
            lineterm="",
            n=4,
        ))

        if not diff:
            self._show_message("✔  Nenhuma diferença — conteúdo idêntico ao checkpoint.")
            self._status.setText("  Arquivo sem alterações")
            self._status.setStyleSheet(
                "background-color: #107c10; color: white; "
                "font-size: 11px; padding: 0 10px;"
            )
            return

        added = sum(1 for l in diff if l.startswith("+") and not l.startswith("+++"))
        removed = sum(1 for l in diff if l.startswith("-") and not l.startswith("---"))

        self._render(diff)
        self._status.setStyleSheet(
            "background-color: #007acc; color: white; "
            "font-size: 11px; padding: 0 10px;"
        )
        self._status.setText(
            f"  +{added} linha(s) adicionada(s)    −{removed} linha(s) removida(s)"
        )

    # ── Internal ───────────────────────────────────────────────────────────

    def _read(self, path: Path | None):
        """Returns list[str] | str (error/binary msg) | None (not found)."""
        if path is None or not path.exists():
            return None
        try:
            raw = path.read_bytes()
            if b"\x00" in raw[:8192]:
                return "Arquivo binário — diff não disponível."
            return raw.decode("utf-8", errors="replace").splitlines(keepends=True)
        except OSError as e:
            return f"Erro ao ler arquivo: {e}"

    def _render(self, lines: list[str]) -> None:
        self._text.clear()
        cursor = self._text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        normal_fmt = QTextCharFormat()
        normal_fmt.setForeground(QColor("#d4d4d4"))

        added_fmt = QTextCharFormat()
        added_fmt.setForeground(QColor("#89d185"))
        added_fmt.setBackground(QColor("#1a3a1a"))

        removed_fmt = QTextCharFormat()
        removed_fmt.setForeground(QColor("#f14c4c"))
        removed_fmt.setBackground(QColor("#3a1a1a"))

        hunk_fmt = QTextCharFormat()
        hunk_fmt.setForeground(QColor("#569cd6"))
        hunk_fmt.setBackground(QColor("#252540"))

        meta_fmt = QTextCharFormat()
        meta_fmt.setForeground(QColor("#9d9d9d"))

        for raw in lines:
            line = raw.rstrip("\n")
            if line.startswith("---") or line.startswith("+++"):
                fmt = meta_fmt
            elif line.startswith("@@"):
                fmt = hunk_fmt
            elif line.startswith("-"):
                fmt = removed_fmt
            elif line.startswith("+"):
                fmt = added_fmt
            else:
                fmt = normal_fmt

            cursor.insertText(line + "\n", fmt)

    def _show_message(self, msg: str) -> None:
        self._text.clear()
        cursor = self._text.textCursor()
        fmt = QTextCharFormat()
        fmt.setForeground(QColor("#9d9d9d"))
        cursor.insertText(f"\n  {msg}\n", fmt)
        self._status.setText(f"  {msg}")
