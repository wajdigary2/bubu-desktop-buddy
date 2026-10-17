"""Bubu's body, drawn entirely with QPainter primitives.

The character is defined in a local coordinate system: the origin sits between
the feet, +x points right, and the body extends upward into negative y. One
``Anim`` snapshot fully describes how the character should look this frame,
which keeps the widget code free of drawing details.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen

# Design height of the character in local units (rendered at any pixel size).
CHAR_HEIGHT = 210.0

FUR = QColor("#B98D62")
FUR_DARK = QColor("#7E5A38")
CREAM = QColor("#F7E9D2")
INNER_EAR = QColor("#E5A99B")
BLUSH = QColor("#EF9BA6")
DARK = QColor("#4A3423")
EYE = QColor("#33241A")
NOSE = QColor("#5C4230")
TONGUE = QColor("#E98C93")
COOKIE = QColor("#D9A05B")
COOKIE_EDGE = QColor("#A5702F")


@dataclass
class Anim:
    facing: int = 1  # 1 = right, -1 = left
    mood: str = "normal"  # normal | happy | sad | sleep | startled
    blink: float = 0.0  # 0 = open, >0 = closing
    walking: bool = False
    walk_phase: float = 0.0
    t: float = 0.0  # seconds, for breathing / idle motion
    sx: float = 1.0  # squash & stretch
    sy: float = 1.0
    rotation: float = 0.0  # whole-body wiggle, degrees
    arm_lift: float = 0.0  # 0..1, raise arms up
    mouth_open: float = 0.0  # 0..1
    eating: bool = False
    eat_progress: float = 0.0  # 0..1


# --------------------------------------------------------------------- helpers
def _ellipse_path(cx: float, cy: float, rx: float, ry: float) -> QPainterPath:
    path = QPainterPath()
    path.addEllipse(QRectF(cx - rx, cy - ry, rx * 2, ry * 2))
    return path


def _paint(
    p: QPainter,
    path: QPainterPath,
    fill: QColor | None,
    stroke: QColor | None = None,
    width: float = 3.0,
) -> None:
    p.setBrush(QBrush(fill) if fill is not None else QBrush(Qt.BrushStyle.NoBrush))
    if stroke is None:
        p.setPen(QPen(Qt.PenStyle.NoPen))
    else:
        pen = QPen(stroke, width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
    p.drawPath(path)


def _arc(
    p: QPainter,
    cx: float,
    cy: float,
    rx: float,
    ry: float,
    start: float,
    sweep: float,
    color: QColor,
    width: float,
) -> None:
    pen = QPen(color, width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.setBrush(QBrush(Qt.BrushStyle.NoBrush))
    rect = QRectF(cx - rx, cy - ry, rx * 2, ry * 2)
    p.drawArc(rect, int(start * 16), int(sweep * 16))


def draw_shadow(
    p: QPainter,
    cx: float,
    feet_y: float,
    height: float,
    alpha: int = 70,
    spread: float = 1.0,
) -> None:
    """Soft ground ellipse, drawn before the character."""
    s = height / CHAR_HEIGHT
    p.setPen(QPen(Qt.PenStyle.NoPen))
    p.setBrush(QBrush(QColor(30, 20, 10, max(0, min(255, alpha)))))
    p.drawEllipse(
        QRectF(cx - 62 * s * spread, feet_y - 8 * s, 124 * s * spread, 18 * s)
    )


# ------------------------------------------------------------------ character
def draw_buddy(
    p: QPainter, cx: float, feet_y: float, height: float, a: Anim
) -> None:
    p.save()
    p.translate(cx, feet_y)
    s = height / CHAR_HEIGHT
    mirror = 1.0 if a.facing >= 0 else -1.0
    p.scale(s * a.sx * mirror, s * a.sy)
    if a.rotation:
        p.rotate(a.rotation)

    phase = a.walk_phase
    if a.walking:
        bob = -abs(math.sin(phase)) * 4.5
    else:
        bob = math.sin(a.t * 2.0) * 1.2  # breathing
    ear_wiggle = math.sin(phase - 0.5) * 5.0 if a.walking else 0.0

    # ---- ears (behind the body)
    for side in (-1.0, 1.0):
        p.save()
        p.translate(side * 58.0, -172.0 + bob * 0.4)
        p.rotate(ear_wiggle * side)
        _paint(p, _ellipse_path(0, 0, 30, 27), FUR, FUR_DARK, 3.2)
        _paint(p, _ellipse_path(0, 1, 15, 13), INNER_EAR, None)
        p.restore()

    # ---- feet (anchored to the ground)
    lifts = (
        (math.sin(phase), math.sin(phase + math.pi)) if a.walking else (0.0, 0.0)
    )
    for side, lift in ((-1.0, lifts[0]), (1.0, lifts[1])):
        p.save()
        p.translate(side * 40.0, -13.0 - max(0.0, lift) * 11.0)
        _paint(p, _ellipse_path(0, 0, 31, 19), FUR, FUR_DARK, 3.2)
        _paint(p, _ellipse_path(0, 4, 17, 9), CREAM, None)
        p.restore()

    # ---- body group (bobs while walking)
    p.save()
    p.translate(0.0, bob)

    # ---- arms
    swing = math.sin(phase) * 24.0 if a.walking else math.sin(a.t * 2.3) * 4.0
    for side in (-1.0, 1.0):
        angle = side * swing - side * a.arm_lift * 80.0
        p.save()
        p.translate(side * 74.0, -118.0)
        p.rotate(angle)
        _paint(p, _ellipse_path(0, 8, 19, 28), FUR, FUR_DARK, 3.2)
        _paint(p, _ellipse_path(0, 33, 12, 10), FUR, FUR_DARK, 2.6)
        p.restore()

    # ---- body + belly
    _paint(p, _ellipse_path(0, -100, 85, 100), FUR, FUR_DARK, 3.6)
    _paint(p, _ellipse_path(0, -70, 54, 50), CREAM, None)

    # ---- face
    eye_y = -142.0
    for side in (-1.0, 1.0):
        ex = side * 34.0
        if a.mood == "sleep":
            _arc(p, ex, eye_y + 4, 11, 8, 0, 180, EYE, 3.6)
        elif a.blink > 0.0 and a.mood not in ("happy", "startled"):
            _arc(p, ex, eye_y, 11, 6, 190, 160, EYE, 3.6)
        elif a.mood == "happy":
            _arc(p, ex, eye_y + 3, 12, 10, 180, 180, EYE, 4.2)
        elif a.mood == "startled":
            _paint(p, _ellipse_path(ex, eye_y, 14, 15), QColor("#FFFFFF"), EYE, 2.4)
            _paint(p, _ellipse_path(ex, eye_y + 2, 7, 8), EYE, None)
            _paint(p, _ellipse_path(ex - 3, eye_y - 2, 2.6, 2.6), QColor("#FFFFFF"), None)
        else:
            _paint(p, _ellipse_path(ex, eye_y, 11, 12.5), EYE, None)
            _paint(p, _ellipse_path(ex - 3.5, eye_y - 4, 3.4, 3.4), QColor("#FFFFFF"), None)
            _paint(p, _ellipse_path(ex + 4, eye_y + 5, 1.6, 1.6), QColor("#FFFFFF"), None)

        if a.mood == "sad":
            p.setPen(QPen(FUR_DARK, 3.2))
            p.setBrush(QBrush(Qt.BrushStyle.NoBrush))
            p.drawLine(QPointF(side * 22, eye_y - 22), QPointF(side * 46, eye_y - 14))

    # ---- blush
    blush_alpha = 150 if a.mood != "sleep" else 90
    for side in (-1.0, 1.0):
        color = QColor(BLUSH)
        color.setAlpha(blush_alpha)
        _paint(p, _ellipse_path(side * 62, -114, 16, 9), color, None)

    # ---- muzzle + nose + mouth
    _paint(p, _ellipse_path(0, -94, 42, 30), CREAM, None)
    if a.eating:
        cookie_r = 19.0 * (1.0 - min(1.0, a.eat_progress) * 0.92)
        if cookie_r > 3.0:
            _paint(p, _ellipse_path(30, -74, cookie_r, cookie_r), COOKIE, COOKIE_EDGE, 2.6)
            for ox, oy in ((-0.35, -0.2), (0.25, -0.35), (0.1, 0.3)):
                _paint(
                    p,
                    _ellipse_path(30 + ox * cookie_r, -74 + oy * cookie_r, 2.6, 2.6),
                    DARK,
                    None,
                )
    _paint(p, _ellipse_path(0, -104, 12, 9), NOSE, None)
    p.setPen(QPen(NOSE, 2.4))
    p.setBrush(QBrush(Qt.BrushStyle.NoBrush))
    p.drawLine(QPointF(0, -96), QPointF(0, -90))

    if a.mouth_open > 0.06:
        open_h = 4.0 + 13.0 * min(1.0, a.mouth_open)
        _paint(p, _ellipse_path(0, -84, 9, open_h), DARK, None)
        if open_h > 8:
            _paint(p, _ellipse_path(0, -84 + open_h * 0.45, 6, open_h * 0.3), TONGUE, None)
    elif a.mood == "sad":
        _arc(p, 0, -80, 14, 12, 200, 140, DARK, 3.2)
    else:
        _arc(p, -7, -90, 7, 7, 0, 180, DARK, 3.0)
        _arc(p, 7, -90, 7, 7, 0, 180, DARK, 3.0)

    p.restore()  # body group
    p.restore()  # whole character
