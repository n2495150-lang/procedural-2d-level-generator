# Procedural 2D Level Generator

A reusable Python module for procedurally generating 2D platformer levels. Drop `level_generator.py` into any Pygame project to get randomised floors, platforms, and hazard placement. No manual level design needed.

## Quick Start

```python
from level_generator import LevelGenerator

gen = LevelGenerator(block_size=64, screen_height=768, seed=42)
level = gen.generate_full_level(level_length=100)

for block in level["floor"]:
    # block.x, block.y, block.size — place your floor tile here
    ...

for block in level["platforms"]:
    # block.x, block.y, block.size — place your platform tile here
    ...

for trap in level["traps"]:
    # trap.x, trap.y, trap.trap_type ("spikes" | "fire" | "saw")
    ...
```

## How It Works

### Platform Patterns

The generator randomly picks from six built-in patterns and places them with randomised spacing:

```
single:       ■                    Basic jump
double_jump:  ■       ■            base to jump to a higher target
stack:        ■  ■                 spaced climb
staircase:    ■  ■  ■             Ascending steps
gap:          ■        ■          gap jump
bridge:       ■ ■ ■               safe area
```

### Hazard Placement

Traps are placed at regular intervals with:
- **Collision checking** — prevents overlapping with existing platforms
- **Probability control** — each trap type has a spawn chance (0–1)
- **Safe zones** — configurable area free of at level start
- **Three types**: spikes (static), fire (floor), saw (moving)

### Infinite Scrolling

For endless or very long levels, generate content on-demand as the player moves:

```python
gen = LevelGenerator(block_size=64, screen_height=768)

# In your game loop:
new_blocks, floor_edge = gen.extend_floor(player.x, floor_edge, max_x)
new_platforms, platform_edge = gen.extend_platforms(player.x, platform_edge, max_x)
```

## API Reference

### `LevelGenerator(block_size, screen_height, style, seed)`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `block_size` | int | 96 | Tile size in pixels (square) |
| `screen_height` | int | 800 | World height in pixels |
| `style` | str | "default" |  tag passed to generated objects |
| `seed` | int/None | None | Random seed for levels |

### Methods

**`generate_floor(start_col, end_col)`** → `list[BlockInfo]`

Generate a row of floor tiles from column `start_col` to `end_col`.

**`generate_platforms(start_x, end_x, spacing_range, patterns)`** → `list[BlockInfo]`

Generate platform clusters. `spacing_range` controls gap between clusters (default 5–8 blocks). `patterns` lets you limit which patterns are used.

**`generate_traps(end_x, existing_objects, ...)`** → `list[TrapInfo]`

Place hazards with collision avoidance. customizable intervals, probabilities, safe zone size, and trap dimensions.

**`generate_full_level(level_length, ...)`** → `dict`

Convenience method: generates floor + platforms + traps in one call. Returns:
```python
{
    "floor": [...],      # list[BlockInfo]
    "platforms": [...],  # list[BlockInfo]
    "traps": [...],      # list[TrapInfo]
    "end_x": 9600,       # int — rightmost boundary
}
```

**`extend_floor(player_x, floor_edge, max_x)`** → `(list[BlockInfo], int)`

For infinite scrolling: generates floor ahead of the player.

**`extend_platforms(player_x, last_platform_x, max_x, ...)`** → `(list[BlockInfo], int)`

For infinite scrolling: generates platform clusters ahead of the player.

### Data Objects

**`BlockInfo`** — describes a platform/floor tile
- `.x`, `.y`, `.size`, `.style`, `.rect`

**`TrapInfo`** — describes a hazard
- `.x`, `.y`, `.width`, `.height`, `.trap_type`, `.move_range`, `.rect`

### Custom Patterns

Register your own platform patterns:

```python
from level_generator import register_pattern, BlockInfo

def pyramid(start_x, block_size, ground_y, style):
    blocks = []
    for row in range(3):
        for col in range(3 - row):
            x = start_x + col * block_size + row * block_size // 2
            y = ground_y - block_size * (row + 2)
            blocks.append(BlockInfo(x, y, block_size, style))
    return blocks

register_pattern("pyramid", pyramid)
```

Now `"pyramid"` will appear in the random selection alongside the built-in patterns.

## Running the Demo

The visual demo lets you scroll through a generated level and switch themes:

```bash
pip install pygame
python example_usage.py
```

| Key | Action |
|-----|--------|
| ← → | Scroll camera |
| R | Regenerate (new random seed) |
| 1 / 2 / 3 | Switch theme (desert / castle / space) |
| ESC | Quit |

## Project Structure

```
procedural-2d-level-generator/
│
├── level_generator.py   # ← The main module
├── example_usage.py      # Visual demo with theme switching
└── README.md             # Documentation
```

## Custom Generation

Key parameters you can adjust:

| Parameter | Default | Effect |
|-----------|---------|--------|
| `block_size` | 96 | Tile dimensions — smaller = more detailed levels |
| `level_length` | 100 | Level width in blocks |
| `spacing_range` | (5, 8) | Gap between platform clusters — lower = denser |
| `spike_interval` | 7 | Blocks between spike spawn attempts |
| `fire_interval` | 10 | Blocks between fire spawn attempts |
| `saw_interval` | 12 | Blocks between saw spawn attempts |
| `spike_chance` | 0.50 | Probability of placing each spike |
| `fire_chance` | 0.45 | Probability of placing each fire trap |
| `saw_chance` | 0.40 | Probability of placing each saw |
| `safe_zone_blocks` | 3 | Trap-free blocks at level start |
| `seed` | None | Set for reproducible levels |

## Requirements

- Python 3.8+
- pygame

```bash
pip install pygame
```


