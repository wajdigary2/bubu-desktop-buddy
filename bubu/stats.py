"""Bubu's needs: hunger and mood. They drift over time so you get reasons to interact."""

from __future__ import annotations

from dataclasses import dataclass

# Full -> empty over roughly these periods (seconds).
_HUNGER_SECONDS = 25 * 60
_MOOD_SECONDS = 60 * 60

HUNGER_DECAY = 100.0 / _HUNGER_SECONDS
MOOD_DECAY = 100.0 / _MOOD_SECONDS


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


@dataclass
class Needs:
    hunger: float = 85.0
    mood: float = 90.0
    enabled: bool = True

    def tick(self, dt: float, sleeping: bool = False) -> None:
        if not self.enabled:
            # Relaxed mode: needs slowly top back up instead of decaying.
            self.hunger = _clamp(self.hunger + 4.0 * dt)
            self.mood = _clamp(self.mood + 4.0 * dt)
            return
        factor = 0.35 if sleeping else 1.0
        self.hunger = _clamp(self.hunger - HUNGER_DECAY * factor * dt)
        self.mood = _clamp(self.mood - MOOD_DECAY * factor * dt)

    def feed(self, amount: float = 30.0) -> None:
        self.hunger = _clamp(self.hunger + amount)
        self.mood = _clamp(self.mood + amount * 0.25)

    def pet(self, amount: float = 12.0) -> None:
        self.mood = _clamp(self.mood + amount)

    @property
    def hungry(self) -> bool:
        return self.enabled and self.hunger < 30.0

    @property
    def starving(self) -> bool:
        return self.enabled and self.hunger < 12.0

    @property
    def happy(self) -> bool:
        return self.mood > 65.0 and self.hunger > 45.0
