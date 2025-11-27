
import math
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import timedelta
from calendar import monthrange

from ..core.constants import (
    PLANET_ORDER, INNER_PLANETS, OUTER_PLANETS, DWARF_PLANETS,
    ORBITAL_ELEMENTS, PHYSICAL_PROPERTIES, AU, J2000
)
from ..core.celestial_body import (
    CelestialBody, Star, Planet, Moon, Spacecraft, BodyType, StateVector
)
from ..core.time_manager import TimeManager, SimulationTime
from ..physics.orbital_mechanics import OrbitalMechanics
from ..physics.trajectory_planner import (
    TrajectoryPlanner, TransferTrajectory, TransferType
)
from .renderer import Renderer, RenderSettings
from .camera import Camera, CameraMode
from ..ui.widgets import (
    DateTimePicker, TimeNavigationPanel, EducationalInfoPanel,
    HistoricalEventsPanel, PanelStyle
)
from ..data.planet_info import PLANET_DESCRIPTIONS

try:
    import pygame
    from pygame.locals import *
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False


@dataclass
class ViewState:
    show_inner_planets: bool = True
    show_outer_planets: bool = True
    show_dwarf_planets: bool = True
    show_orbits: bool = True
    show_labels: bool = True
    show_trajectories: bool = True
    show_info_panel: bool = True
    show_help: bool = True  # Show help by default for new users
    focus_inner_system: bool = False


class SolarSystemScene:

    def __init__(self, settings: RenderSettings = None):
        self.settings = settings or RenderSettings()
        self.renderer: Optional[Renderer] = None
        self.time_manager = TimeManager()
        self.trajectory_planner = TrajectoryPlanner()

        # Celestial bodies
        self.sun: Optional[Star] = None
        self.planets: Dict[str, Planet] = {}
        self.moons: Dict[str, Moon] = {}
        self.spacecraft: Dict[str, Spacecraft] = {}

        # Active trajectories
        self.trajectories: List[TransferTrajectory] = []

        # View state
        self.view_state = ViewState()

        # Selection
        self.selected_body: Optional[CelestialBody] = None

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
            ("  { / }", "Jump backward/forward 1 month"),
            ("  T", "Plan trip to Mars 🚀"),
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
            ("  H", "Toggle this help"),
            ("  ESC", "Quit simulation")
        ]

        # Enhanced UI widgets
        self.date_picker: Optional[DateTimePicker] = None
        self.time_nav_panel: Optional[TimeNavigationPanel] = None
        self.educational_panel: Optional[EducationalInfoPanel] = None
        self.historical_events: Optional[HistoricalEventsPanel] = None

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
            position=(20, 100),
            on_date_change=self._on_date_picker_change
        )
        self.date_picker.set_date(self.time_manager.current_time.datetime_utc)

        # Time navigation panel with quick jump buttons
        self.time_nav_panel = TimeNavigationPanel(
            position=(20, 60)
        )

        # Educational info panel
        self.educational_panel = EducationalInfoPanel(
            position=(self.settings.window_width - 370, 20),
            width=350
        )

        # Historical events panel
        self.historical_events = HistoricalEventsPanel(
            position=(self.settings.window_width - 420, self.settings.window_height - 200),
            width=400
        )
        self.historical_events.set_date(self.time_manager.current_time.datetime_utc)

    def _on_date_picker_change(self, new_date: 'datetime'):
        """
        Handle date changes from the date picker.

        Args:
            new_date: The new selected date
        """
        from datetime import datetime, timezone

        # Ensure timezone aware
        if new_date.tzinfo is None:
            new_date = new_date.replace(tzinfo=timezone.utc)

        # Update simulation time
        self.time_manager.set_datetime(new_date)

        # Update historical events
        if self.historical_events:
            self.historical_events.set_date(new_date)

    def _create_solar_system(self):
        # Create the Sun
        self.sun = Star("Sun")

        # Create planets
        for planet_name in PLANET_ORDER:
            is_dwarf = planet_name in DWARF_PLANETS
            planet = Planet(
                name=planet_name,
                parent=self.sun,
                is_dwarf=is_dwarf
            )
            self.planets[planet_name] = planet

        # Create Earth's Moon
        moon_orbital_elements = type(ORBITAL_ELEMENTS["Mercury"])(
            semi_major_axis=384400 / AU / 1000,  # km to AU
            eccentricity=0.0549,
            inclination=5.145,
            longitude_ascending=125.08,
            longitude_perihelion=318.15,
            mean_longitude=135.27,
            mean_longitude_rate=13.176358  # degrees per day * 36525
        )

        earth_moon = Moon(
            name="Moon",
            parent=self.planets["Earth"],
            orbital_elements=moon_orbital_elements
        )
        self.moons["Moon"] = earth_moon

    def get_all_bodies(self) -> List[CelestialBody]:
        bodies = [self.sun]
        bodies.extend(self.planets.values())
        bodies.extend(self.moons.values())
        bodies.extend(self.spacecraft.values())
        return bodies

    def get_body_by_name(self, name: str) -> Optional[CelestialBody]:
        if name == "Sun":
            return self.sun
        if name in self.planets:
            return self.planets[name]
        if name in self.moons:
            return self.moons[name]
        if name in self.spacecraft:
            return self.spacecraft[name]
        return None

    def select_body(self, body: CelestialBody):
        self.selected_body = body
        self.renderer.selected_body = body

    def plan_trajectory(
        self,
        origin_name: str,
        destination_name: str,
        departure_date: Optional[float] = None
    ) -> Optional[TransferTrajectory]:
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
            transfer_type=TransferType.HOHMANN
        )

        # Create spacecraft for the trajectory
        spacecraft = self.trajectory_planner.create_spacecraft_from_transfer(
            trajectory,
            name=f"{origin_name}-{destination_name} Transfer"
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

        elif key == K_EQUALS or key == K_PLUS or key == K_KP_PLUS:
            self.time_manager.increase_time_warp()

        elif key == K_MINUS or key == K_KP_MINUS:
            self.time_manager.decrease_time_warp()

        elif key == K_r:
            self.time_manager.reverse_time()

        elif key == K_d:
            # Toggle date picker
            if self.date_picker:
                self.date_picker.toggle()
                if self.date_picker.visible:
                    self.date_picker.set_date(self.time_manager.current_time.datetime_utc)

        elif key == K_n:
            # Toggle time navigation panel
            if self.time_nav_panel:
                self.time_nav_panel.toggle()

        elif key == K_e:
            # Toggle historical events panel
            if self.historical_events:
                self.historical_events.toggle()

        elif key == K_LEFTBRACKET:
            # Jump backward 1 day
            self.time_manager.advance_days(-1)
            self._update_ui_date()

        elif key == K_RIGHTBRACKET:
            # Jump forward 1 day
            self.time_manager.advance_days(1)
            self._update_ui_date()

        elif key == K_LEFTBRACE:
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

        elif key == K_RIGHTBRACE:
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

        elif key == K_HOME:
            self.renderer.camera.reset()
            self.renderer.camera.mode = CameraMode.FREE

        elif key == K_o:
            self.view_state.show_orbits = not self.view_state.show_orbits
            self.renderer.settings.show_orbits = self.view_state.show_orbits

        elif key == K_l:
            self.view_state.show_labels = not self.view_state.show_labels
            self.renderer.settings.show_labels = self.view_state.show_labels

        elif key == K_i:
            self.view_state.show_info_panel = not self.view_state.show_info_panel

        elif key == K_g:
            self.renderer.settings.show_grid = not self.renderer.settings.show_grid

        elif key == K_h:
            self.view_state.show_help = not self.view_state.show_help

        elif key == K_c:
            self._cycle_camera_mode()

        elif key == K_f:
            self._focus_on_selected()

        elif key == K_t:
            # Plan trajectory to Mars from Earth
            print("\n" + "="*60)
            print("Planning trajectory from Earth to Mars...")
            trajectory = self.plan_trajectory("Earth", "Mars")
            if trajectory:
                print(f"✓ Trajectory created successfully!")
                print(f"  Departure: {trajectory.departure_time:.1f}")
                print(f"  Arrival: {trajectory.arrival_time:.1f}")
                print(f"  Flight time: {trajectory.time_of_flight:.1f} days")
                print(f"  Total ΔV: {trajectory.total_delta_v/1000:.2f} km/s")
                print("  Spacecraft visible on trajectory (green rocket icon)")
                print("="*60 + "\n")
            else:
                print("✗ Failed to create trajectory")
                print("="*60 + "\n")

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
                if key != 'fun_facts':
                    properties[key.replace('_', ' ').title()] = value

            # Get fun facts
            fun_facts = info.get('fun_facts', [])

            self.educational_panel.set_body(body_name, properties, fun_facts)

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

        # Update UI after time change
        self._update_ui_date()

    def _handle_mouse_button(self, button: int, pressed: bool):
        """Handle mouse button events."""
        if button == 1:  # Left button
            self._mouse_dragging = pressed
            if pressed:
                self._last_mouse_pos = pygame.mouse.get_pos()

        elif button == 3:  # Right button
            if pressed:
                self._mouse_dragging = True
                self._last_mouse_pos = pygame.mouse.get_pos()
            else:
                self._mouse_dragging = False

    def _handle_mouse_motion(self, pos: Tuple[int, int], rel: Tuple[int, int]):
        """Handle mouse motion."""
        if self._mouse_dragging:
            # Get mouse buttons
            buttons = pygame.mouse.get_pressed()

            if buttons[0]:  # Left button - orbit camera
                self.renderer.camera.orbit(-rel[0], -rel[1])

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
        self.time_manager.update()

        # Update camera
        self.renderer.camera.update(
            self.time_manager.julian_date,
            self.renderer.distance_scale
        )

    def _render(self):
        renderer = self.renderer
        jd = self.time_manager.julian_date

        # Begin frame
        renderer.begin_frame()

        # Render star background
        renderer.render_stars()

        # Render grid if enabled
        renderer.render_grid()

        # Render axes if enabled
        renderer.render_axes()

        # Render orbits
        if self.view_state.show_orbits:
            for planet in self.planets.values():
                if self._should_render_body(planet):
                    renderer.render_orbit(planet, jd)

        # Render celestial bodies
        # Sun first
        renderer.render_body(self.sun, jd, self.selected_body == self.sun)

        # Render sun label
        if self.view_state.show_labels:
            sun_pos = np.array([0, 0, 0])
            renderer.render_label("Sun", sun_pos)

        # Planets
        for planet in self.planets.values():
            if self._should_render_body(planet):
                is_selected = self.selected_body == planet
                renderer.render_body(planet, jd, is_selected)

                # Label
                if self.view_state.show_labels:
                    state = planet.get_state_at_time(jd)
                    pos = state.position * renderer.distance_scale
                    renderer.render_label(planet.name, pos)

        # Moons (scaled differently)
        for moon in self.moons.values():
            # Only render if close to parent
            pass  # Skip for now - moons are too small at this scale

        # Render trajectories
        if self.view_state.show_trajectories:
            for trajectory in self.trajectories:
                renderer.render_trajectory(trajectory.trajectory_points)

        # Render spacecraft
        for spacecraft in self.spacecraft.values():
            # Only render if within trajectory time
            if spacecraft.trajectory and len(spacecraft.trajectory) >= 2:
                start_time = spacecraft.trajectory[0].time
                end_time = spacecraft.trajectory[-1].time
                if start_time <= jd <= end_time:
                    state = spacecraft.get_state_at_time(jd)
                    pos = state.position * renderer.distance_scale
                    # Draw as bright point
                    renderer.render_label("🚀 " + spacecraft.name, pos, (0, 255, 128))

        # UI overlays
        # Status bar
        status = self.time_manager.get_status_string()
        status += f"  |  FPS: {renderer.get_fps():.0f}"
        if self.selected_body:
            status += f"  |  Selected: {self.selected_body.name}"
        renderer.render_status_bar(status)

        # Info panel
        if self.view_state.show_info_panel and self.selected_body:
            info = self.selected_body.get_info_dict()

            # Add current position info
            state = self.selected_body.get_state_at_time(jd)
            distance_au = np.linalg.norm(state.position) / AU
            speed_kms = np.linalg.norm(state.velocity) / 1000

            info["Distance from Sun"] = f"{distance_au:.3f} AU"
            info["Orbital Speed"] = f"{speed_kms:.1f} km/s"

            renderer.render_info_panel(info)

        # Help overlay
        if self.view_state.show_help:
            renderer.render_help_overlay(self.controls)

        # Enhanced UI widgets
        if self.date_picker:
            renderer.render_date_picker(self.date_picker.get_render_data())

        if self.time_nav_panel:
            renderer.render_time_navigation_panel(self.time_nav_panel.get_render_data())

        if self.educational_panel and self.selected_body:
            renderer.render_educational_panel(self.educational_panel.get_render_data())

        if self.historical_events:
            renderer.render_historical_events(self.historical_events.get_render_data())

        # End frame
        renderer.end_frame()

    def _should_render_body(self, body: CelestialBody) -> bool:
        if body.name in INNER_PLANETS:
            return self.view_state.show_inner_planets
        elif body.name in OUTER_PLANETS:
            return self.view_state.show_outer_planets
        elif body.name in DWARF_PLANETS:
            return self.view_state.show_dwarf_planets
        return True

    def get_transfer_summary(
        self,
        origin_name: str,
        destination_name: str
    ) -> Optional[Dict[str, Any]]:
        origin = self.get_body_by_name(origin_name)
        destination = self.get_body_by_name(destination_name)

        if not origin or not destination:
            return None

        return self.trajectory_planner.get_transfer_summary(origin, destination)
