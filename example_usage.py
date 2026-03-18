"""
example_usage.py — Visual demo of the Procedural 2D Level Generator
====================================================================

Generates a full level and renders it in a Pygame window so you can
scroll through it with arrow keys. Shows how to convert BlockInfo / TrapInfo
objects into actual Pygame sprites.

Controls:
    Left / Right arrow  — scroll the camera
    R                   — regenerate with a new random seed
    1 / 2 / 3           — switch theme (desert / castle / space)
    ESC                 — quit

Requirements:
    pip install pygame
"""

import random
import sys
import pygame
from level_generator import LevelGenerator, BlockInfo, TrapInfo, register_pattern

# =============================================================================
#  SETTINGS
# =============================================================================
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
BLOCK_SIZE = 64
FPS = 60
SCROLL_SPEED = 8

# Colour palettes for each theme
THEMES = {
    "desert": {
        "floor":    (194, 160, 100),
        "platform": (220, 185, 120),
        "spikes":   (180, 50, 50),
        "fire":     (255, 120, 30),
        "saw":      (160, 160, 170),
        "bg":       (240, 210, 160),
        "sky":      (135, 190, 230),
    },
    "castle": {
        "floor":    (90, 90, 105),
        "platform": (110, 110, 125),
        "spikes":   (170, 40, 40),
        "fire":     (240, 100, 20),
        "saw":      (140, 140, 150),
        "bg":       (70, 75, 85),
        "sky":      (100, 110, 130),
    },
    "space": {
        "floor":    (60, 50, 80),
        "platform": (80, 70, 110),
        "spikes":   (200, 60, 60),
        "fire":     (60, 200, 220),
        "saw":      (180, 180, 190),
        "bg":       (15, 10, 30),
        "sky":      (10, 5, 25),
    },
}


# =============================================================================
#  CUSTOM PATTERN EXAMPLE — register a "pyramid" before generating
# =============================================================================
def pyramid_pattern(start_x, block_size, ground_y, style):
    """3-row pyramid — demonstrates custom pattern registration."""
    blocks = []
    for row in range(3):
        for col in range(3 - row):
            x = start_x + col * block_size + row * block_size // 2
            y = ground_y - block_size * (row + 2)
            blocks.append(BlockInfo(x, y, block_size, style))
    return blocks

register_pattern("pyramid", pyramid_pattern)


# =============================================================================
#  LEVEL BUILDER
# =============================================================================
def build_level(theme_name, seed=None):
    """Generate a level and return renderable data."""
    style = theme_name
    gen = LevelGenerator(
        block_size=BLOCK_SIZE,
        screen_height=SCREEN_HEIGHT,
        style=style,
        seed=seed,
    )
    level = gen.generate_full_level(level_length=120, spacing_range=(4, 7))
    return level, THEMES[theme_name]


# =============================================================================
#  DRAWING HELPERS
# =============================================================================
def draw_block(surface, block, palette, camera_x, is_floor=False):
    """Draw a single BlockInfo as a coloured rect."""
    colour = palette["floor"] if is_floor else palette["platform"]
    rect = pygame.Rect(block.x - camera_x, block.y, block.size, block.size)
    pygame.draw.rect(surface, colour, rect)
    # border
    darker = tuple(max(0, c - 30) for c in colour)
    pygame.draw.rect(surface, darker, rect, 2)


def draw_trap(surface, trap, palette, camera_x):
    """Draw a single TrapInfo as a coloured shape."""
    colour = palette.get(trap.trap_type, (255, 0, 255))
    rect = pygame.Rect(trap.x - camera_x, trap.y, trap.width, trap.height)

    if trap.trap_type == "spikes":
        # Triangle
        points = [rect.bottomleft, rect.midtop, rect.bottomright]
        pygame.draw.polygon(surface, colour, points)
        pygame.draw.polygon(surface, (0, 0, 0), points, 2)
    elif trap.trap_type == "fire":
        # Flickering rect
        pygame.draw.rect(surface, colour, rect)
        inner = rect.inflate(-6, -6)
        pygame.draw.rect(surface, (255, 220, 80), inner)
    elif trap.trap_type == "saw":
        # Circle
        pygame.draw.circle(surface, colour, rect.center, trap.width // 2)
        pygame.draw.circle(surface, (0, 0, 0), rect.center, trap.width // 2, 2)
    else:
        pygame.draw.rect(surface, colour, rect)


def draw_sky_gradient(surface, top_colour, bottom_colour):
    """Fill the screen with a vertical gradient."""
    w, h = surface.get_size()
    for y in range(h):
        ratio = y / h
        r = int(top_colour[0] + (bottom_colour[0] - top_colour[0]) * ratio)
        g = int(top_colour[1] + (bottom_colour[1] - top_colour[1]) * ratio)
        b = int(top_colour[2] + (bottom_colour[2] - top_colour[2]) * ratio)
        pygame.draw.line(surface, (r, g, b), (0, y), (w, y))


# =============================================================================
#  HUD
# =============================================================================
def draw_hud(surface, theme_name, seed_val, block_count, trap_count):
    font = pygame.font.SysFont("consolas", 16)
    lines = [
        f"Theme: {theme_name}   Seed: {seed_val}",
        f"Blocks: {block_count}   Traps: {trap_count}",
        "Arrow Keys: scroll  |  R: regenerate  |  1/2/3: theme  |  ESC: quit",
    ]
    y = 10
    for line in lines:
        text = font.render(line, True, (255, 255, 255))
        bg = pygame.Surface((text.get_width() + 10, text.get_height() + 4), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 160))
        surface.blit(bg, (8, y - 2))
        surface.blit(text, (13, y))
        y += 22


# =============================================================================
#  MAIN LOOP
# =============================================================================
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("Procedural 2D Level Generator — Demo")
    clock = pygame.time.Clock()

    theme_name = "desert"
    seed_val = random.randint(0, 999999)
    level, palette = build_level(theme_name, seed=seed_val)

    camera_x = 0
    running = True

    while running:
        # --- events ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    seed_val = random.randint(0, 999999)
                    level, palette = build_level(theme_name, seed=seed_val)
                    camera_x = 0
                elif event.key == pygame.K_1:
                    theme_name = "desert"
                    level, palette = build_level(theme_name, seed=seed_val)
                elif event.key == pygame.K_2:
                    theme_name = "castle"
                    level, palette = build_level(theme_name, seed=seed_val)
                elif event.key == pygame.K_3:
                    theme_name = "space"
                    level, palette = build_level(theme_name, seed=seed_val)

        # --- scroll ---
        keys = pygame.key.get_pressed()
        if keys[pygame.K_RIGHT]:
            camera_x += SCROLL_SPEED
        if keys[pygame.K_LEFT]:
            camera_x = max(0, camera_x - SCROLL_SPEED)

        # --- draw ---
        draw_sky_gradient(screen, palette["sky"], palette["bg"])

        for block in level["floor"]:
            draw_block(screen, block, palette, camera_x, is_floor=True)
        for block in level["platforms"]:
            draw_block(screen, block, palette, camera_x, is_floor=False)
        for trap in level["traps"]:
            draw_trap(screen, trap, palette, camera_x)

        total_blocks = len(level["floor"]) + len(level["platforms"])
        draw_hud(screen, theme_name, seed_val, total_blocks, len(level["traps"]))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
