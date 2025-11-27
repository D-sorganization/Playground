"""
3D Renderer
===========

OpenGL-based renderer for the solar system visualization.
Provides high-quality rendering of planets, orbits, trajectories,
and UI elements.
"""

import math
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass

try:
    import pygame
    from pygame.locals import *
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

try:
    from OpenGL.GL import *
    from OpenGL.GLU import *
    from OpenGL.GLUT import *
    OPENGL_AVAILABLE = True
except ImportError:
    OPENGL_AVAILABLE = False

from ..core.constants import AU, PLANET_ORDER
from ..core.celestial_body import CelestialBody, StateVector, BodyType
from .camera import Camera


@dataclass
class RenderSettings:
    """Settings for the renderer."""
    window_width: int = 1600
    window_height: int = 900
    fullscreen: bool = False
    vsync: bool = True
    antialiasing: bool = True
    show_orbits: bool = True
    show_labels: bool = True
    show_grid: bool = False
    show_axes: bool = False
    orbit_segments: int = 360
    planet_segments: int = 32
    background_color: Tuple[float, float, float, float] = (0.02, 0.02, 0.05, 1.0)


class Renderer:
    """
    OpenGL renderer for the solar system.

    Handles all rendering including:
    - Planets and sun with proper colors and sizes
    - Orbital paths
    - Trajectory lines
    - Star field background
    - UI overlays
    """

    def __init__(self, settings: RenderSettings = None):
        """
        Initialize the renderer.

        Args:
            settings: Render settings configuration
        """
        if not PYGAME_AVAILABLE or not OPENGL_AVAILABLE:
            raise ImportError(
                "PyGame and PyOpenGL are required for visualization. "
                "Install with: pip install pygame PyOpenGL PyOpenGL_accelerate"
            )

        self.settings = settings or RenderSettings()
        self.camera = Camera()

        # Display state
        self.display: Optional[pygame.Surface] = None
        self.clock: Optional[pygame.time.Clock] = None
        self.running = False

        # Rendering data
        self._sphere_list: Optional[int] = None
        self._ring_list: Optional[int] = None
        self._circle_list: Optional[int] = None
        self._star_list: Optional[int] = None

        # Scale factor for visualization
        self.distance_scale = 1e-9  # Convert meters to viewable units
        self.size_scale = 5e-7  # Scale for body sizes
        self.min_body_size = 0.05
        self.max_body_size = 0.8
        self.sun_size = 1.0

        # UI state
        self.selected_body: Optional[CelestialBody] = None
        self.hovered_body: Optional[CelestialBody] = None

        # Fonts
        self._font: Optional[pygame.font.Font] = None
        self._small_font: Optional[pygame.font.Font] = None

    def initialize(self) -> bool:
        """
        Initialize the rendering system.

        Returns:
            True if initialization successful
        """
        # Initialize pygame
        pygame.init()
        pygame.font.init()

        # Set up display
        flags = DOUBLEBUF | OPENGL
        if self.settings.fullscreen:
            flags |= FULLSCREEN

        if self.settings.antialiasing:
            pygame.display.gl_set_attribute(GL_MULTISAMPLEBUFFERS, 1)
            pygame.display.gl_set_attribute(GL_MULTISAMPLESAMPLES, 4)

        self.display = pygame.display.set_mode(
            (self.settings.window_width, self.settings.window_height),
            flags
        )
        pygame.display.set_caption("Solar System Simulation")

        self.clock = pygame.time.Clock()

        # Initialize fonts
        try:
            self._font = pygame.font.SysFont('Arial', 16)
            self._small_font = pygame.font.SysFont('Arial', 12)
        except Exception:
            self._font = pygame.font.Font(None, 16)
            self._small_font = pygame.font.Font(None, 12)

        # OpenGL setup
        self._setup_opengl()

        # Create display lists for common objects
        self._create_display_lists()

        # Generate star field
        self._generate_stars(3000)

        self.running = True
        return True

    def _setup_opengl(self):
        """Configure OpenGL state."""
        # Enable depth testing
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)

        # Enable blending for transparency
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # Enable smooth lines
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)

        # Enable point smoothing
        glEnable(GL_POINT_SMOOTH)
        glHint(GL_POINT_SMOOTH_HINT, GL_NICEST)

        # Set up lighting
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

        # Light at origin (sun)
        glLightfv(GL_LIGHT0, GL_POSITION, [0, 0, 0, 1])
        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.2, 0.2, 0.2, 1.0])
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [1.0, 1.0, 0.9, 1.0])
        glLightfv(GL_LIGHT0, GL_SPECULAR, [1.0, 1.0, 1.0, 1.0])

        # Normalize normals
        glEnable(GL_NORMALIZE)

        # Background color
        glClearColor(*self.settings.background_color)

        # Set up viewport
        glViewport(0, 0, self.settings.window_width, self.settings.window_height)

    def _create_display_lists(self):
        """Create OpenGL display lists for common objects."""
        # Sphere for planets
        self._sphere_list = glGenLists(1)
        glNewList(self._sphere_list, GL_COMPILE)
        self._draw_sphere(1.0, self.settings.planet_segments)
        glEndList()

        # Circle for orbits
        self._circle_list = glGenLists(1)
        glNewList(self._circle_list, GL_COMPILE)
        self._draw_circle(1.0, self.settings.orbit_segments)
        glEndList()

    def _draw_sphere(self, radius: float, segments: int):
        """Draw a unit sphere using immediate mode."""
        for i in range(segments):
            lat0 = math.pi * (-0.5 + float(i) / segments)
            z0 = math.sin(lat0)
            zr0 = math.cos(lat0)

            lat1 = math.pi * (-0.5 + float(i + 1) / segments)
            z1 = math.sin(lat1)
            zr1 = math.cos(lat1)

            glBegin(GL_QUAD_STRIP)
            for j in range(segments + 1):
                lng = 2 * math.pi * float(j) / segments
                x = math.cos(lng)
                y = math.sin(lng)

                glNormal3f(x * zr0, y * zr0, z0)
                glVertex3f(radius * x * zr0, radius * y * zr0, radius * z0)

                glNormal3f(x * zr1, y * zr1, z1)
                glVertex3f(radius * x * zr1, radius * y * zr1, radius * z1)
            glEnd()

    def _draw_circle(self, radius: float, segments: int):
        """Draw a circle in the XY plane."""
        glBegin(GL_LINE_LOOP)
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            glVertex3f(radius * math.cos(angle), 0, radius * math.sin(angle))
        glEnd()

    def _generate_stars(self, num_stars: int):
        """Generate a random star field."""
        self._star_list = glGenLists(1)
        glNewList(self._star_list, GL_COMPILE)

        glDisable(GL_LIGHTING)
        glPointSize(1.5)
        glBegin(GL_POINTS)

        np.random.seed(42)  # Consistent star field
        for _ in range(num_stars):
            # Random direction on sphere
            theta = np.random.uniform(0, 2 * math.pi)
            phi = np.arccos(2 * np.random.uniform() - 1)

            # Large distance
            r = 500

            x = r * math.sin(phi) * math.cos(theta)
            y = r * math.sin(phi) * math.sin(theta)
            z = r * math.cos(phi)

            # Random brightness
            brightness = np.random.uniform(0.3, 1.0)
            # Slight color variation
            r_color = brightness * np.random.uniform(0.9, 1.0)
            g_color = brightness * np.random.uniform(0.9, 1.0)
            b_color = brightness

            glColor3f(r_color, g_color, b_color)
            glVertex3f(x, y, z)

        glEnd()
        glEnable(GL_LIGHTING)
        glEndList()

    def begin_frame(self):
        """Begin a new frame."""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Set up projection
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()

        aspect = self.settings.window_width / self.settings.window_height
        gluPerspective(self.camera.fov, aspect, self.camera.near, self.camera.far)

        # Set up view
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        # Apply camera
        gluLookAt(
            *self.camera.position,
            *self.camera.target,
            *self.camera.up
        )

    def end_frame(self):
        """End current frame and swap buffers."""
        pygame.display.flip()
        self.clock.tick(60)  # Cap at 60 FPS

    def render_stars(self):
        """Render the star field background."""
        if self._star_list:
            glCallList(self._star_list)

    def render_body(
        self,
        body: CelestialBody,
        julian_date: float,
        highlight: bool = False
    ):
        """
        Render a celestial body.

        Args:
            body: The body to render
            julian_date: Current simulation time
            highlight: Whether to highlight (selected/hovered)
        """
        state = body.get_state_at_time(julian_date)
        position = state.position * self.distance_scale

        # Calculate visual size
        if body.body_type == BodyType.STAR:
            size = self.sun_size
        else:
            # Scale based on actual radius but with limits
            actual_size = body.radius * self.size_scale * 1e6
            size = np.clip(actual_size, self.min_body_size, self.max_body_size)

            # Make larger planets more visible
            if body.radius > 20000:  # Gas giants
                size = max(size, 0.15)

        glPushMatrix()
        glTranslatef(*position)

        # Set color
        color = body.color

        if body.body_type == BodyType.STAR:
            # Sun is emissive - disable lighting
            glDisable(GL_LIGHTING)
            glColor3f(*color)
        else:
            glEnable(GL_LIGHTING)
            glColor3f(*color)

        # Highlight effect
        if highlight:
            glColor3f(
                min(color[0] + 0.3, 1.0),
                min(color[1] + 0.3, 1.0),
                min(color[2] + 0.3, 1.0)
            )

        # Draw sphere
        glPushMatrix()
        glScalef(size, size, size)
        glCallList(self._sphere_list)
        glPopMatrix()

        # Draw rings for Saturn, etc.
        if hasattr(body, 'has_rings') and body.has_rings:
            self._render_rings(body, size)

        glPopMatrix()

        # Re-enable lighting
        glEnable(GL_LIGHTING)

    def _render_rings(self, body: CelestialBody, body_size: float):
        """Render planetary rings."""
        # Ring color (semi-transparent)
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)

        ring_inner = body_size * 1.4
        ring_outer = body_size * 2.3

        # Draw multiple ring bands
        glColor4f(0.8, 0.75, 0.6, 0.5)

        segments = 64
        glBegin(GL_QUAD_STRIP)
        for i in range(segments + 1):
            angle = 2 * math.pi * i / segments
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)

            glVertex3f(ring_inner * cos_a, 0, ring_inner * sin_a)
            glVertex3f(ring_outer * cos_a, 0, ring_outer * sin_a)
        glEnd()

        glEnable(GL_LIGHTING)

    def render_orbit(
        self,
        body: CelestialBody,
        julian_date: float,
        color: Tuple[float, float, float, float] = None
    ):
        """
        Render the orbital path of a body.

        Args:
            body: The body whose orbit to render
            julian_date: Current time for element calculation
            color: Optional override color (RGBA)
        """
        if body.orbital_elements is None:
            return

        # Get orbit points
        points = body.get_orbit_points(julian_date, self.settings.orbit_segments)
        points = points * self.distance_scale

        glDisable(GL_LIGHTING)
        glLineWidth(1.0)

        if color is None:
            # Use body color with reduced alpha
            body_color = body.color
            glColor4f(body_color[0] * 0.6, body_color[1] * 0.6, body_color[2] * 0.6, 0.4)
        else:
            glColor4f(*color)

        glBegin(GL_LINE_LOOP)
        for point in points:
            glVertex3f(*point)
        glEnd()

        glEnable(GL_LIGHTING)

    def render_trajectory(
        self,
        points: List[StateVector],
        color: Tuple[float, float, float, float] = (0.0, 1.0, 0.5, 0.8),
        line_width: float = 2.0
    ):
        """
        Render a spacecraft trajectory.

        Args:
            points: List of state vectors defining the trajectory
            color: Line color (RGBA)
            line_width: Width of the trajectory line
        """
        if len(points) < 2:
            return

        glDisable(GL_LIGHTING)
        glLineWidth(line_width)
        glColor4f(*color)

        glBegin(GL_LINE_STRIP)
        for state in points:
            pos = state.position * self.distance_scale
            glVertex3f(*pos)
        glEnd()

        glEnable(GL_LIGHTING)

    def render_grid(self, size: float = 10.0, divisions: int = 20):
        """Render a reference grid in the ecliptic plane."""
        if not self.settings.show_grid:
            return

        glDisable(GL_LIGHTING)
        glLineWidth(1.0)
        glColor4f(0.2, 0.2, 0.3, 0.3)

        step = size / divisions

        glBegin(GL_LINES)
        for i in range(-divisions, divisions + 1):
            # Lines parallel to X
            glVertex3f(-size, 0, i * step)
            glVertex3f(size, 0, i * step)

            # Lines parallel to Z
            glVertex3f(i * step, 0, -size)
            glVertex3f(i * step, 0, size)
        glEnd()

        glEnable(GL_LIGHTING)

    def render_axes(self, size: float = 2.0):
        """Render coordinate axes for reference."""
        if not self.settings.show_axes:
            return

        glDisable(GL_LIGHTING)
        glLineWidth(2.0)

        glBegin(GL_LINES)
        # X axis - red
        glColor3f(1, 0, 0)
        glVertex3f(0, 0, 0)
        glVertex3f(size, 0, 0)

        # Y axis - green
        glColor3f(0, 1, 0)
        glVertex3f(0, 0, 0)
        glVertex3f(0, size, 0)

        # Z axis - blue
        glColor3f(0, 0, 1)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 0, size)
        glEnd()

        glEnable(GL_LIGHTING)

    def render_label(
        self,
        text: str,
        position_3d: np.ndarray,
        color: Tuple[int, int, int] = (255, 255, 255),
        offset: Tuple[int, int] = (10, -10)
    ):
        """
        Render a text label at a 3D position.

        Args:
            text: Text to render
            position_3d: 3D world position
            color: Text color (RGB 0-255)
            offset: Pixel offset from projected position
        """
        if not self.settings.show_labels:
            return

        # Project 3D to 2D screen coordinates
        screen_pos = self._project_to_screen(position_3d)

        if screen_pos is None:
            return

        x, y = screen_pos
        x += offset[0]
        y += offset[1]

        # Render text
        self._render_text_2d(text, (x, y), color)

    def _project_to_screen(self, position_3d: np.ndarray) -> Optional[Tuple[int, int]]:
        """Project 3D position to 2D screen coordinates."""
        modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
        projection = glGetDoublev(GL_PROJECTION_MATRIX)
        viewport = glGetIntegerv(GL_VIEWPORT)

        try:
            x, y, z = gluProject(
                position_3d[0], position_3d[1], position_3d[2],
                modelview, projection, viewport
            )

            # Check if in front of camera
            if z < 0 or z > 1:
                return None

            # Flip Y for pygame coordinates
            return int(x), int(self.settings.window_height - y)
        except Exception:
            return None

    def _render_text_2d(
        self,
        text: str,
        position: Tuple[int, int],
        color: Tuple[int, int, int] = (255, 255, 255)
    ):
        """Render 2D text overlay."""
        # Switch to orthographic projection for 2D
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.settings.window_width, self.settings.window_height, 0, -1, 1)

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        glDisable(GL_LIGHTING)
        glDisable(GL_DEPTH_TEST)

        # Render text to surface
        text_surface = self._font.render(text, True, color)
        text_data = pygame.image.tostring(text_surface, "RGBA", True)
        width, height = text_surface.get_size()

        # Draw as texture
        glRasterPos2i(position[0], position[1])
        glDrawPixels(width, height, GL_RGBA, GL_UNSIGNED_BYTE, text_data)

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)

        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()

    def render_info_panel(
        self,
        info: Dict[str, Any],
        position: Tuple[int, int] = (20, 20)
    ):
        """Render an information panel overlay."""
        x, y = position
        line_height = 20

        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.settings.window_width, self.settings.window_height, 0, -1, 1)

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        glDisable(GL_LIGHTING)
        glDisable(GL_DEPTH_TEST)

        # Draw semi-transparent background
        glEnable(GL_BLEND)
        glColor4f(0.0, 0.0, 0.0, 0.7)

        max_width = 300
        height = (len(info) + 1) * line_height + 10

        glBegin(GL_QUADS)
        glVertex2f(x - 5, y - 5)
        glVertex2f(x + max_width, y - 5)
        glVertex2f(x + max_width, y + height)
        glVertex2f(x - 5, y + height)
        glEnd()

        # Draw text
        current_y = y
        for key, value in info.items():
            text = f"{key}: {value}"
            text_surface = self._small_font.render(text, True, (220, 220, 220))
            text_data = pygame.image.tostring(text_surface, "RGBA", True)
            w, h = text_surface.get_size()

            glRasterPos2i(x, current_y + h)
            glDrawPixels(w, h, GL_RGBA, GL_UNSIGNED_BYTE, text_data)

            current_y += line_height

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)

        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()

    def render_status_bar(self, text: str):
        """Render status bar at bottom of screen."""
        y = self.settings.window_height - 30

        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.settings.window_width, self.settings.window_height, 0, -1, 1)

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        glDisable(GL_LIGHTING)
        glDisable(GL_DEPTH_TEST)

        # Background
        glEnable(GL_BLEND)
        glColor4f(0.0, 0.0, 0.0, 0.7)

        glBegin(GL_QUADS)
        glVertex2f(0, y - 5)
        glVertex2f(self.settings.window_width, y - 5)
        glVertex2f(self.settings.window_width, self.settings.window_height)
        glVertex2f(0, self.settings.window_height)
        glEnd()

        # Text
        text_surface = self._font.render(text, True, (200, 200, 200))
        text_data = pygame.image.tostring(text_surface, "RGBA", True)
        w, h = text_surface.get_size()

        glRasterPos2i(10, y + h)
        glDrawPixels(w, h, GL_RGBA, GL_UNSIGNED_BYTE, text_data)

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)

        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()

    def render_help_overlay(self, controls: List[Tuple[str, str]]):
        """Render help overlay with control instructions."""
        x = self.settings.window_width - 250
        y = 20
        line_height = 18

        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.settings.window_width, self.settings.window_height, 0, -1, 1)

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        glDisable(GL_LIGHTING)
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)

        # Background
        glColor4f(0.0, 0.0, 0.0, 0.7)
        height = len(controls) * line_height + 30

        glBegin(GL_QUADS)
        glVertex2f(x - 10, y - 10)
        glVertex2f(self.settings.window_width - 10, y - 10)
        glVertex2f(self.settings.window_width - 10, y + height)
        glVertex2f(x - 10, y + height)
        glEnd()

        # Title
        title_surface = self._font.render("Controls", True, (255, 255, 100))
        title_data = pygame.image.tostring(title_surface, "RGBA", True)
        w, h = title_surface.get_size()
        glRasterPos2i(x, y + h)
        glDrawPixels(w, h, GL_RGBA, GL_UNSIGNED_BYTE, title_data)

        current_y = y + 25
        for key, action in controls:
            text = f"{key}: {action}"
            text_surface = self._small_font.render(text, True, (180, 180, 180))
            text_data = pygame.image.tostring(text_surface, "RGBA", True)
            w, h = text_surface.get_size()

            glRasterPos2i(x, current_y + h)
            glDrawPixels(w, h, GL_RGBA, GL_UNSIGNED_BYTE, text_data)
            current_y += line_height

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)

        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()

    def render_date_picker(self, picker_data: Dict[str, Any]):
        """
        Render interactive date picker widget.

        Args:
            picker_data: Dictionary with picker state from DateTimePicker.get_render_data()
        """
        if not picker_data.get("visible", False):
            return

        x, y = picker_data.get("position", (20, 100))
        date = picker_data.get("date")
        editing_field = picker_data.get("editing_field")
        input_buffer = picker_data.get("input_buffer", "")

        if not date:
            return

        line_height = 22
        width = 300

        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.settings.window_width, self.settings.window_height, 0, -1, 1)

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        glDisable(GL_LIGHTING)
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)

        # Background
        glColor4f(0.1, 0.1, 0.15, 0.9)
        height = 80

        glBegin(GL_QUADS)
        glVertex2f(x - 5, y - 5)
        glVertex2f(x + width, y - 5)
        glVertex2f(x + width, y + height)
        glVertex2f(x - 5, y + height)
        glEnd()

        # Title
        title_surface = self._font.render("Jump to Date", True, (255, 255, 100))
        title_data = pygame.image.tostring(title_surface, "RGBA", True)
        w, h = title_surface.get_size()
        glRasterPos2i(x, y + h)
        glDrawPixels(w, h, GL_RGBA, GL_UNSIGNED_BYTE, title_data)

        # Date display
        current_y = y + 28
        date_str = date.strftime("%Y-%m-%d %H:%M UTC")
        text_surface = self._font.render(date_str, True, (200, 240, 255))
        text_data = pygame.image.tostring(text_surface, "RGBA", True)
        w, h = text_surface.get_size()
        glRasterPos2i(x, current_y + h)
        glDrawPixels(w, h, GL_RGBA, GL_UNSIGNED_BYTE, text_data)

        # Instructions
        current_y += line_height
        info_text = "Press [ / ] to jump by day, E for events"
        info_surface = self._small_font.render(info_text, True, (150, 150, 150))
        info_data = pygame.image.tostring(info_surface, "RGBA", True)
        w, h = info_surface.get_size()
        glRasterPos2i(x, current_y + h)
        glDrawPixels(w, h, GL_RGBA, GL_UNSIGNED_BYTE, info_data)

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)

        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()

    def render_time_navigation_panel(self, nav_data: Dict[str, Any]):
        """
        Render time navigation buttons panel.

        Args:
            nav_data: Dictionary with panel state from TimeNavigationPanel.get_render_data()
        """
        if not nav_data.get("visible", False):
            return

        x, y = nav_data.get("position", (20, 60))
        buttons = nav_data.get("buttons", [])

        if not buttons:
            return

        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.settings.window_width, self.settings.window_height, 0, -1, 1)

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        glDisable(GL_LIGHTING)
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)

        # Just display text instructions (button rendering would need more complex UI)
        info_text = "Time Navigation: [ ] keys for day, or press N to hide"
        text_surface = self._small_font.render(info_text, True, (180, 200, 220))
        text_data = pygame.image.tostring(text_surface, "RGBA", True)
        w, h = text_surface.get_size()

        # Background
        glColor4f(0.0, 0.1, 0.15, 0.8)
        glBegin(GL_QUADS)
        glVertex2f(x - 5, y - 5)
        glVertex2f(x + w + 10, y - 5)
        glVertex2f(x + w + 10, y + h + 10)
        glVertex2f(x - 5, y + h + 10)
        glEnd()

        glRasterPos2i(x, y + h)
        glDrawPixels(w, h, GL_RGBA, GL_UNSIGNED_BYTE, text_data)

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)

        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()

    def render_educational_panel(self, edu_data: Dict[str, Any]):
        """
        Render educational information panel about selected body.

        Args:
            edu_data: Dictionary with panel state from EducationalInfoPanel.get_render_data()
        """
        if not edu_data.get("visible", False):
            return

        x, y = edu_data.get("position", (20, 20))
        width = edu_data.get("width", 350)
        body_name = edu_data.get("body_name")
        properties = edu_data.get("properties", {})
        current_fact = edu_data.get("current_fact")

        if not body_name:
            return

        line_height = 18

        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.settings.window_width, self.settings.window_height, 0, -1, 1)

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        glDisable(GL_LIGHTING)
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)

        # Calculate height
        num_lines = 2 + len(properties) + (3 if current_fact else 0)
        height = num_lines * line_height + 20

        # Background
        glColor4f(0.05, 0.1, 0.15, 0.85)
        glBegin(GL_QUADS)
        glVertex2f(x - 5, y - 5)
        glVertex2f(x + width, y - 5)
        glVertex2f(x + width, y + height)
        glVertex2f(x - 5, y + height)
        glEnd()

        # Border
        glColor4f(0.3, 0.5, 0.7, 0.6)
        glLineWidth(2)
        glBegin(GL_LINE_LOOP)
        glVertex2f(x - 5, y - 5)
        glVertex2f(x + width, y - 5)
        glVertex2f(x + width, y + height)
        glVertex2f(x - 5, y + height)
        glEnd()

        # Title
        current_y = y
        title_surface = self._font.render(body_name, True, (100, 200, 255))
        title_data = pygame.image.tostring(title_surface, "RGBA", True)
        w, h = title_surface.get_size()
        glRasterPos2i(x, current_y + h)
        glDrawPixels(w, h, GL_RGBA, GL_UNSIGNED_BYTE, title_data)
        current_y += line_height + 5

        # Properties
        for key, value in properties.items():
            text = f"{key}: {value}"
            # Wrap text if too long
            if len(text) > 45:
                text = text[:42] + "..."

            text_surface = self._small_font.render(text, True, (220, 220, 220))
            text_data = pygame.image.tostring(text_surface, "RGBA", True)
            w, h = text_surface.get_size()
            glRasterPos2i(x, current_y + h)
            glDrawPixels(w, h, GL_RGBA, GL_UNSIGNED_BYTE, text_data)
            current_y += line_height

        # Fun fact
        if current_fact:
            current_y += 5
            fact_title = self._small_font.render("Did you know?", True, (255, 255, 100))
            fact_data = pygame.image.tostring(fact_title, "RGBA", True)
            w, h = fact_title.get_size()
            glRasterPos2i(x, current_y + h)
            glDrawPixels(w, h, GL_RGBA, GL_UNSIGNED_BYTE, fact_data)
            current_y += line_height

            # Word wrap the fact
            words = current_fact.split()
            line = ""
            for word in words:
                test_line = f"{line} {word}".strip()
                if len(test_line) > 45:
                    fact_surface = self._small_font.render(line, True, (180, 220, 180))
                    fact_data = pygame.image.tostring(fact_surface, "RGBA", True)
                    w, h = fact_surface.get_size()
                    glRasterPos2i(x, current_y + h)
                    glDrawPixels(w, h, GL_RGBA, GL_UNSIGNED_BYTE, fact_data)
                    current_y += line_height
                    line = word
                else:
                    line = test_line

            if line:
                fact_surface = self._small_font.render(line, True, (180, 220, 180))
                fact_data = pygame.image.tostring(fact_surface, "RGBA", True)
                w, h = fact_surface.get_size()
                glRasterPos2i(x, current_y + h)
                glDrawPixels(w, h, GL_RGBA, GL_UNSIGNED_BYTE, fact_data)

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)

        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()

    def render_historical_events(self, events_data: Dict[str, Any]):
        """
        Render historical events panel.

        Args:
            events_data: Dictionary with events from HistoricalEventsPanel.get_render_data()
        """
        if not events_data.get("visible", False):
            return

        x, y = events_data.get("position", (20, 450))
        width = events_data.get("width", 400)
        events = events_data.get("events", [])

        if not events:
            return

        line_height = 18

        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.settings.window_width, self.settings.window_height, 0, -1, 1)

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        glDisable(GL_LIGHTING)
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)

        # Calculate height based on events
        num_lines = 2 + sum(3 for _ in events)  # Title + each event (date, title, desc)
        height = num_lines * line_height + 20

        # Background
        glColor4f(0.15, 0.05, 0.1, 0.9)
        glBegin(GL_QUADS)
        glVertex2f(x - 5, y - 5)
        glVertex2f(x + width, y - 5)
        glVertex2f(x + width, y + height)
        glVertex2f(x - 5, y + height)
        glEnd()

        # Border
        glColor4f(0.7, 0.3, 0.5, 0.6)
        glLineWidth(2)
        glBegin(GL_LINE_LOOP)
        glVertex2f(x - 5, y - 5)
        glVertex2f(x + width, y - 5)
        glVertex2f(x + width, y + height)
        glVertex2f(x - 5, y + height)
        glEnd()

        # Title
        current_y = y
        title_surface = self._font.render("Historical Events", True, (255, 200, 100))
        title_data = pygame.image.tostring(title_surface, "RGBA", True)
        w, h = title_surface.get_size()
        glRasterPos2i(x, current_y + h)
        glDrawPixels(w, h, GL_RGBA, GL_UNSIGNED_BYTE, title_data)
        current_y += line_height + 5

        # Events
        for event in events[:5]:  # Limit to 5 events
            # Event date and title
            event_title = f"{event.get('year', '')}: {event.get('title', 'Unknown')}"
            if len(event_title) > 50:
                event_title = event_title[:47] + "..."

            title_surface = self._small_font.render(event_title, True, (255, 255, 100))
            title_data = pygame.image.tostring(title_surface, "RGBA", True)
            w, h = title_surface.get_size()
            glRasterPos2i(x, current_y + h)
            glDrawPixels(w, h, GL_RGBA, GL_UNSIGNED_BYTE, title_data)
            current_y += line_height

            # Description (wrapped)
            description = event.get('description', '')
            if len(description) > 55:
                description = description[:52] + "..."

            desc_surface = self._small_font.render(description, True, (200, 200, 200))
            desc_data = pygame.image.tostring(desc_surface, "RGBA", True)
            w, h = desc_surface.get_size()
            glRasterPos2i(x + 10, current_y + h)
            glDrawPixels(w, h, GL_RGBA, GL_UNSIGNED_BYTE, desc_data)
            current_y += line_height + 3

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)

        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()

    def cleanup(self):
        """Clean up OpenGL resources."""
        if self._sphere_list:
            glDeleteLists(self._sphere_list, 1)
        if self._circle_list:
            glDeleteLists(self._circle_list, 1)
        if self._star_list:
            glDeleteLists(self._star_list, 1)

        pygame.quit()

    def get_fps(self) -> float:
        """Get current frames per second."""
        return self.clock.get_fps() if self.clock else 0.0
