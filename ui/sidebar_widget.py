from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QMenu, QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint


_FILTERS = [
    ("",         "☰", "Todos"),
    ("modified", "✎",  "Modificados"),
    ("created",  "✚",  "Criados"),
    ("deleted",  "✖",  "Deletados"),
    ("moved",    "➜",  "Movidos"),
]

_MENU_STYLE = """
QMenu {
    background: #1C1C1C;
    border: 1px solid #2E2E2E;
    border-radius: 8px;
    padding: 5px;
    color: #E8E8E8;
    font-size: 12px;
}
QMenu::item {
    padding: 7px 18px 7px 12px;
    border-radius: 5px;
}
QMenu::item:selected {
    background: #2D2D2D;
    color: #E8E8E8;
}
QMenu::item:disabled {
    color: #444;
}
QMenu::separator {
    height: 1px;
    background: #2A2A2A;
    margin: 4px 6px;
}
"""

# Folder button styles per (has_checkpoint, is_active) state
_FOLDER_STYLES = {
    # (has_cp, active)
    (False, False): """
        QPushButton {
            background: transparent;
            color: #888;
            text-align: left;
            padding: 8px 10px;
            border-radius: 8px;
            font-size: 12px;
            border: none;
        }
        QPushButton:hover {
            background: #242424;
            color: #CCC;
        }
    """,
    (False, True): """
        QPushButton {
            background: #2D2D2D;
            color: #3498db;
            text-align: left;
            padding: 8px 10px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 600;
            border: none;
        }
    """,
    (True, False): """
        QPushButton {
            background: rgba(46,204,113,.07);
            color: #A0A0A0;
            text-align: left;
            padding: 8px 10px;
            border-radius: 8px;
            font-size: 12px;
            border: 1px solid rgba(46,204,113,.18);
        }
        QPushButton:hover {
            background: rgba(46,204,113,.13);
            color: #DDD;
            border-color: rgba(46,204,113,.3);
        }
    """,
    (True, True): """
        QPushButton {
            background: rgba(46,204,113,.18);
            color: #2ecc71;
            text-align: left;
            padding: 8px 10px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 600;
            border: 1px solid rgba(46,204,113,.35);
        }
    """,
}


class SidebarWidget(QWidget):
    # Filter / folder selection
    filter_changed          = pyqtSignal(str)   # "" = all, else change type key
    folder_selected         = pyqtSignal(str)   # folder path

    # Folder management
    add_folder_requested    = pyqtSignal()
    remove_folder_requested = pyqtSignal(str)   # folder path
    open_folder_requested   = pyqtSignal(str)   # folder path

    # Per-folder checkpoint actions
    checkpoint_requested         = pyqtSignal(str)   # folder path
    cancel_checkpoint_requested  = pyqtSignal(str)   # folder path
    rollback_requested           = pyqtSignal(str)   # folder path

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(240)

        self._active_filter: str = ""
        self._active_folder: str = ""
        self._filter_buttons: dict[str, QPushButton] = {}
        self._folder_btns:   dict[str, QPushButton]  = {}
        self._cp_status:     dict[str, bool]         = {}

        self._setup_ui()

    # ── Setup ───────────────────────────────────────────────────────────────

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        content = QWidget()
        self._layout = QVBoxLayout(content)
        self._layout.setContentsMargins(10, 16, 10, 14)
        self._layout.setSpacing(0)
        scroll.setWidget(content)

        # ── Brand block ─────────────────────────────────────────────────────
        brand = QWidget()
        br = QHBoxLayout(brand)
        br.setContentsMargins(6, 0, 6, 0)
        br.setSpacing(10)

        icon_lbl = QLabel("📁")
        icon_lbl.setStyleSheet("font-size: 20px; background: transparent;")
        br.addWidget(icon_lbl)

        titles = QWidget()
        titles.setStyleSheet("background: transparent;")
        tc = QVBoxLayout(titles)
        tc.setContentsMargins(0, 0, 0, 0)
        tc.setSpacing(0)
        title_lbl = QLabel("Pasta Monitor")
        title_lbl.setObjectName("sidebarTitle")
        sub_lbl   = QLabel("MONITOR DE ARQUIVOS")
        sub_lbl.setObjectName("sidebarSubtitle")
        tc.addWidget(title_lbl)
        tc.addWidget(sub_lbl)
        br.addWidget(titles, 1)

        self._layout.addWidget(brand)
        self._layout.addSpacing(14)
        self._add_separator()
        self._layout.addSpacing(10)

        # ── Filters ─────────────────────────────────────────────────────────
        self._add_section_label("FILTROS")
        for key, icon, label in _FILTERS:
            self._add_filter_btn(key, icon, label)

        self._layout.addSpacing(10)
        self._add_separator()
        self._layout.addSpacing(8)

        # ── Folders ─────────────────────────────────────────────────────────
        self._add_section_label("PASTAS MONITORADAS")

        self._folders_container = QWidget()
        self._folders_container.setStyleSheet("background: transparent;")
        self._folders_layout = QVBoxLayout(self._folders_container)
        self._folders_layout.setContentsMargins(0, 0, 0, 0)
        self._folders_layout.setSpacing(3)   # small gap between folder items
        self._layout.addWidget(self._folders_container)

        self._layout.addSpacing(4)

        add_btn = QPushButton("  ✚  Adicionar Pasta")
        add_btn.setObjectName("addFolderBtn")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self.add_folder_requested.emit)
        self._layout.addWidget(add_btn)

        self._layout.addStretch()

        ver = QLabel("PastaMonitor  v1.0")
        ver.setStyleSheet(
            "color: #2A2A2A; font-size: 10px; "
            "padding: 4px 0 2px 6px; background: transparent;"
        )
        self._layout.addWidget(ver)

        self._update_active()

    # ── Public API ──────────────────────────────────────────────────────────

    def set_folders(
        self,
        folders: list[str],
        checkpoint_status: dict[str, bool] | None = None,
    ) -> None:
        """Rebuild folder rows. checkpoint_status maps folder → has_checkpoint."""
        self._cp_status = checkpoint_status or {}

        # Clear existing rows
        while self._folders_layout.count():
            item = self._folders_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._folder_btns.clear()

        for folder in folders:
            self._add_folder_row(folder)

        if self._active_folder not in folders and self._active_folder:
            self._active_folder = ""
            self.filter_changed.emit(self._active_filter)

        self._update_active()

    def select_folder(self, folder: str) -> None:
        self._active_folder = folder
        self._active_filter = ""
        self._update_active()

    # ── Internal builders ───────────────────────────────────────────────────

    def _add_section_label(self, text: str):
        lbl = QLabel(text)
        lbl.setObjectName("sectionLabel")
        self._layout.addWidget(lbl)
        self._layout.addSpacing(2)

    def _add_separator(self):
        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFrameShape(QFrame.Shape.HLine)
        self._layout.addWidget(sep)

    def _add_filter_btn(self, key: str, icon: str, label: str):
        btn = QPushButton(f"  {icon}  {label}")
        btn.setObjectName("navBtn")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        btn.clicked.connect(lambda _=False, k=key: self._on_filter_click(k))
        self._filter_buttons[key] = btn
        self._layout.addWidget(btn)
        self._layout.addSpacing(2)   # gap between filter items

    def _add_folder_row(self, folder: str):
        has_cp = self._cp_status.get(folder, False)
        name   = Path(folder).name

        # Checkpoint badge shown inside the label — right-aligned via spaces
        cp_tag = "  ⚑" if has_cp else ""
        btn = QPushButton(f" 🗀  {name}{cp_tag}")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setToolTip(folder)
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        btn.clicked.connect(lambda _=False, f=folder: self._on_folder_click(f))
        btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        btn.customContextMenuRequested.connect(
            lambda pos, f=folder, b=btn: self._show_folder_menu(f, b.mapToGlobal(pos))
        )
        self._folder_btns[folder] = btn
        self._folders_layout.addWidget(btn)

    # ── Context menu ────────────────────────────────────────────────────────

    def _show_folder_menu(self, folder: str, global_pos: QPoint):
        has_cp = self._cp_status.get(folder, False)
        name   = Path(folder).name

        menu = QMenu(self)
        menu.setStyleSheet(_MENU_STYLE)

        # Open in Explorer
        a = menu.addAction("📂  Abrir no Explorador")
        a.triggered.connect(lambda: self.open_folder_requested.emit(folder))

        menu.addSeparator()

        # Checkpoint section
        if not has_cp:
            a = menu.addAction("✔  Criar Checkpoint")
            a.triggered.connect(lambda: self.checkpoint_requested.emit(folder))
        else:
            # Checkpoint info header (disabled/decorative)
            info = menu.addAction("⚑  Checkpoint ativo")
            info.setEnabled(False)

            menu.addSeparator()

            a = menu.addAction("↩  Rollback Completo")
            a.triggered.connect(lambda: self.rollback_requested.emit(folder))

            a = menu.addAction("✖  Cancelar Checkpoint")
            a.triggered.connect(lambda: self.cancel_checkpoint_requested.emit(folder))

        menu.addSeparator()

        # Remove
        a = menu.addAction(f"🗑  Remover '{name}'")
        a.triggered.connect(lambda: self.remove_folder_requested.emit(folder))

        menu.exec(global_pos)

    # ── Click handlers ──────────────────────────────────────────────────────

    def _on_filter_click(self, key: str):
        self._active_filter = key
        self._active_folder = ""
        self._update_active()
        self.filter_changed.emit(key)

    def _on_folder_click(self, folder: str):
        self._active_folder = folder
        self._active_filter = ""
        self._update_active()
        self.folder_selected.emit(folder)

    # ── Style refresh ───────────────────────────────────────────────────────

    def _update_active(self):
        # Filter buttons — use Qt property system
        for key, btn in self._filter_buttons.items():
            active = (key == self._active_filter) and not self._active_folder
            btn.setProperty("active", "true" if active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()

        # Folder buttons — inline stylesheet + label update by state
        for folder, btn in self._folder_btns.items():
            has_cp = self._cp_status.get(folder, False)
            active = folder == self._active_folder
            btn.setStyleSheet(_FOLDER_STYLES[(has_cp, active)])

            # Keep label in sync (checkpoint badge in text)
            name   = Path(folder).name
            cp_tag = "  ⚑" if has_cp else ""
            btn.setText(f" 🗀  {name}{cp_tag}")
