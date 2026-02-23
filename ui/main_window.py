from __future__ import annotations

import os
import queue
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QStackedWidget, QFileDialog,
    QFrame, QApplication, QSystemTrayIcon, QMenu, QDialog,
    QLineEdit,
)
from PyQt6.QtCore import Qt, QTimer, QPoint, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont

from ui.sidebar_widget import SidebarWidget
from ui.changes_widget import ChangesWidget
from ui.diff_view import DiffPanel
from ui.win_blur import apply_acrylic_blur


# ── Styled confirm dialog ──────────────────────────────────────────────────────

class _ConfirmDialog(QDialog):
    """Dark-themed confirmation dialog."""

    def __init__(self, parent, message: str, danger: bool = False,
                 info_only: bool = False):
        super().__init__(parent)
        self.setWindowTitle("PastaMonitor")
        self.setModal(True)
        self.setMinimumWidth(360)
        self.setMaximumWidth(520)
        self.setStyleSheet("""
            QDialog {
                background-color: #1E1E1E;
                border: 1px solid #2E2E2E;
                border-radius: 12px;
            }
            QLabel#msgLabel {
                color: #E8E8E8;
                font-size: 13px;
                padding: 4px 0;
            }
            QLabel#iconLabel { font-size: 22px; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(18)

        # Icon + message
        row = QHBoxLayout()
        row.setSpacing(14)

        icon_char = "ℹ" if info_only else ("⚠" if danger else "❓")
        icon_lbl = QLabel(icon_char)
        icon_lbl.setObjectName("iconLabel")
        icon_lbl.setFixedWidth(28)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        row.addWidget(icon_lbl)

        text_lbl = QLabel(message)
        text_lbl.setObjectName("msgLabel")
        text_lbl.setWordWrap(True)
        row.addWidget(text_lbl, 1)
        layout.addLayout(row)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background: #2A2A2A; max-height: 1px; margin: 0;")
        layout.addWidget(sep)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        _neutral = """
            QPushButton {
                background: #2A2A2A; color: #AAAAAA;
                border: 1px solid #383838; border-radius: 7px;
                padding: 0 20px; font-size: 13px;
                min-width: 90px; min-height: 34px;
            }
            QPushButton:hover { background: #333; color: #E8E8E8; border-color: #444; }
        """

        if not info_only:
            cancel_btn = QPushButton("Cancelar")
            cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            cancel_btn.setStyleSheet(_neutral)
            cancel_btn.clicked.connect(self.reject)
            btn_row.addWidget(cancel_btn)

        ok_color = "#e74c3c" if danger else "#3498db"
        ok_hover  = "#c0392b" if danger else "#2980b9"
        ok_btn = QPushButton("Confirmar" if danger else "OK")
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_btn.setStyleSheet(f"""
            QPushButton {{
                background: {ok_color}; color: white; border: none;
                border-radius: 7px; padding: 0 20px; font-size: 13px;
                font-weight: 600; min-width: 90px; min-height: 34px;
            }}
            QPushButton:hover {{ background: {ok_hover}; }}
        """)
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)

        layout.addLayout(btn_row)


# ── Top bar: drag strip + search + window controls ─────────────────────────────

class _TopBar(QWidget):
    search_changed = pyqtSignal(str)   # emitted as user types

    def __init__(self, window: QMainWindow, parent=None):
        super().__init__(parent)
        self._window = window
        self._drag_pos: QPoint | None = None
        self.setObjectName("topBar")
        self.setFixedHeight(48)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 8, 0)
        layout.setSpacing(8)

        # Current view label (left)
        self._subtitle = QLabel("Todos os arquivos")
        self._subtitle.setObjectName("statusText")
        self._subtitle.setFixedWidth(140)
        layout.addWidget(self._subtitle)

        # Search box (center, stretches)
        self._search = QLineEdit()
        self._search.setPlaceholderText(" ⌕  Buscar arquivo…")
        self._search.setClearButtonEnabled(True)
        self._search.setStyleSheet("""
            QLineEdit {
                background: #252525;
                color: #DDD;
                border: 1px solid #333;
                border-radius: 8px;
                padding: 5px 12px;
                font-size: 12px;
                selection-background-color: #3498db;
            }
            QLineEdit:focus {
                border-color: #3498db;
                background: #2A2A2A;
            }
            QLineEdit::placeholder {
                color: #555;
            }
        """)
        self._search.textChanged.connect(self.search_changed.emit)
        layout.addWidget(self._search, 1)

        # Window controls (right)
        for symbol, obj_name, callback in [
            ("─", "iconBtn", self._window.showMinimized),
            ("□", "iconBtn", self._toggle_max),
            ("✕", "closeBtn", self._window._hide_to_tray),
        ]:
            btn = QPushButton(symbol)
            btn.setObjectName(obj_name)
            btn.setFixedSize(32, 32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(callback)
            layout.addWidget(btn)

    def set_subtitle(self, text: str):
        self._subtitle.setText(text)

    def clear_search(self):
        self._search.clear()

    def _toggle_max(self):
        if self._window.isMaximized():
            self._window.showNormal()
        else:
            self._window.showMaximized()

    # Drag support (clicks not on child widgets propagate here)
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint()
                - self._window.frameGeometry().topLeft()
            )

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            self._window.move(
                event.globalPosition().toPoint() - self._drag_pos
            )

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def mouseDoubleClickEvent(self, event):
        if not self._search.underMouse():
            self._toggle_max()


# ── Main window ────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):

    def __init__(self, app) -> None:
        super().__init__()
        self._app = app
        self._change_q: queue.Queue = queue.Queue()
        self._active_filter = ""
        self._active_folder = ""
        self._search_text   = ""

        # ── Window chrome ───────────────────────────────────────────────────
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(1160, 720)
        self.setMinimumSize(860, 500)

        screen = QApplication.primaryScreen().geometry()
        self.move(
            (screen.width() - 1160) // 2,
            (screen.height() - 720) // 2,
        )

        # ── Root layout ─────────────────────────────────────────────────────
        central = QWidget()
        self.setCentralWidget(central)
        main = QHBoxLayout(central)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        self._sidebar = SidebarWidget()
        main.addWidget(self._sidebar)

        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(0)

        self._topbar = _TopBar(self)
        rv.addWidget(self._topbar)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background: #1E1E1E; max-height: 1px;")
        rv.addWidget(sep)

        self._stack = QStackedWidget()
        self._changes_widget = ChangesWidget()
        self._diff_panel = DiffPanel()
        self._stack.addWidget(self._changes_widget)   # 0
        self._stack.addWidget(self._diff_panel)        # 1
        rv.addWidget(self._stack, 1)

        (self._action_bar, self._btn_cp, self._btn_rollback,
         self._btn_cancel, self._btn_clear, self._cp_lbl) = self._build_action_bar()
        rv.addWidget(self._action_bar)

        main.addWidget(right, 1)

        # ── Signals ─────────────────────────────────────────────────────────
        # Sidebar — filter / folder
        self._sidebar.filter_changed.connect(self._on_filter_changed)
        self._sidebar.folder_selected.connect(self._on_folder_selected)
        # Sidebar — folder management
        self._sidebar.add_folder_requested.connect(self._on_add_folder)
        self._sidebar.remove_folder_requested.connect(self._on_remove_folder)
        self._sidebar.open_folder_requested.connect(self._on_open_folder)
        # Sidebar — per-folder checkpoint actions
        self._sidebar.checkpoint_requested.connect(self._on_checkpoint_folder)
        self._sidebar.cancel_checkpoint_requested.connect(self._on_cancel_checkpoint_folder)
        self._sidebar.rollback_requested.connect(self._on_rollback_folder)
        # Changes widget
        self._changes_widget.rollback_requested.connect(self._on_rollback_file)
        self._changes_widget.diff_requested.connect(self._on_show_diff)
        self._diff_panel.closed.connect(self._on_diff_closed)
        # Search
        self._topbar.search_changed.connect(self._on_search_changed)

        # ── Poll timer ──────────────────────────────────────────────────────
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_changes)
        self._poll_timer.start(300)

        # ── Tray ────────────────────────────────────────────────────────────
        self._setup_tray()

        # ── Initial state ───────────────────────────────────────────────────
        self._refresh_sidebar_folders()
        self._refresh_changes()
        self._update_action_bar()

    # ── Public interface ────────────────────────────────────────────────────

    def notify_change(self, folder_path: str) -> None:
        self._change_q.put(folder_path)

    def show(self, select_folder: str | None = None) -> None:  # type: ignore[override]
        if select_folder:
            self._sidebar.select_folder(select_folder)
            self._active_folder = select_folder
            self._active_filter = ""
        super().show()
        self.raise_()
        self.activateWindow()

    def update_tray(self) -> None:
        self._rebuild_tray_menu()

    # ── Qt events ───────────────────────────────────────────────────────────

    def showEvent(self, event):
        super().showEvent(event)
        apply_acrylic_blur(int(self.winId()), opacity=200, color=0x111111)

    def closeEvent(self, event):
        event.ignore()
        self._hide_to_tray()

    # ── Action bar ──────────────────────────────────────────────────────────

    def _build_action_bar(self):
        bar = QWidget()
        bar.setObjectName("actionBar")
        bar.setFixedHeight(58)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(10)

        btn_cp = QPushButton("✔  Criar Checkpoint")
        btn_cp.setObjectName("accentBtn")
        btn_cp.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cp.clicked.connect(self._on_checkpoint)
        layout.addWidget(btn_cp)

        btn_rb = QPushButton("↩  Rollback Completo")
        btn_rb.setObjectName("dangerBtn")
        btn_rb.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_rb.clicked.connect(self._on_rollback)
        layout.addWidget(btn_rb)

        btn_cancel = QPushButton("✖  Cancelar Checkpoint")
        btn_cancel.setObjectName("neutralBtn")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.clicked.connect(self._on_cancel_checkpoint)
        layout.addWidget(btn_cancel)

        cp_lbl = QLabel("⚑  Checkpoint ativo")
        cp_lbl.setObjectName("checkpointLabel")
        cp_lbl.setVisible(False)
        layout.addWidget(cp_lbl)

        layout.addStretch()

        btn_clear = QPushButton("🗑  Limpar Historico")
        btn_clear.setObjectName("neutralBtn")
        btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear.clicked.connect(self._on_clear)
        layout.addWidget(btn_clear)

        return bar, btn_cp, btn_rb, btn_cancel, btn_clear, cp_lbl

    # ── Sidebar — filter / folder ────────────────────────────────────────────

    def _on_filter_changed(self, key: str) -> None:
        self._active_filter = key
        self._active_folder = ""
        self._topbar.set_subtitle({
            "":         "Todos os arquivos",
            "modified": "Modificados",
            "created":  "Criados",
            "deleted":  "Deletados",
            "moved":    "Movidos",
        }.get(key, key.capitalize()))
        self._stack.setCurrentIndex(0)
        self._refresh_changes()

    def _on_folder_selected(self, folder: str) -> None:
        self._active_folder = folder
        self._active_filter = ""
        name = Path(folder).name if folder else "Todos"
        self._topbar.set_subtitle(f"🗀 {name}")
        self._stack.setCurrentIndex(0)
        self._refresh_changes()

    # ── Sidebar — folder management ─────────────────────────────────────────

    def _on_add_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Adicionar pasta para monitorar", str(Path.home()),
        )
        if path:
            self._app.add_folder(str(Path(path).resolve()))
            self._refresh_sidebar_folders()
            self._rebuild_tray_menu()
            self._refresh_changes()
            self._update_action_bar()

    def _on_remove_folder(self, folder: str) -> None:
        name = Path(folder).name
        if self._confirm(
            f"Remover '{name}' do monitoramento?\n\nAs alterações pendentes serão perdidas.",
            danger=False,
        ):
            self._app.remove_folder(folder)
            if self._active_folder == folder:
                self._active_folder = ""
                self._topbar.set_subtitle("Todos os arquivos")
            self._refresh_sidebar_folders()
            self._rebuild_tray_menu()
            self._refresh_changes()
            self._update_action_bar()

    def _on_open_folder(self, folder: str) -> None:
        try:
            os.startfile(folder)          # Windows
        except AttributeError:
            import subprocess
            subprocess.Popen(["xdg-open", folder])   # Linux fallback

    # ── Sidebar — per-folder checkpoint actions ──────────────────────────────

    def _on_checkpoint_folder(self, folder: str) -> None:
        monitor = self._app.monitors.get(folder)
        if monitor and not monitor.has_checkpoint:
            monitor.create_checkpoint()
            self._post_checkpoint_refresh()

    def _on_cancel_checkpoint_folder(self, folder: str) -> None:
        monitor = self._app.monitors.get(folder)
        if monitor:
            monitor.cancel_checkpoint()
            self._post_checkpoint_refresh()

    def _on_rollback_folder(self, folder: str) -> None:
        name = Path(folder).name
        if not self._confirm(
            f"Reverter TODOS os arquivos de '{name}' ao checkpoint?\n\n"
            "Esta ação não pode ser desfeita.",
            danger=True,
        ):
            return
        monitor = self._app.monitors.get(folder)
        if monitor and monitor.has_checkpoint:
            monitor.rollback()
        self._stack.setCurrentIndex(0)
        self._post_checkpoint_refresh()

    def _post_checkpoint_refresh(self) -> None:
        self._update_action_bar()
        self._refresh_sidebar_folders()
        self._refresh_changes()

    # ── Changes widget signals ───────────────────────────────────────────────

    def _on_rollback_file(self, folder: str, rel_path: str) -> None:
        name = Path(rel_path).name
        if not self._confirm(
            f"Reverter '{name}' ao checkpoint?\n\nEsta ação não pode ser desfeita.",
            danger=True,
        ):
            return
        monitor = self._app.monitors.get(folder)
        if monitor:
            monitor.rollback_file(rel_path)
        self._refresh_changes()
        self._update_action_bar()

    def _on_show_diff(self, folder: str, rel_path: str) -> None:
        monitor = self._app.monitors.get(folder)
        if not monitor:
            return
        self._diff_panel.load(folder, rel_path, monitor._checkpoint_dir)
        self._stack.setCurrentIndex(1)

    def _on_diff_closed(self) -> None:
        self._stack.setCurrentIndex(0)

    # ── Search ───────────────────────────────────────────────────────────────

    def _on_search_changed(self, text: str) -> None:
        self._search_text = text.strip().lower()
        self._refresh_changes()

    # ── Global checkpoint actions (action bar) ───────────────────────────────

    def _on_checkpoint(self) -> None:
        if not self._app.monitors:
            self._info_dialog("Nenhuma pasta sendo monitorada.")
            return
        for monitor in self._app.monitors.values():
            if not monitor.has_checkpoint:
                monitor.create_checkpoint()
        self._post_checkpoint_refresh()

    def _on_rollback(self) -> None:
        cp_folders = [
            Path(f).name for f, m in self._app.monitors.items() if m.has_checkpoint
        ]
        if not cp_folders:
            return
        folders_str = ", ".join(cp_folders)
        if not self._confirm(
            f"Reverter TODOS os arquivos ao checkpoint?\nPastas: {folders_str}\n\n"
            "Esta ação não pode ser desfeita.",
            danger=True,
        ):
            return
        for monitor in self._app.monitors.values():
            if monitor.has_checkpoint:
                monitor.rollback()
        self._stack.setCurrentIndex(0)
        self._post_checkpoint_refresh()

    def _on_cancel_checkpoint(self) -> None:
        for monitor in self._app.monitors.values():
            monitor.cancel_checkpoint()
        self._post_checkpoint_refresh()

    def _on_clear(self) -> None:
        has_cp = any(m.has_checkpoint for m in self._app.monitors.values())
        if has_cp:
            self._info_dialog("Cancele o checkpoint antes de limpar a lista.")
            return
        if not self._confirm(
            "Limpar o registro de todas as alterações?\n\nOs arquivos NÃO serão alterados.",
            danger=False,
        ):
            return
        for monitor in self._app.monitors.values():
            monitor.clear_all_changes()
        self._stack.setCurrentIndex(0)
        self._refresh_changes()

    # ── Poll & refresh ───────────────────────────────────────────────────────

    def _poll_changes(self) -> None:
        changed = False
        try:
            while True:
                self._change_q.get_nowait()
                changed = True
        except queue.Empty:
            pass
        if changed:
            self._refresh_changes()
            self._update_action_bar()

    def _refresh_changes(self) -> None:
        all_changes: dict = {}
        has_checkpoint = any(m.has_checkpoint for m in self._app.monitors.values())

        for folder, monitor in self._app.monitors.items():
            if self._active_folder and folder != self._active_folder:
                continue
            for rel_path, info in monitor.get_changes().items():
                if self._active_filter and info.get("type") != self._active_filter:
                    continue
                # Search filter
                if self._search_text:
                    haystack = rel_path.lower()
                    if self._search_text not in haystack:
                        continue
                all_changes[(folder, rel_path)] = info

        self._changes_widget.set_changes(all_changes, has_checkpoint)

    def _refresh_sidebar_folders(self) -> None:
        folders = list(self._app.monitors.keys())
        cp_status = {f: self._app.monitors[f].has_checkpoint for f in folders}
        self._sidebar.set_folders(folders, cp_status)

    def _update_action_bar(self) -> None:
        has_monitors = bool(self._app.monitors)
        cp_count = sum(1 for m in self._app.monitors.values() if m.has_checkpoint)
        has_cp   = cp_count > 0

        self._btn_cp.setEnabled(has_monitors and not has_cp)
        self._btn_rollback.setEnabled(has_cp)
        self._btn_cancel.setEnabled(has_cp)
        self._btn_clear.setEnabled(has_monitors and not has_cp)
        self._cp_lbl.setVisible(has_cp)

        if has_cp:
            total = len(self._app.monitors)
            if cp_count == total:
                self._cp_lbl.setText("⚑  Checkpoint ativo")
            else:
                self._cp_lbl.setText(f"⚑  {cp_count}/{total} checkpoints")

    # ── Tray ─────────────────────────────────────────────────────────────────

    def _setup_tray(self) -> None:
        self._tray = QSystemTrayIcon(self._make_tray_icon(), self)
        self._tray.setToolTip("PastaMonitor")
        self._tray.activated.connect(self._on_tray_activated)
        self._rebuild_tray_menu()
        self._tray.show()

    def _make_tray_icon(self) -> QIcon:
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor("transparent"))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor("#3498db"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, 32, 32, 6, 6)
        painter.setPen(QColor("white"))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        from PyQt6.QtCore import QRect
        painter.drawText(QRect(0, 0, 32, 32), Qt.AlignmentFlag.AlignCenter, "PM")
        painter.end()
        return QIcon(pixmap)

    def _rebuild_tray_menu(self) -> None:
        menu = QMenu()
        menu.addAction("🗀  Mostrar").triggered.connect(lambda: self.show())
        menu.addAction("✙  Adicionar Pasta").triggered.connect(self._on_add_folder)

        if self._app.monitors:
            menu.addSeparator()
            for folder in self._app.monitors:
                name = Path(folder).name
                monitor = self._app.monitors[folder]
                badge = " [CP]" if monitor.has_checkpoint else ""
                action = menu.addAction(f"  {name}{badge}")
                action.triggered.connect(
                    lambda checked=False, f=folder: self.show(select_folder=f)
                )

        menu.addSeparator()
        menu.addAction("Sair").triggered.connect(self._on_quit)
        self._tray.setContextMenu(menu)

    def _on_tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()

    def _hide_to_tray(self) -> None:
        self.hide()
        if self._tray.isVisible():
            self._tray.showMessage(
                "PastaMonitor", "Monitorando em segundo plano.",
                QSystemTrayIcon.MessageIcon.Information, 2000,
            )

    def _on_quit(self) -> None:
        self._app._quit()

    # ── Utilities ────────────────────────────────────────────────────────────

    def _confirm(self, message: str, danger: bool = False) -> bool:
        return _ConfirmDialog(self, message, danger).exec() == QDialog.DialogCode.Accepted

    def _info_dialog(self, message: str) -> None:
        _ConfirmDialog(self, message, info_only=True).exec()
