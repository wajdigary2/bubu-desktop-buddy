"""Application bootstrap: command line, single instance, event loop."""

from __future__ import annotations

import argparse
import sys

from PySide6.QtCore import QSharedMemory, QTimer
from PySide6.QtWidgets import QApplication

from . import APP_NAME, __version__
from .buddy import BuddyWindow
from .config import Config


def _acquire_single_instance() -> tuple[bool, QSharedMemory | None]:
    """Return (allowed, memory). A second launch exits instead of double-buddying."""
    # Use a stable key without spaces to avoid platform-specific issues.
    key = "bubu_desktop_buddy_instance"
    memory = QSharedMemory(key)
    # If another instance owns the segment already, attach() will succeed.
    if memory.attach():
        return False, None
    # Try to create the shared memory segment and check for success.
    if not memory.create(1):
        # Could not create segment (race/permissions) — conservatively refuse to start.
        return False, None
    return True, memory


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)

    parser = argparse.ArgumentParser(
        prog="bubu-desktop-buddy",
        description="Bubu, a tiny open-source desktop companion.",
    )
    parser.add_argument(
        "--version", action="version", version=f"{APP_NAME} {__version__}"
    )
    parser.add_argument(
        "--reset", action="store_true", help="forget saved settings and position"
    )
    parser.add_argument(
        "--new-instance",
        action="store_true",
        help="allow launching a second buddy",
    )
    parser.add_argument(
        "--smoke-test", action="store_true", help=argparse.SUPPRESS
    )
    args, qt_args = parser.parse_known_args(argv[1:])

    if args.reset:
        Config.forget()

    app = QApplication([argv[0], *qt_args])
    app.setApplicationName("BubuDesktopBuddy")
    app.setApplicationDisplayName(APP_NAME)
    app.setOrganizationName("BubuDesktopBuddy")

    instance = None
    if not (args.new_instance or args.smoke_test):
        allowed, instance = _acquire_single_instance()
        if not allowed:
            print("Bubu is already running — look near your taskbar! \U0001f43b")
            return 0

    config = Config.load()
    buddy = BuddyWindow(config)
    buddy.show()

    if args.smoke_test:
        # Headless-ish self check: exercise the main code paths, then quit.
        QTimer.singleShot(300, buddy.greet)
        QTimer.singleShot(500, buddy.pet)
        QTimer.singleShot(800, buddy.feed)
        QTimer.singleShot(1100, buddy.jump)
        QTimer.singleShot(1400, buddy.dance)
        QTimer.singleShot(1500, lambda: buddy.grab())
        QTimer.singleShot(1700, app.quit)
    else:
        QTimer.singleShot(500, buddy.greet)

    code = app.exec()
    del instance  # release the single-instance segment
    config.save()
    return code
