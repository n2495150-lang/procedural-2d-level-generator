# Procedural 2D Level Generator

A procedural content generation (PCG) system for 2D platformer games, built in Python with Pygame. Generates entire playable levels — terrain, platforms, hazards, and boss arenas — using randomised pattern selection, constraint-based placement, and theme-driven asset styling.

## Overview

This project demonstrates key procedural generation techniques applied to side-scrolling platformer level design:

| Technique | Implementation |
|-----------|---------------|
| **Pattern-Based Platform Generation** | Six distinct platform patterns (`single`, `double_jump`, `stack`, `staircase`, `gap`, `bridge`) randomly selected and placed |
| **Constraint-Based Hazard Placement** | Traps positioned using interval spacing with collision-aware overlap prevention |
| **Theme-Driven Asset Styling** | Three visual themes (Egypt, Medieval, Space) with procedurally generated textures and backgrounds |
| **Infinite Scrolling World** | Dynamic floor and platform extension as the player moves through the level |
| **Difficulty Scaling** | Probability-weighted trap density, safe zones, and progressive challenge curves |
| **Procedural Sprite Generation** | Boss characters and background tiles generated algorithmically when image assets aren't required |

## Procedural Generation Architecture

### Platform Pattern System (`main.py`, lines ~3360–3460)

The generator randomly selects from six platforming patterns, each designed around specific player skill requirements:

```
single:       ■                    (basic jump)
double_jump:  ■       ■            (stepping stone → high target)
stack:        ■  ■                 (progressive climb)
staircase:    ■  ■  ■             (ascending steps)
gap:          ■        ■          (precision gap jump)
bridge:       ■ ■ ■               (rest area / safe zone)
```

Each pattern is parameterised by:
- `start_x` — horizontal position in world space
- `block_size` — tile dimensions (default 96px)
- `screen_height` — vertical reference for placement
- `style` — theme selector (`egypt` | `medieval` | `space`)

Platform spacing is randomised (`5–8 blocks`) to prevent repetitive rhythm.

### Hazard Generation (`main.py`, lines ~3500–3635)

Three trap types are placed using interval-based distribution with collision validation:

| Trap | Interval | Probability | Placement |
|------|----------|-------------|-----------|
| **Spikes** | Every 7 blocks | 50% | Floor level |
| **Fire** | Every 10 blocks | 45% | Floor level, toggling on/off |
| **Saw** | Every 12 blocks | 40% | Elevated, moving horizontally |

Placement constraints:
- **Safe zone**: First 3 blocks are always trap-free (tutorial area)
- **Overlap prevention**: `is_clear()` checks rectangular collision against all existing objects
- **Double traps**: 35% chance of paired spike placement at wider intervals for challenge variety

### Infinite World Extension (`main.py`, lines ~4155–4180)

As the player moves, the world generates ahead:

```
extend_floor()      — Appends floor blocks when player approaches the edge
extend_platforms()   — Generates new platform clusters within view distance
```

Both functions enforce a hard `max_x` boundary to ensure finite, completable levels.

### Theme System

Each theme provides a complete visual identity through procedural generation:

**Ancient Egypt** (`create_egypt_background`)
- Sandy colour palette with gradient blending
- Procedurally drawn hieroglyphic-style decorations
- Sandstone block textures with crack details

**Medieval Europe** (`create_medieval_background`)
- Cobblestone pattern generation with mortar lines
- Grey-brown stone palette with lighting variation
- Castle wall aesthetic with randomised stone shapes

**Outer Space** (`get_space_background`)
- Star field generation with varied brightness
- Dark void colour scheme with metallic platform tiles
- Nebula-style colour gradients

## Project Structure

```
procedural-2d-level-generator/
│
├── main.py                     # Core engine (4895 lines)
│   ├── Platform Generation     # PCG pattern system (lines ~3360-3460)
│   ├── Hazard Placement        # Constraint-based trap generation (lines ~3500-3635)
│   ├── World Extension         # Infinite scrolling generation (lines ~4155-4180)
│   ├── Theme Renderers         # Procedural background/texture generation (lines ~1080-1290)
│   ├── Boss Arena Generation   # End-of-level boss area setup (lines ~4280-4310)
│   ├── Collision System        # Physics & collision detection (lines ~3640-3780)
│   ├── Player Physics          # Movement, gravity, double jump (lines ~1270-1580)
│   └── Game Loop               # Level execution & progression (lines ~4200-4480)
│
├── game_database.py            # SQLite persistence — session tracking, settings, logging
├── run_game.py                 # Auto-installer and launcher
├── requirements.txt            # Dependencies (pygame)
├── INSTALL.bat                 # One-click Windows setup
│
├── assets/                     # Sprite assets for characters, terrain, traps, items
├── data/                       # Runtime data (scores, stats, settings)
└── logs/                       # Error and event logs
```

## Key Algorithms

### Pattern Selection & Placement
```python
pattern = random.choice(['single', 'double_jump', 'stack', 'staircase', 'gap', 'bridge'])
```
Uniform random selection ensures equal probability for each pattern type. Patterns are placed with randomised horizontal spacing (`5–8 block widths`) preventing predictable rhythm.

### Collision-Aware Trap Placement
```python
def is_clear(x, y, width, height):
    trap_rect = pygame.Rect(x, y, width, height)
    for obj in objects:
        if trap_rect.colliderect(obj.rect):
            return False
    return True
```
Every trap checks for overlap with all existing objects before spawning, preventing impossible-to-navigate configurations.

### Pixel-Perfect Collision Detection
```python
if player.rect.colliderect(trap.rect):
    offset = (trap.rect.x - player.rect.x, trap.rect.y - player.rect.y)
    if player.mask and player.mask.overlap(trap.mask, offset):
        return True
```
Two-phase collision: fast rectangular pre-check, then precise pixel-mask overlap for accurate hit detection.

### Dynamic World Streaming
```python
while player.rect.right > last_platform_x - view_distance and last_platform_x + block_size * 6 < max_x:
    platform_blocks = generate_platforming_blocks_at_height(...)
    objects.extend(platform_blocks)
    last_platform_x += block_size * random.randint(5, 8)
```
Levels generate content on-demand as the player approaches ungenerated regions, bounded by `max_x` for level completion.

## Running the Generator

### Quick Start
```bash
# Windows — one-click install
INSTALL.bat

# Manual
pip install pygame
python main.py
```

### Controls
| Key | Action |
|-----|--------|
| ← → | Move left / right |
| ↑ | Jump (press again in air for double jump) |
| ESC | Pause / Menu |
| 1, 2, 3 | Select level theme |

### System Requirements
| Requirement | Minimum |
|-------------|---------|
| Python | 3.8+ |
| RAM | 512 MB |
| Display | 1024×768 |

## Generation Parameters

Key constants that control level generation (tuneable in `main.py`):

| Parameter | Value | Effect |
|-----------|-------|--------|
| `block_size` | 96px | Tile dimensions for all terrain |
| `world_length` | `MAX_WIDTH * 2 / block_size` | Total level length in blocks |
| Platform spacing | 5–8 blocks (random) | Gap between platform clusters |
| Spike interval | Every 7 blocks | Base frequency of spike hazards |
| Fire interval | Every 10 blocks | Base frequency of fire hazards |
| Saw interval | Every 12 blocks | Base frequency of saw hazards |
| Safe zone | 3 blocks | Trap-free area at level start |
| `move_range` (Saw) | 120px | Horizontal oscillation of moving saws |

## Technologies

- **Python 3** — Core language
- **Pygame** — Rendering, input, audio
- **SQLite** — Session and statistics persistence
- **Threading** — Async AI dialogue for boss encounters
- **Random** — Seeded procedural generation

## License

MIT
