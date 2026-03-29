"""Input Handling
=================

Extracted mixin providing keyboard and mouse event handling
for the solar system scene.  Keeps ``SolarSystemScene`` focused
on simulation orchestration.
"""

from __future__ import annotations

from calendar import monthrange
from typing import TYPE_CHECKING, Any

try:
    from pygame.locals import (
        K_0,
        K_1,
        K_9,
        K_EQUALS,
        K_ESCAPE,
        K_HOME,
        K_KP_MINUS,
        K_KP_PLUS,
        K_LEFTBRACKET,
        K_MINUS,
        K_PAGEDOWN,
        K_PAGEUP,
        K_PLUS,
        K_RIGHTBRACKET,
        K_SPACE,
        K_c,
        K_d,
        K_e,
        K_f,
        K_g,
        K_h,
        K_i,
        K_l,
        K_m,
        K_n,
        K_o,
        K_PERIOD,
        K_r,
        K_t,
        K_v,
    )

    _PYGAME_AVAILABLE = True
except ImportError:
    _PYGAME_AVAILABLE = False

if TYPE_CHECKING:
    from ..core.celestial_body import CelestialBody
    from ..core.time_manager import TimeManager


class InputHandlerMixin:
    """Mixin providing keyboard input dispatch for the solar system scene.

    The host class must expose at minimum:
    * ``time_manager: TimeManager``
    * ``date_picker``, ``time_nav_panel``, ``historical_events``
    * ``educational_panel``, ``immersion_checklist``
    * ``view_state``, ``renderer``, ``settings``
    * ``selected_body``, ``sun``, ``planets``
    * ``_mark_immersion_task(task_id)``
    * ``_update_ui_date()``, ``_update_educational_panel()``
    * ``_cycle_camera_mode()``, ``_focus_on_selected()``
    * ``select_body(body)``, ``plan_trajectory(src, dst)``
    """

    def _handle_key(self, key: int) -> bool:
        """Handle keyboard input.

        Returns:
            False if should quit, True otherwise.
        """
        from ..core.constants import PLANET_ORDER
        from .camera import CameraMode

        if key == K_ESCAPE:
            return False

        elif key == K_SPACE:
            self.time_manager.toggle_pause()

        elif key in (K_EQUALS, K_PLUS, K_KP_PLUS):
            self.time_manager.increase_time_warp()

        elif key in (K_MINUS, K_KP_MINUS):
            self.time_manager.decrease_time_warp()

        elif key == K_r:
            self.time_manager.reverse_time()

        elif key == K_d:
            if self.date_picker:
                self.date_picker.toggle()
                if self.date_picker.visible:
                    self.date_picker.set_date(self.time_manager.current_time.datetime_utc)
                    self._mark_immersion_task("navigate_time")

        elif key == K_n:
            if self.time_nav_panel:
                self.time_nav_panel.toggle()
                self._mark_immersion_task("navigate_time")

        elif key == K_e:
            if self.historical_events:
                self.historical_events.toggle()
                if self.historical_events.visible:
                    self._mark_immersion_task("historical_events")

        elif key == K_LEFTBRACKET:
            self.time_manager.advance_days(-1)
            self._update_ui_date()
            self._mark_immersion_task("navigate_time")

        elif key == K_RIGHTBRACKET:
            self.time_manager.advance_days(1)
            self._update_ui_date()
            self._mark_immersion_task("navigate_time")

        elif key == K_PAGEUP:
            self._jump_month(-1)

        elif key == K_PAGEDOWN:
            self._jump_month(1)

        elif key == K_HOME:
            self.renderer.camera.reset()
            self.renderer.camera.mode = CameraMode.FREE

        elif key == K_o:
            self.view_state.show_orbits = not self.view_state.show_orbits
            self.renderer.settings.show_orbits = self.view_state.show_orbits
            self._mark_immersion_task("toggle_overlays")

        elif key == K_l:
            self.view_state.show_labels = not self.view_state.show_labels
            self.renderer.settings.show_labels = self.view_state.show_labels
            self._mark_immersion_task("toggle_overlays")

        elif key == K_i:
            self.view_state.show_info_panel = not self.view_state.show_info_panel

        elif key == K_g:
            self.renderer.settings.show_grid = not self.renderer.settings.show_grid
            self._mark_immersion_task("toggle_overlays")

        elif key == K_h:
            self.view_state.show_help = not self.view_state.show_help

        elif key == K_v:
            self.settings.stereo_view = not self.settings.stereo_view

        elif key == K_c:
            self._cycle_camera_mode()

        elif key == K_f:
            self._focus_on_selected()

        elif key == K_t:
            trajectory = self.plan_trajectory("Earth", "Mars")
            if trajectory:
                self._mark_immersion_task("plan_transfer")
                self._action_message = (
                    "Earth\u2192Mars transfer: \u0394V "
                    f"{trajectory.total_delta_v / 1000:.2f} km/s, "
                    f"flight {trajectory.time_of_flight:.1f} days"
                )
            else:
                self._action_message = "Earth\u2192Mars transfer could not be created"

        elif key == K_m:
            if self.immersion_checklist:
                self.immersion_checklist.toggle()
            self.view_state.show_immersion_checklist = not self.view_state.show_immersion_checklist

        elif key == K_PERIOD:
            if self.educational_panel and self.educational_panel.visible:
                self.educational_panel.cycle_fact()

        elif key == K_0:
            self.select_body(self.sun)
            self._update_educational_panel()

        elif K_1 <= key <= K_9:
            planet_index = key - K_1
            if planet_index < len(PLANET_ORDER):
                planet_name = PLANET_ORDER[planet_index]
                self.select_body(self.planets[planet_name])
                self._update_educational_panel()

        return True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _jump_month(self, direction: int) -> None:
        """Jump forward or backward by one month, preserving day of month.

        Args:
            direction: +1 for forward, -1 for backward.
        """
        current_dt = self.time_manager.current_time.datetime_utc
        target_day = current_dt.day

        if direction < 0:
            if current_dt.month == 1:
                new_month, new_year = 12, current_dt.year - 1
            else:
                new_month, new_year = current_dt.month - 1, current_dt.year
        else:
            if current_dt.month == 12:
                new_month, new_year = 1, current_dt.year + 1
            else:
                new_month, new_year = current_dt.month + 1, current_dt.year

        max_days = monthrange(new_year, new_month)[1]
        actual_day = min(target_day, max_days)

        new_date = current_dt.replace(year=new_year, month=new_month, day=actual_day)
        self.time_manager.set_datetime(new_date)
        self._update_ui_date()
        self._mark_immersion_task("navigate_time")
