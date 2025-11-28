from __future__ import annotations

import os

import pygame

from .core import GameConfig, GameWorld, InputState

Color = tuple[int, int, int]


def _draw_circle(
    surface: pygame.Surface, color: Color, position: tuple[float, float], radius: float
) -> None:
    pygame.draw.circle(
        surface, color, (int(position[0]), int(position[1])), int(radius)
    )


def _draw_text(
    surface: pygame.Surface,
    text: str,
    position: tuple[int, int],
    font: pygame.font.Font,
    color: Color,
) -> None:
    surface.blit(font.render(text, True, color), position)


def _build_input_state() -> InputState:
    keys = pygame.key.get_pressed()
    move_x = float(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - float(
        keys[pygame.K_a] or keys[pygame.K_LEFT]
    )
    move_y = float(keys[pygame.K_s] or keys[pygame.K_DOWN]) - float(
        keys[pygame.K_w] or keys[pygame.K_UP]
    )
    return InputState(
        move=(move_x, move_y),
        swing=keys[pygame.K_SPACE],
        deploy_trap=keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL],
        shockwave=keys[pygame.K_q],
        dash=keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT],
    )


def _render_world(
    surface: pygame.Surface, world: GameWorld, hud_font: pygame.font.Font
) -> None:
    surface.fill((20, 16, 28))

    for trap in world.traps:
        _draw_circle(surface, (100, 160, 255), trap.position, trap.radius)

    for sandwich in world.sandwiches:
        color = (0, 180, 120) if sandwich.alive else (120, 80, 80)
        _draw_circle(surface, color, sandwich.position, sandwich.radius)
        health_ratio = sandwich.health / world.config.sandwich_health
        pygame.draw.rect(
            surface,
            (180, 255, 230),
            pygame.Rect(
                sandwich.position[0] - sandwich.radius,
                sandwich.position[1] - sandwich.radius - 10,
                sandwich.radius * 2 * health_ratio,
                6,
            ),
        )

    _draw_circle(surface, (255, 230, 150), world.player.position, world.player.radius)

    for enemy in world.enemies:
        color = (200, 70, 90) if enemy.kind == "modern_swarm" else (120, 180, 210)
        _draw_circle(surface, color, enemy.position, enemy.radius)

    for powerup in world.powerups:
        _draw_circle(surface, (255, 180, 60), powerup.position, powerup.radius)

    hud_lines = [
        f"Score: {world.stats.score}",
        f"Wave: {world.stats.wave}  Combo: x{max(1, world.stats.combo)}",
        f"Sandwiches: {world.stats.sandwiches_saved}/{len(world.sandwiches)}",
        f"Health: {world.player.health}",
        "[Space] Swipe | [Ctrl] Sticky Trap | [Q] Shockwave | [Shift] Dash",
    ]

    for idx, line in enumerate(hud_lines):
        _draw_text(surface, line, (14, 14 + idx * 22), hud_font, (230, 230, 240))


def run(config: GameConfig | None = None) -> None:
    os.environ.setdefault("SDL_VIDEO_CENTERED", "1")
    pygame.init()
    world_config = config or GameConfig()
    screen = pygame.display.set_mode((world_config.width, world_config.height))
    pygame.display.set_caption("Peanut Butter Panic - Remixed")
    clock = pygame.time.Clock()
    hud_font = pygame.font.SysFont("ubuntu", 18)

    world = GameWorld(config=world_config)
    running = True

    while running:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        world.update(dt, _build_input_state())
        _render_world(screen, world, hud_font)
        pygame.display.flip()

        if world.defeated:
            running = False

    pygame.quit()


if __name__ == "__main__":
    run()
