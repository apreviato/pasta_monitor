"""
app.py - Application orchestrator
"""

from __future__ import annotations

import queue
from pathlib import Path
from typing import Optional

from config import ConfigManager
from monitor import FolderMonitor
from tray import SystemTray
from ui import MainWindow


class PastaMonitorApp:
    """Top-level application class that wires together all components."""

    def __init__(self) -> None:
        self.config = ConfigManager()
        self.monitors: dict[str, FolderMonitor] = {}
        self.tray_q: queue.Queue = queue.Queue()

        # Start monitors for previously saved folders
        for folder in list(self.config.folders):
            if Path(folder).is_dir():
                self._start_monitor(folder)
            else:
                # Folder no longer exists – remove from config silently
                self.config.remove_folder(folder)

        # Build UI (must happen before tray so we can reference self.window)
        self.window = MainWindow(self)

        # Build tray
        self.tray = SystemTray(self)
        self.tray.start()

        # Register tray action pump on the tkinter event loop
        self.window.root.after(100, self._pump_tray_queue)

    # ── Monitor management ────────────────────────────────────────────────

    def _start_monitor(self, folder: str) -> FolderMonitor:
        monitor = FolderMonitor(folder)
        monitor.on_change = self._on_file_change
        monitor.start()
        self.monitors[folder] = monitor
        return monitor

    def _stop_monitor(self, folder: str) -> None:
        monitor = self.monitors.pop(folder, None)
        if monitor:
            monitor.stop()

    def _on_file_change(self, folder_path: str) -> None:
        """Called from watchdog thread; forward to UI safely."""
        self.window.notify_change(folder_path)

    # ── Public actions ────────────────────────────────────────────────────

    def add_folder(self, path: str) -> bool:
        """Add and start monitoring a folder. Returns True if it was new."""
        norm = str(Path(path).resolve())
        added = self.config.add_folder(norm)
        if added and norm not in self.monitors:
            self._start_monitor(norm)
        self.tray.update_menu()
        return added

    def remove_folder(self, path: str) -> None:
        norm = str(Path(path).resolve())
        self._stop_monitor(norm)
        self.config.remove_folder(norm)
        self.tray.update_menu()

    # ── Tray → main thread bridge ─────────────────────────────────────────

    def _pump_tray_queue(self) -> None:
        try:
            while True:
                action, data = self.tray_q.get_nowait()
                self._handle_tray_action(action, data)
        except queue.Empty:
            pass
        self.window.root.after(100, self._pump_tray_queue)

    def _handle_tray_action(self, action: str, data) -> None:
        if action == "add_folder":
            self.window.show()
            self.window._add_folder()
        elif action == "open_folder":
            self.window.show(select_folder=data)
        elif action == "show":
            self.window.show()
        elif action == "quit":
            self._quit()

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def _quit(self) -> None:
        for monitor in list(self.monitors.values()):
            monitor.stop()
        self.tray.stop()
        self.window.root.quit()

    def run(self) -> None:
        self.window.run()
