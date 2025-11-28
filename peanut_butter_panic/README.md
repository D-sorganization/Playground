# Peanut Butter Panic - Remixed

A modern remix of Atari's *Peanut Butter Panic* built with Python and Pygame. Guide a
heroic jar of peanut butter as it protects sandwiches from waves of hungry critters.
The remake layers in progression, defensive tools, combo-driven scoring, and quick-hit
power-ups to keep every run fresh.

## Feature highlights

- **Wave-based pressure** with accelerating spawn rates and tougher enemy bites.
- **Retro brawler enemies** occasionally spawn, recalling the chunky doom-like
  monsters from the earliest prototype while offering bigger rewards.
- **Combo-driven scoring** that rewards streaks and speedy clears.
- **Defense toolkit**: wide spatula swipes, sticky traps, dashes, and screen-clearing
  shockwaves.
- **Power-ups** including sugar rush speed boosts, sticky gloves for wider swings, and
  instant shockwave charges.
- **Sandwich integrity tracking** to keep your objectives top-of-mind.

## Controls

- **WASD / Arrow keys**: Move
- **Space**: Spatula swipe (short cooldown)
- **Ctrl**: Drop a sticky trap that slows enemies
- **Shift**: Dash
- **Q**: Shockwave (clears nearby enemies)
- **Close the window** to end the run

## Running the game

```bash
python -m peanut_butter_panic.game
```

For deterministic behavior in tests or practice runs, you can seed the simulation by
passing a `seed` to `GameWorld` in code:

```python
from peanut_butter_panic import GameWorld

world = GameWorld(seed=42)
```
