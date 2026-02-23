"""
diff_view.py - Diff viewer window with syntax-highlighted unified diff.
"""

from __future__ import annotations

import difflib
import re
import tkinter as tk
from pathlib import Path
from tkinter import ttk

# ── Palette ───────────────────────────────────────────────────────────────────
_BG          = "#1e1e1e"
_BG_HEADER   = "#252526"
_BG_INFOBAR  = "#2d2d2d"
_BG_ADDED    = "#1a3a1a"
_BG_REMOVED  = "#3a1a1a"
_BG_HUNK     = "#252540"
_BG_GUTTER   = "#1a1a1a"

_FG_NORMAL   = "#d4d4d4"
_FG_ADDED    = "#89d185"
_FG_REMOVED  = "#f14c4c"
_FG_HUNK     = "#569cd6"
_FG_INFO     = "#9d9d9d"
_FG_HEADER   = "#cccccc"
_FG_GUTTER   = "#4e4e4e"
_FG_GUTTER_A = "#3a6a3a"
_FG_GUTTER_R = "#6a3a3a"
_FG_GUTTER_H = "#3a3a6a"

_FONT_MONO  = ("Consolas", 10)
_FONT_UI    = ("Segoe UI", 9)
_FONT_TITLE = ("Segoe UI Semibold", 10)

_HUNK_RE = re.compile(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")


class DiffViewer(tk.Toplevel):
    """Modal-ish diff window; shows unified diff between checkpoint and current file."""

    def __init__(
        self,
        parent: tk.Misc,
        rel_path: str,
        folder_path: str,
        checkpoint_dir: str | None,
    ) -> None:
        super().__init__(parent)
        self.title(f"Diferenças  —  {rel_path}")
        self.geometry("980x680")
        self.minsize(640, 420)
        self.configure(bg=_BG)

        self._rel      = rel_path
        self._folder   = Path(folder_path)
        self._cp_dir   = Path(checkpoint_dir) if checkpoint_dir else None

        self._build_ui()
        self._load_diff()

        self.transient(parent)
        self.focus_set()

    # ── UI ────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # ── Title bar ─────────────────────────────────────────────────────
        header = tk.Frame(self, bg=_BG_HEADER, padx=14, pady=9)
        header.pack(fill=tk.X)

        tk.Label(
            header, text=f"📄  {self._rel}",
            font=_FONT_TITLE, bg=_BG_HEADER, fg=_FG_HEADER, anchor="w",
        ).pack(side=tk.LEFT)

        legend = tk.Frame(header, bg=_BG_HEADER, padx=10)
        legend.pack(side=tk.RIGHT)
        tk.Label(legend, text="─ removido ", fg=_FG_REMOVED, bg=_BG_HEADER,
                 font=_FONT_UI).pack(side=tk.LEFT)
        tk.Label(legend, text="  ─ adicionado", fg=_FG_ADDED, bg=_BG_HEADER,
                 font=_FONT_UI).pack(side=tk.LEFT)

        # ── Info bar (file paths) ──────────────────────────────────────────
        info = tk.Frame(self, bg=_BG_INFOBAR, padx=14, pady=4)
        info.pack(fill=tk.X)

        self._lbl_old = tk.Label(
            info, text="", fg=_FG_INFO, bg=_BG_INFOBAR, font=_FONT_UI, anchor="w",
        )
        self._lbl_old.pack(side=tk.LEFT)

        self._lbl_new = tk.Label(
            info, text="", fg=_FG_INFO, bg=_BG_INFOBAR, font=_FONT_UI, anchor="e",
        )
        self._lbl_new.pack(side=tk.RIGHT)

        # ── Diff area ─────────────────────────────────────────────────────
        diff_frame = tk.Frame(self, bg=_BG)
        diff_frame.pack(fill=tk.BOTH, expand=True)

        # Vertical scrollbar shared by gutter + text
        self._vscroll = ttk.Scrollbar(diff_frame, orient=tk.VERTICAL,
                                      command=self._scroll_both)
        self._vscroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Gutter (line numbers)
        self._gutter = tk.Text(
            diff_frame,
            width=6, state=tk.DISABLED,
            bg=_BG_GUTTER, fg=_FG_GUTTER,
            font=_FONT_MONO, bd=0, padx=4, pady=4,
            cursor="arrow", relief=tk.FLAT, takefocus=False,
            selectbackground=_BG_GUTTER,
        )
        self._gutter.pack(side=tk.LEFT, fill=tk.Y)
        self._gutter.bind("<MouseWheel>",
                          lambda e: self._text.yview_scroll(-e.delta // 120, "units"))

        # Thin vertical separator
        tk.Frame(diff_frame, bg="#3a3a3a", width=1).pack(side=tk.LEFT, fill=tk.Y)

        # Horizontal scrollbar (below text)
        hscroll_host = tk.Frame(self, bg=_BG)
        hscroll_host.pack(fill=tk.X, side=tk.BOTTOM)
        hscroll = ttk.Scrollbar(hscroll_host, orient=tk.HORIZONTAL)
        hscroll.pack(fill=tk.X)

        # Main text widget
        self._text = tk.Text(
            diff_frame,
            state=tk.DISABLED,
            bg=_BG, fg=_FG_NORMAL,
            font=_FONT_MONO, bd=0, padx=10, pady=4,
            wrap=tk.NONE,
            yscrollcommand=self._on_text_yscroll,
            xscrollcommand=hscroll.set,
            selectbackground="#264f78",
            insertbackground=_FG_NORMAL,
            relief=tk.FLAT,
        )
        hscroll.config(command=self._text.xview)
        self._text.pack(fill=tk.BOTH, expand=True)

        # Colour tags – text
        self._text.tag_configure("added",   foreground=_FG_ADDED,   background=_BG_ADDED)
        self._text.tag_configure("removed", foreground=_FG_REMOVED,  background=_BG_REMOVED)
        self._text.tag_configure("hunk",    foreground=_FG_HUNK,     background=_BG_HUNK)
        self._text.tag_configure("meta",    foreground=_FG_INFO)
        self._text.tag_configure("info",    foreground=_FG_INFO)

        # Colour tags – gutter
        self._gutter.tag_configure("added",   foreground=_FG_GUTTER_A, background=_BG_ADDED)
        self._gutter.tag_configure("removed", foreground=_FG_GUTTER_R, background=_BG_REMOVED)
        self._gutter.tag_configure("hunk",    foreground=_FG_GUTTER_H, background=_BG_HUNK)
        self._gutter.tag_configure("normal",  foreground=_FG_GUTTER)

        # ── Status bar ────────────────────────────────────────────────────
        self._status = tk.Label(
            self, text="", bg="#007acc", fg="white",
            font=_FONT_UI, anchor="w", padx=10, pady=4,
        )
        self._status.pack(fill=tk.X, side=tk.BOTTOM)

    # ── Scroll sync ───────────────────────────────────────────────────────

    def _on_text_yscroll(self, first: str, last: str) -> None:
        self._vscroll.set(first, last)
        self._gutter.yview_moveto(first)

    def _scroll_both(self, action: str, *args) -> None:
        self._text.yview(action, *args)
        self._gutter.yview(action, *args)

    # ── Diff loading ──────────────────────────────────────────────────────

    def _load_diff(self) -> None:
        rel = Path(self._rel)
        current  = self._folder / rel
        cp_file  = (self._cp_dir / rel) if self._cp_dir else None

        # Labels
        cp_label  = str(cp_file) if cp_file else "⚠  sem checkpoint"
        cur_label = str(current)
        self._lbl_old.config(text=f"checkpoint → {cp_label}")
        self._lbl_new.config(text=f"atual → {cur_label}")

        old_lines = self._read(cp_file)
        new_lines = self._read(current)

        # Handle binary / error strings
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
            fromfile=f"checkpoint/{self._rel}",
            tofile=f"atual/{self._rel}",
            lineterm="",
            n=4,
        ))

        if not diff:
            self._show_message("✔  Nenhuma diferença — conteúdo idêntico ao checkpoint.")
            self._status.config(bg="#107c10", text="  Arquivo sem alterações")
            return

        added   = sum(1 for l in diff if l.startswith("+") and not l.startswith("+++"))
        removed = sum(1 for l in diff if l.startswith("-") and not l.startswith("---"))

        self._render(diff)
        self._status.config(
            text=f"  +{added} linha(s) adicionada(s)    −{removed} linha(s) removida(s)"
        )

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

    # ── Rendering ─────────────────────────────────────────────────────────

    def _render(self, lines: list[str]) -> None:
        self._text.config(state=tk.NORMAL)
        self._gutter.config(state=tk.NORMAL)
        self._text.delete("1.0", tk.END)
        self._gutter.delete("1.0", tk.END)

        old_n = new_n = 0

        for raw in lines:
            line = raw.rstrip("\n")

            if line.startswith("---") or line.startswith("+++"):
                gutter_text = "  ···"
                tag = "meta"
            elif line.startswith("@@"):
                m = _HUNK_RE.search(line)
                if m:
                    old_n = int(m.group(1)) - 1
                    new_n = int(m.group(2)) - 1
                gutter_text = "  ···"
                tag = "hunk"
            elif line.startswith("-"):
                old_n += 1
                gutter_text = f"{old_n:>5}"
                tag = "removed"
            elif line.startswith("+"):
                new_n += 1
                gutter_text = f"{new_n:>5}"
                tag = "added"
            else:
                old_n += 1
                new_n += 1
                gutter_text = f"{new_n:>5}"
                tag = "normal"

            self._gutter.insert(tk.END, gutter_text + "\n",
                                tag if tag != "normal" else "normal")
            self._text.insert(tk.END, line + "\n",
                              tag if tag != "normal" else ())

        self._text.config(state=tk.DISABLED)
        self._gutter.config(state=tk.DISABLED)

    def _show_message(self, msg: str) -> None:
        self._text.config(state=tk.NORMAL)
        self._text.delete("1.0", tk.END)
        self._text.insert(tk.END, f"\n  {msg}\n", "info")
        self._text.config(state=tk.DISABLED)
        self._status.config(text=f"  {msg}")
