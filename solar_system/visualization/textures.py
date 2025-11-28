"""Texture management for planet maps sourced from NASA imagery."""

from __future__ import annotations

import pathlib
import urllib.request
from dataclasses import dataclass

try:  # Optional dependency during headless testing
    import pygame
    from OpenGL.GL import (
        GL_LINEAR,
        GL_LINEAR_MIPMAP_LINEAR,
        GL_REPEAT,
        GL_RGBA,
        GL_TEXTURE_2D,
        GL_TEXTURE_MAG_FILTER,
        GL_TEXTURE_MIN_FILTER,
        GL_TEXTURE_WRAP_S,
        GL_TEXTURE_WRAP_T,
        GL_UNSIGNED_BYTE,
        glBindTexture,
        glGenerateMipmap,
        glGenTextures,
        glTexImage2D,
        glTexParameteri,
    )

    TEXTURE_BACKEND_AVAILABLE = True
except Exception:  # pragma: no cover - OpenGL unavailable in tests
    pygame = None
    TEXTURE_BACKEND_AVAILABLE = False


TEXTURE_MANIFEST: dict[str, str] = {
    "Mercury": "https://planetarymaps.usgs.gov/mosaic/Mercury_v1_L3.png",
    "Venus": "https://planetarymaps.usgs.gov/mosaic/VenusMagellan.png",
    "Earth": "https://eoimages.gsfc.nasa.gov/images/imagerecords/57000/57730/land_ocean_ice_cloud_2048.png",
    "Moon": "https://planetarymaps.usgs.gov/mosaic/Lunar_LRO_LOLA_Global_LDEM_118m_Mar2014.png",
    "Mars": "https://planetarymaps.usgs.gov/mosaic/Mars_MGS_MOLA_DEM_mosaic_global_463m.tif",
    "Jupiter": "https://planetarymaps.usgs.gov/mosaic/Jupiter_Voyager_GalileoSSI_global_mosaic_1km.tif",
    "Saturn": "https://planetarymaps.usgs.gov/mosaic/Saturn_Cassini_ISS_Composite_global_mosaic_1km.tif",
    "Uranus": "https://planetarymaps.usgs.gov/mosaic/Uranus_Voyager2_ISS_global_mosaic_1km.tif",
    "Neptune": "https://planetarymaps.usgs.gov/mosaic/Neptune_Voyager2_ISS_global_mosaic_4km.tif",
    "Pluto": "https://planetarymaps.usgs.gov/mosaic/Pluto_NewHorizons_Global_Mosaic_300m_Jul2017_12bit.tif",
}


@dataclass
class TextureHandle:
    path: pathlib.Path
    gl_id: int | None


class TextureManager:
    """Load and bind NASA-sourced textures for planets and moons."""

    def __init__(self, asset_root: pathlib.Path, auto_download: bool = True):
        self.asset_root = asset_root
        self.auto_download = auto_download
        self.textures: dict[str, TextureHandle] = {}

    def _texture_path(self, body_name: str) -> pathlib.Path:
        safe_name = body_name.lower().replace(" ", "_")
        return self.asset_root / "textures" / f"{safe_name}.png"

    def ensure_texture(self, body_name: str) -> pathlib.Path | None:
        path = self._texture_path(body_name)
        if path.exists():
            return path

        url = TEXTURE_MANIFEST.get(body_name)
        if not url or not self.auto_download:
            return None

        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            urllib.request.urlretrieve(url, path)
        except Exception:
            return None

        return path if path.exists() else None

    def load_texture(self, body_name: str) -> TextureHandle | None:
        if not TEXTURE_BACKEND_AVAILABLE:
            return None

        existing = self.textures.get(body_name)
        if existing:
            return existing

        texture_path = self.ensure_texture(body_name)
        if texture_path is None:
            return None

        surface = pygame.image.load(texture_path.as_posix())
        surface = pygame.transform.flip(surface, False, True)
        surface_data = pygame.image.tostring(surface, "RGBA", True)
        width, height = surface.get_size()

        gl_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, gl_id)
        glTexImage2D(
            GL_TEXTURE_2D,
            0,
            GL_RGBA,
            width,
            height,
            0,
            GL_RGBA,
            GL_UNSIGNED_BYTE,
            surface_data,
        )
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glGenerateMipmap(GL_TEXTURE_2D)

        handle = TextureHandle(path=texture_path, gl_id=gl_id)
        self.textures[body_name] = handle
        return handle

    def bind(self, body_name: str) -> bool:
        if not TEXTURE_BACKEND_AVAILABLE:
            return False

        handle = self.load_texture(body_name)
        if not handle or handle.gl_id is None:
            return False

        glBindTexture(GL_TEXTURE_2D, handle.gl_id)
        return True
