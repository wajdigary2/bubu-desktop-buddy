"""The buddy's tiny brain: a state machine deciding what to do next."""

from __future__ import annotations

import enum
import random
from dataclasses import dataclass


class State(enum.Enum):
    IDLE = "idle"
    WALK = "walk"
    SLEEP = "sleep"
    EAT = "eat"
    PET = "pet"
    DANCE = "dance"
    HELD = "held"
    FALL = "fall"


EAT_TIME = 2.4
PET_TIME = 1.5
DANCE_TIME = 3.2


@dataclass
class Brain:
    state: State = State.IDLE
    state_time: float = 0.0
    idle_for: float = 2.5
    target_x: float = 0.0
    facing: int = 1
    speed: float = 70.0
    napping: bool = False

    def _set(self, state: State) -> None:
        self.state = state
        self.state_time = 0.0

    # ------------------------------------------------------------------ API
    def start_walk(self, target_x: float) -> None:
        self._set(State.WALK)
        self.target_x = target_x

    def arrive(self) -> list[str]:
        self._set(State.IDLE)
        self.idle_for = random.uniform(2.5, 8.0)
        return ["arrive"]

    def hold(self) -> None:
        self._set(State.HELD)

    def release(self) -> None:
        self._set(State.IDLE)
        self.idle_for = random.uniform(1.0, 2.5)

    def fall(self) -> None:
        self._set(State.FALL)

    def land(self) -> list[str]:
        self._set(State.IDLE)
        self.idle_for = random.uniform(1.5, 4.0)
        return ["land"]

    def eat(self) -> None:
        self._set(State.EAT)

    def react_pet(self) -> None:
        self._set(State.PET)

    def dance(self) -> None:
        self._set(State.DANCE)

    def sleep(self, napping: bool = True) -> None:
        self._set(State.SLEEP)
        self.napping = napping

    def wake(self) -> None:
        self.napping = False
        self._set(State.IDLE)
        self.idle_for = random.uniform(1.0, 3.0)

    # ------------------------------------------------------------ decision
    def think(self, needs, dt: float, bounds: tuple[float, float]) -> list[str]:
        """Advance timers and pick new behaviour. Returns world events to react to."""
        self.state_time += dt
        events: list[str] = []
        state = self.state

        if state == State.IDLE:
            if self.state_time >= self.idle_for:
                events += self._pick_action(needs, bounds)
        elif state == State.WALK and self.state_time > 60.0:
            # Safety net: never get stuck walking forever.
            self.arrive()
        elif state == State.EAT and self.state_time >= EAT_TIME:
            self._set(State.IDLE)
            self.idle_for = random.uniform(2.0, 5.0)
        elif state == State.PET and self.state_time >= PET_TIME:
            self._set(State.IDLE)
            self.idle_for = random.uniform(1.5, 4.0)
        elif state == State.DANCE and self.state_time >= DANCE_TIME:
            self._set(State.IDLE)
            self.idle_for = random.uniform(2.0, 5.0)
        elif state == State.SLEEP:
            if needs.starving:
                # Even a nap cannot outrun hunger.
                self.wake()
                events += ["wake", "hungry"]
            elif self.napping and self.state_time > 45.0:
                self.wake()
                events.append("wake")
        return events

    def _pick_action(self, needs, bounds: tuple[float, float]) -> list[str]:
        low, high = bounds
        if high - low < 40:
            high = low = (low + high) / 2
        roll = random.random()

        if needs.hungry and roll < 0.4:
            self._set(State.IDLE)
            self.idle_for = random.uniform(3.0, 6.0)
            return ["hungry"]
        if roll < 0.55:
            self.start_walk(random.uniform(low, high))
            return []
        if roll < 0.72:
            self._set(State.DANCE)
            return []
        if roll < 0.86:
            self._set(State.IDLE)
            self.idle_for = random.uniform(3.0, 8.0)
            return ["chatter"]
        self._set(State.SLEEP)
        self.napping = True
        return ["yawn"]
