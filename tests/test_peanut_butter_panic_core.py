from peanut_butter_panic import GameConfig, GameWorld, InputState


def distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return (dx * dx + dy * dy) ** 0.5


def test_shockwave_clears_enemies_and_scores():
    world = GameWorld(seed=1)
    enemy_position = (world.player.position[0] + 10, world.player.position[1])
    world.add_enemy(enemy_position, reward=40)
    world.player.shockwave_cooldown = 0.0

    world.update(0.0, InputState(shockwave=True))

    assert world.stats.score >= 40
    assert world.stats.combo == 1
    assert not world.enemies


def test_combo_decay_resets_multiplier():
    world = GameWorld(seed=2)
    enemy_position = (world.player.position[0] + 5, world.player.position[1])
    world.add_enemy(enemy_position)

    world.update(0.0, InputState(swing=True))
    assert world.stats.combo == 1

    decay_time = world.config.combo_window + 0.5
    world.update(decay_time, InputState())

    assert world.stats.combo == 0


def test_trap_slows_enemy_movement():
    world_with_trap = GameWorld(seed=3)
    world_without_trap = GameWorld(seed=3)
    enemy_position = (
        world_with_trap.config.width / 2,
        world_with_trap.config.height / 2 + 40,
    )

    world_with_trap.add_enemy(enemy_position, speed=120.0)
    world_without_trap.add_enemy(enemy_position, speed=120.0)

    world_with_trap.update(0.0, InputState(deploy_trap=True))

    world_with_trap.update(0.5, InputState())
    world_without_trap.update(0.5, InputState())

    enemy_with_trap = world_with_trap.enemies[0]
    enemy_without_trap = world_without_trap.enemies[0]

    moved_with_trap = distance(enemy_position, enemy_with_trap.position)
    moved_without_trap = distance(enemy_position, enemy_without_trap.position)

    assert moved_with_trap < moved_without_trap


def test_retro_enemy_archetype_spawns_when_forced():
    config = GameConfig(retro_spawn_chance=1.0)
    world = GameWorld(config=config, seed=7)
    world.spawn_timer = 0.0

    world.update(0.0, InputState())

    assert world.enemies[0].kind == "retro_brawler"
    assert world.enemies[0].radius == config.retro_radius
