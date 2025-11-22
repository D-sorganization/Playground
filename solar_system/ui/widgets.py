"""
UI Widgets
==========

Reusable UI components for the simulation overlay.
"""

from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass


@dataclass
class PanelStyle:
    """Styling for UI panels."""
    background_color: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.7)
    text_color: Tuple[int, int, int] = (220, 220, 220)
    title_color: Tuple[int, int, int] = (255, 255, 100)
    border_color: Tuple[float, float, float, float] = (0.3, 0.3, 0.4, 0.5)
    padding: int = 10
    line_height: int = 18
    font_size: int = 12
    title_font_size: int = 14


class InfoPanel:
    """
    Displays information about a selected object.

    Shows details like orbital parameters, physical properties,
    current position, etc.
    """

    def __init__(
        self,
        position: Tuple[int, int] = (20, 20),
        width: int = 300,
        style: PanelStyle = None
    ):
        """
        Initialize the info panel.

        Args:
            position: Top-left position (x, y)
            width: Panel width in pixels
            style: Visual styling
        """
        self.position = position
        self.width = width
        self.style = style or PanelStyle()
        self.visible = True
        self._data: Dict[str, Any] = {}
        self._title: str = ""

    def set_data(self, title: str, data: Dict[str, Any]):
        """
        Set the data to display.

        Args:
            title: Panel title
            data: Dictionary of label -> value pairs
        """
        self._title = title
        self._data = data

    def clear(self):
        """Clear the panel data."""
        self._title = ""
        self._data = {}

    def toggle(self):
        """Toggle visibility."""
        self.visible = not self.visible

    def get_render_data(self) -> Dict[str, Any]:
        """
        Get data formatted for rendering.

        Returns:
            Dictionary with render parameters
        """
        return {
            "position": self.position,
            "width": self.width,
            "title": self._title,
            "data": self._data,
            "style": self.style,
            "visible": self.visible
        }


class StatusBar:
    """
    Status bar showing simulation state at bottom of screen.

    Displays time, speed, selected object, FPS, etc.
    """

    def __init__(self, style: PanelStyle = None):
        """Initialize the status bar."""
        self.style = style or PanelStyle()
        self.visible = True
        self._components: List[str] = []

    def set_time(self, time_str: str):
        """Set the time display."""
        self._time = time_str

    def set_speed(self, speed_str: str):
        """Set the time warp display."""
        self._speed = speed_str

    def set_selected(self, name: str):
        """Set the selected object name."""
        self._selected = name

    def set_fps(self, fps: float):
        """Set the FPS display."""
        self._fps = fps

    def set_paused(self, paused: bool):
        """Set paused state."""
        self._paused = paused

    def get_text(self) -> str:
        """Get formatted status bar text."""
        parts = []

        if hasattr(self, '_time'):
            parts.append(self._time)

        if hasattr(self, '_paused') and self._paused:
            parts.append("[PAUSED]")
        elif hasattr(self, '_speed'):
            parts.append(f"[{self._speed}]")

        if hasattr(self, '_selected') and self._selected:
            parts.append(f"Selected: {self._selected}")

        if hasattr(self, '_fps'):
            parts.append(f"FPS: {self._fps:.0f}")

        return "  |  ".join(parts)


class HelpOverlay:
    """
    Overlay showing keyboard controls and help information.
    """

    def __init__(
        self,
        position: Tuple[int, int] = None,
        style: PanelStyle = None
    ):
        """
        Initialize the help overlay.

        Args:
            position: Position or None for auto-placement
            style: Visual styling
        """
        self.position = position
        self.style = style or PanelStyle()
        self.visible = False
        self._controls: List[Tuple[str, str]] = []

    def set_controls(self, controls: List[Tuple[str, str]]):
        """
        Set the control bindings to display.

        Args:
            controls: List of (key, description) tuples
        """
        self._controls = controls

    def toggle(self):
        """Toggle visibility."""
        self.visible = not self.visible

    def get_render_data(self) -> Dict[str, Any]:
        """Get data for rendering."""
        return {
            "position": self.position,
            "controls": self._controls,
            "style": self.style,
            "visible": self.visible
        }


class TransferPlanner:
    """
    UI for planning interplanetary transfers.

    Allows selection of origin, destination, and departure date.
    """

    def __init__(self, style: PanelStyle = None):
        """Initialize the transfer planner."""
        self.style = style or PanelStyle()
        self.visible = False
        self.origin: Optional[str] = None
        self.destination: Optional[str] = None
        self.departure_date: Optional[float] = None
        self._transfer_info: Dict[str, Any] = {}

    def set_origin(self, name: str):
        """Set origin body."""
        self.origin = name

    def set_destination(self, name: str):
        """Set destination body."""
        self.destination = name

    def set_transfer_info(self, info: Dict[str, Any]):
        """Set transfer calculation results."""
        self._transfer_info = info

    def toggle(self):
        """Toggle visibility."""
        self.visible = not self.visible

    def get_render_data(self) -> Dict[str, Any]:
        """Get data for rendering."""
        return {
            "origin": self.origin,
            "destination": self.destination,
            "departure_date": self.departure_date,
            "transfer_info": self._transfer_info,
            "style": self.style,
            "visible": self.visible
        }


class TooltipManager:
    """
    Manages tooltips for celestial bodies on hover.
    """

    def __init__(self, style: PanelStyle = None):
        """Initialize tooltip manager."""
        self.style = style or PanelStyle()
        self._active_tooltip: Optional[Dict[str, Any]] = None
        self._hover_time: float = 0.0
        self._show_delay: float = 0.5  # Seconds before showing

    def set_hover(self, body_name: str, position: Tuple[int, int], info: Dict[str, Any]):
        """
        Set the currently hovered body.

        Args:
            body_name: Name of the body
            position: Screen position
            info: Information to display
        """
        self._active_tooltip = {
            "name": body_name,
            "position": position,
            "info": info
        }

    def clear_hover(self):
        """Clear the current hover."""
        self._active_tooltip = None
        self._hover_time = 0.0

    def update(self, delta_time: float):
        """Update tooltip timing."""
        if self._active_tooltip:
            self._hover_time += delta_time

    def should_show(self) -> bool:
        """Check if tooltip should be displayed."""
        return self._active_tooltip is not None and self._hover_time >= self._show_delay

    def get_render_data(self) -> Optional[Dict[str, Any]]:
        """Get tooltip data for rendering."""
        if self.should_show():
            return self._active_tooltip
        return None
