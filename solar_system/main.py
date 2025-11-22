#!/usr/bin/env python3
"""
Solar System Simulation
=======================

A professional-grade, scientifically accurate solar system model.

This application provides:
- Real-time visualization of planetary orbits
- Accurate positions based on Keplerian mechanics
- Interplanetary trajectory planning
- Multiple camera perspectives
- Educational information overlays

Usage:
    python -m solar_system.main [options]

Options:
    --fullscreen    Start in fullscreen mode
    --width W       Window width (default: 1600)
    --height H      Window height (default: 900)
    --no-vsync      Disable vertical sync
    --start-date    Start date in YYYY-MM-DD format
    --help          Show this help message

Controls:
    SPACE       Pause/Resume simulation
    +/-         Speed up/slow down time
    R           Reverse time flow
    0-9         Select celestial body
    F           Focus on selected body
    C           Cycle camera mode
    O           Toggle orbital paths
    L           Toggle labels
    I           Toggle info panel
    G           Toggle grid
    H           Toggle help overlay
    T           Plan trajectory to Mars
    HOME        Reset view
    ESC         Quit

Mouse:
    Left drag   Orbit camera
    Right drag  Pan camera
    Scroll      Zoom in/out
"""

import sys
import argparse
from datetime import datetime

from .visualization.renderer import RenderSettings
from .visualization.scene import SolarSystemScene
from .core.time_manager import SimulationTime


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Solar System Simulation - A scientifically accurate model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--fullscreen',
        action='store_true',
        help='Start in fullscreen mode'
    )

    parser.add_argument(
        '--width',
        type=int,
        default=1600,
        help='Window width (default: 1600)'
    )

    parser.add_argument(
        '--height',
        type=int,
        default=900,
        help='Window height (default: 900)'
    )

    parser.add_argument(
        '--no-vsync',
        action='store_true',
        help='Disable vertical sync'
    )

    parser.add_argument(
        '--start-date',
        type=str,
        default=None,
        help='Start date in YYYY-MM-DD format'
    )

    parser.add_argument(
        '--no-antialiasing',
        action='store_true',
        help='Disable antialiasing'
    )

    return parser.parse_args()


def main():
    """Main entry point for the simulation."""
    args = parse_arguments()

    # Configure render settings
    settings = RenderSettings(
        window_width=args.width,
        window_height=args.height,
        fullscreen=args.fullscreen,
        vsync=not args.no_vsync,
        antialiasing=not args.no_antialiasing
    )

    # Create scene
    scene = SolarSystemScene(settings)

    # Initialize
    print("Solar System Simulation")
    print("=" * 50)
    print("Initializing...")

    if not scene.initialize():
        print("ERROR: Failed to initialize. Make sure PyGame and PyOpenGL are installed.")
        print("Install with: pip install pygame PyOpenGL PyOpenGL_accelerate numpy")
        return 1

    # Set start date if specified
    if args.start_date:
        try:
            dt = datetime.strptime(args.start_date, "%Y-%m-%d")
            scene.time_manager.set_datetime(dt)
            print(f"Starting at: {args.start_date}")
        except ValueError:
            print(f"Warning: Invalid date format '{args.start_date}', using current date")

    print("Initialization complete!")
    print()
    print("Controls:")
    print("  SPACE      - Pause/Resume")
    print("  +/-        - Speed up/slow down time")
    print("  0-9        - Select planet (0=Sun)")
    print("  H          - Toggle help overlay")
    print("  ESC        - Quit")
    print()
    print("Starting simulation...")

    # Run the simulation
    try:
        scene.run()
    except KeyboardInterrupt:
        print("\nSimulation interrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        raise

    print("Simulation ended.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
