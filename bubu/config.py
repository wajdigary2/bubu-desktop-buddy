"""Settings + saved state, stored as JSON in a per-user config directory.

On Windows this is ``%APPDATA%\\BubuDesktopBuddy``; on Linux it follows the
XDG spec (``$XDG_CONFIG_HOME/BubuDesktopBuddy``, usually
``~/.config/BubuDesktopBuddy``).
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

APP_ID = "bubu-desktop-buddy"


def _config_home() -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", str(Path.home())))
    return Path(
        os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    )


APP_DIR = _config_home() / "BubuDesktopBuddy"
SETTINGS_FILE = APP_DIR / "settings.json"

_SPEED_MULTIPLIERS = {"slow": 0.6, "normal": 1.0, "fast": 1.6}


@dataclass
class Config:
    scale: float = 1.0
    speed: str = "normal"
    bubbles: bool = True
    always_on_top: bool = True
    needs_enabled: bool = True
    auto_start: bool = False
    x: float | None = None  # last horizontal position (feet x, screen coords)

    @classmethod
    def load(cls) -> "Config":
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls()
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})

    def save(self) -> None:
        try:
            APP_DIR.mkdir(parents=True, exist_ok=True)
            SETTINGS_FILE.write_text(
                json.dumps(asdict(self), indent=2), encoding="utf-8"
            )
        except OSError:
            pass  # A read-only drive should not crash the buddy.

    @staticmethod
    def forget() -> None:
        try:
            SETTINGS_FILE.unlink()
        except OSError:
            pass

    def speed_multiplier(self) -> float:
        return _SPEED_MULTIPLIERS.get(self.speed, 1.0)


def _launch_command() -> str:
    """Command that (re)launches Bubu, for autostart entries."""
    if getattr(sys, "frozen", False):  # PyInstaller build
        return f'"{sys.executable}"'
    return f'"{sys.executable}" -m bubu'


def _set_auto_start_windows(enabled: bool) -> bool:
    try:
        import winreg

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            key_path,
            0,
            winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE,
        ) as key:
            if enabled:
                winreg.SetValueEx(
                    key,
                    "BubuDesktopBuddy",
                    0,
                    winreg.REG_SZ,
                    _launch_command(),
                )
            else:
                try:
                    winreg.DeleteValue(key, "BubuDesktopBuddy")
                except FileNotFoundError:
                    pass
        return True
    except OSError:
        return False


def _set_auto_start_linux(enabled: bool) -> bool:
    autostart_dir = _config_home() / "autostart"
    desktop_file = autostart_dir / f"{APP_ID}.desktop"
    try:
        if enabled:
            autostart_dir.mkdir(parents=True, exist_ok=True)
            desktop_file.write_text(
                "[Desktop Entry]\n"
                "Type=Application\n"
                "Name=Bubu Desktop Buddy\n"
                "Comment=A tiny desktop companion\n"
                f"Exec={_launch_command()}\n"
                f"Icon={APP_ID}\n"
                "Terminal=false\n"
                "X-GNOME-Autostart-enabled=true\n",
                encoding="utf-8",
            )
        else:
            desktop_file.unlink()
        return True
    except OSError:
        return False


def set_auto_start(enabled: bool) -> bool:
    """Add/remove Bubu from the current user's startup programs."""
    if sys.platform == "win32":
        return _set_auto_start_windows(enabled)
    if sys.platform.startswith("linux"):
        return _set_auto_start_linux(enabled)
    return False


def resource_path(relative: str) -> Path:
    """Resolve a bundled asset path (works both from source and PyInstaller)."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / relative
