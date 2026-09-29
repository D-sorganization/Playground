"""Tests for asteroid_jumper.wheel_blocker."""

from __future__ import annotations

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtCore import QEvent, QObject
from PyQt6.QtWidgets import QApplication, QWidget

from asteroid_jumper.wheel_blocker import WheelEventBlocker, suppress_wheel_events


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_wheel_event_blocker_blocks_wheel_event(qapp: QApplication) -> None:
    blocker = WheelEventBlocker()
    widget = QWidget()
    event = QEvent(QEvent.Type.Wheel)
    assert blocker.eventFilter(widget, event) is True
    assert not event.isAccepted()


def test_wheel_event_blocker_allows_other_events(qapp: QApplication) -> None:
    blocker = WheelEventBlocker()
    widget = QWidget()
    event = QEvent(QEvent.Type.Paint)
    # Non-wheel events should not be consumed by the blocker
    assert blocker.eventFilter(widget, event) is False

    obj = QObject()
    assert blocker.eventFilter(obj, event) is False


def test_wheel_event_blocker_handles_none_event_and_obj(qapp: QApplication) -> None:
    blocker = WheelEventBlocker()
    # Event and obj may be None per PyQt6 QObject.eventFilter signature
    assert blocker.eventFilter(None, None) is False


def test_suppress_wheel_events_installs_filter(qapp: QApplication) -> None:
    widget = QWidget()
    suppress_wheel_events(widget)
    # Sending a wheel event to the widget should be filtered
    event = QEvent(QEvent.Type.Wheel)
    result = qapp.notify(widget, event)
    assert result is True
