"""Settings and About dialogs."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QMessageBox,
    QSlider,
    QVBoxLayout,
)

from . import APP_NAME, REPO_URL, __version__
from .config import Config, set_auto_start


class SettingsDialog(QDialog):
    def __init__(self, config: Config, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} — Settings")
        self.setModal(True)
        self.config = config

        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        self.scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.scale_slider.setRange(60, 140)
        self.scale_slider.setValue(int(config.scale * 100))
        self.scale_label = QLabel(f"{self.scale_slider.value()}%")
        self.scale_slider.valueChanged.connect(
            lambda value: self.scale_label.setText(f"{value}%")
        )
        row = QFormLayout()
        row.addRow(self.scale_slider, self.scale_label)
        form.addRow("Bubu size", row)

        self.speed_box = QComboBox()
        self.speed_box.addItems(["slow", "normal", "fast"])
        self.speed_box.setCurrentText(config.speed)
        form.addRow("Walk speed", self.speed_box)

        self.bubbles_box = QCheckBox("Show speech bubbles")
        self.bubbles_box.setChecked(config.bubbles)
        form.addRow("", self.bubbles_box)

        self.needs_box = QCheckBox("Needs: hunger & mood (Bubu asks for snacks)")
        self.needs_box.setChecked(config.needs_enabled)
        form.addRow("", self.needs_box)

        self.top_box = QCheckBox("Always on top of other windows")
        self.top_box.setChecked(config.always_on_top)
        form.addRow("", self.top_box)

        self.autostart_box = QCheckBox("Start automatically when I log in")
        self.autostart_box.setChecked(config.auto_start)
        form.addRow("", self.autostart_box)

        note = QLabel("Changes are applied when you press OK.")
        note.setStyleSheet("color: #808080;")
        layout.addWidget(note)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def apply_to(self, config: Config) -> None:
        config.scale = self.scale_slider.value() / 100.0
        config.speed = self.speed_box.currentText()
        config.bubbles = self.bubbles_box.isChecked()
        config.needs_enabled = self.needs_box.isChecked()
        config.always_on_top = self.top_box.isChecked()
        autostart = self.autostart_box.isChecked()
        config.auto_start = autostart
        set_auto_start(autostart)


def show_about(parent=None) -> None:
    QMessageBox.about(
        parent,
        f"About {APP_NAME}",
        f"<b>{APP_NAME} {__version__}</b><br><br>"
        "A tiny open-source desktop companion, drawn entirely in code.<br>"
        "Bubu is free software under the MIT license.<br><br>"
        f"<a href='{REPO_URL}'>{REPO_URL}</a>",
    )
