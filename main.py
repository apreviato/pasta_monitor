#!/usr/bin/env python3
"""
PastaMonitor - Monitor de arquivos com suporte a checkpoint e rollback.

Uso:
    python main.py

Dependências:
    pip install watchdog PyQt6
"""

import sys
import os

# Ensure the script's directory is on the path so relative imports work
# whether launched from IDE, terminal, or double-click.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)


def _check_dependencies() -> None:
    missing = []
    for pkg in ("watchdog", "PyQt6"):
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(
            "Dependências faltando. Instale com:\n"
            f"    pip install {' '.join(missing)}\n"
        )
        sys.exit(1)


def main() -> None:
    _check_dependencies()

    from PyQt6.QtWidgets import QApplication
    from ui.styles import STYLESHEET

    qt_app = QApplication(sys.argv)
    qt_app.setStyleSheet(STYLESHEET)
    qt_app.setQuitOnLastWindowClosed(False)  # Keep alive when window is hidden to tray

    from app import PastaMonitorApp
    pasta_app = PastaMonitorApp()
    pasta_app.run()

    sys.exit(qt_app.exec())


if __name__ == "__main__":
    main()
