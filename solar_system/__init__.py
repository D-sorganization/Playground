"""
Solar System Simulation
========================

A professional-grade, scientifically accurate solar system model for educational purposes.

Features:
- Accurate planetary positions using Keplerian orbital mechanics
- Real-time or time-accelerated simulation
- Multiple camera perspectives (heliocentric, planet-centric, spacecraft-following)
- Interplanetary trajectory planning with Hohmann transfers
- Beautiful 3D visualization with OpenGL
- Educational information overlays

Author: Solar System Simulation Project
License: MIT
"""

__version__ = "1.0.0"
__author__ = "Solar System Simulation Project"

from .core.constants import *
from .core.celestial_body import CelestialBody, Planet, Star, Moon
from .physics.orbital_mechanics import OrbitalMechanics
from .physics.trajectory_planner import TrajectoryPlanner
