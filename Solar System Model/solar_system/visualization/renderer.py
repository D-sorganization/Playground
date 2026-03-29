"""3D Renderer
===============

OpenGL-based renderer for the solar system visualization.
Provides high-quality rendering of planets, orbits, trajectories,
and UI elements.
"""

from __future__ import annotations

import math
import pathlib
from dataclasses import dataclass
from typing import Any

import numpy as np

try:
    import pygame
    from pygame.locals import (
        DOUBLEBUF,
        FULLSCREEN,
        GL_MULTISAMPLEBUFFERS,
        GL_MULTISAMPLESAMPLES,
        OPENGL,
    )

    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

try:
    from OpenGL.GL import (
        GL_AMBIENT,
        GL_AMBIENT_AND_DIFFUSE,
        GL_BLEND,
        GL_COLOR_BUFFER_BIT,
        GL_COLOR_MATERIAL,
        GL_COMPILE,
        GL_DEPTH_BUFFER_BIT,
        GL_DEPTH_TEST,
        GL_DIFFUSE,
        GL_FRAGMENT_SHADER,
        GL_FRONT_AND_BACK,
        GL_LEQUAL,
        GL_LIGHT0,
        GL_LIGHTING,
        GL_LINE_LOOP,
        GL_LINE_SMOOTH,
        GL_LINE_SMOOTH_HINT,
        GL_LINE_STRIP,
        GL_LINES,
        GL_MODELVIEW,
        GL_MODELVIEW_MATRIX,
        GL_NICEST,
        GL_NORMALIZE,
        GL_ONE_MINUS_SRC_ALPHA,
        GL_POINT_SMOOTH,
        GL_POINT_SMOOTH_HINT,
        GL_POINTS,
        GL_POSITION,
        GL_PROJECTION,
        GL_PROJECTION_MATRIX,
        GL_QUAD_STRIP,
        GL_QUADS,
        GL_RGBA,
        GL_SPECULAR,
        GL_SRC_ALPHA,
        GL_TEXTURE_2D,
        GL_UNSIGNED_BYTE,
        GL_VERTEX_SHADER,
        GL_VIEWPORT,
        glAttachShader,
        glBegin,
        glBlendFunc,
        glCallList,
        glClear,
        glClearColor,
        glColor3f,
        glColor4f,
        glColorMaterial,
        glCompileShader,
        glCreateProgram,
        glCreateShader,
        glDeleteLists,
        glDepthFunc,
        glDisable,
        glDrawPixels,
        glEnable,
        glEnd,
        glEndList,
        glGenLists,
        glGetDoublev,
        glGetIntegerv,
        glHint,
        glLightfv,
        glLineWidth,
        glLinkProgram,
        glLoadIdentity,
        glMatrixMode,
        glNewList,
        glNormal3f,
        glOrtho,
        glPointSize,
        glPopMatrix,
        glPushMatrix,
        glRasterPos2i,
        glScalef,
        glShaderSource,
        glTexCoord2f,
        glTranslatef,
        glUseProgram,
        glVertex2f,
        glVertex3f,
        glViewport,
    )
    from OpenGL.GLU import (
        gluLookAt,
        gluPerspective,
        gluProject,
    )

    OPENGL_AVAILABLE = True
except ImportError:
    OPENGL_AVAILABLE = False

from ..core.celestial_body import BodyType, CelestialBody, StateVector
from ..core.constants import AU
from ..data.star_catalog import iter_catalog
from .camera import Camera, CameraState
from .starfield import build_star_vertices, point_size_from_magnitude
from .textures import TextureManager
from .ui_panels import UIPanelRendererMixin


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
    use_textures: bool = True
    use_shaders: bool = True
    stereo_view: bool = False
    orbit_segments: int = 360
    planet_segments: int = 32
    background_color: tuple[float, float, float, float] = (0.02, 0.02, 0.05, 1.0)


class Renderer(UIPanelRendererMixin):
    """
    OpenGL renderer for the solar system.

    Handles all rendering including:
    - Planets and sun with proper colors and sizes
    - Orbital paths
    - Trajectory lines
    - Star field background
    - UI overlays (via UIPanelRendererMixin)
    """

    def __init__(self, settings: RenderSettings | None = None):
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
        self.display: pygame.Surface | None = None
        self.clock: pygame.time.Clock | None = None
        self.running = False

        # Rendering data
        self._sphere_list: int | None = None
        self._ring_list: int | None = None
        self._circle_list: int | None = None
        self._star_list: int | None = None
        self.star_vertices = []

        # Scale factor for visualization
        self.distance_scale = 1e-9  # Convert meters to viewable units
        self.size_scale = 5e-7  # Scale for body sizes
        self.min_body_size = 0.05
        self.max_body_size = 0.8
        self.sun_size = 1.0

        # UI state
        self.selected_body: CelestialBody | None = None
        self.hovered_body: CelestialBody | None = None

        # Textures and shaders
        assets_root = pathlib.Path(__file__).resolve().parent.parent
        self.texture_manager = TextureManager(assets_root, auto_download=True)
        self._shaders_enabled = False
        self._shader_program: int | None = None

        # Fonts
        self._font: pygame.font.Font | None = None
        self._small_font: pygame.font.Font | None = None

        # Label collision
        self.drawn_labels: list[pygame.Rect] = []

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
            (self.settings.window_width, self.settings.window_height), flags
        )
        pygame.display.set_caption("Solar System Simulation")

        self.clock = pygame.time.Clock()

        # Initialize fonts
        # Initialize fonts
        try:
            self._font = pygame.font.SysFont("segoeui", 28, bold=True)
            self._small_font = pygame.font.SysFont("segoeui", 20)
            self._title_font = pygame.font.SysFont("segoeui", 32, bold=True)
        except (OSError, RuntimeError):
            self._font = pygame.font.Font(None, 28)
            self._small_font = pygame.font.Font(None, 20)
            self._title_font = pygame.font.Font(None, 32)

        # OpenGL setup
        self._setup_opengl()

        # Create display lists for common objects
        self._create_display_lists()

        # Generate star field from catalog
        self._generate_stars()

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

        # Modern shading pipeline
        self._setup_shaders()

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

    def _setup_shaders(self):
        """Compile a minimal Lambert shader for per-pixel lighting."""

        if not self.settings.use_shaders:
            return

        try:
            vertex_shader = glCreateShader(GL_VERTEX_SHADER)
            fragment_shader = glCreateShader(GL_FRAGMENT_SHADER)

            vertex_src = """
            varying vec3 vNormal;
            varying vec3 vPosition;
            void main() {
                vNormal = normalize(gl_NormalMatrix * gl_Normal);
                vPosition = vec3(gl_ModelViewMatrix * gl_Vertex);
                gl_Position = gl_ModelViewProjectionMatrix * gl_Vertex;
                gl_TexCoord[0] = gl_MultiTexCoord0;
            }
            """

            fragment_src = """
            varying vec3 vNormal;
            varying vec3 vPosition;
            void main() {
                vec3 lightDir = normalize(vec3(0.0, 0.0, 0.0) - vPosition);
                float diffuse = max(dot(vNormal, lightDir), 0.2);
                vec4 baseColor = gl_Color;
                if (gl_TexCoord[0].s > 0.0) {
                    baseColor *= texture2D(gl_Texture_2D, gl_TexCoord[0].st);
                }
                gl_FragColor = vec4(baseColor.rgb * diffuse, baseColor.a);
            }
            """

            glShaderSource(vertex_shader, vertex_src)
            glCompileShader(vertex_shader)
            glShaderSource(fragment_shader, fragment_src)
            glCompileShader(fragment_shader)

            program = glCreateProgram()
            glAttachShader(program, vertex_shader)
            glAttachShader(program, fragment_shader)
            glLinkProgram(program)
            glUseProgram(program)
            self._shader_program = program
            self._shaders_enabled = True
        except (RuntimeError, ValueError, OSError):
            self._shader_program = None
            self._shaders_enabled = False

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

                u = float(j) / segments
                v0 = 0.5 + (lat0 / math.pi)
                v1 = 0.5 + (lat1 / math.pi)

                glTexCoord2f(u, v0)
                glNormal3f(x * zr0, y * zr0, z0)
                glVertex3f(radius * x * zr0, radius * y * zr0, radius * z0)

                glTexCoord2f(u, v1)
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

    def _generate_stars(self):
        """Build a star field from the curated catalog for accurate sky matches."""

        self.star_vertices = build_star_vertices(iter_catalog())
        # Sort by magnitude for efficient state switching if we were using variable
        # point sizes
        # However, to be maximally efficient with glBegin/glEnd as requested, we
        # should batch them.
        # But point_size_from_magnitude returns variable sizes.
        # We will group stars by size bin to minimize state changes.

        # Group stars by integer point size for batching
        stars_by_size = {}
        for star in self.star_vertices:
            size = int(point_size_from_magnitude(star.magnitude))
            if size not in stars_by_size:
                stars_by_size[size] = []
            stars_by_size[size].append(star)

        self._star_list = glGenLists(1)
        glNewList(self._star_list, GL_COMPILE)
        glDisable(GL_LIGHTING)

        for size, stars in stars_by_size.items():
            glPointSize(float(size))
            glBegin(GL_POINTS)
            for star in stars:
                glColor3f(*star.color)
                glVertex3f(*star.position)
            glEnd()

        glEnable(GL_LIGHTING)
        glEndList()

    def begin_frame(self, camera_state: CameraState | None = None, clear: bool = True):
        """Begin a new frame."""
        self.drawn_labels.clear()
        if clear:
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Set up projection
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()

        active_camera = camera_state or self.camera
        aspect = self.settings.window_width / self.settings.window_height
        gluPerspective(active_camera.fov, aspect, active_camera.near, active_camera.far)

        # Set up view
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        # Apply camera
        gluLookAt(*active_camera.position, *active_camera.target, *active_camera.up)

    def end_frame(self):
        """End current frame and swap buffers."""
        pygame.display.flip()
        self.clock.tick(60)  # Cap at 60 FPS

    def render_stars(self):
        """Render the star field background."""
        if self._star_list:
            glCallList(self._star_list)

    def render_body(self, body: CelestialBody, julian_date: float, highlight: bool = False):
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
                min(color[2] + 0.3, 1.0),
            )

        texturing_active = False
        if self.settings.use_textures:
            texturing_active = self.texture_manager.bind(body.name)
            if texturing_active:
                glEnable(GL_TEXTURE_2D)

        # Draw sphere
        glPushMatrix()
        glScalef(size, size, size)
        glCallList(self._sphere_list)
        glPopMatrix()

        # Draw rings for Saturn, etc.
        if hasattr(body, "has_rings") and body.has_rings:
            self._render_rings(body, size)

        glPopMatrix()

        # Re-enable lighting
        glEnable(GL_LIGHTING)
        if texturing_active:
            glDisable(GL_TEXTURE_2D)

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
        color: tuple[float, float, float, float] | None = None,
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
        points: list[StateVector],
        color: tuple[float, float, float, float] = (0.0, 1.0, 0.5, 0.8),
        line_width: float = 2.0,
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

    def render_asteroid_belt(self, belt_points_au: np.ndarray):
        """Render a faint asteroid belt based on pre-generated particle positions."""

        if belt_points_au.size == 0:
            return

        glDisable(GL_LIGHTING)
        glPointSize(1.2)
        glColor4f(0.7, 0.7, 0.7, 0.35)

        glBegin(GL_POINTS)
        for point in belt_points_au:
            scaled = point * AU * self.distance_scale
            glVertex3f(*scaled)
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
        color: tuple[int, int, int] = (255, 255, 255),
        offset: tuple[int, int] = (10, -10),
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

    def _project_to_screen(self, position_3d: np.ndarray) -> tuple[int, int] | None:
        """Project 3D position to 2D screen coordinates."""
        modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
        projection = glGetDoublev(GL_PROJECTION_MATRIX)
        viewport = glGetIntegerv(GL_VIEWPORT)

        try:
            x, y, z = gluProject(
                position_3d[0],
                position_3d[1],
                position_3d[2],
                modelview,
                projection,
                viewport,
            )

            # Check if in front of camera
            if z < 0 or z > 1:
                return None

            # Flip Y for pygame coordinates
            return int(x), int(self.settings.window_height - y)
        except (ValueError, ZeroDivisionError, OverflowError):
            return None

    def _render_text_2d(
        self,
        text: str,
        position: tuple[int, int],
        color: tuple[int, int, int] = (255, 255, 255),
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

        # Check for overlaps and adjust
        rect = pygame.Rect(position[0], position[1], width, height)
        original_y = rect.y

        # Try a few offsets if overlapping
        offsets = [0, height + 2, -(height + 2), (height + 2) * 2]

        final_pos = position
        found_spot = False

        for offset in offsets:
            test_rect = rect.copy()
            test_rect.y = original_y + offset

            # constrain to screen
            if test_rect.top < 0 or test_rect.bottom > self.settings.window_height:
                continue

            collision = False
            for other_rect in self.drawn_labels:
                if test_rect.colliderect(other_rect):
                    collision = True
                    break

            if not collision:
                rect = test_rect
                final_pos = (rect.x, rect.y)
                found_spot = True
                break

        if not found_spot:
            # If we simply can't find a spot, draw it anyway at original position
            # This ensures labels are never missing, even if overlapping
            final_pos = position

        self.drawn_labels.append(rect)

        # Draw as texture
        glRasterPos2i(final_pos[0], final_pos[1])
        glDrawPixels(width, height, GL_RGBA, GL_UNSIGNED_BYTE, text_data)

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)

        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()

    # UI panel methods (render_info_panel, render_status_bar, render_help_overlay,
    # render_date_picker, render_time_navigation_panel, render_educational_panel,
    # render_historical_events, render_immersion_checklist) are provided by
    # UIPanelRendererMixin in ui_panels.py

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

    # Additional UI panel methods (render_settings_panel, render_nav_mode_panel,
    # render_sidebar, render_unified_controls) are provided by
    # UIPanelRendererMixin in ui_panels.py
