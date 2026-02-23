from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QApplication, QMenu,
)
from PyQt6.QtCore import Qt, pyqtSignal


_TYPE_CONFIG = {
    "modified": ("✎", "#3498db", "Modificado"),
    "created":  ("✚", "#2ecc71", "Criado"),
    "deleted":  ("✖", "#e74c3c", "Deletado"),
    "moved":    ("➜", "#f39c12", "Movido"),
}

_BADGE_BG = {
    "modified": "rgba(52,152,219,.15)",
    "created":  "rgba(46,204,113,.15)",
    "deleted":  "rgba(231,76,60,.15)",
    "moved":    "rgba(243,156,18,.15)",
}
_BADGE_BORDER = {
    "modified": "rgba(52,152,219,.3)",
    "created":  "rgba(46,204,113,.3)",
    "deleted":  "rgba(231,76,60,.3)",
    "moved":    "rgba(243,156,18,.3)",
}

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
    color: #555;
}
QMenu::separator {
    height: 1px;
    background: #2A2A2A;
    margin: 4px 6px;
}
"""


class ChangeCardWidget(QFrame):
    rollback_requested = pyqtSignal(str, str)   # folder, rel_path
    diff_requested = pyqtSignal(str, str)        # folder, rel_path

    def __init__(self, folder: str, rel_path: str, info: dict,
                 has_checkpoint: bool, parent=None):
        super().__init__(parent)
        self.setObjectName("changeCard")
        self._folder = folder
        self._rel_path = rel_path
        self._info = info
        self._has_checkpoint = has_checkpoint
        self.setMinimumHeight(70)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)

        change_type = self._info.get("type", "modified")
        icon, color, badge_label = _TYPE_CONFIG.get(
            change_type, ("?", "#999", change_type.capitalize())
        )

        # ── Left: type icon ─────────────────────────────────────────────────
        icon_wrap = QWidget()
        icon_wrap.setFixedWidth(30)
        icon_wrap_l = QVBoxLayout(icon_wrap)
        icon_wrap_l.setContentsMargins(0, 0, 0, 0)
        icon_wrap_l.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_lbl = QLabel(icon)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(
            f"color: {color}; font-size: 15px; font-weight: 700; "
            "background: transparent;"
        )
        icon_wrap_l.addWidget(icon_lbl)
        layout.addWidget(icon_wrap)

        # ── Center: file info ───────────────────────────────────────────────
        center = QWidget()
        center.setStyleSheet("background: transparent;")
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(3)

        p = Path(self._rel_path)

        # File name — bold
        name_lbl = QLabel(p.name)
        name_lbl.setStyleSheet(
            "color: #E8E8E8; font-size: 13px; font-weight: 600; background: transparent;"
        )
        name_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        center_layout.addWidget(name_lbl)

        # Parent path — only if not root
        if str(p.parent) != ".":
            path_lbl = QLabel(str(p.parent) + "/")
            path_lbl.setStyleSheet(
                "color: #777; font-size: 11px; background: transparent;"
            )
            center_layout.addWidget(path_lbl)

        # Meta row: badge + folder + time
        meta_row = QHBoxLayout()
        meta_row.setContentsMargins(0, 2, 0, 0)
        meta_row.setSpacing(8)

        badge = QLabel(badge_label)
        badge.setStyleSheet(
            f"background: {_BADGE_BG.get(change_type, 'transparent')};"
            f"color: {color};"
            f"border: 1px solid {_BADGE_BORDER.get(change_type, 'transparent')};"
            "border-radius: 8px; padding: 1px 8px;"
            "font-size: 10px; font-weight: 700;"
        )
        meta_row.addWidget(badge)

        folder_name = Path(self._folder).name
        folder_lbl = QLabel(f"🗀 {folder_name}")
        folder_lbl.setStyleSheet(
            "color: #555; font-size: 10px; background: transparent;"
        )
        meta_row.addWidget(folder_lbl)

        time_str = self._info.get("time", "")
        if time_str:
            if "T" in time_str:
                time_str = time_str.split("T")[-1][:8]
            time_lbl = QLabel(f"❶ {time_str}")
            time_lbl.setStyleSheet(
                "color: #555; font-size: 10px; background: transparent;"
            )
            meta_row.addWidget(time_lbl)

        meta_row.addStretch()
        center_layout.addLayout(meta_row)
        layout.addWidget(center, 1)

        # ── Right: action buttons ───────────────────────────────────────────
        if self._has_checkpoint:
            btns = QWidget()
            btns.setStyleSheet("background: transparent;")
            btns_layout = QHBoxLayout(btns)
            btns_layout.setContentsMargins(0, 0, 0, 0)
            btns_layout.setSpacing(6)

            if change_type != "deleted":
                diff_btn = _action_btn("☷  Diff", "blue")
                diff_btn.setToolTip("Ver diferenças em relação ao checkpoint (duplo clique)")
                diff_btn.clicked.connect(
                    lambda: self.diff_requested.emit(self._folder, self._rel_path)
                )
                btns_layout.addWidget(diff_btn)

            rb_btn = _action_btn("↩  Reverter", "red")
            rb_btn.setToolTip("Reverter este arquivo ao checkpoint")
            rb_btn.clicked.connect(
                lambda: self.rollback_requested.emit(self._folder, self._rel_path)
            )
            btns_layout.addWidget(rb_btn)

            layout.addWidget(btns)

    # ── Mouse events ────────────────────────────────────────────────────────

    def mouseDoubleClickEvent(self, event):
        if (self._has_checkpoint
                and self._info.get("type") != "deleted"):
            self.diff_requested.emit(self._folder, self._rel_path)
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        change_type = self._info.get("type", "modified")
        menu = QMenu(self)
        menu.setStyleSheet(_MENU_STYLE)

        can_diff = self._has_checkpoint and change_type != "deleted"
        can_rb   = self._has_checkpoint

        # ── Diff ──────────────────────────────────────────────────────────
        diff_action = menu.addAction("☷  Ver Diferenças")
        diff_action.setEnabled(can_diff)
        if can_diff:
            diff_action.triggered.connect(
                lambda: self.diff_requested.emit(self._folder, self._rel_path)
            )

        # ── Rollback ──────────────────────────────────────────────────────
        menu.addSeparator()
        rb_action = menu.addAction("↩  Reverter este Arquivo")
        rb_action.setEnabled(can_rb)
        if can_rb:
            rb_action.triggered.connect(
                lambda: self.rollback_requested.emit(self._folder, self._rel_path)
            )

        # ── Copy ──────────────────────────────────────────────────────────
        menu.addSeparator()

        p = Path(self._rel_path)
        a = menu.addAction("⎘  Copiar nome do arquivo")
        a.triggered.connect(lambda: QApplication.clipboard().setText(p.name))

        a = menu.addAction("⎘  Copiar caminho relativo")
        a.triggered.connect(lambda: QApplication.clipboard().setText(self._rel_path))

        full = str(Path(self._folder) / self._rel_path)
        a = menu.addAction("⎘  Copiar caminho completo")
        a.triggered.connect(lambda: QApplication.clipboard().setText(full))

        menu.exec(event.globalPos())


# ── Shared helper ──────────────────────────────────────────────────────────────

def _action_btn(label: str, variant: str) -> QPushButton:
    btn = QPushButton(label)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    if variant == "blue":
        btn.setStyleSheet("""
            QPushButton {
                background: rgba(52,152,219,.12);
                color: #3498db;
                border: 1px solid rgba(52,152,219,.25);
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: rgba(52,152,219,.24);
                border-color: #3498db;
            }
        """)
    else:
        btn.setStyleSheet("""
            QPushButton {
                background: rgba(231,76,60,.10);
                color: #e74c3c;
                border: 1px solid rgba(231,76,60,.2);
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: rgba(231,76,60,.24);
                border-color: #e74c3c;
            }
        """)
    return btn


# ── Changes list widget ────────────────────────────────────────────────────────

class ChangesWidget(QWidget):
    rollback_requested = pyqtSignal(str, str)
    diff_requested = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Header ─────────────────────────────────────────────────────────
        header = QWidget()
        header.setObjectName("listHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 14, 20, 10)
        header_layout.setSpacing(10)

        self._title_lbl = QLabel("Alterações")
        self._title_lbl.setObjectName("listTitle")
        header_layout.addWidget(self._title_lbl)

        header_layout.addStretch()

        self._count_lbl = QLabel("")
        self._count_lbl.setObjectName("listCount")
        header_layout.addWidget(self._count_lbl)

        outer.addWidget(header)

        # Thin separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background: #1E1E1E; max-height: 1px;")
        outer.addWidget(sep)

        # ── Scroll area for cards ───────────────────────────────────────────
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(self._scroll, 1)

        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._cards_layout = QVBoxLayout(self._container)
        self._cards_layout.setContentsMargins(16, 10, 16, 16)
        self._cards_layout.setSpacing(8)
        self._cards_layout.addStretch()   # keeps cards aligned to top
        self._scroll.setWidget(self._container)

        # ── Empty state ────────────────────────────────────────────────────
        self._empty = QWidget()
        self._empty.setStyleSheet("background: transparent;")
        empty_layout = QVBoxLayout(self._empty)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setSpacing(10)

        icon_lbl = QLabel("📭")
        icon_lbl.setObjectName("emptyIcon")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(icon_lbl)

        msg_lbl = QLabel("Nenhuma alteração detectada")
        msg_lbl.setObjectName("emptyText")
        msg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(msg_lbl)

        hint_lbl = QLabel("Adicione uma pasta na barra lateral para começar")
        hint_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint_lbl.setStyleSheet("color: #3A3A3A; font-size: 11px;")
        empty_layout.addWidget(hint_lbl)

        # Give empty state stretch=1 so it fills the available height
        outer.addWidget(self._empty, 1)

        self._show_empty(True)

    # ── Public API ─────────────────────────────────────────────────────────

    def set_changes(self, changes: dict, has_checkpoint: bool) -> None:
        """Rebuild the card list.

        Args:
            changes: {(folder, rel_path): {"type": str, "time": str}}
            has_checkpoint: whether any monitor has an active checkpoint
        """
        # Remove existing cards (keep the trailing stretch at index 0 when empty)
        while self._cards_layout.count() > 1:
            item = self._cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not changes:
            self._count_lbl.setText("")
            self._show_empty(True)
            return

        self._show_empty(False)
        count = len(changes)
        self._count_lbl.setText(
            f"{count} {'alteração' if count == 1 else 'alterações'}"
        )

        sorted_items = sorted(
            changes.items(),
            key=lambda x: x[1].get("time", ""),
            reverse=True,
        )
        for i, ((folder, rel_path), info) in enumerate(sorted_items):
            card = ChangeCardWidget(folder, rel_path, info, has_checkpoint)
            card.rollback_requested.connect(self.rollback_requested.emit)
            card.diff_requested.connect(self.diff_requested.emit)
            # Insert before the trailing stretch
            self._cards_layout.insertWidget(i, card)

    # ── Internal ───────────────────────────────────────────────────────────

    def _show_empty(self, empty: bool) -> None:
        self._scroll.setVisible(not empty)
        self._empty.setVisible(empty)
