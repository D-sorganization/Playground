from __future__ import annotations

import math
from calendar import monthrange
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np

from ..core.celestial_body import (
    BodyType,
    CelestialBody,
    Moon,
    Planet,
    Spacecraft,
    Star,
)
from ..core.constants import (
    AU,
    DWARF_PLANETS,
    INNER_PLANETS,
    OUTER_PLANETS,
    PLANET_ORDER,
)
from ..core.time_manager import TimeManager
from ..data.asteroids import MAJOR_ASTEROIDS, generate_belt_particles
from ..data.comets import COMETS
from ..data.moon_systems import moons_by_parent
from ..data.planet_info import PLANET_DESCRIPTIONS
from ..physics.trajectory_planner import (
    TrajectoryPlanner,
    TransferTrajectory,
    TransferType,
)
from ..ui.widgets import (
    Checkbox,
    DateTimePicker,
    EducationalInfoPanel,
    HistoricalEventsPanel,
    ImmersionChecklistPanel,
    NavigationPanel,
    SettingsPanel,
    TimeNavigationPanel,
)
from .camera import CameraMode
from .renderer import Renderer, RenderSettings

try:
    import pygame
    from pygame.locals import (
        K_0,
        K_1,
        K_9,
        K_EQUALS,
        K_ESCAPE,
        K_HOME,
        K_KP_MINUS,
        K_KP_PLUS,
        K_PAGEUP,
        K_LEFTBRACKET,
        K_MINUS,
        K_PERIOD,
        K_PLUS,
        K_PAGEDOWN,
        K_RIGHTBRACKET,
        K_SPACE,
        KEYDOWN,
        MOUSEBUTTONDOWN,
        MOUSEBUTTONUP,
        MOUSEMOTION,
        MOUSEWHEEL,
        QUIT,
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
        K_r,
        K_t,
        K_v,
    )

    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

try:
    from OpenGL.GL import GL_DEPTH_BUFFER_BIT, glClear, glViewport

    OPENGL_AVAILABLE = True
except ImportError:
    OPENGL_AVAILABLE = False


@dataclass
class ViewState:
    show_inner_planets: bool = True
    show_outer_planets: bool = True
    show_dwarf_planets: bool = True
    show_minor_bodies: bool = True
    show_orbits: bool = True
    show_labels: bool = True
    show_trajectories: bool = True
    show_info_panel: bool = True
    show_help: bool = True  # Show help by default for new users
    focus_inner_system: bool = False
    show_immersion_checklist: bool = True


class SolarSystemScene:

    def __init__(self, settings: RenderSettings | None = None):
        self.settings = settings or RenderSettings()
        self.renderer: Renderer | None = None
        self.time_manager = TimeManager()
        self.trajectory_planner = TrajectoryPlanner()

        # Celestial bodies
        self.sun: Star | None = None
        self.planets: dict[str, Planet] = {}
        self.moons: dict[str, Moon] = {}
        self.asteroids: dict[str, CelestialBody] = {}
        self.comets: dict[str, CelestialBody] = {}
        self.spacecraft: dict[str, Spacecraft] = {}

        # Pre-computed asteroid belt cloud
        self.asteroid_belt_points = generate_belt_particles()

        # Active trajectories
        self.trajectories: list[TransferTrajectory] = []

        # View state
        self.view_state = ViewState()

        # Recent action feedback for status bar
        self._action_message: str = ""

        # Selection
        self.selected_body: CelestialBody | None = None

        # Mouse state
        self._mouse_dragging = False
        self._last_mouse_pos = (0, 0)

        # Control bindings displayed in help
        self.controls = [
            ("MOUSE:", ""),
            ("  Scroll Wheel", "Zoom in/out"),
            ("  Left Drag", "Rotate camera"),
            ("  Right Drag", "Pan camera"),
            ("", ""),
            ("KEYBOARD:", ""),
            ("  SPACE", "Pause/Resume"),
            ("  + / -", "Speed up/slow down time"),
            ("  R", "Reverse time flow"),
            ("  D", "Toggle date picker"),
            ("  N", "Toggle time navigation panel"),
            ("  E", "Toggle historical events"),
            ("  [ / ]", "Jump backward/forward 1 day"),
            ("  PgUp/Dn", "Jump backward/forward 1 month"),
            ("  T", "Plan trip to Mars 🚀"),
            ("  M", "Toggle immersion checklist"),
            ("", ""),
            ("  0-9", "Select planet (0=Sun, 3=Earth, 4=Mars)"),
            ("  F", "Focus camera on selected"),
            ("  C", "Cycle camera modes"),
            ("  HOME", "Reset camera view"),
            ("", ""),
            ("  O", "Toggle orbital paths"),
            ("  L", "Toggle planet labels"),
            ("  I", "Toggle info panel"),
            ("  G", "Toggle reference grid"),
            ("  V", "Toggle stereo/VR view"),
            ("  H", "Toggle this help"),
            ("  ESC", "Quit simulation"),
        ]

        # Enhanced UI widgets
        self.date_picker: DateTimePicker | None = None
        self.time_nav_panel: TimeNavigationPanel | None = None
        self.educational_panel: EducationalInfoPanel | None = None
        self.historical_events: HistoricalEventsPanel | None = None
        self.immersion_checklist: ImmersionChecklistPanel | None = None
        self.settings_panel: SettingsPanel | None = None
        self.nav_mode_panel: NavigationPanel | None = None
        self._last_ui_sync_jd: float | None = None

    def initialize(self) -> bool:
        # Create renderer
        self.renderer = Renderer(self.settings)
        if not self.renderer.initialize():
            return False

        # Create celestial bodies
        self._create_solar_system()

        # Set initial time to current date
        self.time_manager.set_to_now()

        # Set initial time warp
        self.time_manager.time_warp = 86400  # 1 day per second

        # Initialize enhanced UI widgets
        self._initialize_ui_widgets()

        return True

    def _initialize_ui_widgets(self):
        """Initialize enhanced UI widgets for educational features."""
        # Date picker for manual time navigation
        self.date_picker = DateTimePicker(
            position=(20, 100), on_date_change=self._on_date_picker_change
        )
        self.date_picker.set_date(self.time_manager.current_time.datetime_utc)

        # Time navigation panel with quick jump buttons
        self.time_nav_panel = TimeNavigationPanel(position=(20, 60))

        # Educational info panel
        self.educational_panel = EducationalInfoPanel(
            position=(self.settings.window_width - 370, 20), width=350
        )

        # Historical events panel
        self.historical_events = HistoricalEventsPanel(
            position=(
                self.settings.window_width - 420,
                self.settings.window_height - 200,
            ),
            width=400,
        )
        self.historical_events.set_date(self.time_manager.current_time.datetime_utc)

        # Immersive checklist to guide educational exploration
        self.immersion_checklist = ImmersionChecklistPanel(position=(20, 240))
        
        # Settings Panel
        self.settings_panel = SettingsPanel(position=(20, 500))
        self.settings_panel.add_checkbox("Orbits (O)", self.view_state.show_orbits, "toggle_orbits")
        self.settings_panel.add_checkbox("Labels (L)", self.view_state.show_labels, "toggle_labels")
        self.settings_panel.add_checkbox("Grid (G)", self.renderer.settings.show_grid, "toggle_grid")
        self.settings_panel.add_checkbox("Stereo (V)", self.settings.stereo_view, "toggle_stereo")
        self.settings_panel.visible = True
        
        # Navigation Mode Panel
        self.nav_mode_panel = NavigationPanel(position=(20, 350))

    def _on_date_picker_change(self, new_date: datetime):
        """
        Handle date changes from the date picker.

        Args:
            new_date: The new selected date
        """
        # Ensure timezone aware
        if new_date.tzinfo is None:
            new_date = new_date.replace(tzinfo=datetime.UTC)

        # Update simulation time
        self.time_manager.set_datetime(new_date)

        # Update historical events
        if self.historical_events:
            self.historical_events.set_date(new_date)

        self._mark_immersion_task("navigate_time")

    def _create_solar_system(self):
        # Create the Sun
        self.sun = Star("Sun")

        # Create planets
        for planet_name in PLANET_ORDER:
            is_dwarf = planet_name in DWARF_PLANETS
            planet = Planet(name=planet_name, parent=self.sun, is_dwarf=is_dwarf)
            self.planets[planet_name] = planet

        # Create Earth's Moon
        for parent_name, moon_list in moons_by_parent().items():
            parent_body = self.planets.get(parent_name)
            if not parent_body:
                continue
            for descriptor in moon_list:
                moon = Moon(
                    name=descriptor.name,
                    parent=parent_body,
                    orbital_elements=descriptor.elements,
                    physical_properties=descriptor.properties,
                )
                self.moons[descriptor.name] = moon

        for asteroid in MAJOR_ASTEROIDS:
            asteroid_body = CelestialBody(
                name=asteroid.name,
                body_type=BodyType.ASTEROID,
                orbital_elements=asteroid.elements,
                physical_properties=asteroid.properties,
                parent=self.sun,
            )
            self.asteroids[asteroid.name] = asteroid_body

        for comet in COMETS:
            comet_body = CelestialBody(
                name=comet.name,
                body_type=BodyType.COMET,
                orbital_elements=comet.elements,
                physical_properties=comet.properties,
                parent=self.sun,
            )
            self.comets[comet.name] = comet_body

    def get_all_bodies(self) -> list[CelestialBody]:
        bodies = [self.sun]
        bodies.extend(self.planets.values())
        bodies.extend(self.moons.values())
        bodies.extend(self.asteroids.values())
        bodies.extend(self.comets.values())
        bodies.extend(self.spacecraft.values())
        return bodies

    def get_body_by_name(self, name: str) -> CelestialBody | None:
        if name == "Sun":
            return self.sun
        if name in self.planets:
            return self.planets[name]
        if name in self.moons:
            return self.moons[name]
        if name in self.asteroids:
            return self.asteroids[name]
        if name in self.comets:
            return self.comets[name]
        if name in self.spacecraft:
            return self.spacecraft[name]
        return None

    def select_body(self, body: CelestialBody):
        self.selected_body = body
        self.renderer.selected_body = body
        self._mark_immersion_task("select_body")

    def plan_trajectory(
        self,
        origin_name: str,
        destination_name: str,
        departure_date: float | None = None,
    ) -> TransferTrajectory | None:
        origin = self.get_body_by_name(origin_name)
        destination = self.get_body_by_name(destination_name)

        if not origin or not destination:
            return None

        if departure_date is None:
            departure_date = self.time_manager.julian_date

        trajectory = self.trajectory_planner.calculate_transfer(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            transfer_type=TransferType.HOHMANN,
        )

        # Create spacecraft for the trajectory
        spacecraft = self.trajectory_planner.create_spacecraft_from_transfer(
            trajectory, name=f"{origin_name}-{destination_name} Transfer"
        )

        self.spacecraft[spacecraft.name] = spacecraft
        self.trajectories.append(trajectory)

        return trajectory

    def run(self):
        if not self.renderer:
            raise RuntimeError("Scene not initialized. Call initialize() first.")

        running = True

        while running:
            # Handle events
            running = self._handle_events()

            # Update simulation
            self._update()

            # Render
            self._render()

        # Cleanup
        self.renderer.cleanup()

    def _handle_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == QUIT:
                return False

            elif event.type == KEYDOWN:
                if not self._handle_key(event.key):
                    return False

            elif event.type == MOUSEBUTTONDOWN:
                self._handle_mouse_button(event.button, True)

            elif event.type == MOUSEBUTTONUP:
                self._handle_mouse_button(event.button, False)

            elif event.type == MOUSEMOTION:
                self._handle_mouse_motion(event.pos, event.rel)

            elif event.type == MOUSEWHEEL:
                self.renderer.camera.zoom(event.y * 0.5)

        return True

    def _handle_key(self, key: int) -> bool:
        """
        Handle keyboard input.

        Returns:
            False if should quit, True otherwise
        """
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
            # Toggle date picker
            if self.date_picker:
                self.date_picker.toggle()
                if self.date_picker.visible:
                    self.date_picker.set_date(self.time_manager.current_time.datetime_utc)
                    self._mark_immersion_task("navigate_time")

        elif key == K_n:
            # Toggle time navigation panel
            if self.time_nav_panel:
                self.time_nav_panel.toggle()
                self._mark_immersion_task("navigate_time")

        elif key == K_e:
            # Toggle historical events panel
            if self.historical_events:
                self.historical_events.toggle()
                if self.historical_events.visible:
                    self._mark_immersion_task("historical_events")

        elif key == K_LEFTBRACKET:
            # Jump backward 1 day
            self.time_manager.advance_days(-1)
            self._update_ui_date()
            self._mark_immersion_task("navigate_time")

        elif key == K_RIGHTBRACKET:
            # Jump forward 1 day
            self.time_manager.advance_days(1)
            self._update_ui_date()
            self._mark_immersion_task("navigate_time")

        elif key == K_PAGEUP:
            # Jump backward 1 month, preserving day of month when possible
            current_dt = self.time_manager.current_time.datetime_utc
            target_day = current_dt.day

            # Calculate previous month
            if current_dt.month == 1:
                prev_month = 12
                prev_year = current_dt.year - 1
            else:
                prev_month = current_dt.month - 1
                prev_year = current_dt.year

            # Ensure day exists in previous month (handle cases like Jan 31 -> Dec 31)
            max_days_in_prev = monthrange(prev_year, prev_month)[1]
            actual_day = min(target_day, max_days_in_prev)

            prev_date = current_dt.replace(year=prev_year, month=prev_month, day=actual_day)
            self.time_manager.set_datetime(prev_date)
            self._update_ui_date()
            self._mark_immersion_task("navigate_time")

        elif key == K_PAGEDOWN:
            # Jump forward 1 month, preserving day of month when possible
            current_dt = self.time_manager.current_time.datetime_utc
            target_day = current_dt.day

            # Calculate next month
            if current_dt.month == 12:
                next_month = 1
                next_year = current_dt.year + 1
            else:
                next_month = current_dt.month + 1
                next_year = current_dt.year

            # Ensure day exists in next month (handle cases like Jan 31 -> Feb 28/29)
            max_days_in_next = monthrange(next_year, next_month)[1]
            actual_day = min(target_day, max_days_in_next)

            next_date = current_dt.replace(year=next_year, month=next_month, day=actual_day)
            self.time_manager.set_datetime(next_date)
            self._update_ui_date()
            self._mark_immersion_task("navigate_time")

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
            # Plan trajectory to Mars from Earth
            trajectory = self.plan_trajectory("Earth", "Mars")
            if trajectory:
                self._mark_immersion_task("plan_transfer")
                self._action_message = (
                    "Earth→Mars transfer: ΔV "
                    f"{trajectory.total_delta_v/1000:.2f} km/s, "
                    f"flight {trajectory.time_of_flight:.1f} days"
                )
            else:
                self._action_message = "Earth→Mars transfer could not be created"

        elif key == K_m:
            if self.immersion_checklist:
                self.immersion_checklist.toggle()
            self.view_state.show_immersion_checklist = not self.view_state.show_immersion_checklist

        # Period/comma for cycling fun facts
        elif key == K_PERIOD:
            if self.educational_panel and self.educational_panel.visible:
                self.educational_panel.cycle_fact()

        # Number keys for planet selection
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

    def _update_ui_date(self):
        """Update all UI widgets with current date."""
        current_dt = self.time_manager.current_time.datetime_utc

        if self.date_picker:
            self.date_picker.set_date(current_dt)

        if self.historical_events:
            self.historical_events.set_date(current_dt)

    def _update_educational_panel(self):
        """Update educational panel with selected body information."""
        if not self.selected_body or not self.educational_panel:
            return

        # Get educational info from PLANET_DESCRIPTIONS
        body_name = self.selected_body.name
        if body_name in PLANET_DESCRIPTIONS:
            info = PLANET_DESCRIPTIONS[body_name]

            # Build properties dict
            properties = {}
            for key, value in info.items():
                if key != "fun_facts":
                    properties[key.replace("_", " ").title()] = value

            # Get fun facts
            fun_facts = info.get("fun_facts", [])

            self.educational_panel.set_body(body_name, properties, fun_facts)

        self._mark_immersion_task("select_body")

    def _mark_immersion_task(self, task_id: str):
        """Mark an immersion checklist task as complete if available."""
        if self.immersion_checklist:
            self.immersion_checklist.mark_complete(task_id)

    def _handle_time_nav_action(self, action: str):
        """
        Handle time navigation panel button actions.

        Args:
            action: The navigation action to perform
        """
        if action == "prev_day":
            self.time_manager.advance_days(-1)
        elif action == "next_day":
            self.time_manager.advance_days(1)
        elif action == "prev_week":
            self.time_manager.advance_days(-7)
        elif action == "next_week":
            self.time_manager.advance_days(7)
        elif action == "prev_month":
            self.time_manager.advance_days(-30)
        elif action == "next_month":
            self.time_manager.advance_days(30)
        elif action == "prev_year":
            self.time_manager.advance_years(-1)
        elif action == "next_year":
            self.time_manager.advance_years(1)
        elif action == "goto_today":
            self.time_manager.set_to_now()
        elif action == "goto_j2000":
            self.time_manager.set_to_j2000()
        elif action == "goto_j2030":
            self.time_manager.set_datetime(self.time_manager.J2030)
        elif action == "reset":
            self.time_manager.set_to_now()
        elif action == "faster":
            self.time_manager.increase_time_warp()
        elif action == "slower":
            self.time_manager.decrease_time_warp()
        elif action == "reverse":
            self.time_manager.reverse_time()
        elif action == "toggle_pause":
            self.time_manager.toggle_pause()

        # Update UI after time change
        self._update_ui_date()
        self._mark_immersion_task("navigate_time")

    def _handle_mouse_button(self, button: int, pressed: bool):
        """Handle mouse button events."""
        if button == 1:  # Left button
            # Check UI clicks first
            if pressed and self._handle_ui_click(pygame.mouse.get_pos()):
                return

            self._mouse_dragging = pressed
            if pressed:
                self._last_mouse_pos = pygame.mouse.get_pos()

        elif button == 3:  # Right button
            if pressed:
                self._mouse_dragging = True
                self._last_mouse_pos = pygame.mouse.get_pos()
            else:
                self._mouse_dragging = False

    def _handle_mouse_motion(self, pos: tuple[int, int], rel: tuple[int, int]):
        """Handle mouse motion."""
        if self._mouse_dragging:
            # Get mouse buttons
            buttons = pygame.mouse.get_pressed()
            
            mode = "Orbit"
            if self.nav_mode_panel:
                mode = self.nav_mode_panel.get_current_mode()

            if buttons[0]:  # Left button - depends on mode
                if mode == "Orbit":
                    self.renderer.camera.orbit(-rel[0], -rel[1])
                elif mode == "Pan":
                    self.renderer.camera.pan(-rel[0], rel[1])
                elif mode == "Zoom":
                    self.renderer.camera.zoom(rel[1] * 0.5)

            elif buttons[2]:  # Right button - pan camera
                self.renderer.camera.pan(-rel[0], rel[1])

    def _cycle_camera_mode(self):
        """Cycle through camera modes."""
        camera = self.renderer.camera
        modes = [CameraMode.FREE, CameraMode.HELIOCENTRIC, CameraMode.TOP_DOWN]

        if self.selected_body:
            modes.append(CameraMode.PLANET_CENTRIC)

        current_index = modes.index(camera.mode) if camera.mode in modes else 0
        next_index = (current_index + 1) % len(modes)

        new_mode = modes[next_index]
        camera.set_mode(new_mode, self.selected_body)

    def _focus_on_selected(self):
        if not self.selected_body:
            return

        # Get body position
        state = self.selected_body.get_state_at_time(self.time_manager.julian_date)
        pos = state.position * self.renderer.distance_scale

        self.renderer.camera.look_at(pos)

        # Set appropriate distance based on body type
        if self.selected_body.body_type == BodyType.STAR:
            self.renderer.camera.set_distance(20)
        elif self.selected_body.name in INNER_PLANETS:
            self.renderer.camera.set_distance(5)
        else:
            self.renderer.camera.set_distance(15)

    def _update(self):
        # Update time
        delta_jd = self.time_manager.update()

        current_jd = self.time_manager.julian_date

        if (delta_jd or self._last_ui_sync_jd is None) and (
            self._last_ui_sync_jd is None or not math.isclose(current_jd, self._last_ui_sync_jd)
        ):
            self._update_ui_date()
            self._last_ui_sync_jd = current_jd

        # Update camera
        self.renderer.camera.update(self.time_manager.julian_date, self.renderer.distance_scale)

    def _render(self):
        renderer = self.renderer
        jd = self.time_manager.julian_date

        if self.settings.stereo_view:
            left_eye, right_eye = renderer.camera.stereo_states()
            half_width = renderer.settings.window_width // 2

            glViewport(0, 0, half_width, renderer.settings.window_height)
            renderer.begin_frame(camera_state=left_eye)
            self._render_view_contents(jd)

            glViewport(half_width, 0, half_width, renderer.settings.window_height)
            renderer.begin_frame(camera_state=right_eye, clear=False)
            glClear(GL_DEPTH_BUFFER_BIT)
            self._render_view_contents(jd)

            glViewport(0, 0, renderer.settings.window_width, renderer.settings.window_height)
            renderer.begin_frame(clear=False)
            self._render_overlays(jd)
            renderer.end_frame()
            return

        renderer.begin_frame()
        self._render_view_contents(jd)
        self._render_overlays(jd)
        renderer.end_frame()

    def _render_view_contents(self, julian_date: float):
        renderer = self.renderer

        renderer.render_stars()
        renderer.render_grid()
        renderer.render_axes()

        if self.view_state.show_orbits:
            for planet in self.planets.values():
                if self._should_render_body(planet):
                    renderer.render_orbit(planet, julian_date)

        renderer.render_body(self.sun, julian_date, self.selected_body == self.sun)

        if self.view_state.show_labels:
            sun_pos = np.array([0, 0, 0])
            renderer.render_label("Sun", sun_pos)

        for planet in self.planets.values():
            if self._should_render_body(planet):
                is_selected = self.selected_body == planet
                renderer.render_body(planet, julian_date, is_selected)

                if self.view_state.show_labels:
                    state = planet.get_state_at_time(julian_date)
                    pos = state.position * renderer.distance_scale
                    renderer.render_label(planet.name, pos)

        if self.view_state.show_minor_bodies:
            renderer.render_asteroid_belt(self.asteroid_belt_points)
            for asteroid in self.asteroids.values():
                renderer.render_body(asteroid, julian_date, self.selected_body == asteroid)
                if self.view_state.show_labels:
                    state = asteroid.get_state_at_time(julian_date)
                    renderer.render_label(asteroid.name, state.position * renderer.distance_scale)

            for comet in self.comets.values():
                renderer.render_body(comet, julian_date, self.selected_body == comet)
                if self.view_state.show_orbits:
                    renderer.render_orbit(comet, julian_date, color=(0.6, 0.8, 1.0, 0.7))
                if self.view_state.show_labels:
                    state = comet.get_state_at_time(julian_date)
                    renderer.render_label(comet.name, state.position * renderer.distance_scale)

        for moon in self.moons.values():
            renderer.render_body(moon, julian_date, self.selected_body == moon)
            if self.view_state.show_labels:
                state = moon.get_state_at_time(julian_date)
                renderer.render_label(moon.name, state.position * renderer.distance_scale)

        if self.view_state.show_trajectories:
            for trajectory in self.trajectories:
                renderer.render_trajectory(trajectory.trajectory_points)

        for spacecraft in self.spacecraft.values():
            if spacecraft.trajectory and len(spacecraft.trajectory) >= 2:
                start_time = spacecraft.trajectory[0].time
                end_time = spacecraft.trajectory[-1].time
                if start_time <= julian_date <= end_time:
                    state = spacecraft.get_state_at_time(julian_date)
                    pos = state.position * renderer.distance_scale
                    renderer.render_label("🚀 " + spacecraft.name, pos, (0, 255, 128))

    def _render_overlays(self, julian_date: float):
        renderer = self.renderer

        status = self.time_manager.get_status_string()
        status += f"  |  FPS: {renderer.get_fps():.0f}"
        if self.selected_body:
            status += f"  |  Selected: {self.selected_body.name}"
        if self._action_message:
            status += f"  |  {self._action_message}"
        renderer.render_status_bar(status)

        if self.view_state.show_info_panel and self.selected_body:
            info = self.selected_body.get_info_dict()
            state = self.selected_body.get_state_at_time(julian_date)
            distance_au = np.linalg.norm(state.position) / AU
            speed_kms = np.linalg.norm(state.velocity) / 1000
            info["Distance from Sun"] = f"{distance_au:.3f} AU"
            info["Orbital Speed"] = f"{speed_kms:.1f} km/s"
            renderer.render_info_panel(info)

        if self.view_state.show_help:
            renderer.render_help_overlay(self.controls)

        if self.date_picker:
            renderer.render_date_picker(self.date_picker.get_render_data())

        if self.time_nav_panel:
            renderer.render_time_navigation_panel(self.time_nav_panel.get_render_data())

        if self.educational_panel and self.selected_body:
            renderer.render_educational_panel(self.educational_panel.get_render_data())

        if self.historical_events:
            renderer.render_historical_events(self.historical_events.get_render_data())

        if self.view_state.show_immersion_checklist and self.immersion_checklist:
            renderer.render_immersion_checklist(self.immersion_checklist.get_render_data())
            
        if self.settings_panel:
            renderer.render_settings_panel(self.settings_panel.get_render_data())
            
        if self.nav_mode_panel:
            renderer.render_nav_mode_panel(self.nav_mode_panel.get_render_data())

    def _should_render_body(self, body: CelestialBody) -> bool:
        if body.name in INNER_PLANETS:
            return self.view_state.show_inner_planets
        elif body.name in OUTER_PLANETS:
            return self.view_state.show_outer_planets
        elif body.name in DWARF_PLANETS:
            return self.view_state.show_dwarf_planets
        elif body.body_type in {BodyType.ASTEROID, BodyType.COMET}:
            return self.view_state.show_minor_bodies
        return True

    def get_transfer_summary(
        self, origin_name: str, destination_name: str
    ) -> dict[str, Any] | None:
        origin = self.get_body_by_name(origin_name)
        destination = self.get_body_by_name(destination_name)

        if not origin or not destination:
            return None

        return self.trajectory_planner.get_transfer_summary(origin, destination)

    def _handle_ui_click(self, pos: tuple[int, int]) -> bool:
        """Handle clicks on UI overlays."""
        x, y = pos
        
        # Check Settings Panel
        if self.settings_panel and self.settings_panel.visible:
            # Simple hit test based on known layout in renderer
            # position, width=200, height=header+items
            px, py = self.settings_panel.position
            width = 200
            line_height = 24
            header_height = 30
            height = header_height + len(self.settings_panel.checkboxes) * line_height + 10
            
            if px <= x <= px + width and py <= y <= py + height:
                # Clicked info, check items
                if py + header_height <= y:
                    idx = (y - (py + header_height)) // line_height
                    action = self.settings_panel.toggle_checkbox(idx)
                    if action:
                        self._handle_setting_action(action)
                return True
                
        # Check Navigation Panel
        if self.nav_mode_panel and self.nav_mode_panel.visible:
            px, py = self.nav_mode_panel.position
            width = 150
            line_height = 24
            header_height = 30
            height = header_height + len(self.nav_mode_panel.modes) * line_height + 10
            
            if px <= x <= px + width and py <= y <= py + height:
                if py + header_height <= y:
                    idx = (y - (py + header_height)) // line_height
                    if 0 <= idx < len(self.nav_mode_panel.modes):
                         mode = self.nav_mode_panel.modes[idx]
                         self.nav_mode_panel.set_mode(mode)
                return True

        return False

    def _handle_setting_action(self, action: str):
        if action == "toggle_orbits":
            self.view_state.show_orbits = not self.view_state.show_orbits
            self.renderer.settings.show_orbits = self.view_state.show_orbits
        elif action == "toggle_labels":
            self.view_state.show_labels = not self.view_state.show_labels
            self.renderer.settings.show_labels = self.view_state.show_labels
        elif action == "toggle_grid":
            self.renderer.settings.show_grid = not self.renderer.settings.show_grid
        elif action == "toggle_stereo":
            self.settings.stereo_view = not self.settings.stereo_view
