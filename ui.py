"""
ui.py - Main application window — modern design.
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app import PastaMonitorApp

from diff_view import DiffViewer

# ── Palette ───────────────────────────────────────────────────────────────────
_C = {
    # Backgrounds
    "bg":          "#FAFAFA",
    "sidebar":     "#F0F2F5",
    "header":      "#0E0C0D",
    "toolbar":     "#F5F6F8",
    "separator":   "#E0E2E6",
    # Text
    "text":        "#1A1A2E",
    "text_muted":  "#6B7280",
    "text_header": "#E8E8F0",
    # Accent
    "accent":      "#097EEB",
    "accent_h":    "#0055A5",   # hover
    "accent_lt":   "#EBF4FF",   # light tint
    # Sidebar selection
    "sel_bg":      "#D6E8FF",
    "sel_fg":      "#085EDF",
    # Status bar
    "status_bg":   "#375E83",
    "status_fg":   "#FFFFFF",
    # Checkpoint badge
    "cp_bg":       "#F5F6F8",
    "cp_fg":       "#0B4913",
    "cp_border":   "#0C571F",
    # Change type colours
    "modified":    "#0060BB",
    "created":     "#107C10",
    "deleted":     "#A02E23",
    "moved":       "#A1761A",
    # Buttons  (bg, fg, hover-bg)
    "btn_primary": ("#0068C9", "#FFFFFF", "#0055A5"),
    "btn_danger":  ("#E8FFD6", "#1A1A2E", "#C7DDB6"),
    "btn_warn":    ("#FFD6D6", "#1A1A2E", "#E2BEBE"),
    "btn_neutral": ("#EAEAEC", "#1A1A2E", "#F5F5F5"),
    # Row stripes
    "row_even":    "#FFFFFF",
    "row_odd":     "#F6F7F9",
    # Tree heading
    "tree_head":   "#EBEDF1",
}

_TYPE_LABELS = {
    "modified": "Modificado",
    "created":  "Criado",
    "deleted":  "Deletado",
    "moved":    "Movido",
}
_TYPE_ICONS = {
    "modified": "✎",
    "created":  "✚",
    "deleted":  "✖",
    "moved":    "➜",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _btn(parent, text: str, command, kind: str = "neutral",
         state: str = tk.NORMAL, **kw) -> tk.Button:
    """Create a flat, coloured tkinter button with hover effect."""
    bg, fg, hover = _C[f"btn_{kind}"]
    b = tk.Button(
        parent, text=text, command=command,
        bg=bg, fg=fg, disabledforeground="#999999",
        relief=tk.FLAT, overrelief=tk.FLAT,
        font=("Segoe UI", 9),
        padx=12, pady=6,
        cursor="hand2",
        activebackground=hover,
        activeforeground=fg,
        borderwidth=0,
        state=state,
        **kw,
    )
    b.bind("<Enter>", lambda e: b.config(bg=hover) if b["state"] == tk.NORMAL else None)
    b.bind("<Leave>", lambda e: b.config(bg=bg)    if b["state"] == tk.NORMAL else None)
    return b


def _separator(parent, orient: str = "horizontal", **kw) -> tk.Frame:
    w = 1 if orient == "vertical" else None
    h = 1 if orient == "horizontal" else None
    return tk.Frame(parent, bg=_C["separator"],
                    width=w, height=h, **kw)


# ── Tooltip ───────────────────────────────────────────────────────────────────

class _Tooltip:
    def __init__(self, widget: tk.Widget, text: str) -> None:
        self._w = widget
        self._text = text
        self._tip: Optional[tk.Toplevel] = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, _=None) -> None:
        if self._tip or not self._text:
            return
        x = self._w.winfo_rootx() + 10
        y = self._w.winfo_rooty() + self._w.winfo_height() + 4
        self._tip = tw = tk.Toplevel(self._w)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(
            tw, text=self._text,
            bg="#1C1C2E", fg="#E8E8F0",
            font=("Segoe UI", 8),
            padx=8, pady=4, relief=tk.FLAT,
        ).pack()

    def _hide(self, _=None) -> None:
        if self._tip:
            self._tip.destroy()
            self._tip = None


# ── Main Window ───────────────────────────────────────────────────────────────

class MainWindow:
    """The main tkinter window — modern design."""

    def __init__(self, app: "PastaMonitorApp") -> None:
        self.app = app
        self._selected_folder: Optional[str] = None
        self._update_q: queue.Queue = queue.Queue()

        self.root = tk.Tk()
        self.root.title("PastaMonitor")
        self.root.geometry("1020x660")
        self.root.minsize(760, 480)
        self.root.configure(bg=_C["bg"])
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._setup_ttk_styles()
        self._build_ui()
        self._start_queue_loop()

    # ── TTK styles ────────────────────────────────────────────────────────

    def _setup_ttk_styles(self) -> None:
        s = ttk.Style(self.root)

        for theme in ("vista", "xpnative", "clam", "alt", "default"):
            if theme in s.theme_names():
                s.theme_use(theme)
                break

        s.configure("Files.Treeview",
                    background=_C["row_even"],
                    fieldbackground=_C["row_even"],
                    foreground=_C["text"],
                    font=("Consolas", 9),
                    rowheight=22)
        s.configure("Files.Treeview.Heading",
                    background=_C["tree_head"],
                    foreground=_C["text_muted"],
                    font=("Segoe UI", 9, "bold"),
                    relief="flat",
                    padding=(4, 5))
        s.map("Files.Treeview",
              background=[("selected", _C["accent_lt"])],
              foreground=[("selected", _C["accent"])])

        s.configure("Folders.Treeview",
                    background=_C["sidebar"],
                    fieldbackground=_C["sidebar"],
                    foreground=_C["text"],
                    font=("Segoe UI", 10),
                    rowheight=28)
        s.configure("Folders.Treeview.Heading",
                    background=_C["sidebar"],
                    foreground=_C["text_muted"],
                    font=("Segoe UI", 8, "bold"))
        s.map("Folders.Treeview",
              background=[("selected", _C["sel_bg"])],
              foreground=[("selected", _C["sel_fg"])])

    # ── UI Construction ───────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = self.root

        # ── Header bar ────────────────────────────────────────────────────
        # header = tk.Frame(root, bg=_C["header"], padx=16, pady=10)
        # header.pack(fill=tk.X)

        # tk.Label(
        #     header, text="PastaMonitor",
        #     font=("Segoe UI Semibold", 13),
        #     bg=_C["header"], fg=_C["text_header"],
        # ).pack(side=tk.LEFT)

        # self._cp_badge = tk.Label(
        #     header, text="",
        #     font=("Segoe UI", 9, "bold"),
        #     bg=_C["cp_bg"], fg=_C["cp_fg"],
        #     padx=10, pady=3, relief=tk.FLAT,
        # )
        # self._cp_badge.pack(side=tk.RIGHT, padx=(0, 4))

        # ── Toolbar ───────────────────────────────────────────────────────
        toolbar = tk.Frame(root, bg=_C["toolbar"], padx=10, pady=7)
        toolbar.pack(fill=tk.X)
        _separator(root, "horizontal").pack(fill=tk.X)

        _btn(toolbar, "➕  Adicionar Pasta",
             self._add_folder, "primary").pack(side=tk.LEFT, padx=(0, 6))
        _btn(toolbar, "✖  Remover",
             self._remove_folder, "neutral").pack(side=tk.LEFT)

        # Folder path label (right side of toolbar)

        self._cp_badge = tk.Label(
            toolbar, text="",
            font=("Segoe UI", 9, "bold"),
            bg=_C["cp_bg"], fg=_C["cp_fg"],
            padx=10, pady=3, relief=tk.FLAT,
        )
        self._cp_badge.pack(side=tk.RIGHT, padx=(0, 4))
        self._path_label = tk.Label(
            toolbar, text="", font=("Segoe UI", 8),
            bg=_C["toolbar"], fg=_C["text_muted"], anchor="e",
        )
        self._path_label.pack(side=tk.RIGHT, padx=(0, 4))

        # ── Paned area ────────────────────────────────────────────────────
        main = tk.Frame(root, bg=_C["bg"])
        main.pack(fill=tk.BOTH, expand=True)

        paned = tk.PanedWindow(
            main, orient=tk.HORIZONTAL,
            sashwidth=5, sashrelief=tk.FLAT,
            bg=_C["separator"],
        )
        paned.pack(fill=tk.BOTH, expand=True)

        # ── Left panel: folder list ───────────────────────────────────────
        left_outer = tk.Frame(paned, bg=_C["sidebar"])
        paned.add(left_outer, minsize=160, width=230)

        lbl_folders = tk.Label(
            left_outer, text="PASTAS",
            font=("Segoe UI", 8, "bold"),
            bg=_C["sidebar"], fg=_C["text_muted"],
            padx=10, pady=6, anchor="w",
        )
        lbl_folders.pack(fill=tk.X)
        _separator(left_outer, "horizontal").pack(fill=tk.X)

        self.folder_tree = ttk.Treeview(
            left_outer, style="Folders.Treeview",
            show="tree", selectmode="browse",
        )
        folder_sb = ttk.Scrollbar(left_outer, orient=tk.VERTICAL,
                                  command=self.folder_tree.yview)
        self.folder_tree.configure(yscrollcommand=folder_sb.set)
        folder_sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.folder_tree.pack(fill=tk.BOTH, expand=True)
        self.folder_tree.bind("<<TreeviewSelect>>", self._on_folder_select)

        # ── Right panel: file list ────────────────────────────────────────
        right_outer = tk.Frame(paned, bg=_C["bg"])
        paned.add(right_outer, minsize=420)

        lbl_files = tk.Label(
            right_outer, text="ARQUIVOS MODIFICADOS",
            font=("Segoe UI", 8, "bold"),
            bg=_C["bg"], fg=_C["text_muted"],
            padx=10, pady=6, anchor="w",
        )
        lbl_files.pack(fill=tk.X)
        _separator(right_outer, "horizontal").pack(fill=tk.X)

        cols = ("icon", "path", "time")
        self.files_tree = ttk.Treeview(
            right_outer, columns=cols,
            show="headings", selectmode=tk.BROWSE,
            style="Files.Treeview",
        )
        self.files_tree.heading("icon", text="Status")
        self.files_tree.heading("path", text="Arquivo")
        self.files_tree.heading("time", text="Horário")
        self.files_tree.column("icon", width=100, minwidth=80,  anchor="center", stretch=False)
        self.files_tree.column("path", width=480, minwidth=200, anchor="w")
        self.files_tree.column("time", width=155, minwidth=120, anchor="center", stretch=False)

        for ctype, colour in {
            "modified": _C["modified"],
            "created":  _C["created"],
            "deleted":  _C["deleted"],
            "moved":    _C["moved"],
        }.items():
            self.files_tree.tag_configure(ctype, foreground=colour)
        self.files_tree.tag_configure("odd", background=_C["row_odd"])

        file_sb_y = ttk.Scrollbar(right_outer, orient=tk.VERTICAL,
                                  command=self.files_tree.yview)
        file_sb_x = ttk.Scrollbar(right_outer, orient=tk.HORIZONTAL,
                                  command=self.files_tree.xview)
        self.files_tree.configure(yscrollcommand=file_sb_y.set,
                                  xscrollcommand=file_sb_x.set)
        file_sb_y.pack(side=tk.RIGHT, fill=tk.Y)
        file_sb_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.files_tree.pack(fill=tk.BOTH, expand=True)
        self.files_tree.bind("<Button-3>", self._on_tree_right_click)
        self.files_tree.bind("<Double-1>", self._on_tree_double_click)
        # ── Status bar ────────────────────────────────────────────────────
        self._status_var = tk.StringVar(value="Pronto.")
        status_bar = tk.Label(
            root,
            textvariable=self._status_var,
            bg=_C["status_bg"], fg=_C["status_fg"],
            font=("Segoe UI", 9),
            anchor="w", padx=12, pady=4,
        )
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        # ── Action bar ────────────────────────────────────────────────────
        _separator(root, "horizontal").pack(fill=tk.X)
        action_bar = tk.Frame(root, bg=_C["toolbar"], padx=10, pady=8)
        action_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self.btn_checkpoint = _btn(
            action_bar, "✔  Criar Checkpoint",
            self._create_checkpoint, "primary",
        )
        self.btn_checkpoint.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_rollback = _btn(
            action_bar, "↩  Rollback Completo",
            self._rollback, "danger", state=tk.DISABLED,
        )
        self.btn_rollback.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_cancel_cp = _btn(
            action_bar, "✖  Cancelar Checkpoint",
            self._cancel_checkpoint, "warn", state=tk.DISABLED,
        )
        self.btn_cancel_cp.pack(side=tk.LEFT)

        self.btn_clear = _btn(
            action_bar, "🗑  Limpar Lista",
            self._clear_changes, "neutral",
        )
        self.btn_clear.pack(side=tk.RIGHT)


        self._refresh_folder_list()

    # ── Folder list ───────────────────────────────────────────────────────

    def _refresh_folder_list(self) -> None:
        # Save current selection
        sel_iid = self.folder_tree.focus()
        sel_folder = self.folder_tree.item(sel_iid, "values")[0] if sel_iid else None

        self.folder_tree.delete(*self.folder_tree.get_children())

        for folder in self.app.config.folders:
            name = Path(folder).name
            monitor = self.app.monitors.get(folder)
            has_cp = bool(monitor and monitor.has_checkpoint)
            label = f"🗀  {name}{'  ⚑' if has_cp else ''}"
            iid = self.folder_tree.insert("", tk.END, text=label,
                                          values=(folder,), tags=("cp",) if has_cp else ())

        # Colour checkpoint items
        self.folder_tree.tag_configure("cp", foreground=_C["cp_fg"])

        # Restore selection
        if self._selected_folder:
            for iid in self.folder_tree.get_children():
                if self.folder_tree.item(iid, "values")[0] == self._selected_folder:
                    self.folder_tree.selection_set(iid)
                    self.folder_tree.focus(iid)
                    break

    def _add_folder(self) -> None:
        path = filedialog.askdirectory(
            parent=self.root, title="Selecionar Pasta para Monitorar",
        )
        if path:
            added = self.app.add_folder(path)
            self._refresh_folder_list()
            if added:
                norm = str(Path(path).resolve())
                self._selected_folder = norm
                for iid in self.folder_tree.get_children():
                    if self.folder_tree.item(iid, "values")[0] == norm:
                        self.folder_tree.selection_set(iid)
                        self.folder_tree.focus(iid)
                        break
                self._refresh_files()
                self._update_button_states()

    def _remove_folder(self) -> None:
        if not self._selected_folder:
            messagebox.showinfo("Remover Pasta",
                                "Selecione uma pasta na lista primeiro.",
                                parent=self.root)
            return
        if messagebox.askyesno("Remover Pasta",
                               f"Parar monitoramento de:\n{self._selected_folder}",
                               parent=self.root):
            self.app.remove_folder(self._selected_folder)
            self._selected_folder = None
            self._refresh_folder_list()
            self._refresh_files()
            self._update_button_states()

    def _on_folder_select(self, _=None) -> None:
        iid = self.folder_tree.focus()
        if not iid:
            return
        vals = self.folder_tree.item(iid, "values")
        if vals:
            self._selected_folder = vals[0]
            self._path_label.config(text=self._selected_folder)
            self._refresh_files()
            self._update_button_states()

    # ── File list ─────────────────────────────────────────────────────────

    def _refresh_files(self) -> None:
        self.files_tree.delete(*self.files_tree.get_children())

        if not self._selected_folder:
            self._status_var.set("Selecione uma pasta monitorada.")
            self._cp_badge.config(text="")
            return

        monitor = self.app.monitors.get(self._selected_folder)
        if not monitor:
            self._status_var.set("Monitor não encontrado.")
            self._cp_badge.config(text="")
            return

        changes = monitor.get_changes()
        sorted_items = sorted(changes.items(),
                              key=lambda kv: kv[1]["time"], reverse=True)

        for i, (rel_path, info) in enumerate(sorted_items):
            ctype = info["type"]
            icon  = f"{_TYPE_ICONS.get(ctype, '?')}  {_TYPE_LABELS.get(ctype, ctype)}"
            time_str = info["time"].replace("T", " ")
            tags = [ctype]
            if i % 2 == 1:
                tags.append("odd")
            self.files_tree.insert("", tk.END,
                                   values=(icon, rel_path, time_str),
                                   tags=tuple(tags))

        count = len(changes)
        if monitor.has_checkpoint:
            self._cp_badge.config(text="  ⚑  CHECKPOINT ATIVO  ")
            self._status_var.set(
                f"{count} arquivo(s) modificado(s) desde o checkpoint  •  "
                "Clique com botão direito para opções por arquivo"
            )
        else:
            self._cp_badge.config(text="")
            self._status_var.set(
                f"{count} arquivo(s) modificado(s) desde o início do monitoramento"
            )

    # ── Context menu (right-click) ────────────────────────────────────────

    def _on_tree_right_click(self, event) -> None:
        iid = self.files_tree.identify_row(event.y)
        if not iid:
            return
        self.files_tree.selection_set(iid)

        vals = self.files_tree.item(iid, "values")
        if not vals:
            return

        # Recover original change type from tags
        tags = self.files_tree.item(iid, "tags")
        ctype = next((t for t in tags if t in _TYPE_LABELS), None)
        rel_path = vals[1]
        monitor  = self.app.monitors.get(self._selected_folder) if self._selected_folder else None

        menu = tk.Menu(self.root, tearoff=False,
                       font=("Segoe UI", 9),
                       bg="#FFFFFF", fg=_C["text"],
                       activebackground=_C["accent_lt"],
                       activeforeground=_C["accent"])

        # ── Diff ──────────────────────────────────────────────────────────
        can_diff = bool(monitor and (monitor.has_checkpoint or ctype == "created"))
        menu.add_command(
            label="🔍  Mostrar Diferenças",
            command=lambda: self._open_diff(rel_path),
            state=tk.NORMAL if can_diff else tk.DISABLED,
        )

        menu.add_separator()

        # ── Single-file rollback ───────────────────────────────────────────
        can_rollback = bool(monitor and monitor.has_checkpoint)
        menu.add_command(
            label="↩  Rollback deste Arquivo",
            command=lambda: self._rollback_file(rel_path),
            state=tk.NORMAL if can_rollback else tk.DISABLED,
        )

        menu.add_separator()

        # ── Copy ──────────────────────────────────────────────────────────
        menu.add_command(
            label="⎘  Copiar caminho relativo",
            command=lambda: self._copy(rel_path),
        )
        if self._selected_folder:
            full = str(Path(self._selected_folder) / rel_path)
            menu.add_command(
                label="⎘  Copiar caminho completo",
                command=lambda: self._copy(full),
            )

        menu.tk_popup(event.x_root, event.y_root)

    def _on_tree_double_click(self, event) -> None:
        """Double-click opens diff if available."""
        iid = self.files_tree.identify_row(event.y)
        if not iid:
            return
        vals = self.files_tree.item(iid, "values")
        if vals:
            self._open_diff(vals[1])

    def _open_diff(self, rel_path: str) -> None:
        monitor = self.app.monitors.get(self._selected_folder) if self._selected_folder else None
        if not monitor:
            return
        cp_dir = monitor._checkpoint_dir
        DiffViewer(self.root, rel_path, self._selected_folder, cp_dir)

    def _copy(self, text: str) -> None:
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self._status_var.set(f"Copiado: {text}")

    # ── Button states ─────────────────────────────────────────────────────

    def _update_button_states(self) -> None:
        monitor = (self.app.monitors.get(self._selected_folder)
                   if self._selected_folder else None)
        has_cp  = bool(monitor and monitor.has_checkpoint)
        has_sel = bool(self._selected_folder)

        def _s(btn: tk.Button, enabled: bool) -> None:
            bg, fg, hover = _C[f"btn_{btn._kind}"]  # type: ignore[attr-defined]
            btn.config(state=tk.NORMAL if enabled else tk.DISABLED,
                       bg=bg if enabled else _C["btn_neutral"][0])

        # Simpler state helper (avoid attribute tricks)
        self.btn_checkpoint.config(
            state=tk.NORMAL if (has_sel and not has_cp) else tk.DISABLED)
        self.btn_rollback.config(
            state=tk.NORMAL if has_cp else tk.DISABLED)
        self.btn_cancel_cp.config(
            state=tk.NORMAL if has_cp else tk.DISABLED)
        self.btn_clear.config(
            state=tk.NORMAL if (has_sel and not has_cp) else tk.DISABLED)

    # ── Checkpoint actions ────────────────────────────────────────────────

    def _create_checkpoint(self) -> None:
        monitor = self._require_monitor()
        if not monitor:
            return
        self._status_var.set("Criando checkpoint… aguarde.")
        self.root.update_idletasks()

        def _work():
            monitor.create_checkpoint()
            self._update_q.put("refresh")

        threading.Thread(target=_work, daemon=True).start()

    def _rollback(self) -> None:
        monitor = self._require_monitor()
        if not monitor:
            return
        if not messagebox.askyesno(
            "Rollback Completo",
            "Restaurar TODOS os arquivos para o estado do checkpoint?\n\n"
            "As alterações após o checkpoint serão perdidas permanentemente.",
            icon="warning", parent=self.root,
        ):
            return
        self._status_var.set("Fazendo rollback… aguarde.")
        self.root.update_idletasks()

        def _work():
            monitor.rollback()
            self._update_q.put("refresh")

        threading.Thread(target=_work, daemon=True).start()

    def _rollback_file(self, rel_path: str) -> None:
        monitor = self._require_monitor()
        if not monitor or not monitor.has_checkpoint:
            return
        if not messagebox.askyesno(
            "Rollback de Arquivo",
            f"Restaurar este arquivo para o estado do checkpoint?\n\n{rel_path}",
            icon="warning", parent=self.root,
        ):
            return
        ok = monitor.rollback_file(rel_path)
        if ok:
            self._status_var.set(f"Arquivo restaurado: {rel_path}")
        else:
            messagebox.showerror("Erro", f"Não foi possível restaurar:\n{rel_path}",
                                 parent=self.root)
        self._refresh_folder_list()
        self._refresh_files()
        self._update_button_states()

    def _cancel_checkpoint(self) -> None:
        monitor = self._require_monitor()
        if not monitor:
            return
        monitor.cancel_checkpoint()
        self._refresh_folder_list()
        self._refresh_files()
        self._update_button_states()
        self._status_var.set("Checkpoint cancelado. Continuando monitoramento.")

    def _clear_changes(self) -> None:
        monitor = self._require_monitor()
        if not monitor or monitor.has_checkpoint:
            return
        if messagebox.askyesno(
            "Limpar Lista",
            "Limpar a lista de arquivos modificados?\n(Os arquivos NÃO serão alterados.)",
            parent=self.root,
        ):
            monitor.clear_all_changes()
            self._refresh_files()

    def _require_monitor(self):
        if not self._selected_folder:
            messagebox.showinfo("Sem pasta",
                                "Selecione uma pasta na lista primeiro.",
                                parent=self.root)
            return None
        return self.app.monitors.get(self._selected_folder)

    # ── Queue loop ────────────────────────────────────────────────────────

    def _start_queue_loop(self) -> None:
        def _loop():
            try:
                while True:
                    msg = self._update_q.get_nowait()
                    if msg == "refresh":
                        self._refresh_folder_list()
                        self._refresh_files()
                        self._update_button_states()
            except queue.Empty:
                pass
            self.root.after(250, _loop)

        self.root.after(250, _loop)

    # ── Called from watchdog thread ───────────────────────────────────────

    def notify_change(self, folder_path: str) -> None:
        if folder_path == self._selected_folder:
            self._update_q.put("refresh")

    # ── Visibility ────────────────────────────────────────────────────────

    def _on_close(self) -> None:
        self.root.withdraw()

    def show(self, select_folder: Optional[str] = None) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

        if select_folder:
            self._selected_folder = select_folder
            self._path_label.config(text=select_folder)
            for iid in self.folder_tree.get_children():
                if self.folder_tree.item(iid, "values")[0] == select_folder:
                    self.folder_tree.selection_set(iid)
                    self.folder_tree.focus(iid)
                    break
            self._refresh_files()
            self._update_button_states()

    def run(self) -> None:
        self.root.mainloop()
