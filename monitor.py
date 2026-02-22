"""
monitor.py - File system monitoring logic
"""

from __future__ import annotations

import fnmatch
import os
import shutil
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# Default patterns to ignore (similar to .gitignore)
DEFAULT_IGNORE_PATTERNS: list[str] = [
    ".git",
    "__pycache__",
    "*.pyc",
    "*.pyo",
    "node_modules",
    ".DS_Store",
    "Thumbs.db",
    "*.tmp",
    "*.log",
    ".idea",
    ".vscode",
    "*.egg-info",
    ".pastamonitor_backup",
]

IGNORE_FILENAME = ".pastamonitor_ignore"


class _ChangeHandler(FileSystemEventHandler):
    def __init__(self, monitor: "FolderMonitor") -> None:
        super().__init__()
        self.monitor = monitor

    def on_modified(self, event):
        if not event.is_directory:
            self.monitor._register_change(event.src_path, "modified")

    def on_created(self, event):
        if not event.is_directory:
            self.monitor._register_change(event.src_path, "created")

    def on_deleted(self, event):
        if not event.is_directory:
            self.monitor._register_change(event.src_path, "deleted")

    def on_moved(self, event):
        if not event.is_directory:
            self.monitor._register_change(event.dest_path, "moved")


class FolderMonitor:
    """Monitors a folder recursively for file changes.

    Attributes
    ----------
    folder_path : Path
    on_change : Callable[[str], None] | None
        Called (with the folder path string) whenever a change is recorded.
    """

    def __init__(self, folder_path: str | Path) -> None:
        self.folder_path = Path(folder_path).resolve()
        self._ignore_patterns: list[str] = self._load_ignore_patterns()

        # {rel_path: {"type": str, "time": str}}
        self._all_changes: dict[str, dict] = {}
        # Changes recorded after the last checkpoint
        self._checkpoint_changes: dict[str, dict] = {}

        self._checkpoint_dir: Optional[str] = None
        self._has_checkpoint: bool = False
        self._lock = threading.Lock()

        # rel_path -> timestamp until which watchdog events are suppressed
        # (used to silence events triggered by our own rollback writes)
        self._suppressed: dict[str, float] = {}

        self.on_change: Optional[Callable[[str], None]] = None

        self._observer: Optional[Observer] = None

    # ── Public properties ─────────────────────────────────────────────────

    @property
    def has_checkpoint(self) -> bool:
        return self._has_checkpoint

    @property
    def ignore_patterns(self) -> list[str]:
        return list(self._ignore_patterns)

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def start(self) -> None:
        handler = _ChangeHandler(self)
        self._observer = Observer()
        self._observer.schedule(handler, str(self.folder_path), recursive=True)
        self._observer.start()

    def stop(self) -> None:
        if self._observer and self._observer.is_alive():
            self._observer.stop()
            self._observer.join()
        # Clean up any dangling checkpoint
        if self._checkpoint_dir and Path(self._checkpoint_dir).exists():
            shutil.rmtree(self._checkpoint_dir, ignore_errors=True)

    # ── Ignore patterns ───────────────────────────────────────────────────

    def _load_ignore_patterns(self) -> list[str]:
        patterns = list(DEFAULT_IGNORE_PATTERNS)
        ignore_file = self.folder_path / IGNORE_FILENAME
        if ignore_file.exists():
            try:
                for line in ignore_file.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        patterns.append(line)
            except OSError:
                pass
        return patterns

    def reload_ignore_patterns(self) -> None:
        self._ignore_patterns = self._load_ignore_patterns()

    def _is_ignored(self, path: str | Path) -> bool:
        try:
            rel = Path(path).relative_to(self.folder_path)
        except ValueError:
            return False
        parts = rel.parts
        rel_str = rel.as_posix()
        for pattern in self._ignore_patterns:
            # Match any individual path component
            for part in parts:
                if fnmatch.fnmatch(part, pattern):
                    return True
            # Match the full relative path
            if fnmatch.fnmatch(rel_str, pattern):
                return True
        return False

    # ── Change tracking ───────────────────────────────────────────────────

    def _suppress_path(self, rel_path: str, duration: float = 3.0) -> None:
        """Temporarily ignore watchdog events for this relative path."""
        self._suppressed[rel_path] = time.monotonic() + duration

    def _register_change(self, path: str, change_type: str) -> None:
        if self._is_ignored(path):
            return
        try:
            rel = Path(path).relative_to(self.folder_path).as_posix()
        except ValueError:
            return

        # Skip events we triggered ourselves (rollback writes)
        expiry = self._suppressed.get(rel)
        if expiry and time.monotonic() < expiry:
            return
        # Clean up expired suppressions lazily
        if expiry:
            del self._suppressed[rel]

        now = datetime.now().isoformat(timespec="seconds")

        with self._lock:
            # Preserve semantic type across multiple watchdog events for the same file.
            # Windows often fires on_created followed immediately by on_modified.
            # Rules:
            #   created  + modified  → created   (still a brand-new file)
            #   deleted  + created   → modified   (file came back = effectively modified)
            #   anything + deleted   → deleted    (file is gone)
            def _merge(prev_type: str | None, new_type: str) -> str:
                if prev_type is None:
                    return new_type
                if prev_type == "created" and new_type == "modified":
                    return "created"
                if prev_type == "deleted" and new_type == "created":
                    return "modified"
                return new_type

            eff_all = _merge(
                self._all_changes.get(rel, {}).get("type"),
                change_type,
            )
            self._all_changes[rel] = {"type": eff_all, "time": now}

            if self._has_checkpoint:
                eff_cp = _merge(
                    self._checkpoint_changes.get(rel, {}).get("type"),
                    change_type,
                )
                self._checkpoint_changes[rel] = {"type": eff_cp, "time": now}

        if self.on_change:
            try:
                self.on_change(str(self.folder_path))
            except Exception:
                pass

    def get_changes(self) -> dict[str, dict]:
        """Return current changes (post-checkpoint if active, else all)."""
        with self._lock:
            if self._has_checkpoint:
                return dict(self._checkpoint_changes)
            return dict(self._all_changes)

    def clear_all_changes(self) -> None:
        with self._lock:
            self._all_changes.clear()
            self._checkpoint_changes.clear()

    # ── Checkpoint ────────────────────────────────────────────────────────

    def create_checkpoint(self) -> None:
        """Copy the current folder state to a temp directory."""
        # Remove any existing checkpoint first
        if self._checkpoint_dir and Path(self._checkpoint_dir).exists():
            shutil.rmtree(self._checkpoint_dir, ignore_errors=True)

        tmp = tempfile.mkdtemp(prefix="pastamonitor_")
        errors: list[str] = []

        for root, dirs, files in os.walk(self.folder_path):
            # Prune ignored directories in-place
            dirs[:] = [
                d for d in dirs
                if not self._is_ignored(Path(root) / d)
            ]
            for fname in files:
                src = Path(root) / fname
                if self._is_ignored(src):
                    continue
                try:
                    rel = src.relative_to(self.folder_path)
                    dst = Path(tmp) / rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(src), str(dst))
                except OSError as exc:
                    errors.append(f"{src}: {exc}")

        with self._lock:
            self._checkpoint_dir = tmp
            self._has_checkpoint = True
            self._checkpoint_changes = {}

        if errors:
            print(f"[PastaMonitor] Checkpoint warnings:\n" + "\n".join(errors))

    def rollback(self) -> bool:
        """Restore ALL files to checkpoint state and clear change list."""
        if not self._checkpoint_dir or not Path(self._checkpoint_dir).exists():
            return False

        errors: list[str] = []

        # Restore backed-up files
        for root, dirs, files in os.walk(self._checkpoint_dir):
            for fname in files:
                src = Path(root) / fname
                try:
                    rel_p = src.relative_to(self._checkpoint_dir)
                    rel_s = rel_p.as_posix()
                    dst   = self.folder_path / rel_p
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    self._suppress_path(rel_s)
                    shutil.copy2(str(src), str(dst))
                except OSError as exc:
                    errors.append(f"{src}: {exc}")

        # Delete files that were *created* after the checkpoint
        with self._lock:
            created_after = [
                rel for rel, info in self._checkpoint_changes.items()
                if info["type"] == "created"
            ]

        for rel in created_after:
            target = self.folder_path / rel
            if target.exists():
                try:
                    self._suppress_path(rel)
                    target.unlink()
                except OSError as exc:
                    errors.append(f"{target}: {exc}")

        # Clean up, reset checkpoint, and clear change list
        self._discard_checkpoint(clear_all=True)

        if errors:
            print("[PastaMonitor] Rollback warnings:\n" + "\n".join(errors))

        return len(errors) == 0

    def rollback_file(self, rel_path: str) -> bool:
        """Restore a single file to its checkpoint state.

        - "created" after checkpoint → deleted from disk
        - "modified"/"moved"/"deleted" → restored from checkpoint copy
        Removes the file from the change tracking dicts.
        """
        if not self._checkpoint_dir:
            return False

        checkpoint_file = Path(self._checkpoint_dir) / rel_path
        current_file = self.folder_path / rel_path

        with self._lock:
            info = self._checkpoint_changes.get(rel_path) or self._all_changes.get(rel_path)
            change_type = info["type"] if info else "modified"

        try:
            if change_type == "created":
                # File didn't exist at checkpoint; delete it
                self._suppress_path(rel_path)
                current_file.unlink(missing_ok=True)
            elif checkpoint_file.exists():
                # Restore from checkpoint
                current_file.parent.mkdir(parents=True, exist_ok=True)
                self._suppress_path(rel_path)
                shutil.copy2(str(checkpoint_file), str(current_file))
            else:
                # Not in checkpoint and not "created" — just remove current if it exists
                self._suppress_path(rel_path)
                current_file.unlink(missing_ok=True)
        except OSError as exc:
            print(f"[PastaMonitor] rollback_file error for {rel_path}: {exc}")
            return False

        with self._lock:
            self._checkpoint_changes.pop(rel_path, None)
            self._all_changes.pop(rel_path, None)

        return True

    def get_checkpoint_path(self, rel_path: str) -> Optional[Path]:
        """Return the Path to the checkpoint copy of rel_path, or None."""
        if not self._checkpoint_dir:
            return None
        p = Path(self._checkpoint_dir) / rel_path
        return p if p.exists() else None

    def cancel_checkpoint(self) -> None:
        """Discard checkpoint without restoring files."""
        self._discard_checkpoint()

    def _discard_checkpoint(self, clear_all: bool = False) -> None:
        if self._checkpoint_dir and Path(self._checkpoint_dir).exists():
            shutil.rmtree(self._checkpoint_dir, ignore_errors=True)
        with self._lock:
            self._checkpoint_dir = None
            self._has_checkpoint = False
            self._checkpoint_changes = {}
            if clear_all:
                self._all_changes.clear()
