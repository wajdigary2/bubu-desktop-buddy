"""The buddy window: a frameless, translucent companion that lives on your desktop.

Bubu is drawn inside a small transparent window that follows him around, so he
never blocks clicks on your other apps. He walks along the top of the taskbar,
falls back down when you drop him, and can be petted, fed, danced, slept and
of course dragged anywhere.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from PySide6.QtCore import (
    QElapsedTimer,
    QPoint,
    QPointF,
    QRectF,
    Qt,
    QTimer,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QContextMenuEvent,
    QCursor,
    QFont,
    QFontMetricsF,
    QGuiApplication,
    QIcon,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
)
from PySide6.QtWidgets import QWidget

from . import APP_NAME, character, lines
from .brain import EAT_TIME, Brain, State
from .config import Config, resource_path
from .character import Anim
from .stats import Needs

BASE_W, BASE_H = 360, 400  # window size at scale 1.0
FOOT_PAD = 26  # window pixels kept below the feet (shadow room)
CHAR_H = character.CHAR_HEIGHT  # character height at scale 1.0, see character.py
TICK_MS = 16  # ~60 fps
GRAVITY = 2400.0  # px/s^2 while falling
JUMP_VELOCITY = -720.0
MAX_DT = 0.1


def _pick(pool: list[str]) -> str:
    return random.choice(pool)


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    kind: str
    gravity: float = 0.0
    size: float = 1.0


@dataclass
class Bubble:
    text: str
    ttl: float
    age: float = 0.0


class BuddyWindow(QWidget):
    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config = config
        self.needs = Needs(enabled=config.needs_enabled)
        self.brain = Brain(speed=70.0 * config.speed_multiplier())

        self.x = 0.0  # feet x, screen coordinates
        self.feet_y = 0.0  # feet y, screen coordinates
        self.vy = 0.0
        self.grounded = True
        self.walk_phase = 0.0
        self.time = 0.0

        self.blink = 0.0
        self.blink_timer = random.uniform(1.5, 4.0)
        self.land_t = 0.0
        self.mouth = 0.0
        self.crumb_timer = 0.0
        self.z_timer = 0.0

        self.bubble: Bubble | None = None
        self.particles: list[Particle] = []

        self._press_global: QPoint | None = None
        self._press_offset = QPointF()
        self._dragging = False
        self._said_while_held = False
        self._last_tick = 0.0

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowTitle(APP_NAME)
        icon = QIcon(str(resource_path("assets/icon.png")))
        if not icon.isNull():
            self.setWindowIcon(icon)

        self.resize(int(BASE_W * config.scale), int(BASE_H * config.scale))
        self._place_initial()

        self._clock = QElapsedTimer()
        self._clock.start()
        self._timer = QTimer(self)
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    # ------------------------------------------------------------ placement
    def _screen(self):
        screen = QGuiApplication.screenAt(QPoint(int(self.x), int(self.feet_y)))
        return screen or QGuiApplication.primaryScreen()

    def _floor_y(self) -> float:
        return float(self._screen().availableGeometry().bottom()) - 6.0

    def _place_initial(self) -> None:
        geo = QGuiApplication.primaryScreen().availableGeometry()
        if self.config.x is not None:
            self.x = float(self.config.x)
        else:
            self.x = geo.center().x()
        self.feet_y = self._floor_y()
        self._clamp_x()
        self._sync_geometry()

    def _clamp_x(self) -> None:
        geo = self._screen().availableGeometry()
        half = self.width() / 2
        if geo.width() > self.width():
            self.x = min(max(self.x, geo.left() + half), geo.right() - half + 1)

    def _sync_geometry(self) -> None:
        top = self.feet_y + FOOT_PAD - self.height()
        self.setGeometry(
            int(round(self.x - self.width() / 2)), int(round(top)),
            self.width(), self.height(),
        )

    def _char_px(self) -> float:
        return self.height() * (CHAR_H / BASE_H)

    # ------------------------------------------------------------ main loop
    def _tick(self) -> None:
        now = self._clock.elapsed()
        dt = min(MAX_DT, (now - self._last_tick) / 1000.0)
        self._last_tick = now
        if dt <= 0:
            return
        self.time += dt

        sleeping = self.brain.state == State.SLEEP
        self.needs.tick(dt, sleeping=sleeping)

        low, high = self._walk_bounds()
        for event in self.brain.think(self.needs, dt, (low, high)):
            self._handle_event(event)

        state = self.brain.state
        if state == State.WALK and self.grounded:
            self._walk(dt)
        if not self.grounded:
            self._apply_gravity(dt)

        self._animate(dt)
        self._update_particles(dt)
        self._clamp_x()
        self._sync_geometry()
        self.update()

    def _walk_bounds(self) -> tuple[float, float]:
        geo = self._screen().availableGeometry()
        margin = self.width() / 2 + 20
        if geo.width() <= self.width() * 1.2:
            center = geo.center().x()
            return center, center
        return geo.left() + margin, geo.right() - margin

    def _walk(self, dt: float) -> None:
        target = self.brain.target_x
        delta = target - self.x
        step = self.brain.speed * dt
        if abs(delta) <= step:
            self.x = target
            for event in self.brain.arrive():
                self._handle_event(event)
            if random.random() < 0.35:
                self.brain.facing *= -1
            return
        direction = 1 if delta > 0 else -1
        self.brain.facing = direction
        self.x += direction * step
        self.walk_phase += dt * self.brain.speed * 0.075

    def _apply_gravity(self, dt: float) -> None:
        self.vy += GRAVITY * dt
        self.feet_y += self.vy * dt
        floor = self._floor_y()
        if self.feet_y >= floor:
            self.feet_y = floor
            self.grounded = True
            impact = min(1.0, self.vy / 900.0)
            self.vy = 0.0
            self.land_t = 0.16 * (0.6 + impact)
            self._spawn_dust(impact)
            if self.brain.state == State.FALL:
                events = self.brain.land()
                for event in events:
                    self._handle_event(event)
                if impact > 0.45 and random.random() < 0.5:
                    self.say(_pick(lines.LAND), ttl=1.8)

    def _animate(self, dt: float) -> None:
        # Blinking
        if self.blink > 0.0:
            self.blink = max(0.0, self.blink - dt)
        else:
            self.blink_timer -= dt
            if self.blink_timer <= 0.0:
                self.blink = 0.15
                self.blink_timer = random.uniform(2.2, 6.0)
        # Landing squash decay
        if self.land_t > 0.0:
            self.land_t = max(0.0, self.land_t - dt)

        state = self.brain.state
        # Eating: chewing mouth + flying crumbs
        if state == State.EAT:
            progress = min(1.0, self.brain.state_time / EAT_TIME)
            self.mouth = (math.sin(self.brain.state_time * 14.0) * 0.5 + 0.5) * (
                1.0 - progress * 0.8
            )
            self.crumb_timer -= dt
            if self.crumb_timer <= 0.0 and progress < 0.85:
                self.crumb_timer = 0.22
                self._spawn_crumb()
        elif self.bubble is not None and state in (State.IDLE, State.WALK):
            # Cute chatter animation while talking.
            self.mouth = 0.2 + 0.25 * abs(math.sin(self.time * 18.0))
        else:
            self.mouth = max(0.0, self.mouth - dt * 6.0)

        # Sleeping zzz
        if state == State.SLEEP:
            self.z_timer -= dt
            if self.z_timer <= 0.0:
                self.z_timer = 1.4
                self._spawn("z")

        # Speech bubble lifetime
        if self.bubble is not None:
            self.bubble.age += dt
            if self.bubble.age >= self.bubble.ttl:
                self.bubble = None

    def _handle_event(self, event: str) -> None:
        if event == "chatter":
            if random.random() < 0.6:
                self.say(_pick(lines.IDLE))
        elif event == "arrive":
            if random.random() < 0.35:
                self.say(_pick(lines.ARRIVE), ttl=2.2)
        elif event == "hungry":
            self.say(_pick(lines.HUNGRY))
        elif event == "yawn":
            self.say(_pick(lines.SLEEP))
        elif event == "wake":
            self.say(_pick(lines.WAKE))
        elif event == "land":
            pass  # handled by physics (impact decides)

    # ----------------------------------------------------------- interaction
    def greet(self) -> None:
        self.say(_pick(lines.GREET))

    def say(self, text: str, ttl: float | None = None) -> None:
        if not self.config.bubbles or not text:
            return
        if ttl is None:
            ttl = 3.0 + min(2.0, len(text) * 0.035)
        self.bubble = Bubble(text=text, ttl=ttl)

    def pet(self) -> None:
        if self.brain.state == State.SLEEP:
            self.wake()
            return
        self.needs.pet()
        self.brain.react_pet()
        self.say(_pick(lines.PET))
        self._spawn_hearts(random.randint(2, 3))

    def feed(self) -> None:
        if self.brain.state == State.SLEEP:
            self.wake()
        self.needs.feed()
        self.brain.eat()
        self.say(_pick(lines.FEED))

    def dance(self) -> None:
        if self.brain.state == State.SLEEP:
            self.wake()
        self.brain.dance()
        self.say(_pick(lines.DANCE), ttl=2.2)

    def toggle_sleep(self) -> None:
        if self.brain.state == State.SLEEP:
            self.wake()
        else:
            self.brain.sleep(napping=True)
            self.say(_pick(lines.SLEEP))

    def wake(self) -> None:
        self.brain.wake()
        self.say(_pick(lines.WAKE))

    def show_settings(self) -> None:
        from .dialog import SettingsDialog

        dialog = SettingsDialog(self.config, self)
        if dialog.exec():
            dialog.apply_to(self.config)
            self.config.save()
            self.apply_settings()

    def show_about(self) -> None:
        from .dialog import show_about

        show_about(self)

    def jump(self) -> None:
        if self.brain.state == State.SLEEP:
            self.wake()
        if not self.grounded:
            return
        self.vy = JUMP_VELOCITY
        self.grounded = False
        if self.brain.state not in (State.HELD, State.FALL):
            self.brain.release()

    # ------------------------------------------------------------- dragging
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_global = event.globalPosition().toPoint()
            self._press_offset = event.position()
            self._dragging = False
            self._said_while_held = False
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._press_global is not None and (
            event.buttons() & Qt.MouseButton.LeftButton
        ):
            global_pos = event.globalPosition().toPoint()
            if not self._dragging:
                if (global_pos - self._press_global).manhattanLength() > 6:
                    self._dragging = True
                    self.brain.hold()
                    self.grounded = True
                    self.vy = 0.0
                    if not self._said_while_held:
                        self._said_while_held = True
                        self.say(_pick(lines.HELD))
            if self._dragging:
                top_left = global_pos - QPoint(
                    int(self._press_offset.x()), int(self._press_offset.y())
                )
                self._drag_to(top_left)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def _drag_to(self, top_left: QPoint) -> None:
        virtual = QGuiApplication.primaryScreen().virtualGeometry()
        half = self.width() / 2
        cx = min(
            max(top_left.x() + half, virtual.left() + half),
            virtual.right() - half,
        )
        cy = min(
            max(top_left.y() + self.height() - FOOT_PAD, virtual.top() + CHAR_H),
            virtual.bottom(),
        )
        self.setGeometry(
            int(round(cx - half)), int(round(cy - self.height() + FOOT_PAD)),
            self.width(), self.height(),
        )
        self.x = float(cx)
        self.feet_y = float(cy)
        self.brain.facing = 1 if QCursor.pos().x() >= self.x else -1

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self._press_global is not None
        ):
            if self._dragging:
                self._drop()
            else:
                self.pet()
            self._press_global = None
            self._dragging = False
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.jump()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def _drop(self) -> None:
        floor = self._floor_y()
        self.brain.release()
        if self.feet_y < floor - 2.0:
            self.grounded = False
            self.vy = 0.0
            self.brain.fall()
            if self.feet_y < floor - 60.0:
                self.say(_pick(lines.DROP), ttl=2.0)
        else:
            self.feet_y = floor
            self.grounded = True
            self.land_t = 0.12

    def contextMenuEvent(  # type: ignore[override]
        self, event: QContextMenuEvent
    ) -> None:
        from .menu import build_menu

        menu = build_menu(self)
        menu.exec(event.globalPos())
        event.accept()

    # --------------------------------------------------------------- config
    def apply_settings(self) -> None:
        self.resize(int(BASE_W * self.config.scale), int(BASE_H * self.config.scale))
        self.needs.enabled = self.config.needs_enabled
        if not self.config.needs_enabled:
            self.needs.hunger = 100.0
            self.needs.mood = 100.0
        self.brain.speed = 70.0 * self.config.speed_multiplier()
        self.setWindowFlag(
            Qt.WindowType.WindowStaysOnTopHint, self.config.always_on_top
        )
        self.show()  # setWindowFlag() hides the window again
        self.feet_y = min(self.feet_y, self._floor_y())
        self._clamp_x()
        self._sync_geometry()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self.config.x = self.x
        self.config.save()
        super().closeEvent(event)

    # ------------------------------------------------------------ particles
    def _head_pos(self) -> tuple[float, float]:
        return self.width() / 2.0, self.height() - FOOT_PAD - self._char_px()

    def _spawn(self, kind: str, **kwargs: float) -> None:
        w, h = self.width(), self.height()
        cx = w / 2.0
        feet = h - FOOT_PAD
        defaults: dict[str, tuple[float, float, float]] = {
            # kind: (x, y, gravity)
            "heart": (cx + random.uniform(-40, 40), feet - self._char_px() - 6, -30),
            "z": (cx + random.uniform(10, 45), feet - self._char_px() + 20, -35),
            "crumb": (cx + self.brain.facing * 28, feet - self._char_px() * 0.42, 500),
            "dust": (cx, feet, 0),
        }
        x, y, gravity = defaults.get(kind, (cx, feet, 0.0))
        self.particles.append(
            Particle(
                x=kwargs.get("x", x),
                y=kwargs.get("y", y),
                vx=kwargs.get("vx", random.uniform(-25, 25)),
                vy=kwargs.get("vy", random.uniform(-90, -40)),
                life=kwargs.get("life", 1.0),
                max_life=kwargs.get("life", 1.0),
                kind=kind,
                gravity=gravity,
                size=kwargs.get("size", 1.0),
            )
        )

    def _spawn_hearts(self, count: int) -> None:
        for _ in range(count):
            self._spawn("heart", life=random.uniform(0.9, 1.4))

    def _spawn_crumb(self) -> None:
        self._spawn(
            "crumb",
            vx=self.brain.facing * random.uniform(20, 70),
            vy=random.uniform(-160, -60),
            life=random.uniform(0.6, 1.0),
        )

    def _spawn_dust(self, impact: float) -> None:
        for _ in range(int(3 + impact * 4)):
            self._spawn(
                "dust",
                x=self.width() / 2.0 + random.uniform(-45, 45),
                vx=random.uniform(-70, 70),
                vy=random.uniform(-60, -10),
                life=random.uniform(0.35, 0.6),
                size=random.uniform(0.6, 1.2),
            )

    def _update_particles(self, dt: float) -> None:
        alive: list[Particle] = []
        for part in self.particles:
            part.life -= dt
            if part.life <= 0:
                continue
            part.vy += part.gravity * dt
            part.x += part.vx * dt
            part.y += part.vy * dt
            alive.append(part)
        self.particles = alive

    # ------------------------------------------------------------- painting
    def _anim(self) -> Anim:
        state = self.brain.state
        a = Anim()
        a.facing = self.brain.facing
        a.t = self.time
        a.walk_phase = self.walk_phase
        a.walking = state == State.WALK and self.grounded
        a.blink = self.blink
        a.mouth_open = self.mouth

        if state == State.SLEEP:
            a.mood = "sleep"
        elif state in (State.PET, State.DANCE):
            a.mood = "happy"
        elif state == State.HELD:
            a.mood = "startled"
        elif self.needs.hungry:
            a.mood = "sad"

        if state == State.PET:
            a.rotation = math.sin(self.time * 18.0) * 6.0
            a.arm_lift = 0.55
        elif state == State.DANCE:
            a.rotation = math.sin(self.time * 9.0) * 10.0
            a.arm_lift = 0.5 + 0.3 * math.sin(self.time * 10.0)
            a.sy = 1.0 + 0.03 * math.sin(self.time * 16.0)
        elif state == State.HELD:
            a.sy, a.sx = 1.06, 0.94

        if self.grounded and self.vy == 0.0 and not a.walking:
            pass
        elif self.vy < -60.0:  # rising: stretch up, arms up
            a.sy, a.sx = a.sy * 1.08, a.sx * 0.93
            a.arm_lift = max(a.arm_lift, 0.95)
        elif self.vy > 60.0:  # falling: stretch down, arms up
            a.sy, a.sx = a.sy * 1.05, a.sx * 0.95
            a.arm_lift = max(a.arm_lift, 0.9)

        if self.land_t > 0.0:
            k = min(1.0, self.land_t / 0.16)
            a.sy *= 1.0 - 0.2 * k
            a.sx *= 1.0 + 0.18 * k

        if state == State.EAT:
            a.eating = True
            a.eat_progress = self.brain.state_time / EAT_TIME
        return a

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing
        )
        w, h = self.width(), self.height()
        feet_local = h - FOOT_PAD
        char_h = self._char_px()

        airborne = max(0.0, min(1.0, (self._floor_y() - self.feet_y) / 260.0))
        character.draw_shadow(
            p,
            w / 2.0,
            feet_local,
            char_h,
            alpha=int(70 - 50 * airborne),
            spread=1.0 - 0.25 * airborne,
        )
        character.draw_buddy(p, w / 2.0, feet_local, char_h, self._anim())

        for part in self.particles:
            self._draw_particle(p, part)

        if self.bubble is not None:
            self._draw_bubble(p, w, h, feet_local, char_h)
        p.end()

    def _draw_particle(self, p: QPainter, part: Particle) -> None:
        fade = max(0.0, min(1.0, part.life / part.max_life))
        if part.kind == "heart":
            color = QColor("#F06E86")
            color.setAlphaF(fade)
            p.setPen(QPen(Qt.PenStyle.NoPen))
            p.setBrush(QBrush(color))
            p.save()
            p.translate(part.x, part.y)
            size = 15.0 * part.size * (1.6 - 0.6 * fade)
            p.scale(size, size)
            p.drawEllipse(QRectF(-0.52, -0.45, 0.55, 0.55))
            p.drawEllipse(QRectF(-0.03, -0.45, 0.55, 0.55))
            p.drawPolygon(
                QPolygonF([QPointF(-0.5, -0.08), QPointF(0.5, -0.08), QPointF(0.0, 0.5)])
            )
            p.restore()
        elif part.kind == "z":
            color = QColor("#7C8FC7")
            color.setAlphaF(fade)
            p.setPen(color)
            font = QFont(self.font().family(), max(9, int(11 * part.size)))
            font.setBold(True)
            p.setFont(font)
            p.drawText(QRectF(part.x - 12, part.y - 12, 24, 24), Qt.AlignmentFlag.AlignCenter, "z")
        elif part.kind == "crumb":
            color = QColor("#C98A4B")
            color.setAlphaF(fade)
            p.setPen(QPen(Qt.PenStyle.NoPen))
            p.setBrush(QBrush(color))
            p.drawEllipse(QRectF(part.x - 4, part.y - 4, 8, 8))
        elif part.kind == "dust":
            color = QColor("#8A7B6B")
            color.setAlphaF(fade * 0.6)
            p.setPen(QPen(Qt.PenStyle.NoPen))
            p.setBrush(QBrush(color))
            r = 6.0 * part.size
            p.drawEllipse(QRectF(part.x - r, part.y - r * 0.6, r * 2, r * 1.2))

    def _draw_bubble(
        self, p: QPainter, w: int, h: int, feet_local: float, char_h: float
    ) -> None:
        bubble = self.bubble
        assert bubble is not None
        size = max(9, int(12 * self.config.scale))
        font = QFont(self.font().family(), size)
        p.setFont(font)
        fm = QFontMetricsF(font)

        max_text_w = w - 44
        words = bubble.text.split(" ")
        wrapped: list[str] = []
        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if fm.horizontalAdvance(candidate) <= max_text_w:
                current = candidate
            else:
                if current:
                    wrapped.append(current)
                current = word
        if current:
            wrapped.append(current)

        line_h = fm.height() + 2
        text_w = max(fm.horizontalAdvance(line) for line in wrapped)
        bw = min(float(w - 16), text_w + 26.0)
        bh = line_h * len(wrapped) + 20.0
        head_top = feet_local - char_h
        bx = (w - bw) / 2.0
        by = max(8.0, head_top - bh - 14.0)
        tail = 12.0

        remaining = bubble.ttl - bubble.age
        opacity = min(1.0, bubble.age / 0.15, max(0.0, remaining) / 0.35)
        p.setOpacity(opacity)

        path = QPainterPath()
        path.addRoundedRect(QRectF(bx, by, bw, bh), 12.0, 12.0)
        path.moveTo(w / 2.0 - 9.0, by + bh - 1.0)
        path.lineTo(w / 2.0, by + bh + tail)
        path.lineTo(w / 2.0 + 9.0, by + bh - 1.0)
        p.setBrush(QBrush(QColor(255, 255, 255, 240)))
        pen = QPen(QColor("#4A3423"), 2.4)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.drawPath(path)

        p.setPen(QPen(QColor("#33241A")))
        for i, line in enumerate(wrapped):
            p.drawText(
                QRectF(bx, by + 9.0 + i * line_h, bw, line_h),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                line,
            )
        p.setOpacity(1.0)
