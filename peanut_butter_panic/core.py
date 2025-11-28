from __future__ import annotations

import math
import random
from collections.abc import Iterable
from dataclasses import dataclass

Vec2 = tuple[float, float]


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _length(vec: Vec2) -> float:
    return math.sqrt(vec[0] ** 2 + vec[1] ** 2)


def _normalize(vec: Vec2) -> Vec2:
    magnitude = _length(vec)
    if magnitude == 0:
        return (0.0, 0.0)
    return (vec[0] / magnitude, vec[1] / magnitude)


def _add(a: Vec2, b: Vec2) -> Vec2:
    return (a[0] + b[0], a[1] + b[1])


def _scale(vec: Vec2, scalar: float) -> Vec2:
    return (vec[0] * scalar, vec[1] * scalar)


def _distance(a: Vec2, b: Vec2) -> float:
    return _length((a[0] - b[0], a[1] - b[1]))


@dataclass
class InputState:
    move: Vec2 = (0.0, 0.0)
    swing: bool = False
    deploy_trap: bool = False
    shockwave: bool = False
    dash: bool = False


@dataclass
class GameConfig:
    width: int = 960
    height: int = 640
    player_speed: float = 220.0
    dash_speed: float = 360.0
    dash_time: float = 0.3
    dash_cooldown: float = 3.5
    swing_radius: float = 60.0
    swing_cooldown: float = 0.45
    trap_radius: float = 72.0
    trap_slow_factor: float = 0.45
    trap_lifetime: float = 8.0
    trap_cooldown: float = 4.0
    shockwave_radius: float = 140.0
    shockwave_cooldown: float = 12.0
    combo_window: float = 2.8
    combo_bonus: float = 0.35
    max_combo: int = 5
    base_spawn_interval: float = 2.4
    wave_duration: float = 36.0
    spawn_acceleration: float = 0.12
    max_wave: int = 12
    powerup_chance: float = 0.18
    sandwich_health: int = 5
    player_health: int = 3
    retro_spawn_chance: float = 0.22
    retro_speed_scale: float = 0.82
    retro_radius: float = 18.0
    retro_damage_bonus: int = 1
    retro_reward_bonus: int = 15


@dataclass
class Player:
    position: Vec2
    speed: float
    radius: float = 16.0
    dash_cooldown: float = 0.0
    dash_time: float = 0.0
    swing_cooldown: float = 0.0
    trap_cooldown: float = 0.0
    shockwave_cooldown: float = 0.0
    health: int = 3


@dataclass
class Sandwich:
    position: Vec2
    health: int
    radius: float = 20.0

    @property
    def alive(self) -> bool:
        return self.health > 0


@dataclass(frozen=True)
class EnemyArchetype:
    name: str
    speed_scale: float
    damage_bonus: int
    reward_bonus: int
    radius: float


@dataclass
class Enemy:
    position: Vec2
    speed: float
    damage: int
    reward: int
    radius: float = 14.0
    kind: str = "modern_swarm"


@dataclass
class Trap:
    position: Vec2
    radius: float
    slow_factor: float
    lifetime: float

    def tick(self, dt: float) -> None:
        self.lifetime = max(0.0, self.lifetime - dt)

    @property
    def expired(self) -> bool:
        return self.lifetime <= 0.0


@dataclass
class PowerUp:
    position: Vec2
    kind: str
    duration: float
    radius: float = 16.0


@dataclass
class WorldStats:
    score: int = 0
    combo: int = 0
    combo_timer: float = 0.0
    wave: int = 1
    elapsed: float = 0.0
    sandwiches_saved: int = 0


class GameWorld:
    def __init__(self, config: GameConfig | None = None, seed: int | None = 1337):
        self.config = config or GameConfig()
        self.rng = random.Random(seed)
        self.base_player_speed = self.config.player_speed
        self.base_swing_radius = self.config.swing_radius
        self.player = Player(
            position=(self.config.width / 2, self.config.height / 2),
            speed=self.config.player_speed,
            health=self.config.player_health,
        )
        self.sandwiches: list[Sandwich] = [
            Sandwich(
                position=(self.config.width * 0.3, self.config.height / 2),
                health=self.config.sandwich_health,
            ),
            Sandwich(
                position=(self.config.width * 0.7, self.config.height / 2),
                health=self.config.sandwich_health,
            ),
        ]
        self.enemies: list[Enemy] = []
        self.traps: list[Trap] = []
        self.powerups: list[PowerUp] = []
        self.active_effects: dict[str, float] = {}
        self.stats = WorldStats()
        self.stats.sandwiches_saved = len(self.sandwiches)
        self.spawn_timer = self.config.base_spawn_interval
        self.wave_timer = self.config.wave_duration

    def update(self, dt: float, input_state: InputState) -> None:
        self.stats.elapsed += dt
        self._handle_wave_progression(dt)
        self._tick_cooldowns(dt)
        self._update_player(dt, input_state)
        self._move_enemies(dt)
        self._resolve_enemy_collisions()
        self._collect_powerups()
        self._age_traps(dt)
        self._tick_effects(dt)
        self._decay_combo(dt)
        self._maybe_spawn_enemy(dt)

    def _handle_wave_progression(self, dt: float) -> None:
        self.wave_timer -= dt
        if self.wave_timer <= 0 and self.stats.wave < self.config.max_wave:
            self.stats.wave += 1
            self.wave_timer = self.config.wave_duration
            self.spawn_timer = max(
                0.6, self.spawn_timer * (1 - self.config.spawn_acceleration)
            )

    def _tick_cooldowns(self, dt: float) -> None:
        self.player.dash_cooldown = max(0.0, self.player.dash_cooldown - dt)
        self.player.dash_time = max(0.0, self.player.dash_time - dt)
        self.player.swing_cooldown = max(0.0, self.player.swing_cooldown - dt)
        self.player.trap_cooldown = max(0.0, self.player.trap_cooldown - dt)
        self.player.shockwave_cooldown = max(0.0, self.player.shockwave_cooldown - dt)

    def _update_player(self, dt: float, input_state: InputState) -> None:
        direction = _normalize(input_state.move)
        speed = (
            self.config.dash_speed if self.player.dash_time > 0 else self.player.speed
        )
        self.player.position = self._clamped_position(
            _add(self.player.position, _scale(direction, speed * dt))
        )

        if input_state.dash and self.player.dash_cooldown == 0.0:
            self.player.dash_time = self.config.dash_time
            self.player.dash_cooldown = self.config.dash_cooldown

        if input_state.swing and self.player.swing_cooldown == 0.0:
            self._perform_swing()
            self.player.swing_cooldown = self.config.swing_cooldown

        if input_state.deploy_trap and self.player.trap_cooldown == 0.0:
            self._deploy_trap()
            self.player.trap_cooldown = self.config.trap_cooldown

        if input_state.shockwave and self.player.shockwave_cooldown == 0.0:
            self._detonate_shockwave()
            self.player.shockwave_cooldown = self.config.shockwave_cooldown

    def _perform_swing(self) -> None:
        radius = self.config.swing_radius
        defeated: list[Enemy] = []
        for enemy in list(self.enemies):
            if _distance(self.player.position, enemy.position) <= radius + enemy.radius:
                defeated.append(enemy)
                self._register_kill(enemy)
        self._remove_enemies(defeated)

    def _deploy_trap(self) -> None:
        self.traps.append(
            Trap(
                position=self.player.position,
                radius=self.config.trap_radius,
                slow_factor=self.config.trap_slow_factor,
                lifetime=self.config.trap_lifetime,
            )
        )

    def _detonate_shockwave(self) -> None:
        defeated: list[Enemy] = []
        for enemy in list(self.enemies):
            if (
                _distance(self.player.position, enemy.position)
                <= self.config.shockwave_radius
            ):
                defeated.append(enemy)
                self._register_kill(enemy)
        self._remove_enemies(defeated)

    def _move_enemies(self, dt: float) -> None:
        for enemy in self.enemies:
            target = self._primary_target(enemy)
            direction = _normalize(
                (target[0] - enemy.position[0], target[1] - enemy.position[1])
            )
            speed = enemy.speed * self._trap_slowdown(enemy)
            enemy.position = self._clamped_position(
                _add(enemy.position, _scale(direction, speed * dt))
            )

    def _primary_target(self, enemy: Enemy) -> Vec2:
        living = [s for s in self.sandwiches if s.alive]
        if living:
            return min(
                living, key=lambda s: _distance(s.position, enemy.position)
            ).position
        return self.player.position

    def _trap_slowdown(self, enemy: Enemy) -> float:
        slowdown = 1.0
        for trap in self.traps:
            if _distance(trap.position, enemy.position) <= trap.radius:
                slowdown *= trap.slow_factor
        return slowdown

    def _resolve_enemy_collisions(self) -> None:
        surviving_enemies: list[Enemy] = []
        for enemy in self.enemies:
            target = self._find_hit_target(enemy)
            if target is None:
                surviving_enemies.append(enemy)
            elif isinstance(target, Sandwich):
                target.health = max(0, target.health - enemy.damage)
            else:
                self.player.health = max(0, self.player.health - enemy.damage)
        self.enemies = surviving_enemies
        self.stats.sandwiches_saved = sum(
            1 for sandwich in self.sandwiches if sandwich.alive
        )

    def _find_hit_target(self, enemy: Enemy) -> Sandwich | Player | None:
        for sandwich in self.sandwiches:
            if (
                sandwich.alive
                and _distance(sandwich.position, enemy.position)
                <= sandwich.radius + enemy.radius
            ):
                return sandwich
        if (
            _distance(self.player.position, enemy.position)
            <= self.player.radius + enemy.radius
        ):
            return self.player
        return None

    def _collect_powerups(self) -> None:
        remaining: list[PowerUp] = []
        for powerup in self.powerups:
            if (
                _distance(powerup.position, self.player.position)
                <= powerup.radius + self.player.radius
            ):
                self._apply_powerup(powerup)
            else:
                remaining.append(powerup)
        self.powerups = remaining

    def _age_traps(self, dt: float) -> None:
        for trap in self.traps:
            trap.tick(dt)
        self.traps = [trap for trap in self.traps if not trap.expired]

    def _tick_effects(self, dt: float) -> None:
        expired: list[str] = []
        for name, remaining in list(self.active_effects.items()):
            remaining -= dt
            if remaining <= 0:
                expired.append(name)
            else:
                self.active_effects[name] = remaining

        for name in expired:
            del self.active_effects[name]
            if name == "sugar_rush":
                self.player.speed = self.base_player_speed
            elif name == "sticky_gloves":
                self.config.swing_radius = self.base_swing_radius

    def _decay_combo(self, dt: float) -> None:
        if self.stats.combo_timer > 0:
            self.stats.combo_timer = max(0.0, self.stats.combo_timer - dt)
            if self.stats.combo_timer == 0:
                self.stats.combo = 0

    def _maybe_spawn_enemy(self, dt: float) -> None:
        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self.spawn_timer = max(
                0.6,
                self.config.base_spawn_interval * (1 - 0.04 * (self.stats.wave - 1)),
            )
            self.enemies.append(self._make_enemy())

    def _make_enemy(self) -> Enemy:
        side = self.rng.choice(["top", "bottom", "left", "right"])
        if side == "top":
            position = (self.rng.uniform(0, self.config.width), -10)
        elif side == "bottom":
            position = (self.rng.uniform(0, self.config.width), self.config.height + 10)
        elif side == "left":
            position = (-10, self.rng.uniform(0, self.config.height))
        else:
            position = (self.config.width + 10, self.rng.uniform(0, self.config.height))

        archetype = self._choose_archetype()
        speed = (90 + 14 * (self.stats.wave - 1)) * archetype.speed_scale
        damage = 1 + (self.stats.wave // 4) + archetype.damage_bonus
        reward = 30 + 5 * self.stats.wave + archetype.reward_bonus
        return Enemy(
            position=position,
            speed=float(speed),
            damage=damage,
            reward=reward,
            radius=archetype.radius,
            kind=archetype.name,
        )

    def _choose_archetype(self) -> EnemyArchetype:
        retro_roll = self.rng.random()
        if retro_roll <= self.config.retro_spawn_chance:
            return EnemyArchetype(
                name="retro_brawler",
                speed_scale=self.config.retro_speed_scale,
                damage_bonus=self.config.retro_damage_bonus,
                reward_bonus=self.config.retro_reward_bonus,
                radius=self.config.retro_radius,
            )

        return EnemyArchetype(
            name="modern_swarm",
            speed_scale=1.0,
            damage_bonus=0,
            reward_bonus=0,
            radius=14.0,
        )

    def _register_kill(self, enemy: Enemy) -> None:
        self.stats.combo = min(self.config.max_combo, self.stats.combo + 1)
        self.stats.combo_timer = self.config.combo_window
        multiplier = 1 + (self.stats.combo - 1) * self.config.combo_bonus
        self.stats.score += int(enemy.reward * multiplier)
        self.stats.sandwiches_saved = sum(
            1 for sandwich in self.sandwiches if sandwich.alive
        )
        if self.rng.random() <= self.config.powerup_chance:
            self._drop_powerup(enemy.position)

    def _drop_powerup(self, position: Vec2) -> None:
        kind = self.rng.choice(["sugar_rush", "sticky_gloves", "free_shockwave"])
        duration = 7.0 if kind != "free_shockwave" else 0.0
        self.powerups.append(PowerUp(position=position, kind=kind, duration=duration))

    def _apply_powerup(self, powerup: PowerUp) -> None:
        if powerup.kind == "sugar_rush":
            self.active_effects["sugar_rush"] = max(
                powerup.duration, self.active_effects.get("sugar_rush", 0.0)
            )
            self.player.speed = self.base_player_speed * 1.25
        elif powerup.kind == "sticky_gloves":
            self.active_effects["sticky_gloves"] = max(
                powerup.duration, self.active_effects.get("sticky_gloves", 0.0)
            )
            self.config.swing_radius = self.base_swing_radius + 12
        elif powerup.kind == "free_shockwave":
            self.player.shockwave_cooldown = 0.0

    def _remove_enemies(self, defeated: Iterable[Enemy]) -> None:
        defeated_ids = {id(enemy) for enemy in defeated}
        self.enemies = [
            enemy for enemy in self.enemies if id(enemy) not in defeated_ids
        ]

    def _clamped_position(self, position: Vec2) -> Vec2:
        return (
            _clamp(position[0], 0, self.config.width),
            _clamp(position[1], 0, self.config.height),
        )

    def reset(self) -> None:
        self.player = Player(
            position=(self.config.width / 2, self.config.height / 2),
            speed=self.config.player_speed,
            health=self.config.player_health,
        )
        self.sandwiches = [
            Sandwich(
                position=(self.config.width * 0.3, self.config.height / 2),
                health=self.config.sandwich_health,
            ),
            Sandwich(
                position=(self.config.width * 0.7, self.config.height / 2),
                health=self.config.sandwich_health,
            ),
        ]
        self.enemies.clear()
        self.traps.clear()
        self.powerups.clear()
        self.active_effects.clear()
        self.player.speed = self.base_player_speed
        self.config.swing_radius = self.base_swing_radius
        self.stats = WorldStats()
        self.stats.sandwiches_saved = len(self.sandwiches)
        self.spawn_timer = self.config.base_spawn_interval
        self.wave_timer = self.config.wave_duration

    def add_enemy(
        self,
        position: Vec2,
        speed: float = 120.0,
        damage: int = 1,
        reward: int = 25,
        radius: float = 14.0,
        kind: str = "modern_swarm",
    ) -> None:
        self.enemies.append(
            Enemy(
                position=position,
                speed=speed,
                damage=damage,
                reward=reward,
                radius=radius,
                kind=kind,
            )
        )

    @property
    def defeated(self) -> bool:
        sandwiches_lost = all(not sandwich.alive for sandwich in self.sandwiches)
        return sandwiches_lost or self.player.health <= 0
