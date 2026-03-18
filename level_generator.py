"""
level_generator.py — Reusable Procedural 2D Level Generator
============================================================

A standalone procedural content generation module for 2D platformer games.
Drop this file into any Pygame project and call the functions to generate
floors, platforms, and hazard layouts automatically.

No game-specific dependencies. Works with any block/trap classes that have
a pygame.Rect attribute.

Usage:
    from level_generator import LevelGenerator

    gen = LevelGenerator(block_size=96, screen_height=800)
    floor = gen.generate_floor(-10, 100)
    platforms = gen.generate_platforms(start_x=400, end_x=8000)
    traps = gen.generate_traps(end_x=8000, existing_objects=floor + platforms)

Author: n2495150-lang
License: MIT
"""

import random
import pygame


# =============================================================================
#  CORE DATA STRUCTURES
# =============================================================================

class BlockInfo:
    """
    Lightweight data object describing where a block should be placed.
    
    This is engine-agnostic — it just stores position and size.
    Your game converts these into whatever Block/Sprite class it uses.
    
    Attributes:
        x (int): World X position in pixels
        y (int): World Y position in pixels
        size (int): Block width and height (square tiles)
        style (str): Theme tag your game can use for texture selection
    """
    def __init__(self, x, y, size, style="default"):
        self.x = x
        self.y = y
        self.size = size
        self.style = style
        self.rect = pygame.Rect(x, y, size, size)

    def __repr__(self):
        return f"BlockInfo(x={self.x}, y={self.y}, size={self.size}, style='{self.style}')"


class TrapInfo:
    """
    Lightweight data object describing where a trap should be placed.
    
    Attributes:
        x (int): World X position in pixels
        y (int): World Y position in pixels
        width (int): Trap width in pixels
        height (int): Trap height in pixels
        trap_type (str): One of "spikes", "fire", "saw"
        move_range (int): For moving traps — horizontal patrol distance
    """
    def __init__(self, x, y, width, height, trap_type="spikes", move_range=0):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.trap_type = trap_type
        self.move_range = move_range
        self.rect = pygame.Rect(x, y, width, height)

    def __repr__(self):
        return f"TrapInfo(x={self.x}, y={self.y}, type='{self.trap_type}')"


# =============================================================================
#  PLATFORM PATTERNS
# =============================================================================
# Each pattern is a function that takes a starting position and returns
# a list of BlockInfo objects. Add your own patterns by following the
# same signature: f(start_x, block_size, ground_y, style) -> list[BlockInfo]
# =============================================================================

def _pattern_single(start_x, block_size, ground_y, style):
    """One block 2-3 tiles above ground. Basic single jump."""
    height = random.randint(2, 3)
    y = ground_y - block_size * height
    return [BlockInfo(start_x, y, block_size, style)]


def _pattern_double_jump(start_x, block_size, ground_y, style):
    """Stepping stone at height 2, target at height 3. Requires double jump."""
    return [
        BlockInfo(start_x, ground_y - block_size * 2, block_size, style),
        BlockInfo(start_x + block_size * 2, ground_y - block_size * 3, block_size, style),
    ]


def _pattern_stack(start_x, block_size, ground_y, style):
    """Two blocks at increasing heights. Progressive climb."""
    return [
        BlockInfo(start_x, ground_y - block_size * 2, block_size, style),
        BlockInfo(start_x + block_size, ground_y - block_size * 3, block_size, style),
    ]


def _pattern_staircase(start_x, block_size, ground_y, style):
    """Three blocks forming ascending steps."""
    blocks = []
    for i in range(3):
        x = start_x + i * block_size
        y = ground_y - block_size * (2 + i)
        blocks.append(BlockInfo(x, y, block_size, style))
    return blocks


def _pattern_gap(start_x, block_size, ground_y, style):
    """Two blocks separated by a 2-block gap. Precision jumping."""
    y = ground_y - block_size * 2
    return [
        BlockInfo(start_x, y, block_size, style),
        BlockInfo(start_x + block_size * 3, y, block_size, style),
    ]


def _pattern_bridge(start_x, block_size, ground_y, style):
    """Flat 2-3 block wide platform. Rest area / safe zone."""
    y = ground_y - block_size * 2
    width = random.randint(2, 3)
    return [BlockInfo(start_x + i * block_size, y, block_size, style) for i in range(width)]


# Registry of all available patterns — add custom ones here
PATTERNS = {
    "single": _pattern_single,
    "double_jump": _pattern_double_jump,
    "stack": _pattern_stack,
    "staircase": _pattern_staircase,
    "gap": _pattern_gap,
    "bridge": _pattern_bridge,
}


# =============================================================================
#  COLLISION CHECKER
# =============================================================================

def is_position_clear(x, y, width, height, existing_objects):
    """
    Check whether a rectangular area is free of existing objects.
    
    Args:
        x, y (int): Top-left corner of the area to check.
        width, height (int): Dimensions of the area.
        existing_objects (list): Objects with a .rect attribute.
    
    Returns:
        bool: True if the area doesn't overlap any existing object.
    """
    check_rect = pygame.Rect(x, y, width, height)
    for obj in existing_objects:
        if check_rect.colliderect(obj.rect):
            return False
    return True


# =============================================================================
#  LEVEL GENERATOR CLASS
# =============================================================================

class LevelGenerator:
    """
    Main procedural level generator.
    
    Create an instance, then call its methods to build a full level
    piece by piece — or call generate_full_level() for everything at once.
    
    Args:
        block_size (int): Tile size in pixels (tiles are square). Default 96.
        screen_height (int): Height of the game world in pixels. Default 800.
        style (str): Theme tag passed to all generated objects. Default "default".
        seed (int | None): Random seed for reproducible levels. None = random.
    
    Example:
        gen = LevelGenerator(block_size=96, screen_height=800, style="desert")
        level = gen.generate_full_level(level_length=80)
        # level["floor"]     -> list of BlockInfo
        # level["platforms"]  -> list of BlockInfo
        # level["traps"]      -> list of TrapInfo
    """

    def __init__(self, block_size=96, screen_height=800, style="default", seed=None):
        self.block_size = block_size
        self.screen_height = screen_height
        self.style = style
        self.ground_y = screen_height - block_size  # top of the floor row

        if seed is not None:
            random.seed(seed)

    # -----------------------------------------------------------------
    #  FLOOR GENERATION
    # -----------------------------------------------------------------

    def generate_floor(self, start_col=-5, end_col=100):
        """
        Generate a row of floor blocks spanning a column range.
        
        Args:
            start_col (int): First column index (can be negative for off-screen buffer).
            end_col (int): Last column index (exclusive).
        
        Returns:
            list[BlockInfo]: One BlockInfo per floor tile.
        """
        bs = self.block_size
        return [
            BlockInfo(i * bs, self.ground_y, bs, self.style)
            for i in range(start_col, end_col)
        ]

    # -----------------------------------------------------------------
    #  PLATFORM GENERATION
    # -----------------------------------------------------------------

    def generate_platforms(self, start_x=None, end_x=None,
                           spacing_range=(5, 8), patterns=None):
        """
        Generate platform clusters between start_x and end_x.
        
        Args:
            start_x (int): Starting X pixel. Default: 4 blocks from origin.
            end_x (int): Ending X pixel. Default: calculated from end_col.
            spacing_range (tuple): Min/max block-widths between clusters.
            patterns (list[str] | None): Pattern names to use. None = all.
        
        Returns:
            list[BlockInfo]: All platform blocks.
        """
        bs = self.block_size
        if start_x is None:
            start_x = 4 * bs
        if end_x is None:
            end_x = 100 * bs

        available = patterns or list(PATTERNS.keys())
        all_blocks = []
        current_x = start_x

        while current_x + bs * 6 < end_x:
            pattern_name = random.choice(available)
            pattern_fn = PATTERNS[pattern_name]
            cluster = pattern_fn(current_x, bs, self.ground_y, self.style)
            all_blocks.extend(cluster)
            current_x += bs * random.randint(*spacing_range)

        return all_blocks

    # -----------------------------------------------------------------
    #  TRAP / HAZARD GENERATION
    # -----------------------------------------------------------------

    def generate_traps(self, end_x=None, existing_objects=None,
                        trap_size=48, safe_zone_blocks=3,
                        spike_interval=7, fire_interval=10, saw_interval=12,
                        spike_chance=0.50, fire_chance=0.45, saw_chance=0.40):
        """
        Generate hazard traps throughout the level.
        
        Places spikes, fire, and saws at regular intervals with
        probability-based spawning and collision-aware placement.
        
        Args:
            end_x (int): Maximum X for trap placement.
            existing_objects (list): Objects with .rect to avoid overlapping.
            trap_size (int): Width/height of each trap in pixels.
            safe_zone_blocks (int): Trap-free zone at level start (in blocks).
            spike_interval (int): Blocks between spike placement attempts.
            fire_interval (int): Blocks between fire placement attempts.
            saw_interval (int): Blocks between saw placement attempts.
            spike_chance (float): Probability [0-1] of placing a spike.
            fire_chance (float): Probability [0-1] of placing fire.
            saw_chance (float): Probability [0-1] of placing a saw.
        
        Returns:
            list[TrapInfo]: All generated trap descriptors.
        """
        bs = self.block_size
        if end_x is None:
            end_x = 100 * bs
        if existing_objects is None:
            existing_objects = []

        traps = []
        safe_x = safe_zone_blocks * bs

        # --- Spikes (floor level) ---
        for i in range(5, 80, spike_interval):
            x = i * bs + bs // 2
            if x < safe_x or x >= end_x:
                continue
            y = self.ground_y - trap_size
            if is_position_clear(x, y, trap_size, trap_size, existing_objects) and random.random() < spike_chance:
                traps.append(TrapInfo(x, y, trap_size, trap_size, "spikes"))

        # --- Fire (floor level, toggling) ---
        for i in range(8, 70, fire_interval):
            x = i * bs + bs // 4
            if x < safe_x or x >= end_x:
                continue
            y = self.ground_y - trap_size
            if is_position_clear(x, y, trap_size, trap_size, existing_objects) and random.random() < fire_chance:
                traps.append(TrapInfo(x, y, trap_size, trap_size, "fire"))

        # --- Saws (elevated, moving) ---
        for i in range(12, 75, saw_interval):
            x = i * bs + bs
            if x < safe_x or x >= end_x:
                continue
            y = self.ground_y - bs - trap_size
            if is_position_clear(x, y, trap_size, trap_size, existing_objects) and random.random() < saw_chance:
                traps.append(TrapInfo(x, y, trap_size, trap_size, "saw", move_range=120))

        # --- Double spikes (challenge clusters) ---
        for i in range(15, 60, 16):
            x = i * bs
            if x < safe_x or x >= end_x:
                continue
            y = self.ground_y - trap_size
            if is_position_clear(x, y, trap_size * 2, trap_size, existing_objects) and random.random() < 0.35:
                traps.append(TrapInfo(x, y, trap_size, trap_size, "spikes"))
                if is_position_clear(x + trap_size + 10, y, trap_size, trap_size, existing_objects):
                    traps.append(TrapInfo(x + trap_size + 10, y, trap_size, trap_size, "spikes"))

        return traps

    # -----------------------------------------------------------------
    #  FULL LEVEL GENERATION (convenience)
    # -----------------------------------------------------------------

    def generate_full_level(self, level_length=100, spacing_range=(5, 8),
                             patterns=None, **trap_kwargs):
        """
        Generate a complete level: floor + platforms + traps.
        
        Args:
            level_length (int): Level width in blocks.
            spacing_range (tuple): Platform spacing range.
            patterns (list[str] | None): Platform patterns to use.
            **trap_kwargs: Extra arguments forwarded to generate_traps().
        
        Returns:
            dict with keys:
                "floor"      -> list[BlockInfo]
                "platforms"  -> list[BlockInfo]
                "traps"      -> list[TrapInfo]
                "end_x"      -> int (rightmost X boundary)
        """
        bs = self.block_size
        end_x = level_length * bs

        floor = self.generate_floor(start_col=-5, end_col=level_length)
        platforms = self.generate_platforms(
            start_x=4 * bs, end_x=end_x, spacing_range=spacing_range, patterns=patterns
        )
        all_solids = floor + platforms
        traps = self.generate_traps(end_x=end_x, existing_objects=all_solids, **trap_kwargs)

        return {
            "floor": floor,
            "platforms": platforms,
            "traps": traps,
            "end_x": end_x,
        }

    # -----------------------------------------------------------------
    #  INFINITE SCROLLING HELPERS
    # -----------------------------------------------------------------

    def extend_floor(self, player_x, floor_edge, max_x):
        """
        Generate more floor blocks as the player moves right.
        
        Call this every frame. Returns new blocks and the updated edge position.
        
        Args:
            player_x (int): Player's current X world position.
            floor_edge (int): Current rightmost floor X.
            max_x (int): Hard boundary — stop generating past this.
        
        Returns:
            (new_blocks, new_floor_edge): list[BlockInfo], int
        """
        bs = self.block_size
        new_blocks = []
        while player_x > floor_edge - self.screen_height and floor_edge < max_x:
            new_blocks.append(BlockInfo(floor_edge, self.ground_y, bs, self.style))
            floor_edge += bs
        return new_blocks, floor_edge

    def extend_platforms(self, player_x, last_platform_x, max_x,
                          view_distance=None, spacing_range=(5, 8)):
        """
        Generate more platform clusters as the player moves right.
        
        Args:
            player_x (int): Player's current X world position.
            last_platform_x (int): X of the last generated platform cluster.
            max_x (int): Hard boundary.
            view_distance (int): How far ahead to generate. Default: screen_height.
            spacing_range (tuple): Block-widths between clusters.
        
        Returns:
            (new_blocks, new_last_platform_x): list[BlockInfo], int
        """
        bs = self.block_size
        if view_distance is None:
            view_distance = self.screen_height

        new_blocks = []
        while (player_x > last_platform_x - view_distance
               and last_platform_x + bs * 6 < max_x):
            pattern_name = random.choice(list(PATTERNS.keys()))
            cluster = PATTERNS[pattern_name](last_platform_x, bs, self.ground_y, self.style)
            new_blocks.extend(cluster)
            last_platform_x += bs * random.randint(*spacing_range)

        return new_blocks, last_platform_x


# =============================================================================
#  CUSTOM PATTERN REGISTRATION
# =============================================================================

def register_pattern(name, func):
    """
    Register a custom platform pattern.
    
    Your function must have the signature:
        f(start_x: int, block_size: int, ground_y: int, style: str) -> list[BlockInfo]
    
    Example:
        def my_pyramid(start_x, block_size, ground_y, style):
            blocks = []
            for row in range(3):
                for col in range(3 - row):
                    x = start_x + col * block_size + row * block_size // 2
                    y = ground_y - block_size * (row + 2)
                    blocks.append(BlockInfo(x, y, block_size, style))
            return blocks
        
        register_pattern("pyramid", my_pyramid)
    """
    PATTERNS[name] = func


# =============================================================================
#  MODULE SELF-TEST
# =============================================================================

if __name__ == "__main__":
    pygame.init()
    print("=== Procedural 2D Level Generator — Self-Test ===\n")

    gen = LevelGenerator(block_size=96, screen_height=800, style="desert", seed=42)
    level = gen.generate_full_level(level_length=80)

    print(f"Floor blocks:    {len(level['floor'])}")
    print(f"Platform blocks: {len(level['platforms'])}")
    print(f"Traps:           {len(level['traps'])}")
    print(f"Level end X:     {level['end_x']}px")
    print()

    # Count trap types
    trap_counts = {}
    for t in level["traps"]:
        trap_counts[t.trap_type] = trap_counts.get(t.trap_type, 0) + 1
    for ttype, count in sorted(trap_counts.items()):
        print(f"  {ttype}: {count}")

    print("\nSample platforms (first 5):")
    for b in level["platforms"][:5]:
        print(f"  {b}")

    print("\n✓ Generation complete — all systems working.")
    pygame.quit()
