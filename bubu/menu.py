"""Right-click context menu."""

from __future__ import annotations

from PySide6.QtWidgets import QMenu


def build_menu(buddy) -> QMenu:
    menu = QMenu(buddy)

    menu.addAction("\U0001f36a  Feed a snack", buddy.feed)
    menu.addAction("\U0001f44f  Pet", buddy.pet)
    menu.addAction("\U0001f483  Dance", buddy.dance)
    menu.addAction("\U0001f634  Nap / wake up", buddy.toggle_sleep)
    menu.addAction("\U0001f4ac  Say something", lambda: buddy.say(_random_line()))
    menu.addSeparator()
    menu.addAction("⚙️  Settings…", buddy.show_settings)
    menu.addAction("ℹ️  About", buddy.show_about)
    menu.addSeparator()
    menu.addAction("✖  Quit Bubu", buddy.close)
    return menu


def _random_line() -> str:
    import random

    from . import lines

    return random.choice(lines.IDLE)
