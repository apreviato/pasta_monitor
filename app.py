"""
app.py - Application orchestrator
"""

from __future__ import annotations

from pathlib import Path

from config import ConfigManager
from monitor import FolderMonitor


class PastaMonitorApp:
    """Top-level application class that wires together all components."""

    def __init__(self) -> None:
        self.config = ConfigManager()
        self.monitors: dict[str, FolderMonitor] = {}

        # Start monitors for previously saved folders
        for folder in list(self.config.folders):
            if Path(folder).is_dir():
                self._start_monitor(folder)
            else:
                # Folder no longer exists – remove from config silently
                self.config.remove_folder(folder)

        # Build UI (PyQt6 MainWindow — includes its own system tray)
        from ui import MainWindow
        self.window = MainWindow(self)

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
        self.window.update_tray()
        return added

    def remove_folder(self, path: str) -> None:
        norm = str(Path(path).resolve())
        self._stop_monitor(norm)
        self.config.remove_folder(norm)
        self.window.update_tray()

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def _quit(self) -> None:
        for monitor in list(self.monitors.values()):
            monitor.stop()
        from PyQt6.QtWidgets import QApplication
        QApplication.instance().quit()

    def run(self) -> None:
        self.window.show()
