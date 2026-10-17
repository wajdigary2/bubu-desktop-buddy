#!/usr/bin/env python
"""Render docs/screenshot.png of the buddy, composited onto a soft gradient.

Uses Qt's offscreen platform so it works without a visible desktop session:

    python tools/make_screenshot.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QRectF, Qt, QTimer  # noqa: E402
from PySide6.QtGui import (  # noqa: E402
    QColor,
    QGuiApplication,
    QLinearGradient,
    QPainter,
    QPixmap,
)
from PySide6.QtWidgets import QApplication  # noqa: E402

from bubu.buddy import BuddyWindow  # noqa: E402
from bubu.config import Config  # noqa: E402


def main() -> int:
    app = QApplication(sys.argv[:1])
    config = Config()
    buddy = BuddyWindow(config)
    buddy.needs.hunger = 70.0
    buddy.needs.mood = 95.0
    buddy.show()

    def pose() -> None:
        buddy.brain.dance()
        buddy.say("Hi! I'm Bubu your desktop buddy \U0001f43b")

    QTimer.singleShot(100, pose)
    deadline = time.time() + 1.2
    while time.time() < deadline:
        app.processEvents()
        time.sleep(0.005)

    shot = buddy.grab()

    screen = QGuiApplication.primaryScreen()
    target = screen.size() if screen else shot.size()
    canvas = QPixmap(max(shot.width(), 420), max(shot.height(), 340))
    canvas.fill(Qt.GlobalColor.transparent)

    painter = QPainter(canvas)
    gradient = QLinearGradient(0, 0, canvas.width(), canvas.height())
    gradient.setColorAt(0.0, QColor("#FFF4E4"))
    gradient.setColorAt(1.0, QColor("#FFDCB8"))
    painter.fillRect(QRectF(0, 0, canvas.width(), canvas.height()), gradient)
    painter.drawPixmap(0, 0, shot)
    painter.end()

    out = ROOT / "docs" / "screenshot.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(str(out))
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
