"""
tray.py - System tray icon (pystray + Pillow)
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import TYPE_CHECKING

import pystray
from PIL import Image, ImageDraw, ImageFont

if TYPE_CHECKING:
    from app import PastaMonitorApp

APP_NAME = "PastaMonitor"


def _make_icon_image(size: int = 64) -> Image.Image:
    """Draw a simple folder icon with a magnifier overlay."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    s = size
    # Folder body
    d.rounded_rectangle(
        [s * 0.04, s * 0.30, s * 0.96, s * 0.88],
        radius=s * 0.08,
        fill=(60, 120, 200),
    )
    # Folder tab
    d.rounded_rectangle(
        [s * 0.04, s * 0.22, s * 0.42, s * 0.36],
        radius=s * 0.06,
        fill=(60, 120, 200),
    )
    # White lines (files)
    lw = max(1, int(s * 0.04))
    for frac in (0.52, 0.63, 0.74):
        y = int(s * frac)
        d.line([(int(s * 0.16), y), (int(s * 0.84), y)],
               fill="white", width=lw)

    # Small magnifier circle (top-right)
    cx, cy, r = int(s * 0.74), int(s * 0.28), int(s * 0.16)
    lw2 = max(2, int(s * 0.06))
    d.ellipse([cx - r, cy - r, cx + r, cy + r],
              outline=(255, 210, 50), width=lw2)
    d.line([(cx + r - 2, cy + r - 2), (cx + r + 5, cy + r + 5)],
           fill=(255, 210, 50), width=lw2)

    return img


class SystemTray:
    """Manages the system tray icon using pystray."""

    def __init__(self, app: "PastaMonitorApp") -> None:
        self.app = app
        self._icon: pystray.Icon | None = None
        self._icon_image = _make_icon_image(64)

    # ── Menu construction ─────────────────────────────────────────────────

    def _build_menu(self) -> pystray.Menu:
        items: list = []

        # Add folder
        items.append(
            pystray.MenuItem("Adicionar Pasta…", self._cb_add_folder)
        )
        items.append(pystray.Menu.SEPARATOR)

        # Monitored folders
        for folder in self.app.config.folders:
            name = Path(folder).name
            monitor = self.app.monitors.get(folder)
            badge = " [CP]" if (monitor and monitor.has_checkpoint) else ""
            label = f"📁  {name}{badge}"
            # Capture folder in closure
            items.append(
                pystray.MenuItem(
                    label,
                    self._make_folder_cb(folder),
                )
            )

        if self.app.config.folders:
            items.append(pystray.Menu.SEPARATOR)

        items.append(pystray.MenuItem("Monitor", self._cb_show))
        items.append(pystray.Menu.SEPARATOR)
        items.append(pystray.MenuItem("Fechar", self._cb_quit))

        return pystray.Menu(*items)

    def _make_folder_cb(self, folder: str):
        def _cb(icon, item):
            self.app.tray_q.put(("open_folder", folder))
        return _cb

    # ── Callbacks (called from tray thread → enqueue to main thread) ──────

    def _cb_add_folder(self, icon, item):
        self.app.tray_q.put(("add_folder", None))

    def _cb_show(self, icon, item):
        self.app.tray_q.put(("show", None))

    def _cb_quit(self, icon, item):
        self.app.tray_q.put(("quit", None))

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def start(self) -> None:
        self._icon = pystray.Icon(
            APP_NAME,
            self._icon_image,
            APP_NAME,
            menu=self._build_menu(),
        )
        threading.Thread(target=self._icon.run, daemon=True, name="tray").start()

    def update_menu(self) -> None:
        if self._icon:
            self._icon.menu = self._build_menu()
            try:
                self._icon.update_menu()
            except Exception:
                pass  # Not all backends support update_menu

    def stop(self) -> None:
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass
