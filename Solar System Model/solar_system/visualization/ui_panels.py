"""UI Panel Rendering
====================

Extracted mixin providing all 2D overlay panel rendering methods
for the solar system visualization.  Keeps the core ``Renderer``
class focused on 3D scene rendering.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

try:
    import pygame

    from OpenGL.GL import (
        GL_BLEND,
        GL_DEPTH_TEST,
        GL_LIGHTING,
        GL_LINE_LOOP,
        GL_LINES,
        GL_MODELVIEW,
        GL_PROJECTION,
        GL_QUADS,
        GL_RGBA,
        GL_UNSIGNED_BYTE,
        glBegin,
        glColor4f,
        glDisable,
        glDrawPixels,
        glEnable,
        glEnd,
        glLineWidth,
        glLoadIdentity,
        glMatrixMode,
        glOrtho,
        glPopMatrix,
        glPushMatrix,
        glRasterPos2i,
        glVertex2f,
    )

    _GL_AVAILABLE = True
except ImportError:
    _GL_AVAILABLE = False

if TYPE_CHECKING:
    from .renderer import RenderSettings


class UIPanelRendererMixin:
    """Mixin providing 2D overlay panel rendering methods.

    Requires the host class to expose:
    * ``settings: RenderSettings``
    * ``_font`` / ``_small_font`` – pygame Font objects
    """

    settings: RenderSettings
    _font: Any
    _small_font: Any

    # ------------------------------------------------------------------
    # Info panel
    # ------------------------------------------------------------------

    def render_info_panel(self, info: dict[str, Any], position: tuple[int, int] = (20, 20)):
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

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Help overlay
    # ------------------------------------------------------------------

    def render_help_overlay(self, help_data: dict[str, Any]):
        """Render help overlay with control instructions."""
        if not help_data.get("visible", False):
            return

        controls = help_data.get("controls", [])
        if not controls:
            return

        x, y = help_data.get("position") or (self.settings.window_width - 350, 20)
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
        glEnable(GL_BLEND)

        # Background with border
        glColor4f(0.0, 0.0, 0.0, 0.85)
        height = len(controls) * line_height + 40

        glBegin(GL_QUADS)
        glVertex2f(x - 15, y - 15)
        glVertex2f(self.settings.window_width - 10, y - 15)
        glVertex2f(self.settings.window_width - 10, y + height)
        glVertex2f(x - 15, y + height)
        glEnd()

        # Border
        glLineWidth(2.0)
        glColor4f(0.3, 0.5, 0.7, 0.8)
        glBegin(GL_LINE_LOOP)
        glVertex2f(x - 15, y - 15)
        glVertex2f(self.settings.window_width - 10, y - 15)
        glVertex2f(self.settings.window_width - 10, y + height)
        glVertex2f(x - 15, y + height)
        glEnd()

        # Title
        title_surface = self._font.render("CONTROLS (Press H to hide)", True, (100, 200, 255))
        title_data = pygame.image.tostring(title_surface, "RGBA", True)
        w, h = title_surface.get_size()
        glRasterPos2i(x, y + h)
        glDrawPixels(w, h, GL_RGBA, GL_UNSIGNED_BYTE, title_data)

        current_y = y + 30
        for key, action in controls:
            # Section headers (MOUSE:, KEYBOARD:)
            if action == "":
                if key:  # Section header
                    text_surface = self._font.render(key, True, (255, 200, 100))
                else:  # Empty line for spacing
                    current_y += line_height // 2
                    continue
            else:
                # Regular control line
                if key.strip():  # Has a key
                    text = f"{key}: {action}"
                    text_surface = self._small_font.render(text, True, (220, 220, 220))
                else:  # No key, just action
                    text_surface = self._small_font.render(action, True, (180, 180, 180))

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

    # ------------------------------------------------------------------
    # Date picker
    # ------------------------------------------------------------------

    def render_date_picker(self, picker_data: dict[str, Any]):
        """Render interactive date picker widget.

        Args:
            picker_data: Dictionary with picker state from
                DateTimePicker.get_render_data()
        """
        if not picker_data.get("visible", False):
            return

        x, y = picker_data.get("position", (20, 100))
        date = picker_data.get("date")

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

    # ------------------------------------------------------------------
    # Time navigation panel
    # ------------------------------------------------------------------

    def render_time_navigation_panel(self, nav_data: dict[str, Any]):
        """Render time navigation buttons panel.

        Args:
            nav_data: Dictionary with panel state from
                TimeNavigationPanel.get_render_data()
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

    # ------------------------------------------------------------------
    # Educational panel
    # ------------------------------------------------------------------

    def render_educational_panel(self, edu_data: dict[str, Any]):
        """Render educational information panel about selected body.

        Args:
            edu_data: Dictionary with panel state from
                EducationalInfoPanel.get_render_data()
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

    # ------------------------------------------------------------------
    # Historical events panel
    # ------------------------------------------------------------------

    def render_historical_events(self, events_data: dict[str, Any]):
        """Render historical events panel.

        Args:
            events_data: Dictionary with events from
                HistoricalEventsPanel.get_render_data()
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
            description = event.get("description", "")
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

    # ------------------------------------------------------------------
    # Immersion checklist
    # ------------------------------------------------------------------

    def render_immersion_checklist(self, checklist_data: dict[str, Any]):
        """Render the immersive learning checklist."""
        if not checklist_data.get("visible", False):
            return

        tasks = checklist_data.get("tasks", [])
        if not tasks:
            return

        x, y = checklist_data.get("position", (20, 240))
        width = checklist_data.get("width", 360)
        completed, total = checklist_data.get("progress", (0, len(tasks)))
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

        num_lines = 2 + len(tasks) * 2
        height = num_lines * line_height + 20

        glColor4f(0.08, 0.12, 0.16, 0.88)
        glBegin(GL_QUADS)
        glVertex2f(x - 5, y - 5)
        glVertex2f(x + width, y - 5)
        glVertex2f(x + width, y + height)
        glVertex2f(x - 5, y + height)
        glEnd()

        glColor4f(0.35, 0.55, 0.75, 0.65)
        glLineWidth(2)
        glBegin(GL_LINE_LOOP)
        glVertex2f(x - 5, y - 5)
        glVertex2f(x + width, y - 5)
        glVertex2f(x + width, y + height)
        glVertex2f(x - 5, y + height)
        glEnd()

        current_y = y
        title = f"Immersion Guide ({completed}/{total})"
        title_surface = self._font.render(title, True, (160, 230, 255))
        title_data = pygame.image.tostring(title_surface, "RGBA", True)
        w, h = title_surface.get_size()
        glRasterPos2i(x, current_y + h)
        glDrawPixels(w, h, GL_RGBA, GL_UNSIGNED_BYTE, title_data)
        current_y += line_height + 4

        for task in tasks:
            marker = "\u2713" if task.get("completed") else "\u2022"
            marker_color = (140, 220, 170) if task.get("completed") else (240, 210, 160)
            text_color = (200, 220, 240) if task.get("completed") else (230, 230, 230)

            title_text = f"{marker} {task.get('title', '')}"
            title_surface = self._small_font.render(title_text, True, marker_color)
            title_data = pygame.image.tostring(title_surface, "RGBA", True)
            w, h = title_surface.get_size()
            glRasterPos2i(x, current_y + h)
            glDrawPixels(w, h, GL_RGBA, GL_UNSIGNED_BYTE, title_data)
            current_y += line_height

            description = task.get("description", "")
            desc_surface = self._small_font.render(description, True, text_color)
            desc_data = pygame.image.tostring(desc_surface, "RGBA", True)
            w, h = desc_surface.get_size()
            glRasterPos2i(x + 14, current_y + h)
            glDrawPixels(w, h, GL_RGBA, GL_UNSIGNED_BYTE, desc_data)
            current_y += line_height

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)

        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()

    # ------------------------------------------------------------------
    # Settings panel
    # ------------------------------------------------------------------

    def render_settings_panel(self, settings_data: dict[str, Any]):
        """Render the settings panel."""
        if not settings_data.get("visible", False):
            return

        x, y = settings_data.get("position", (20, 500))
        checkboxes = settings_data.get("checkboxes", [])

        # Dimensions
        width = 200
        line_height = 24
        header_height = 30
        height = header_height + len(checkboxes) * line_height + 10

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
        glBegin(GL_QUADS)
        glVertex2f(x - 5, y - 5)
        glVertex2f(x + width, y - 5)
        glVertex2f(x + width, y + height)
        glVertex2f(x - 5, y + height)
        glEnd()

        # Border
        glColor4f(0.5, 0.5, 0.6, 0.8)
        glLineWidth(1)
        glBegin(GL_LINE_LOOP)
        glVertex2f(x - 5, y - 5)
        glVertex2f(x + width, y - 5)
        glVertex2f(x + width, y + height)
        glVertex2f(x - 5, y + height)
        glEnd()

        # Title
        title_surface = self._font.render("Settings", True, (255, 255, 100))
        title_data = pygame.image.tostring(title_surface, "RGBA", True)
        w, h = title_surface.get_size()
        glRasterPos2i(x, y + 20)
        glDrawPixels(w, h, GL_RGBA, GL_UNSIGNED_BYTE, title_data)

        # Checkboxes
        current_y = y + header_height
        for cb in checkboxes:
            # Draw box
            text_color = (255, 255, 255) if cb.checked else (180, 180, 180)

            marker = "[x]" if cb.checked else "[ ]"
            label = f"{marker} {cb.label}"

            text_surface = self._small_font.render(label, True, text_color)
            text_data = pygame.image.tostring(text_surface, "RGBA", True)
            w, h = text_surface.get_size()

            glRasterPos2i(x + 5, current_y + 15)
            glDrawPixels(w, h, GL_RGBA, GL_UNSIGNED_BYTE, text_data)

            current_y += line_height

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)

        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()

    # ------------------------------------------------------------------
    # Navigation mode panel
    # ------------------------------------------------------------------

    def render_nav_mode_panel(self, nav_data: dict[str, Any]):
        """Render the navigation mode panel."""
        if not nav_data.get("visible", False):
            return

        x, y = nav_data.get("position", (20, 300))
        modes = nav_data.get("modes", [])
        current_index = nav_data.get("current_mode_index", 0)

        # Dimensions
        width = 150
        line_height = 24
        header_height = 30
        height = header_height + len(modes) * line_height + 10

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
        glBegin(GL_QUADS)
        glVertex2f(x - 5, y - 5)
        glVertex2f(x + width, y - 5)
        glVertex2f(x + width, y + height)
        glVertex2f(x - 5, y + height)
        glEnd()

        # Border
        glColor4f(0.5, 0.5, 0.6, 0.8)
        glLineWidth(1)
        glBegin(GL_LINE_LOOP)
        glVertex2f(x - 5, y - 5)
        glVertex2f(x + width, y - 5)
        glVertex2f(x + width, y + height)
        glVertex2f(x - 5, y + height)
        glEnd()

        # Title
        title_surface = self._font.render("Mouse Control", True, (255, 255, 100))
        title_data = pygame.image.tostring(title_surface, "RGBA", True)
        w, h = title_surface.get_size()
        glRasterPos2i(x, y + 20)
        glDrawPixels(w, h, GL_RGBA, GL_UNSIGNED_BYTE, title_data)

        # Modes
        current_y = y + header_height
        for i, mode in enumerate(modes):
            is_active = i == current_index
            text_color = (100, 255, 100) if is_active else (180, 180, 180)
            prefix = ">> " if is_active else "   "

            label = f"{prefix}{mode}"

            text_surface = self._small_font.render(label, True, text_color)
            text_data = pygame.image.tostring(text_surface, "RGBA", True)
            w, h = text_surface.get_size()

            glRasterPos2i(x + 5, current_y + 15)
            glDrawPixels(w, h, GL_RGBA, GL_UNSIGNED_BYTE, text_data)

            current_y += line_height

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)

        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()

    # ------------------------------------------------------------------
    # Sidebar
    # ------------------------------------------------------------------

    def render_sidebar(self, sidebar_data: dict[str, Any], content_data: dict[str, Any]):
        """Render the unified sidebar."""
        if not sidebar_data.get("visible", False):
            return

        x, y = sidebar_data.get("position", (0, 0))
        width = sidebar_data.get("width", 380)
        height = sidebar_data.get("height", 600)
        tabs = sidebar_data.get("tabs", [])
        current_tab = sidebar_data.get("current_tab_index", 0)
        content_key = sidebar_data.get("current_content_key", "")

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

        # Main Background
        glColor4f(0.05, 0.08, 0.12, 0.95)
        glBegin(GL_QUADS)
        glVertex2f(x, y)
        glVertex2f(x + width, y)
        glVertex2f(x + width, y + height)
        glVertex2f(x, y + height)
        glEnd()

        # Border
        glColor4f(0.3, 0.5, 0.7, 0.5)
        glLineWidth(2)
        glBegin(GL_LINE_LOOP)
        glVertex2f(x, y)
        glVertex2f(x + width, y)
        glVertex2f(x + width, y + height)
        glVertex2f(x, y + height)
        glEnd()

        # Tabs Header
        header_height = 35
        tab_width = width / len(tabs) if tabs else 10

        for i, tab_name in enumerate(tabs):
            tab_x = x + i * tab_width
            is_active = i == current_tab

            # Tab Background
            if is_active:
                glColor4f(0.2, 0.3, 0.4, 0.9)
            else:
                glColor4f(0.1, 0.15, 0.2, 0.8)

            glBegin(GL_QUADS)
            glVertex2f(tab_x, y)
            glVertex2f(tab_x + tab_width, y)
            glVertex2f(tab_x + tab_width, y + header_height)
            glVertex2f(tab_x, y + header_height)
            glEnd()

            # Active indicator line
            if is_active:
                glColor4f(0.4, 0.8, 1.0, 1.0)
                glLineWidth(3)
                glBegin(GL_LINES)
                glVertex2f(tab_x, y + header_height)
                glVertex2f(tab_x + tab_width, y + header_height)
                glEnd()

            # Tab Text
            color = (255, 255, 255) if is_active else (150, 150, 150)
            text_surface = self._font.render(tab_name, True, color)
            text_data = pygame.image.tostring(text_surface, "RGBA", True)
            w, h = text_surface.get_size()
            text_pos_x = tab_x + (tab_width - w) // 2
            text_pos_y = y + (header_height - h) // 2
            glRasterPos2i(int(text_pos_x), int(text_pos_y + h))
            glDrawPixels(w, h, GL_RGBA, GL_UNSIGNED_BYTE, text_data)

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()

        # Render Content based on active tab
        content_pos = (x + 10, y + header_height + 10)

        if content_data:
            # Override position to fit in sidebar
            content_data["position"] = content_pos
            content_data["width"] = width - 20
            content_data["visible"] = True  # Force visible since tab is active

            if content_key == "educational":
                self.render_educational_panel(content_data)
            elif content_key == "checklist":
                self.render_immersion_checklist(content_data)
            elif content_key == "history":
                self.render_historical_events(content_data)

    # ------------------------------------------------------------------
    # Unified controls
    # ------------------------------------------------------------------

    def render_unified_controls(self, ctrl_data: dict[str, Any], time_data: dict[str, Any]):
        """Render the bottom unified control panel."""
        if not ctrl_data.get("visible", False):
            return

        x, y = ctrl_data.get("position", (0, 0))
        width = ctrl_data.get("width", 800)
        height = ctrl_data.get("height", 100)
        checkboxes = ctrl_data.get("checkboxes", [])
        modes = ctrl_data.get("modes", [])
        curr_mode = ctrl_data.get("current_mode_index", 0)

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

        # Background Gradient-ish (Solid for now)
        glColor4f(0.05, 0.08, 0.12, 0.95)
        glBegin(GL_QUADS)
        glVertex2f(x, y)
        glVertex2f(x + width, y)
        glVertex2f(x + width, y + height)
        glVertex2f(x, y + height)
        glEnd()

        # Top Border
        glColor4f(0.4, 0.8, 1.0, 0.6)
        glLineWidth(2)
        glBegin(GL_LINES)
        glVertex2f(x, y)
        glVertex2f(x + width, y)
        glEnd()

        # 1. Navigation Modes (Left)
        mode_x = x + 20
        mode_y = y + 20
        title_surface = self._small_font.render("NAVIGATION", True, (100, 200, 255))
        w, h = title_surface.get_size()
        text_data = pygame.image.tostring(title_surface, "RGBA", True)
        glRasterPos2i(int(mode_x), int(mode_y + h))
        glDrawPixels(w, h, GL_RGBA, GL_UNSIGNED_BYTE, text_data)

        mode_y += 25
        for i, mode in enumerate(modes):
            color = (100, 255, 100) if i == curr_mode else (150, 150, 150)
            prefix = "\u25cf " if i == curr_mode else "\u25cb "
            label = f"{prefix}{mode}"

            s = self._small_font.render(label, True, color)
            wd, hd = s.get_size()
            d = pygame.image.tostring(s, "RGBA", True)
            glRasterPos2i(int(mode_x), int(mode_y + hd))
            glDrawPixels(wd, hd, GL_RGBA, GL_UNSIGNED_BYTE, d)
            mode_x += 80  # horizontal layout

        # 2. View Settings (Right)
        set_x = x + width - 350
        set_y = y + 20
        title_surface = self._small_font.render("VIEW SETTINGS", True, (100, 200, 255))
        w, h = title_surface.get_size()
        text_data = pygame.image.tostring(title_surface, "RGBA", True)
        glRasterPos2i(int(set_x), int(set_y + h))
        glDrawPixels(w, h, GL_RGBA, GL_UNSIGNED_BYTE, text_data)

        set_y += 35
        col_1_x = set_x
        col_2_x = set_x + 160

        for i, cb in enumerate(checkboxes):
            # 2 columns
            cx = col_1_x if i % 2 == 0 else col_2_x
            cy = set_y + (i // 2) * 30

            color = (255, 255, 255) if cb.checked else (150, 150, 150)
            marker = "\u2611" if cb.checked else "\u2610"
            label = f"{marker} {cb.label}"

            s = self._small_font.render(label, True, color)
            wd, hd = s.get_size()
            d = pygame.image.tostring(s, "RGBA", True)
            glRasterPos2i(int(cx), int(cy + hd))
            glDrawPixels(wd, hd, GL_RGBA, GL_UNSIGNED_BYTE, d)

        # 3. Action Buttons
        btn_x = x + 20
        btn_y = y + 80

        buttons = ctrl_data.get("buttons", [])
        for btn in buttons:
            # Draw Button BG
            glColor4f(0.2, 0.4, 0.6, 0.8)
            glBegin(GL_QUADS)
            glVertex2f(btn_x, btn_y)
            glVertex2f(btn_x + btn.width, btn_y)
            glVertex2f(btn_x + btn.width, btn_y + 30)
            glVertex2f(btn_x, btn_y + 30)
            glEnd()

            # Text
            s = self._small_font.render(btn.label, True, (255, 255, 255))
            wd, hd = s.get_size()
            d = pygame.image.tostring(s, "RGBA", True)
            text_pos_x = btn_x + (btn.width - wd) // 2
            text_pos_y = btn_y + (30 - hd) // 2
            glRasterPos2i(int(text_pos_x), int(text_pos_y + hd))
            glDrawPixels(wd, hd, GL_RGBA, GL_UNSIGNED_BYTE, d)

            btn_x += btn.width + 10

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
