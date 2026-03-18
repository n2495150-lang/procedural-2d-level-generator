"""
==============================================================================
                      CHRONOQUEST: FRACTURES IN TIME
==============================================================================

A time-traveling 2D platformer game built with Pygame.

Game Overview:
--------------
The player takes on the role of TimeMarine 067, tasked with traveling through
three distinct time periods to defeat rogue Timekeepers who threaten the
stability of Timeline 041. Each level features unique visuals, enemies, and
a boss fight at the end.

Levels:
-------
1. Ancient Egypt      - Desert theme with Pharaoh Netriljunakhil as boss
2. Medieval Europe    - Castle/cobblestone theme with Sir Aldric the Knight
3. Outer Space        - Sci-fi theme with Commander Zyx-9 the Alien

Controls:
---------
- Arrow Left  (←)   : Move left
- Arrow Right (→)   : Move right  
- Arrow Up    (↑)   : Jump (press again in air for double jump)
- ESC               : Pause / Exit
- 1, 2, 3           : Quick level select from menu

Architecture:
-------------
The game is structured into several major sections:
1. IMPORTS & INITIALIZATION  - Pygame setup, constants, global state
2. MENU SYSTEM               - Main menu, level select, UI components
3. SPRITE UTILITIES          - Loading and caching sprite assets
4. PLAYER CLASS              - Player movement, physics, animations
5. OBJECT & BLOCK CLASSES    - Terrain blocks and platforms
6. TRAP CLASSES              - Hazards (spikes, fire, saw)
7. BOSS CLASSES              - AI-powered bosses for each level
8. PORTAL CLASS              - Level transition portals
9. PLATFORM GENERATION       - Procedural level generation
10. COLLISION HANDLERS       - Physics and collision detection
11. RENDERING                - Drawing, camera, HUD
12. MAIN GAME LOOP           - Level progression and game state

AI Integration:
---------------
Bosses feature optional AI-powered dialogue using Ollama (local AI).
If Ollama is not running, pre-written fallback dialogue is used.

Dependencies:
-------------
- pygame           : Game engine and rendering
- threading        : Async AI dialogue fetching
- queue            : Thread-safe dialogue queue
- urllib.request   : Ollama API communication
- json             : Data serialization
- math             : Trigonometry for animations
- random           : Procedural generation
- os               : File system operations

Author: ChronoQuest Development Team
Version: 1.0
License: MIT

==============================================================================
"""

# ==============================================================================
#                           IMPORTS & DEPENDENCIES
# ==============================================================================
# Standard library imports for core functionality

import os               # Operating system interface (file paths, directory changes)
import random           # Random number generation for procedural content
import math             # Mathematical functions (sin, cos for smooth animations)
import pygame           # Main game engine - handles graphics, input, audio
import threading        # Multi-threading for async AI dialogue fetching
import queue            # Thread-safe queue for passing AI responses
import urllib.request   # HTTP requests for Ollama API communication
import json             # JSON encoding/decoding for API data
import traceback        # Stack trace formatting for error reporting
from os import listdir         # List directory contents for sprite loading
from os.path import isfile, join  # Path utilities for cross-platform file access

# ==============================================================================
#                     DATABASE & LOGGING SYSTEM (Optional)
# ==============================================================================
# The game_database module provides:
#   - Player statistics persistence (high scores, play time)
#   - Settings storage (volume, last level played)
#   - Error logging with severity levels
#   - Crash report submission with email
#
# If the module is not found, the game continues without these features.
# This allows the game to run standalone without the database dependency.
# ==============================================================================
try:
    import game_database as db
    from game_database import ErrorSeverity
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    ErrorSeverity = None  # Fallback if database module unavailable
    print("Warning: game_database.py not found. Database features disabled.")

# ==============================================================================
#                        OLLAMA AI INTEGRATION
# ==============================================================================
# Ollama is a free, local AI server that runs on the user's machine.
# It provides AI-generated dialogue for boss characters, making each
# playthrough unique. If Ollama is not running, the game uses pre-written
# fallback dialogue instead.
#
# Installation: https://ollama.ai
# Usage: Run "ollama run mistral" in terminal before starting the game
#
# The AI uses the "mistral" model for generating character dialogue.
# Each boss has a custom system prompt defining their personality.
# ==============================================================================

# API endpoint for Ollama text generation
OLLAMA_URL = "http://localhost:11434/api/generate"

# Global flag indicating if Ollama AI is available
OLLAMA_AVAILABLE = False


def check_ollama():
    """
    Check if Ollama AI server is running locally.
    
    This function makes a quick HTTP request to the Ollama API to verify
    the server is running and accessible. Called once at startup.
    
    Returns:
        bool: True if Ollama is available, False otherwise
    
    Side Effects:
        Sets global OLLAMA_AVAILABLE flag
    
    Note:
        Uses a 2-second timeout to allow time for server startup
    """
    global OLLAMA_AVAILABLE
    try:
        # Attempt to fetch the list of available models from Ollama
        req = urllib.request.Request(
            "http://localhost:11434/api/tags",
            method='GET'
        )
        with urllib.request.urlopen(req, timeout=2) as response:
            data = json.loads(response.read().decode())
            # Check if at least one model is available
            if 'models' in data and len(data['models']) > 0:
                OLLAMA_AVAILABLE = True
                print(f"✓ Ollama AI available! Loaded models: {[m['name'] for m in data['models']]}")
                return True
            else:
                print("✗ Ollama running but no models loaded. Run: ollama pull neural-chat")
                OLLAMA_AVAILABLE = False
                return False
    except Exception as e:
        # Any error (connection refused, timeout, etc.) means Ollama unavailable
        print(f"✗ Ollama not available: {e}")
        OLLAMA_AVAILABLE = False
        return False


# Check for Ollama availability when game starts
check_ollama()


# ==============================================================================
#                         PYGAME INITIALIZATION
# ==============================================================================
# Initialize all Pygame subsystems (display, audio, input, etc.)
# and set up the working directory for asset loading.
# ==============================================================================

# Initialize all Pygame modules
pygame.init()

# Change working directory to the script's location
# This ensures assets are found regardless of where the game is launched from
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# ==============================================================================
#                          AUDIO INITIALIZATION
# ==============================================================================
# Initialize the audio mixer and load background music.
# If audio files are missing, the game continues silently.
# ==============================================================================

pygame.mixer.init()
try:
    # Load the default background music track
    pygame.mixer.music.load(os.path.join("assets", "europeSound.mp3"))
    pygame.mixer.music.set_volume(0.5)  # 50% volume (range: 0.0 to 1.0)
    # Play music in infinite loop (-1), starting from beginning (0.0), no fade
    pygame.mixer.music.play(loops=-1, start=0.0, fade_ms=0)
except Exception:
    # Gracefully handle missing audio file
    print("Warning: Could not load europeSound.mp3 - music disabled")


# ==============================================================================
#                          GAME CONSTANTS
# ==============================================================================
# Screen dimensions, timing, and physics constants.
# The game uses the system's screen resolution for responsive window sizing.
# ==============================================================================

# Query the current display resolution
screen_info = pygame.display.Info()

# Maximum screen dimensions - used for level generation to ensure
# the world is large enough even when window is maximized
MAX_WIDTH = screen_info.current_w    # Monitor width in pixels
MAX_HEIGHT = screen_info.current_h   # Monitor height in pixels

# Initial window size (80% of screen for comfortable windowed play)
Width = int(MAX_WIDTH * 0.8)   # Current window width (changes with resize)
Height = int(MAX_HEIGHT * 0.8)  # Current window height (changes with resize)

# Game timing
FPS = 60  # Target frames per second (affects physics calculations)
# Player physics
player_VEL = 5  # Player horizontal movement speed (pixels per frame)

# ==============================================================================
#                          DISPLAY SETUP
# ==============================================================================
# Create the game window with resizing support.
# RESIZABLE flag allows the player to adjust window size during gameplay.
# ==============================================================================

pygame.display.set_caption("ChronoQuest Fractures In Time")
window = pygame.display.set_mode((Width, Height), pygame.RESIZABLE)


# ==============================================================================
#                            MENU SYSTEM
# ==============================================================================
# The main menu provides:
#   - Game title and branding
#   - Level selection (1-3)
#   - Controls display
#   - Visual theming consistent with the game's aesthetic
#
# The menu uses a medieval font for the title to match the time-travel theme.
# All UI elements use a consistent color scheme (cyan/gold on dark background).
# ==============================================================================


def get_medieval_font(size):
    """
    Get a medieval-style font for game titles and headings.
    
    Attempts to load a gothic/blackletter font for authentic medieval feel.
    Falls back to Times New Roman if no medieval fonts are available.
    
    Args:
        size (int): Font size in points
    
    Returns:
        pygame.font.Font: The loaded font object
    
    Note:
        Font availability varies by operating system. Windows typically has
        'Old English Text MT', while Linux may have 'UnifrakturMaguntia'.
    """
    # List of medieval-style fonts to try, in order of preference
    medieval_fonts = ['Old English Text MT', 'Blackletter', 'UnifrakturMaguntia', 
                      'MedievalSharp', 'Cloister Black', 'Fraktur', 'Gothic']
    
    for font_name in medieval_fonts:
        try:
            font = pygame.font.SysFont(font_name, size)
            if font:
                return font
        except:
            continue
    
    # Fallback to a serif font for a classic look
    return pygame.font.SysFont('times new roman', size, bold=True)


def load_start_button():
    """
    Create a procedurally generated START button for the main menu.
    
    The button is a circular design with a play triangle inside,
    using the game's cyan/dark color scheme. Creating it procedurally
    ensures consistency and eliminates the need for external button assets.
    
    Returns:
        pygame.Surface: A 120x120 pixel surface containing the button graphic
    
    Visual Design:
        - Outer cyan glow ring for visibility
        - Dark center circle for contrast
        - Play triangle (right-pointing) in cyan
        - Consistent with the HUD aesthetic
    """
    size = 120
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    center = size // 2
    
    # Outer ring - cyan glow effect for visibility
    pygame.draw.circle(surface, (0, 180, 180), (center, center), 55)
    
    # Main button body - dark background
    pygame.draw.circle(surface, (25, 25, 40), (center, center), 50)
    
    # Inner highlight - slightly lighter for depth
    pygame.draw.circle(surface, (40, 40, 60), (center, center), 45)
    
    # Play triangle icon (points right)
    triangle_color = (0, 220, 220)  # Matching cyan
    play_points = [
        (center - 15, center - 25),  # Top-left vertex
        (center - 15, center + 25),  # Bottom-left vertex
        (center + 25, center)        # Right vertex (point)
    ]
    pygame.draw.polygon(surface, triangle_color, play_points)
    
    # Outer border ring
    pygame.draw.circle(surface, (0, 220, 220), (center, center), 55, 4)
    
    return surface


def draw_menu(window, bg_image, title_font, subtitle_font, start_button, button_rect):
    """
    Render the complete main menu screen.
    
    The menu features:
    - Large hourglass icon in the center (time-travel theme)
    - Game title with shadow effect
    - Subtitle with decorative line
    - Start button in center
    - Controls panel on the left
    - Level selection panel on the right
    
    Args:
        window (pygame.Surface): The display surface to draw on
        bg_image (pygame.Surface): Background tile image (unused, solid color used)
        title_font (pygame.font.Font): Font for main title
        subtitle_font (pygame.font.Font): Font for subtitle
        start_button (pygame.Surface): Pre-rendered start button image
        button_rect (pygame.Rect): Position rectangle for the start button
    
    Returns:
        tuple: (level_panel_x, level_panel_y) - Position of level select panel
               for click detection in the main_menu function
    
    Color Scheme:
        - Background: Dark blue-black (15, 15, 25)
        - Accents: Cyan (0, 220, 220)
        - Title: Gold (255, 215, 0)
        - Subtitle: Tan (200, 180, 140)
    """
    # Fill entire background with HUD color (dark blue-black)
    bg_color = (15, 15, 25)
    window.fill(bg_color)
    
    # Draw large hourglass in the center background
    hourglass_color = (0, 80, 80)  # Subtle cyan hourglass
    frame_color = (0, 120, 120)  # Slightly brighter for frame
    
    hg_center_x = Width // 2
    hg_center_y = Height // 2
    hg_width = min(Width, Height) // 3  # Scale based on screen size
    hg_height = int(hg_width * 1.5)
    
    # Top triangle of hourglass
    top_points = [
        (hg_center_x - hg_width//2, hg_center_y - hg_height//2),
        (hg_center_x + hg_width//2, hg_center_y - hg_height//2),
        (hg_center_x, hg_center_y)
    ]
    pygame.draw.polygon(window, hourglass_color, top_points)
    
    # Bottom triangle of hourglass
    bottom_points = [
        (hg_center_x, hg_center_y),
        (hg_center_x - hg_width//2, hg_center_y + hg_height//2),
        (hg_center_x + hg_width//2, hg_center_y + hg_height//2)
    ]
    pygame.draw.polygon(window, hourglass_color, bottom_points)
    
    # Hourglass frame outline
    pygame.draw.lines(window, frame_color, True, top_points, 4)
    pygame.draw.lines(window, frame_color, True, bottom_points, 4)
    
    # Top and bottom caps of hourglass
    cap_extend = 15
    pygame.draw.line(window, frame_color, 
                     (hg_center_x - hg_width//2 - cap_extend, hg_center_y - hg_height//2),
                     (hg_center_x + hg_width//2 + cap_extend, hg_center_y - hg_height//2), 6)
    pygame.draw.line(window, frame_color, 
                     (hg_center_x - hg_width//2 - cap_extend, hg_center_y + hg_height//2),
                     (hg_center_x + hg_width//2 + cap_extend, hg_center_y + hg_height//2), 6)
    
    # Draw title "ChronoQuest"
    title_text = title_font.render("ChronoQuest", True, (255, 215, 0))
    title_shadow = title_font.render("ChronoQuest", True, (80, 50, 20))
    title_rect = title_text.get_rect(center=(Width // 2, Height // 3 - 30))
    
    # Draw shadow first (offset)
    shadow_rect = title_rect.copy()
    shadow_rect.x += 4
    shadow_rect.y += 4
    window.blit(title_shadow, shadow_rect)
    window.blit(title_text, title_rect)
    
    # Draw subtitle "Fractures In Time"
    subtitle_text = subtitle_font.render("Fractures In Time", True, (200, 180, 140))
    subtitle_shadow = subtitle_font.render("Fractures In Time", True, (60, 40, 20))
    subtitle_rect = subtitle_text.get_rect(center=(Width // 2, Height // 3 + 40))
    
    # Draw shadow
    sub_shadow_rect = subtitle_rect.copy()
    sub_shadow_rect.x += 3
    sub_shadow_rect.y += 3
    window.blit(subtitle_shadow, sub_shadow_rect)
    window.blit(subtitle_text, subtitle_rect)
    
    # Draw decorative line
    line_y = Height // 3 + 80
    pygame.draw.line(window, (255, 215, 0), (Width // 2 - 150, line_y), (Width // 2 + 150, line_y), 3)
    
    # Draw start button
    window.blit(start_button, button_rect)
    
    # Draw "START" text below button
    start_font = pygame.font.SysFont('times new roman', 28, bold=True)
    start_text = start_font.render("START", True, (255, 255, 255))
    start_text_rect = start_text.get_rect(center=(Width // 2, button_rect.bottom + 25))
    window.blit(start_text, start_text_rect)
    
    # Draw controls section on the left side - using consolas font to match HUD
    try:
        controls_font = pygame.font.SysFont('consolas', 18, bold=True)
        controls_small_font = pygame.font.SysFont('consolas', 16, bold=True)
    except:
        controls_font = pygame.font.SysFont('arial', 18, bold=True)
        controls_small_font = pygame.font.SysFont('arial', 16, bold=True)
    
    # Controls box position and dimensions
    controls_x = 30
    controls_y = Height // 2 - 60
    panel_width = 260
    panel_height = 180
    
    # Draw solid color background panel
    panel_bg = (25, 25, 40)  # Slightly lighter than main background for contrast
    border_color = (0, 220, 220)  # Cyan border matching HUD
    border_glow = (0, 180, 180, 100)
    
    # Draw panel with glow effect
    glow_surface = pygame.Surface((panel_width + 6, panel_height + 6), pygame.SRCALPHA)
    pygame.draw.rect(glow_surface, border_glow, glow_surface.get_rect(), border_radius=12)
    window.blit(glow_surface, (controls_x - 3, controls_y - 3))
    
    # Main panel background
    panel_surface = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
    pygame.draw.rect(panel_surface, panel_bg + (240,), panel_surface.get_rect(), border_radius=10)
    window.blit(panel_surface, (controls_x, controls_y))
    
    # Border
    panel_rect = pygame.Rect(controls_x, controls_y, panel_width, panel_height)
    pygame.draw.rect(window, border_color, panel_rect, 3, border_radius=10)
    
    # Inner border accent
    inner_rect = pygame.Rect(controls_x + 4, controls_y + 4, panel_width - 8, panel_height - 8)
    pygame.draw.rect(window, (border_color[0]//3, border_color[1]//3, border_color[2]//3), inner_rect, 1, border_radius=8)
    
    # Draw "CONTROLS" header with gold text
    gold_text = (255, 215, 0)
    cyan_text = (0, 230, 230)
    controls_header = controls_font.render("CONTROLS", True, gold_text)
    header_rect = controls_header.get_rect(centerx=controls_x + panel_width // 2, top=controls_y + 12)
    window.blit(controls_header, header_rect)
    
    # Decorative line under header
    line_y = controls_y + 35
    pygame.draw.line(window, cyan_text, (controls_x + 20, line_y), (controls_x + panel_width - 20, line_y), 1)
    
    # Draw control instructions
    controls_list = [
        "→  Right Arrow - Move Right",
        "←  Left Arrow - Move Left",
        "↑  Up Arrow - Jump",
        "↑↑ Double Jump in Air"
    ]
    
    text_start_y = controls_y + 50
    for i, text in enumerate(controls_list):
        control_text = controls_small_font.render(text, True, (200, 220, 220))
        text_rect = control_text.get_rect(left=controls_x + 15, top=text_start_y + i * 28)
        window.blit(control_text, text_rect)
    
    # Draw level select panel on the right side
    level_panel_width = 200
    level_panel_height = 180
    level_panel_x = Width - level_panel_width - 30
    level_panel_y = Height // 2 - 60
    
    # Panel background with glow
    level_glow_surface = pygame.Surface((level_panel_width + 6, level_panel_height + 6), pygame.SRCALPHA)
    pygame.draw.rect(level_glow_surface, border_glow, level_glow_surface.get_rect(), border_radius=12)
    window.blit(level_glow_surface, (level_panel_x - 3, level_panel_y - 3))
    
    level_panel_surface = pygame.Surface((level_panel_width, level_panel_height), pygame.SRCALPHA)
    pygame.draw.rect(level_panel_surface, panel_bg + (240,), level_panel_surface.get_rect(), border_radius=10)
    window.blit(level_panel_surface, (level_panel_x, level_panel_y))
    
    level_panel_rect = pygame.Rect(level_panel_x, level_panel_y, level_panel_width, level_panel_height)
    pygame.draw.rect(window, border_color, level_panel_rect, 3, border_radius=10)
    
    # Inner border
    level_inner_rect = pygame.Rect(level_panel_x + 4, level_panel_y + 4, level_panel_width - 8, level_panel_height - 8)
    pygame.draw.rect(window, (border_color[0]//3, border_color[1]//3, border_color[2]//3), level_inner_rect, 1, border_radius=8)
    
    # Header
    level_header = controls_font.render("SELECT LEVEL", True, gold_text)
    level_header_rect = level_header.get_rect(centerx=level_panel_x + level_panel_width // 2, top=level_panel_y + 12)
    window.blit(level_header, level_header_rect)
    
    # Decorative line
    level_line_y = level_panel_y + 35
    pygame.draw.line(window, cyan_text, (level_panel_x + 20, level_line_y), (level_panel_x + level_panel_width - 20, level_line_y), 1)
    
    # Instruction caption below the level panel
    instruction_text = controls_small_font.render("Click level, then START", True, (150, 180, 180))
    instruction_rect = instruction_text.get_rect(centerx=level_panel_x + level_panel_width // 2, top=level_panel_y + level_panel_height + 10)
    window.blit(instruction_text, instruction_rect)
    
    # Return level button rects for click detection (don't flip here - do it after buttons are drawn)
    return level_panel_x, level_panel_y


def draw_level_buttons(window, level_panel_x, level_panel_y, selected_level, hover_level):
    """Draw the level selection buttons."""
    level_names = ["Egypt", "Medieval", "Space"]
    level_colors = [(255, 200, 100), (150, 150, 200), (100, 255, 150)]
    
    button_rects = []
    button_width = 160
    button_height = 35
    button_start_y = level_panel_y + 50
    
    try:
        button_font = pygame.font.SysFont('consolas', 16, bold=True)
    except:
        button_font = pygame.font.SysFont('arial', 16, bold=True)
    
    for i, (name, color) in enumerate(zip(level_names, level_colors)):
        button_x = level_panel_x + 20
        button_y = button_start_y + i * 42
        button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
        button_rects.append(button_rect)
        
        # Button background - highlight if selected or hovered
        if i + 1 == selected_level:
            bg_color = (50, 70, 80)
            border_col = (0, 220, 220)
        elif i + 1 == hover_level:
            bg_color = (35, 45, 55)
            border_col = (0, 180, 180)
        else:
            bg_color = (25, 30, 40)
            border_col = (60, 70, 80)
        
        pygame.draw.rect(window, bg_color, button_rect, border_radius=6)
        pygame.draw.rect(window, border_col, button_rect, 2, border_radius=6)
        
        # Level number circle
        circle_x = button_x + 18
        circle_y = button_y + button_height // 2
        pygame.draw.circle(window, color, (circle_x, circle_y), 12)
        pygame.draw.circle(window, (255, 255, 255), (circle_x, circle_y), 12, 2)
        
        # Level number
        num_text = button_font.render(str(i + 1), True, (20, 20, 20))
        num_rect = num_text.get_rect(center=(circle_x, circle_y))
        window.blit(num_text, num_rect)
        
        # Level name
        name_text = button_font.render(name, True, (220, 230, 240))
        name_rect = name_text.get_rect(left=button_x + 38, centery=button_y + button_height // 2)
        window.blit(name_text, name_rect)
    
    return button_rects


def main_menu(window):
    """Display the main menu and wait for user to start the game. Returns selected level."""
    global Width, Height
    
    bg_image = get_background("Blue.png")
    clock = pygame.time.Clock()
    
    # Load fonts
    title_font = get_medieval_font(72)
    subtitle_font = get_medieval_font(36)
    
    # Load start button
    start_button = load_start_button()
    
    selected_level = 1
    hover_level = 0
    
    # Menu loop
    running = True
    while running:
        clock.tick(FPS)
        
        # Get current window size (handles resizing)
        current_width, current_height = window.get_size()
        Width = current_width
        Height = current_height
        
        # Calculate button positions based on current window size
        button_rect = start_button.get_rect(center=(Width // 2, Height // 2 + 80))
        
        level_panel_x = Width - 200 - 30
        level_panel_y = Height // 2 - 60
        button_width = 160
        button_height = 35
        button_start_y = level_panel_y + 50
        
        level_button_rects = []
        for i in range(3):
            button_x = level_panel_x + 20
            button_y = button_start_y + i * 42
            level_button_rects.append(pygame.Rect(button_x, button_y, button_width, button_height))
        
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            elif event.type == pygame.VIDEORESIZE:
                Width = event.w
                Height = event.h
                window = pygame.display.set_mode((Width, Height), pygame.RESIZABLE)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click only
                    click_pos = event.pos
                    
                    # Check level button clicks
                    for i, rect in enumerate(level_button_rects):
                        if rect.collidepoint(click_pos):
                            selected_level = i + 1
                            break
                    
                    # Check start button click
                    if button_rect.collidepoint(click_pos):
                        return selected_level
                        
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    return selected_level
                elif event.key == pygame.K_1:
                    selected_level = 1
                elif event.key == pygame.K_2:
                    selected_level = 2
                elif event.key == pygame.K_3:
                    selected_level = 3
        
        # Update hover state
        mouse_pos = pygame.mouse.get_pos()
        hover_level = 0
        for i, rect in enumerate(level_button_rects):
            if rect.collidepoint(mouse_pos):
                hover_level = i + 1
        
        # Draw menu
        draw_menu(window, bg_image, title_font, subtitle_font, start_button, button_rect)
        draw_level_buttons(window, level_panel_x, level_panel_y, selected_level, hover_level)
        
        # Update display
        pygame.display.flip()
    
    return 1


# CRASH SCREEN AND ERROR REPORTING

def is_valid_email(email):
    """Simple email validation."""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def show_crash_screen(window, category, message, exception=None, traceback_str=None):
    """
    Display a crash screen that asks for user's email to send crash report.
    
    Args:
        window: Pygame display surface
        category: Error category
        message: Error message
        exception: The exception object
        traceback_str: Full traceback string
    
    Returns:
        bool: True if crash report was submitted, False if user skipped
    """
    global Width, Height
    
    clock = pygame.time.Clock()
    
    # Try to get saved email
    saved_email = ""
    if DATABASE_AVAILABLE:
        saved_email = db.get_user_email() or ""
    
    user_email = saved_email
    input_active = True
    cursor_visible = True
    cursor_timer = 0
    
    # Fonts
    try:
        title_font = pygame.font.SysFont('consolas', 36, bold=True)
        text_font = pygame.font.SysFont('consolas', 20)
        small_font = pygame.font.SysFont('consolas', 16)
        input_font = pygame.font.SysFont('consolas', 22)
    except:
        title_font = pygame.font.SysFont('arial', 36, bold=True)
        text_font = pygame.font.SysFont('arial', 20)
        small_font = pygame.font.SysFont('arial', 16)
        input_font = pygame.font.SysFont('arial', 22)
    
    # Colors
    bg_color = (25, 15, 15)  # Dark red-tinted background
    error_red = (255, 80, 80)
    text_color = (220, 220, 220)
    dim_text = (150, 150, 150)
    input_bg = (40, 40, 50)
    input_border = (100, 100, 120)
    input_active_border = (0, 200, 200)
    button_color = (60, 60, 80)
    button_hover = (80, 80, 100)
    submit_color = (40, 120, 80)
    submit_hover = (50, 150, 100)
    
    # UI element positions
    input_width = min(400, Width - 100)
    input_height = 40
    input_x = (Width - input_width) // 2
    input_y = Height // 2
    input_rect = pygame.Rect(input_x, input_y, input_width, input_height)
    
    button_width = 120
    button_height = 40
    button_y = input_y + 70
    
    submit_rect = pygame.Rect(Width // 2 - button_width - 20, button_y, button_width, button_height)
    skip_rect = pygame.Rect(Width // 2 + 20, button_y, button_width, button_height)
    
    email_error = ""
    submitted = False
    
    running = True
    while running:
        clock.tick(30)
        cursor_timer += 1
        if cursor_timer >= 15:
            cursor_visible = not cursor_visible
            cursor_timer = 0
        
        mouse_pos = pygame.mouse.get_pos()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                
            elif event.type == pygame.VIDEORESIZE:
                Width, Height = event.w, event.h
                window = pygame.display.set_mode((Width, Height), pygame.RESIZABLE)
                # Recalculate positions
                input_x = (Width - input_width) // 2
                input_y = Height // 2
                input_rect = pygame.Rect(input_x, input_y, input_width, input_height)
                button_y = input_y + 70
                submit_rect = pygame.Rect(Width // 2 - button_width - 20, button_y, button_width, button_height)
                skip_rect = pygame.Rect(Width // 2 + 20, button_y, button_width, button_height)
                
            elif event.type == pygame.KEYDOWN:
                if input_active:
                    if event.key == pygame.K_BACKSPACE:
                        user_email = user_email[:-1]
                    elif event.key == pygame.K_RETURN:
                        # Try to submit
                        if is_valid_email(user_email):
                            email_error = ""
                            if DATABASE_AVAILABLE:
                                db.set_user_email(user_email)
                                db.submit_crash_report(category, message, exception, traceback_str, user_email)
                            submitted = True
                            running = False
                        else:
                            email_error = "Please enter a valid email address"
                    elif event.key == pygame.K_ESCAPE:
                        running = False
                    else:
                        # Add character to email (limit length)
                        if len(user_email) < 50 and event.unicode.isprintable():
                            user_email += event.unicode
                            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    # Check if clicked on input
                    input_active = input_rect.collidepoint(mouse_pos)
                    
                    # Check submit button
                    if submit_rect.collidepoint(mouse_pos):
                        if is_valid_email(user_email):
                            email_error = ""
                            if DATABASE_AVAILABLE:
                                db.set_user_email(user_email)
                                db.submit_crash_report(category, message, exception, traceback_str, user_email)
                            submitted = True
                            running = False
                        else:
                            email_error = "Please enter a valid email address"
                    
                    # Check skip button
                    if skip_rect.collidepoint(mouse_pos):
                        running = False
        
        # Draw crash screen
        window.fill(bg_color)
        
        # Draw error icon (X in circle)
        icon_y = Height // 4
        pygame.draw.circle(window, error_red, (Width // 2, icon_y), 50, 5)
        pygame.draw.line(window, error_red, (Width // 2 - 25, icon_y - 25), (Width // 2 + 25, icon_y + 25), 5)
        pygame.draw.line(window, error_red, (Width // 2 + 25, icon_y - 25), (Width // 2 - 25, icon_y + 25), 5)
        
        # Title
        title_text = title_font.render("GAME CRASHED", True, error_red)
        title_rect = title_text.get_rect(center=(Width // 2, icon_y + 80))
        window.blit(title_text, title_rect)
        
        # Error message
        error_msg = text_font.render(f"{category}: {message[:50]}{'...' if len(message) > 50 else ''}", True, text_color)
        error_rect = error_msg.get_rect(center=(Width // 2, icon_y + 120))
        window.blit(error_msg, error_rect)
        
        # Help text
        help_text = small_font.render("Help us fix this! Enter your email to send a crash report:", True, dim_text)
        help_rect = help_text.get_rect(center=(Width // 2, input_y - 30))
        window.blit(help_text, help_rect)
        
        # Email input box
        border_color = input_active_border if input_active else input_border
        pygame.draw.rect(window, input_bg, input_rect, border_radius=5)
        pygame.draw.rect(window, border_color, input_rect, 2, border_radius=5)
        
        # Email text
        display_email = user_email
        if input_active and cursor_visible:
            display_email += "|"
        email_surface = input_font.render(display_email, True, text_color)
        # Clip text to input box
        email_x = input_rect.x + 10
        email_y = input_rect.y + (input_height - email_surface.get_height()) // 2
        window.blit(email_surface, (email_x, email_y))
        
        # Placeholder text if empty
        if not user_email and not input_active:
            placeholder = input_font.render("your.email@example.com", True, dim_text)
            window.blit(placeholder, (email_x, email_y))
        
        # Email validation error
        if email_error:
            error_surface = small_font.render(email_error, True, error_red)
            error_rect = error_surface.get_rect(center=(Width // 2, input_y + input_height + 15))
            window.blit(error_surface, error_rect)
        
        # Submit button
        submit_bg = submit_hover if submit_rect.collidepoint(mouse_pos) else submit_color
        pygame.draw.rect(window, submit_bg, submit_rect, border_radius=5)
        pygame.draw.rect(window, (80, 180, 120), submit_rect, 2, border_radius=5)
        submit_text = text_font.render("SEND", True, (255, 255, 255))
        submit_text_rect = submit_text.get_rect(center=submit_rect.center)
        window.blit(submit_text, submit_text_rect)
        
        # Skip button
        skip_bg = button_hover if skip_rect.collidepoint(mouse_pos) else button_color
        pygame.draw.rect(window, skip_bg, skip_rect, border_radius=5)
        pygame.draw.rect(window, input_border, skip_rect, 2, border_radius=5)
        skip_text = text_font.render("SKIP", True, text_color)
        skip_text_rect = skip_text.get_rect(center=skip_rect.center)
        window.blit(skip_text, skip_text_rect)
        
        # Footer text
        footer = small_font.render("Your email will only be used to follow up on this crash.", True, dim_text)
        footer_rect = footer.get_rect(center=(Width // 2, Height - 50))
        window.blit(footer, footer_rect)
        
        press_esc = small_font.render("Press ESC to close without sending", True, dim_text)
        esc_rect = press_esc.get_rect(center=(Width // 2, Height - 30))
        window.blit(press_esc, esc_rect)
        
        pygame.display.flip()
    
    return submitted


# ==============================================================================
#                         SPRITE UTILITIES
# ==============================================================================
# Functions for loading, caching, and manipulating sprite graphics.
# Sprites are loaded from the assets folder and cached for performance.
#
# The game uses sprite sheets - single images containing multiple animation
# frames arranged in a row. These functions extract individual frames and
# optionally create mirrored versions for left/right facing animations.
# ==============================================================================


def flip(sprites):
    """
    Mirror a list of sprites horizontally to create left-facing versions.
    
    Used to create left-facing character animations from right-facing sprites,
    eliminating the need for duplicate sprite assets.
    
    Args:
        sprites (list): List of pygame.Surface objects (right-facing)
    
    Returns:
        list: New list of horizontally flipped surfaces (left-facing)
    
    Example:
        right_run = [frame1, frame2, frame3]
        left_run = flip(right_run)  # Mirrored versions
    """
    return [pygame.transform.flip(sprite, True, False) for sprite in sprites]


def load_sprite_sheets(dir1, dir2, width, height, direction=False):
    """
    Load all animation sprite sheets from a character folder.
    
    Scans the specified directory for PNG files, each representing a different
    animation (idle, run, jump, etc.). Each file is a horizontal strip of
    frames that are extracted and optionally doubled in size.
    
    Args:
        dir1 (str): First directory level (e.g., "MainCharacters")
        dir2 (str): Second directory level (e.g., "VirtualGuy")
        width (int): Width of each frame in the sprite sheet
        height (int): Height of each frame in the sprite sheet
        direction (bool): If True, create both _right and _left versions
    
    Returns:
        dict: Animation name -> list of frame surfaces
              If direction=True: {"run_right": [...], "run_left": [...], ...}
              If direction=False: {"run": [...], "idle": [...], ...}
    
    File Structure Expected:
        assets/
          MainCharacters/
            VirtualGuy/
              idle.png      # Horizontal strip of idle frames
              run.png       # Horizontal strip of run frames
              jump.png      # Single jump frame or strip
              ...
    
    Note:
        Frames are automatically scaled 2x using pygame.transform.scale2x()
        for better visibility on modern high-resolution displays.
    """
    path = join("Assets", dir1, dir2)
    images = [f for f in listdir(path) if isfile(join(path, f)) and f.endswith(".png")]
    all_sprites = {}

    for image in images:
        # Load the sprite sheet image with alpha channel
        sprite_sheet = pygame.image.load(join(path, image)).convert_alpha()
        sprites = []
        
        # Calculate number of frames based on image width
        num_frames = sprite_sheet.get_width() // width
        
        for i in range(num_frames):
            # Create a new surface for this frame
            surface = pygame.Surface((width, height), pygame.SRCALPHA, 32)
            # Define the region to extract from the sprite sheet
            rect = pygame.Rect(i * width, 0, width, height)
            # Copy the frame from the sheet
            surface.blit(sprite_sheet, (0, 0), rect)
            # Scale up 2x for better visibility
            sprites.append(pygame.transform.scale2x(surface))

        # Generate animation name from filename
        if direction:
            # Create both right and left facing versions
            all_sprites[image.replace(".png", "") + "_right"] = sprites
            all_sprites[image.replace(".png", "") + "_left"] = flip(sprites)
        else:
            all_sprites[image.replace(".png", "")] = sprites

    return all_sprites

# ==============================================================================
#                        BLOCK SPRITE CACHING
# ==============================================================================
# Terrain blocks are cached to avoid reloading textures every frame.
# Each level style (Egypt, Medieval, Space) has its own cache.
# This significantly improves performance when rendering many blocks.
# ==============================================================================

# Cache dictionary for Egypt-style sandy blocks
_block_cache = {}


def get_block(size):
    """
    Get a sandy Egypt-style block tile, using cache for performance.
    
    Loads the terrain texture once and caches it. Subsequent calls
    return the cached version, avoiding expensive disk I/O.
    
    Args:
        size (int): Block size in pixels (typically 96)
    
    Returns:
        pygame.Surface: The scaled block texture (2x original size)
    
    Cache Behavior:
        First call: Loads from disk, caches, returns
        Subsequent calls: Returns cached version immediately
    """
    if size in _block_cache:
        return _block_cache[size]
    
    # Load the terrain sprite sheet
    path = join("assets", "Terrain", "Terrain.png")
    image = pygame.image.load(path).convert_alpha()
    
    # Create surface for the block
    surface = pygame.Surface((size, size), pygame.SRCALPHA, 32)
    
    # Extract sandy/desert block from terrain sheet (row 1, position 96,64)
    rect = pygame.Rect(96, 64, size, size)
    surface.blit(image, (0, 0), rect)
    
    # Scale up 2x for visibility
    result = pygame.transform.scale2x(surface)
    
    # Cache for future use
    _block_cache[size] = result
    return result


def get_background(name):
    """
    Load a background image from the assets folder.
    
    Args:
        name (str): Filename of the background (e.g., "Blue.png")
    
    Returns:
        pygame.Surface: The loaded background image
    """
    image = pygame.image.load(os.path.join("Assets", "Background", name)).convert()
    return image


def create_egypt_background(width=64, height=64):
    """
    Create a procedurally generated Egypt-themed background tile.
    
    Generates a small tile that can be repeated to fill the screen.
    Features a desert sky gradient, distant pyramids, and a sun.
    
    Args:
        width (int): Tile width in pixels (default: 64)
        height (int): Tile height in pixels (default: 64)
    
    Returns:
        pygame.Surface: The generated background tile
    
    Visual Elements:
        - Top half: Sky gradient (light blue to warm orange)
        - Bottom half: Sandy desert gradient
        - Distant pyramid silhouettes
        - Sun in the corner
    """
    surface = pygame.Surface((width, height))
    
    # ===========================================================================
    # SKY AND SAND GRADIENT
    # ===========================================================================
    # Draw horizontal lines from top to bottom, gradually changing color.
    # Top 50%: Sky colors (blue fading to warm yellow)
    # Bottom 50%: Sand colors (sandy orange to darker tan)
    # ===========================================================================
    for y in range(height):
        ratio = y / height  # 0.0 at top, 1.0 at bottom
        
        if ratio < 0.5:
            # Sky portion - interpolate from light blue to warm yellow
            sky_ratio = ratio / 0.5  # 0.0 to 1.0 within sky region
            r = int(135 + (230 - 135) * sky_ratio)  # 135 -> 230
            g = int(206 + (190 - 206) * sky_ratio)  # 206 -> 190
            b = int(235 + (100 - 235) * sky_ratio)  # 235 -> 100
        else:
            # Desert/sand portion - warm sandy colors
            sand_ratio = (ratio - 0.5) / 0.5  # 0.0 to 1.0 within sand region
            r = int(230 + (210 - 230) * sand_ratio)
            g = int(190 + (160 - 190) * sand_ratio)
            b = int(100 + (80 - 100) * sand_ratio)
        
        pygame.draw.line(surface, (r, g, b), (0, y), (width, y))
    
    # Color definitions for decorative elements
    sand_color = (220, 180, 120)
    sand_dark = (190, 150, 90)
    pyramid_color = (180, 140, 80)
    
    # ===========================================================================
    # PYRAMID SILHOUETTES
    # ===========================================================================
    # Draw simple triangular pyramids in the distance for atmosphere.
    # Small pyramid on left, larger pyramid on right.
    # ===========================================================================
    
    # Small pyramid (left side)
    pyramid_points = [(5, height - 10), (15, height - 25), (25, height - 10)]
    pygame.draw.polygon(surface, pyramid_color, pyramid_points)
    
    # Larger pyramid (right side)
    pyramid_points2 = [(40, height - 10), (52, height - 30), (64, height - 10)]
    pygame.draw.polygon(surface, pyramid_color, pyramid_points2)
    
    # ===========================================================================
    # SUN
    # ===========================================================================
    # Draw a glowing sun in the top-right corner.
    # ===========================================================================
    sun_color = (255, 220, 100)
    pygame.draw.circle(surface, sun_color, (width - 12, 12), 8)
    
    return surface.convert()


def create_medieval_background(width=64, height=64):
    """Create a procedurally generated Medieval Europe cobblestone-themed background."""
    surface = pygame.Surface((width, height))
    
    # Gloomy overcast sky gradient
    for y in range(height):
        ratio = y / height
        if ratio < 0.4:
            # Overcast sky - grey to dark grey
            sky_ratio = ratio / 0.4
            r = int(120 + (80 - 120) * sky_ratio)
            g = int(130 + (90 - 130) * sky_ratio)
            b = int(150 + (110 - 150) * sky_ratio)
        else:
            # Ground/castle wall area - stone grey
            ground_ratio = (ratio - 0.4) / 0.6
            r = int(80 + (60 - 80) * ground_ratio)
            g = int(90 + (70 - 90) * ground_ratio)
            b = int(110 + (85 - 110) * ground_ratio)
        
        pygame.draw.line(surface, (r, g, b), (0, y), (width, y))
    
    # Draw cobblestone pattern
    stone_colors = [
        (70, 75, 85),
        (80, 85, 95),
        (65, 70, 80),
        (75, 80, 90)
    ]
    
    # Create cobblestone grid pattern
    stone_size = 10
    for row in range(int(height * 0.4) // stone_size, height // stone_size + 1):
        offset = (row % 2) * (stone_size // 2)
        for col in range(-1, width // stone_size + 2):
            x = col * stone_size + offset
            y = row * stone_size
            color = random.choice(stone_colors)
            pygame.draw.rect(surface, color, (x, y, stone_size - 1, stone_size - 1))
            # Add mortar lines
            mortar_color = (50, 55, 65)
            pygame.draw.rect(surface, mortar_color, (x, y, stone_size, stone_size), 1)
    
    # Draw distant castle silhouette
    castle_color = (50, 55, 65)
    # Main tower
    pygame.draw.rect(surface, castle_color, (10, height - 35, 15, 25))
    # Battlements
    for i in range(3):
        pygame.draw.rect(surface, castle_color, (10 + i * 5, height - 40, 4, 5))
    # Second tower
    pygame.draw.rect(surface, castle_color, (40, height - 28, 12, 18))
    for i in range(2):
        pygame.draw.rect(surface, castle_color, (40 + i * 5, height - 32, 4, 4))
    
    # Dim moon in overcast sky
    moon_color = (180, 190, 200)
    pygame.draw.circle(surface, moon_color, (width - 15, 15), 6)
    
    return surface.convert()


# Cache for medieval block images
_block_medieval_cache = {}

def get_block_medieval(size):
    """Get a medieval-style stone block from terrain.png."""
    if size in _block_medieval_cache:
        return _block_medieval_cache[size]
    path = join("assets", "Terrain", "Terrain.png")
    image = pygame.image.load(path).convert_alpha()
    surface = pygame.Surface((size, size), pygame.SRCALPHA, 32)
    # Use grey stone block from terrain.png (different position than sand block)
    # Row 0, column 0 is usually a grey/neutral stone
    rect = pygame.Rect(0, 0, size, size)
    surface.blit(image, (0, 0), rect)
    result = pygame.transform.scale2x(surface)
    _block_medieval_cache[size] = result
    return result


# Cache for space block images
_block_space_cache = {}

def get_block_space(size):
    """Get a space-themed block (purple/dark blue metallic)."""
    if size in _block_space_cache:
        return _block_space_cache[size]
    path = join("assets", "Terrain", "Terrain.png")
    image = pygame.image.load(path).convert_alpha()
    surface = pygame.Surface((size, size), pygame.SRCALPHA, 32)
    # Use a different block position for space theme (row 2, purple-ish block)
    rect = pygame.Rect(96, 128, size, size)
    surface.blit(image, (0, 0), rect)
    result = pygame.transform.scale2x(surface)
    _block_space_cache[size] = result
    return result


def get_space_background():
    """Load the space background image."""
    path = join("assets", "Background", "Space Background.png")
    return pygame.image.load(path).convert()


# ==============================================================================
#                           PLAYER CLASS
# ==============================================================================
# The Player class represents the main character controlled by the user.
# It handles:
#   - Movement (left/right walking)
#   - Jumping (single and double jump)
#   - Physics (gravity, velocity, falling)
#   - Animation state machine (idle, run, jump, fall)
#   - Collision detection using pixel-perfect masks
#
# The player character is "VirtualGuy" from the sprite assets.
# ==============================================================================


class Player(pygame.sprite.Sprite):
    """
    The main player character sprite.
    
    Inherits from pygame.sprite.Sprite for compatibility with sprite groups
    and built-in collision detection.
    
    Attributes:
        rect (pygame.Rect): Collision hitbox (position and size)
        x_vel (int): Horizontal velocity (negative = left, positive = right)
        y_vel (float): Vertical velocity (negative = up, positive = down)
        mask (pygame.Mask): Pixel-perfect collision mask from current sprite
        direction (str): "left" or "right" - current facing direction
        animation_count (int): Frame counter for animation timing
        fall_count (int): Frames spent falling (used for gravity acceleration)
        jump_count (int): Number of jumps used (0=ground, 1=jumped, 2=double jumped)
        sprite (pygame.Surface): Current animation frame being displayed
    
    Physics Model:
        - Gravity accelerates the player downward over time
        - Terminal velocity is capped to prevent excessive speed
        - Double jump resets vertical velocity for second jump
    """
    
    # Class constants
    COLOR = (255, 0, 0)  # Debug color (not used in normal rendering)
    Gravity = 1          # Gravity acceleration constant
    
    # Pre-load all character sprites at class definition time
    # This happens once when the module loads, not per-instance
    SPRITES = load_sprite_sheets("MainCharacters", "VirtualGuy", 32, 32, True)
    
    ANIMATION_Delay = 1  # Frames between animation frame changes (lower = faster)

    def __init__(self, x, y, width, height):
        """
        Initialize a new player at the specified position.
        
        Args:
            x (int): Starting X position in world coordinates
            y (int): Starting Y position in world coordinates
            width (int): Hitbox width in pixels
            height (int): Hitbox height in pixels
        """
        super().__init__()
        self.rect = pygame.Rect(x, y, width, height)  # Collision hitbox
        self.x_vel = 0         # Horizontal velocity (pixels per frame)
        self.y_vel = 0         # Vertical velocity (positive = falling)
        self.mask = None       # Pixel-perfect collision mask
        self.direction = "right"
        self.animation_count = 0
        self.fall_count = 0    # Frames spent falling (for gravity acceleration)
        self.jump_count = 0    # 0 = grounded, 1 = single jump, 2 = double jump
        self.sprite = None     # Current animation frame
        self.sprite_rect = None

    def move(self, dx, dy):
        """
        Move the player by the specified delta values.
        
        Args:
            dx (int): Horizontal displacement (positive = right)
            dy (int): Vertical displacement (positive = down)
        """
        self.rect.x += dx
        self.rect.y += dy

    def set_direction(self, new_direction, vel):
        """
        Set the player's facing direction and velocity.
        
        Resets animation counter when direction changes to ensure
        smooth animation transitions.
        
        Args:
            new_direction (str): "left" or "right"
            vel (int): Horizontal velocity to set
        """
        self.x_vel = vel
        if self.direction != new_direction:
            self.direction = new_direction
            self.animation_count = 0  # Reset animation on direction change

    def move_left(self, vel):
        """
        Start moving the player left.
        
        Args:
            vel (int): Movement speed (will be negated for leftward motion)
        """
        self.set_direction("left", -vel)

    def move_right(self, vel):
        """
        Start moving the player right.
        
        Args:
            vel (int): Movement speed
        """
        self.set_direction("right", vel)

    def jump(self):
        """
        Execute a jump (or double jump if already airborne).
        
        The jump velocity is calculated as: -Gravity * 7
        The negative value propels the player upward.
        
        Physics Notes:
            - First jump from ground: jump_count becomes 1
            - Second jump in air: jump_count becomes 2
            - Landing resets jump_count to 0
        """
        self.y_vel = -self.Gravity * 7  # Negative = upward velocity
        self.animation_count = 0        # Reset animation for jump sprite
        self.jump_count += 1            # Track number of jumps used

    def landed(self):
        """
        Called when the player lands on a surface.
        
        Resets all vertical physics state to prepare for the next jump.
        """
        self.fall_count = 0   # Reset gravity acceleration
        self.y_vel = 0        # Stop vertical movement
        self.jump_count = 0   # Allow jumping again

    def hit_head(self):
        """
        Called when the player hits a ceiling.
        
        Reverses or stops upward momentum to prevent clipping through.
        """
        self.animation_count = 0
        if self.y_vel < -1:
            self.y_vel = 2  # Bounce back down slightly
        else:
            self.y_vel = 0  # Stop vertical movement

    def update_sprite(self):
        """
        Update the current animation frame based on player state.
        
        State Machine Logic:
            1. If moving upward (y_vel < 0):
               - Use "jump" sprite for first jump
               - Use "double_jump" sprite for second jump
            2. If falling fast (y_vel > Gravity * 2):
               - Use "fall" sprite
            3. If moving horizontally (x_vel != 0):
               - Use "run" animation
            4. Otherwise:
               - Use "idle" animation
        
        The animation frame advances based on ANIMATION_Delay.
        """
        # Determine which animation to play based on current state
        if self.y_vel < 0:
            # Moving upward - use jump animations
            sprite_sheet = "jump" if self.jump_count == 1 else "double_jump"
        elif self.y_vel > self.Gravity * 2:
            # Falling fast enough to show fall animation
            sprite_sheet = "fall"
        elif self.x_vel != 0:
            # Moving horizontally - run animation
            sprite_sheet = "run"
        else:
            # Stationary - idle animation
            sprite_sheet = "idle"

        # Combine animation name with direction (e.g., "run_right")
        sprite_sheet_name = sprite_sheet + "_" + self.direction
        sprites = self.SPRITES[sprite_sheet_name]
        
        # Calculate current frame index using modulo for looping
        sprite_index = (self.animation_count // self.ANIMATION_Delay) % len(sprites)
        self.sprite = sprites[sprite_index]
        
        # Advance animation counter
        self.animation_count += 1
        self.update()

    def update(self):
        """
        Update the collision mask from the current sprite.
        
        Called after sprite changes to keep collision detection accurate.
        The mask is used for pixel-perfect collision with traps and enemies.
        """
        self.mask = pygame.mask.from_surface(self.sprite)

    def apply_physics(self, fps):
        """
        Apply gravity and update player position.
        
        Gravity Model:
            - Gravity accelerates over time based on fall_count
            - Acceleration is capped at 1 pixel/frame^2 for stability
            - The longer you fall, the faster you go (realistic feel)
        
        Args:
            fps (int): Target frames per second (used for timing calculations)
        """
        # Apply gravity acceleration (capped at 1 unit per frame)
        # Formula: velocity += min(1, (fall_time / fps) * gravity)
        # This creates smooth acceleration that caps out after ~1 second of falling
        self.y_vel += min(1, (self.fall_count / fps) * self.Gravity)
        
        # Move player vertically based on current velocity
        self.move(0, self.y_vel)
        
        # Increment fall counter for acceleration calculation
        self.fall_count += 1
        
        # Update sprite to match current state
        self.update_sprite()

    def draw(self, win, offset_x, offset_y=0):
        """
        Render the player sprite to the screen.
        
        Args:
            win (pygame.Surface): The window surface to draw on
            offset_x (int): Camera X offset for scrolling
            offset_y (int): Camera Y offset for vertical scrolling
        """
        # Ensure sprite is initialized before drawing
        if not hasattr(self, 'sprite') or self.sprite is None:
            key = f"idle_{self.direction}"
            sprites = self.SPRITES.get(key)
            if not sprites:
                sprites = next(iter(self.SPRITES.values()))
            self.sprite = sprites[0]
        
        # Draw sprite at screen position (world position - camera offset)
        win.blit(self.sprite, (self.rect.x - offset_x, self.rect.y - offset_y))


# ==============================================================================
#                      OBJECT & BLOCK CLASSES
# ==============================================================================
# Base classes for all game objects (terrain, obstacles, etc.)
#
# Object: Abstract base class providing common functionality
# Block: Solid terrain that players can stand on and collide with
#
# All objects use pygame's Sprite class for compatibility with
# sprite groups and collision detection systems.
# ==============================================================================


class Object(pygame.sprite.Sprite):
    """
    Base class for all game objects.
    
    Provides common functionality for positioning, rendering, and collision.
    Subclasses should override or extend as needed.
    
    Attributes:
        rect (pygame.Rect): Position and size for collision detection
        image (pygame.Surface): Visual representation of the object
        width (int): Object width in pixels
        height (int): Object height in pixels
        name (str): Identifier for debugging and type checking
    """
    
    def __init__(self, x, y, width, height, name=None):
        """
        Initialize a game object at the specified position.
        
        Args:
            x (int): X position in world coordinates
            y (int): Y position in world coordinates
            width (int): Width in pixels
            height (int): Height in pixels
            name (str, optional): Object identifier
        """
        super().__init__()
        self.rect = pygame.Rect(x, y, width, height)
        self.image = pygame.Surface((width, height), pygame.SRCALPHA)
        self.width = width 
        self.height = height
        self.name = name

    def draw(self, win, offset_x, offset_y=0):
        """
        Render the object to the screen.
        
        Args:
            win (pygame.Surface): Target surface to draw on
            offset_x (int): Camera X offset for scrolling
            offset_y (int): Camera Y offset for vertical scrolling
        """
        win.blit(self.image, (self.rect.x - offset_x, self.rect.y - offset_y))


class Block(Object):
    """
    A solid terrain block that players can stand on.
    
    Blocks form the floor and platforms of each level. They use cached
    textures that vary based on the level style (Egypt, Medieval, Space).
    
    Attributes:
        mask (pygame.Mask): Pixel-perfect collision mask
    """
    
    def __init__(self, x, y, size, name="Block", style="egypt"):
        """
        Create a terrain block at the specified position.
        
        Args:
            x (int): X position in world coordinates
            y (int): Y position in world coordinates
            size (int): Block size (blocks are square)
            name (str): Block identifier (default: "Block")
            style (str): Visual style - "egypt", "medieval", or "space"
        """
        super().__init__(x, y, size, size)
        
        # Select texture based on level style
        if style == "medieval":
            block = get_block_medieval(size)
        elif style == "space":
            block = get_block_space(size)
        else:
            block = get_block(size)  # Default: Egypt sandy block
        
        # Apply texture to this block's surface
        self.image.blit(block, (0, 0))  
        
        # Create collision mask for pixel-perfect detection
        self.mask = pygame.mask.from_surface(self.image)


# ==============================================================================
#                           TRAP CLASSES
# ==============================================================================
# Traps are hazards that damage or kill the player on contact.
# Different trap types have different behaviors:
#
#   Spikes: Static hazard, always deadly
#   Fire:   Animated, toggles on/off periodically
#   Saw:    Animated, moves back and forth along a path
#
# All traps use pixel-perfect collision detection via masks.
# ==============================================================================


class Trap(Object):
    """
    Base class for all trap objects.
    
    Provides common animation infrastructure for traps.
    Subclasses implement specific trap behaviors.
    
    Attributes:
        animation_count (int): Current frame in animation cycle
        animation_delay (int): Frames between animation updates
    """
    
    def __init__(self, x, y, width, height, name="Trap"):
        """
        Initialize a trap at the specified position.
        
        Args:
            x (int): X position in world coordinates
            y (int): Y position in world coordinates
            width (int): Trap width in pixels
            height (int): Trap height in pixels
            name (str): Trap type identifier
        """
        super().__init__(x, y, width, height, name)
        self.animation_count = 0
        self.animation_delay = 5


class Spikes(Trap):
    """
    Static spike trap - always deadly on contact.
    
    The simplest trap type. Uses a single static image.
    No animation or movement.
    """
    
    def __init__(self, x, y, width, height):
        """
        Create a spike trap at the specified position.
        
        Args:
            x (int): X position in world coordinates
            y (int): Y position in world coordinates
            width (int): Trap width in pixels
            height (int): Trap height in pixels
        """
        super().__init__(x, y, width, height, "Spikes")
        
        # Load spike sprite and scale to desired size
        self.image = pygame.image.load(join("assets", "Traps", "Spikes", "Idle.png")).convert_alpha()
        self.image = pygame.transform.scale(self.image, (width, height))
        
        # Create collision mask for pixel-perfect detection
        self.mask = pygame.mask.from_surface(self.image)


class Fire(Trap):
    """
    Animated fire trap that toggles on/off.
    
    The fire cycles between active (deadly) and inactive (safe) states.
    Players can pass through when the fire is off.
    
    Attributes:
        is_on (bool): True if fire is currently active and deadly
        timer (int): Countdown to next state toggle
        toggle_time (int): Frames between on/off toggles
    """
    
    ANIMATION_DELAY = 5
    
    def __init__(self, x, y, width, height):
        """
        Create a fire trap at the specified position.
        
        Args:
            x (int): X position in world coordinates
            y (int): Y position in world coordinates
            width (int): Trap width in pixels
            height (int): Trap height in pixels
        """
        super().__init__(x, y, width, height, "Fire")
        
        # Load both on and off states
        self.on_image = pygame.image.load(join("assets", "Traps", "Fire", "on.png")).convert_alpha()
        self.off_image = pygame.image.load(join("assets", "Traps", "Fire", "off.png")).convert_alpha()
        
        # Scale to desired size
        self.on_image = pygame.transform.scale(self.on_image, (width, height))
        self.off_image = pygame.transform.scale(self.off_image, (width, height))
        
        # Start in the "on" (active) state
        self.image = self.on_image
        self.mask = pygame.mask.from_surface(self.image)
        self.is_on = True
        
        # Toggle timing
        self.timer = 0
        self.toggle_time = 120  # Frames between toggles (2 seconds at 60 FPS)
    
    def update(self):
        """
        Update fire state, toggling on/off periodically.
        
        Called once per frame from the main game loop.
        """
        self.timer += 1
        
        if self.timer >= self.toggle_time:
            # Toggle state
            self.is_on = not self.is_on
            self.image = self.on_image if self.is_on else self.off_image
            self.mask = pygame.mask.from_surface(self.image)
            self.timer = 0  # Reset timer


class Saw(Trap):
    """
    Animated spinning saw that moves back and forth.
    
    The saw has both animation (spinning blades) and movement
    (patrolling left and right within a defined range).
    
    Attributes:
        sprites (list): Animation frames for spinning effect
        start_x (int): Starting X position (patrol center)
        move_range (int): Distance to patrol in each direction
        speed (int): Movement speed in pixels per frame
        direction (int): Current movement direction (1 or -1)
    """
    
    ANIMATION_DELAY = 3  # Fast animation for spinning effect
    
    def __init__(self, x, y, width, height, move_range=100):
        """
        Create a saw trap at the specified position.
        
        Args:
            x (int): X position in world coordinates
            y (int): Y position in world coordinates
            width (int): Trap width in pixels
            height (int): Trap height in pixels
            move_range (int): Pixels to move left/right from starting position
        """
        super().__init__(x, y, width, height, "Saw")
        
        # Load spinning animation frames
        self.sprites = self.load_saw_sprites(width, height)
        self.image = self.sprites[0]
        self.mask = pygame.mask.from_surface(self.image)
        
        # Animation state
        self.animation_count = 0
        
        # Movement state
        self.start_x = x          # Center of patrol path
        self.move_range = move_range  # Distance to patrol each direction
        self.speed = 2            # Movement speed
        self.direction = 1        # 1 = right, -1 = left
    
    def load_saw_sprites(self, width, height):
        """
        Load all animation frames for the spinning saw.
        
        Args:
            width (int): Desired frame width
            height (int): Desired frame height
        
        Returns:
            list: List of pygame.Surface objects for each frame
        """
        # Load the sprite sheet (horizontal strip of frames)
        sprite_sheet = pygame.image.load(join("assets", "Traps", "Saw", "on.png")).convert_alpha()
        sprites = []
        
        # Calculate frame dimensions (assuming 8 frames in the strip)
        sprite_width = sprite_sheet.get_width() // 8
        sprite_height = sprite_sheet.get_height()
        
        # Extract each frame
        for i in range(8):
            surface = pygame.Surface((sprite_width, sprite_height), pygame.SRCALPHA)
            surface.blit(sprite_sheet, (0, 0), (i * sprite_width, 0, sprite_width, sprite_height))
            sprites.append(pygame.transform.scale(surface, (width, height)))
        
        return sprites
    
    def update(self):
        """
        Update saw animation and movement.
        
        Handles both the spinning animation (cycling through frames)
        and the patrol movement (bouncing between boundaries).
        """
        # Advance animation frame for spinning effect
        self.animation_count += 1
        sprite_index = (self.animation_count // self.ANIMATION_DELAY) % len(self.sprites)
        self.image = self.sprites[sprite_index]
        
        # Move in current direction
        self.rect.x += self.speed * self.direction
        
        # Reverse direction at patrol boundaries
        if self.rect.x >= self.start_x + self.move_range:
            self.direction = -1  # Start moving left
        elif self.rect.x <= self.start_x:
            self.direction = 1   # Start moving right


# BOSS CLASS - PHARAOH BOSS
# The first boss - an ancient Egyptian pharaoh
# Has AI dialogue if Ollama is running, otherwise uses pre-written lines

class PharaohBoss:
    """An AI-powered Egyptian Pharaoh boss at the end of the level."""
    
    # Pre-written dialogue for when AI is unavailable
    FALLBACK_DIALOGUE = {
        'intro': [
            "Mortal! Thou hast trespassed into the sacred realm of the eternal Pharaoh!",
            "I am Netriljunakhil, Guardian of the Sands, Keeper of the Ancient Seal!",
            "For three thousand years I have awaited one worthy of facing my wrath!"
        ],
        'taunt': [
            "Thy feeble strikes are but whispers against the storm of ages!",
            "The gods themselves forged my being from the eternal sands!",
            "Hast thou no greater power? Thy ancestors weep in shame!",
            "I have crushed empires! What art thou but a fleeting shadow?",
            "The Nile shall run red with thy defeat!"
        ],
        'damaged': [
            "Impossible! How dost thou wound that which is eternal?!",
            "A lucky strike, mortal! It shall not happen again!",
            "Pain... I had forgotten this sensation... THOU SHALL PAY!",
            "By the curse of Anubis, thou shalt suffer for this insolence!"
        ],
        'low_health': [
            "No... NO! The prophecy spoke of this day... but I refused to believe!",
            "My power... it wanes! What sorcery dost thou possess?!",
            "The sands of time turn against their master... how can this be?!"
        ],
        'defeat': [
            "Thou... hast bested me... The eternal Pharaoh... falls...",
            "The curse is lifted... After millennia... I am... free...",
            "Go forth, champion... Greater trials await thee beyond these sands..."
        ]
    }
    
    def __init__(self, x, y, max_x):
        self.x = x
        self.y = y
        self.width = 120
        self.height = 150
        self.rect = pygame.Rect(x, y, self.width, self.height)
        
        # Boss stats
        self.max_health = 100
        self.health = self.max_health
        self.is_alive = True
        self.is_defeated = False
        self.phase = 1  # Boss phases for increasing difficulty
        
        # Movement
        self.start_x = x
        self.move_range = 200
        self.speed = 2
        self.direction = 1
        self.hover_offset = 0
        self.hover_speed = 0.05
        
        # Combat
        self.attack_cooldown = 0
        self.attack_pattern = 0
        self.projectiles = []
        self.is_vulnerable = True
        self.invincibility_frames = 0
        
        # Dialogue system
        self.current_dialogue = ""
        self.dialogue_timer = 0
        self.dialogue_queue = queue.Queue()
        self.has_introduced = False
        self.last_taunt_time = 0
        
        # AI dialogue - uses Ollama (free local AI)
        self.ai_thread = None
        self.ai_available = OLLAMA_AVAILABLE
        
        # System prompt for the Pharaoh character
        self.system_prompt = """You are Netriljunakhil, an ancient Egyptian Pharaoh who has been cursed to guard a sacred temple for 3000 years. 
You speak in an archaic, regal manner befitting ancient Egyptian royalty. Use 'thee', 'thou', 'thy', 'hast', 'doth', 'shalt' etc.
Reference Egyptian gods (Ra, Anubis, Osiris, Horus, Set), the Nile, pyramids, and ancient Egyptian culture.
Keep responses to 1-2 sentences maximum. Be dramatic and intimidating . Do not use quotation marks."""
        
        # Animation
        self.animation_count = 0
        self.glow_intensity = 0
        
        # Create boss visual
        self.create_boss_sprite()
    
    def create_boss_sprite(self):
        """Create the Pharaoh boss sprite procedurally."""
        self.image = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        
        # Body - mummy wrappings (tan/beige)
        body_color = (210, 180, 140)
        pygame.draw.rect(self.image, body_color, (30, 50, 60, 80), border_radius=5)
        
        # Head with Pharaoh headdress (Nemes)
        headdress_gold = (255, 215, 0)
        headdress_blue = (30, 60, 150)
        
        # Headdress base
        pygame.draw.polygon(self.image, headdress_gold, [
            (60, 10), (20, 50), (10, 80), (30, 60), (60, 55), (90, 60), (110, 80), (100, 50)
        ])
        # Stripes on headdress
        for i in range(3):
            pygame.draw.line(self.image, headdress_blue, (25 + i*25, 30), (20 + i*30, 70), 4)
        
        # Face
        face_color = (180, 150, 110)
        pygame.draw.ellipse(self.image, face_color, (35, 35, 50, 40))
        
        # Glowing eyes
        eye_color = (0, 255, 200)
        pygame.draw.ellipse(self.image, eye_color, (45, 48, 12, 8))
        pygame.draw.ellipse(self.image, eye_color, (63, 48, 12, 8))
        
        # Beard (ceremonial)
        pygame.draw.polygon(self.image, headdress_gold, [
            (55, 70), (65, 70), (62, 95), (58, 95)
        ])
        
        # Arms with bandages
        pygame.draw.rect(self.image, body_color, (10, 60, 20, 50), border_radius=3)
        pygame.draw.rect(self.image, body_color, (90, 60, 20, 50), border_radius=3)
        
        # Staff in right hand
        staff_color = (139, 69, 19)
        pygame.draw.rect(self.image, staff_color, (100, 40, 8, 100))
        # Staff head (Ankh symbol simplified)
        pygame.draw.ellipse(self.image, headdress_gold, (95, 25, 18, 20))
        pygame.draw.rect(self.image, headdress_gold, (101, 40, 6, 15))
        
        # Collar/necklace
        pygame.draw.arc(self.image, headdress_gold, (25, 45, 70, 30), 0, 3.14, 4)
        
        # Wrap details (mummy bandages)
        bandage_dark = (180, 150, 120)
        for i in range(4):
            pygame.draw.line(self.image, bandage_dark, (30, 60 + i*18), (90, 65 + i*18), 2)
        
        self.mask = pygame.mask.from_surface(self.image)
    
    def get_ai_dialogue(self, context):
        """Get dialogue from Ollama AI in a separate thread."""
        if not self.ai_available:
            return
        
        def fetch_dialogue():
            try:
                prompt = f"{self.system_prompt}\n\nSituation: {context}\n\nRespond as the Pharaoh:"
                
                data = json.dumps({
                    "model": "neural-chat:latest",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.5,
                        "num_predict": 12,
                        "top_k": 10,
                        "top_p": 0.8
                    }
                }).encode('utf-8')
                
                req = urllib.request.Request(
                    OLLAMA_URL,
                    data=data,
                    headers={'Content-Type': 'application/json'},
                    method='POST'
                )
                
                with urllib.request.urlopen(req, timeout=25) as response:
                    result = json.loads(response.read().decode('utf-8'))
                    dialogue = result.get('response', '').strip()
                    # Clean up the dialogue
                    dialogue = dialogue.replace('"', '').replace("'", "'")
                    if dialogue and len(dialogue) > 5:
                        self.dialogue_queue.put(dialogue)
                        print(f"✓ Pharaoh AI dialogue: {dialogue[:60]}...")
            except Exception as e:
                print(f"✗ Pharaoh AI error: {e}")
        
        self.ai_thread = threading.Thread(target=fetch_dialogue, daemon=True)
        self.ai_thread.start()
    
    def get_fallback_dialogue(self, category):
        """Get pre-written dialogue when AI is unavailable."""
        dialogues = self.FALLBACK_DIALOGUE.get(category, self.FALLBACK_DIALOGUE['taunt'])
        return random.choice(dialogues)
    
    def introduce(self):
        """Boss introduction sequence."""
        if not self.has_introduced:
            self.has_introduced = True
            if self.ai_available:
                self.get_ai_dialogue("The hero has just arrived at your chamber. Give a dramatic introduction declaring who you are and threatening them.")
                # Also show fallback immediately while AI loads
                self.current_dialogue = self.get_fallback_dialogue('intro')
                self.dialogue_timer = 180
            else:
                self.current_dialogue = self.get_fallback_dialogue('intro')
                self.dialogue_timer = 180
    
    def taunt(self):
        """Random taunts during battle."""
        current_time = pygame.time.get_ticks()
        if current_time - self.last_taunt_time > 5000:  # Taunt every 5 seconds
            self.last_taunt_time = current_time
            if self.ai_available and random.random() < 0.5:
                self.get_ai_dialogue("Taunt the hero during battle. Be intimidating and reference your ancient power.")
            else:
                self.current_dialogue = self.get_fallback_dialogue('taunt')
                self.dialogue_timer = 120
    
    def on_damaged(self, damage):
        """Handle taking damage."""
        if not self.is_vulnerable or self.invincibility_frames > 0:
            return False
        
        self.health -= damage
        self.invincibility_frames = 60
        
        # Update phase based on health
        if self.health <= 30:
            self.phase = 3
            self.speed = 4
        elif self.health <= 60:
            self.phase = 2
            self.speed = 3
        
        # Dialogue response
        if self.health <= 0:
            self.is_defeated = True
            self.is_alive = False
            if self.ai_available:
                self.get_ai_dialogue("You have been defeated by the hero. Give dying words acknowledging their victory.")
            self.current_dialogue = self.get_fallback_dialogue('defeat')
            self.dialogue_timer = 300
        elif self.health <= 30:
            if self.ai_available:
                self.get_ai_dialogue("You are badly wounded and near defeat. Express desperation and disbelief.")
            else:
                self.current_dialogue = self.get_fallback_dialogue('low_health')
                self.dialogue_timer = 120
        else:
            if self.ai_available:
                self.get_ai_dialogue("You just took damage from the hero. React with anger.")
            else:
                self.current_dialogue = self.get_fallback_dialogue('damaged')
                self.dialogue_timer = 90
        
        return True
    
    def create_projectile(self):
        """Create an attack projectile."""
        proj = {
            'x': self.rect.centerx,
            'y': self.rect.centery,
            'dx': -8 if self.direction < 0 else -8,  # Always toward player (left)
            'dy': random.uniform(-2, 2),
            'size': 20,
            'lifetime': 180
        }
        self.projectiles.append(proj)
    
    def update(self, player_x):
        """Update boss state."""
        if self.is_defeated:
            return
        
        # Check for AI dialogue responses
        try:
            while True:
                dialogue = self.dialogue_queue.get_nowait()
                self.current_dialogue = dialogue
                self.dialogue_timer = 150
        except queue.Empty:
            pass
        
        # Update dialogue timer
        if self.dialogue_timer > 0:
            self.dialogue_timer -= 1
        else:
            self.current_dialogue = ""
        
        # Update invincibility timer
        if self.invincibility_frames > 0:
            self.invincibility_frames -= 1
        
        # Floating hover effect - sin() gives us smooth -1 to 1 oscillation
        # multiply by 10 so boss bobs up/down by 10 pixels
        self.hover_offset = math.sin(self.animation_count * self.hover_speed) * 10
        self.animation_count += 1
        
        # Pulsing glow - shift sin() from [-1,1] to [0,1] range
        # so the glow fades in and out smoothly
        self.glow_intensity = (math.sin(self.animation_count * 0.1) + 1) * 0.5
        
        # Movement - move toward player somewhat
        if abs(player_x - self.rect.centerx) > 100:
            if player_x < self.rect.centerx:
                self.rect.x -= self.speed
            else:
                self.rect.x += self.speed
        
        # Keep in bounds
        if self.rect.x < self.start_x - self.move_range:
            self.rect.x = self.start_x - self.move_range
        elif self.rect.x > self.start_x + self.move_range:
            self.rect.x = self.start_x + self.move_range
        
        # Attack patterns
        self.attack_cooldown -= 1
        if self.attack_cooldown <= 0:
            self.create_projectile()
            self.attack_cooldown = max(30, 90 - self.phase * 20)  # Faster attacks in later phases
        
        # Update projectiles
        for proj in self.projectiles[:]:
            proj['x'] += proj['dx']
            proj['y'] += proj['dy']
            proj['lifetime'] -= 1
            if proj['lifetime'] <= 0 or proj['x'] < self.start_x - 500:
                self.projectiles.remove(proj)
        
        # Taunt occasionally
        if self.has_introduced:
            self.taunt()
    
    def check_projectile_collision(self, player):
        """Check if any projectiles hit the player."""
        player_rect = player.rect
        for proj in self.projectiles[:]:
            proj_rect = pygame.Rect(proj['x'] - proj['size']//2, proj['y'] - proj['size']//2, 
                                   proj['size'], proj['size'])
            if player_rect.colliderect(proj_rect):
                self.projectiles.remove(proj)
                return True
        return False
    
    def check_player_attack(self, player):
        """Check if player is attacking the boss (jumping on head)."""
        if player.y_vel > 0:  # Player is falling
            # Check if player lands on boss head area
            head_rect = pygame.Rect(self.rect.x + 20, self.rect.y, self.rect.width - 40, 30)
            feet_rect = pygame.Rect(player.rect.x + 5, player.rect.bottom - 10, player.rect.width - 10, 15)
            
            if feet_rect.colliderect(head_rect):
                return True
        return False
    
    def draw(self, window, offset_x, offset_y):
        """Draw the boss and its effects."""
        if self.is_defeated and self.dialogue_timer <= 0:
            return
        
        screen_x = self.rect.x - offset_x
        screen_y = self.rect.y - offset_y + int(self.hover_offset)
        
        # Draw glow effect
        if self.is_alive:
            glow_size = int(30 + self.glow_intensity * 20)
            glow_surface = pygame.Surface((self.width + glow_size*2, self.height + glow_size*2), pygame.SRCALPHA)
            glow_color = (255, 200, 50, int(50 + self.glow_intensity * 50))
            pygame.draw.ellipse(glow_surface, glow_color, glow_surface.get_rect())
            window.blit(glow_surface, (screen_x - glow_size, screen_y - glow_size))
        
        # Flash when invincible
        if self.invincibility_frames > 0 and self.invincibility_frames % 6 < 3:
            tinted = self.image.copy()
            tinted.fill((255, 100, 100, 100), special_flags=pygame.BLEND_RGBA_MULT)
            window.blit(tinted, (screen_x, screen_y))
        else:
            window.blit(self.image, (screen_x, screen_y))
        
        # Draw health bar
        if self.is_alive:
            bar_width = 100
            bar_height = 12
            bar_x = screen_x + (self.width - bar_width) // 2
            bar_y = screen_y - 25
            
            # Background
            pygame.draw.rect(window, (40, 40, 40), (bar_x - 2, bar_y - 2, bar_width + 4, bar_height + 4), border_radius=3)
            pygame.draw.rect(window, (80, 0, 0), (bar_x, bar_y, bar_width, bar_height), border_radius=2)
            
            # Health fill
            health_width = int(bar_width * (self.health / self.max_health))
            if health_width > 0:
                health_color = (0, 200, 0) if self.health > 60 else (255, 200, 0) if self.health > 30 else (255, 50, 50)
                pygame.draw.rect(window, health_color, (bar_x, bar_y, health_width, bar_height), border_radius=2)
            
            # Boss name
            font = pygame.font.SysFont('arial', 14, bold=True)
            name_text = font.render("PHARAOH Netriljunakhil ", True, (255, 215, 0))
            name_x = screen_x + (self.width - name_text.get_width()) // 2
            window.blit(name_text, (name_x, bar_y - 18))
        
        # Draw projectiles
        for proj in self.projectiles:
            proj_x = proj['x'] - offset_x
            proj_y = proj['y'] - offset_y
            # Scarab beetle / sand projectile
            pygame.draw.circle(window, (255, 200, 50), (int(proj_x), int(proj_y)), proj['size']//2)
            pygame.draw.circle(window, (200, 150, 50), (int(proj_x), int(proj_y)), proj['size']//2 - 3)
        
        # Draw dialogue bubble
        if self.current_dialogue:
            self.draw_dialogue(window, screen_x, screen_y)
    
    def draw_dialogue(self, window, boss_x, boss_y):
        """Draw the boss dialogue bubble."""
        font = pygame.font.SysFont('arial', 16, bold=True)
        
        # Word wrap the dialogue
        words = self.current_dialogue.split()
        lines = []
        current_line = ""
        max_width = 300
        
        for word in words:
            test_line = current_line + " " + word if current_line else word
            if font.size(test_line)[0] < max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        
        if not lines:
            return
        
        # Calculate bubble size
        padding = 15
        line_height = 22
        bubble_width = max(font.size(line)[0] for line in lines) + padding * 2
        bubble_height = len(lines) * line_height + padding * 2
        
        bubble_x = boss_x + self.width // 2 - bubble_width // 2
        bubble_y = boss_y - bubble_height - 30
        
        # Keep on screen
        win_width = window.get_width()
        if bubble_x < 10:
            bubble_x = 10
        if bubble_x + bubble_width > win_width - 10:
            bubble_x = win_width - bubble_width - 10
        if bubble_y < 10:
            bubble_y = boss_y + self.height + 10
        
        # Draw bubble
        bubble_surface = pygame.Surface((bubble_width, bubble_height), pygame.SRCALPHA)
        pygame.draw.rect(bubble_surface, (20, 20, 30, 230), bubble_surface.get_rect(), border_radius=10)
        window.blit(bubble_surface, (bubble_x, bubble_y))
        pygame.draw.rect(window, (255, 215, 0), (bubble_x, bubble_y, bubble_width, bubble_height), 3, border_radius=10)
        
        # Draw text
        for i, line in enumerate(lines):
            text_surface = font.render(line, True, (255, 230, 180))
            window.blit(text_surface, (bubble_x + padding, bubble_y + padding + i * line_height))


# ==============================================================================
#                           PORTAL CLASS
# ==============================================================================
# The Portal appears after defeating a boss and allows the player to
# transition to the next level. Features include:
#
#   - Activation: Portal appears only after boss is defeated
#   - Visual Effects: Pulsing glow, swirling particles, rotating lines
#   - Particle System: Particles spawn around the portal and spiral inward
#   - Player Detection: Checks when player enters to trigger level transition
#
# Animation Math:
#   - Uses polar coordinates (angle + distance) for particle positioning
#   - sin/cos convert polar to Cartesian (x, y) coordinates
#   - Particles rotate around center while shrinking toward it (spiral)
#
# Visual Design:
#   - Purple/magenta color scheme for magical portal feel
#   - Multiple glow layers for depth
#   - Rotating swirl lines inside the portal
# ==============================================================================


class Portal:
    """Portal that opens after a boss dies. Player entering it advances the level.

    Includes a simple particle spiral and pulsing glow.

    Attributes: rect, active, particles, animation_count
    """
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 80
        self.height = 120
        self.rect = pygame.Rect(x, y, self.width, self.height)
        self.animation_count = 0
        self.active = False
        self.particles = []
        
    def activate(self):
        """Activate the portal after boss defeat."""
        self.active = True
        
    def update(self):
        """Update portal animation."""
        if not self.active:
            return
        self.animation_count += 1
        
        # Spawn particles around the portal using polar coords (angle, radius).
        # Convert to Cartesian via cos/sin when placing particles:
        #   x = cx + cos(angle) * r
        #   y = cy + sin(angle) * r
        # We spawn a few particles at random angles/distances for a simple spiral effect.
        if random.random() < 0.3:
            # Random angle around the circle (0 to 2π radians = 0 to 360 degrees)
            angle = random.uniform(0, 2 * math.pi)
            # Random distance from portal center (20 to 50 pixels)
            distance = random.uniform(20, 50)
            self.particles.append({
                # Convert polar to Cartesian: x = center + cos(angle) * distance
                'x': self.rect.centerx + math.cos(angle) * distance,
                # Convert polar to Cartesian: y = center + sin(angle) * distance
                'y': self.rect.centery + math.sin(angle) * distance,
                'angle': angle,      # Store angle for rotation animation
                'distance': distance, # Store distance for spiral-in effect
                'lifetime': 60,       # Frames until particle disappears
                'speed': random.uniform(0.05, 0.1)  # Rotation speed (radians/frame)
            })
        
        # =============================================================================
        # PARTICLE UPDATE - Creating the SPIRAL EFFECT
        # =============================================================================
        # Each frame we:
        #   1. Increase angle -> particle rotates around the center
        #   2. Decrease distance -> particle moves closer to center
        #   3. Recalculate x,y from new polar coords
        #
        # Combined effect: particles spiral inward toward the portal center
        # =============================================================================
        for p in self.particles[:]:
            # Rotate: increase angle so particle orbits around center
            p['angle'] += p['speed']
            # Shrink: decrease distance so particle moves toward center
            p['distance'] -= 0.5
            # Recalculate Cartesian position from updated polar coordinates
            p['x'] = self.rect.centerx + math.cos(p['angle']) * p['distance']
            p['y'] = self.rect.centery + math.sin(p['angle']) * p['distance']
            p['lifetime'] -= 1
            # Remove particle when it reaches center or expires
            if p['lifetime'] <= 0 or p['distance'] <= 5:
                self.particles.remove(p)
    
    def check_player_enter(self, player):
        """Check if player enters the portal."""
        if not self.active:
            return False
        return self.rect.colliderect(player.rect)
    
    def draw(self, window, offset_x, offset_y):
        """Draw the portal."""
        if not self.active:
            return
            
        screen_x = self.rect.x - offset_x
        screen_y = self.rect.y - offset_y
        
        # Draw outer glow
        glow_colors = [
            (100, 0, 200, 30),
            (150, 50, 255, 50),
            (200, 100, 255, 70)
        ]
        for i, color in enumerate(glow_colors):
            glow_size = 30 - i * 8
            glow_surface = pygame.Surface((self.width + glow_size*2, self.height + glow_size*2), pygame.SRCALPHA)
            pygame.draw.ellipse(glow_surface, color, glow_surface.get_rect())
            window.blit(glow_surface, (screen_x - glow_size, screen_y - glow_size))
        
        # =============================================================================
        # PORTAL COLOR PULSING using math.sin()
        # =============================================================================
        # sin() oscillates between -1 and 1, multiplied by 5 gives -5 to +5
        # This offset is used to slightly vary the portal's red channel
        # Result: portal color subtly pulses between darker and lighter purple
        # =============================================================================
        swirl_offset = math.sin(self.animation_count * 0.1) * 5
        portal_color = (120 + int(swirl_offset * 10), 50, 220)
        pygame.draw.ellipse(window, portal_color, (screen_x + 5, screen_y + 5, self.width - 10, self.height - 10))
        
        # Inner portal (darker center)
        inner_color = (60, 20, 120)
        pygame.draw.ellipse(window, inner_color, (screen_x + 15, screen_y + 15, self.width - 30, self.height - 30))
        
        # Draw four rotating swirl lines using cos/sin offsets. They rotate over time and are spaced 90° apart.
        for i in range(4):
            # Base angle rotates over time; each line offset by 90° (π/2 radians)
            angle = self.animation_count * 0.05 + i * (math.pi / 2)
            # Outer point of line (further from center)
            start_x = self.rect.centerx - offset_x + math.cos(angle) * 20
            start_y = self.rect.centery - offset_y + math.sin(angle) * 30
            # Inner point of line (closer to center, slightly rotated)
            end_x = self.rect.centerx - offset_x + math.cos(angle + 0.5) * 10
            end_y = self.rect.centery - offset_y + math.sin(angle + 0.5) * 15
            pygame.draw.line(window, (200, 150, 255), (int(start_x), int(start_y)), (int(end_x), int(end_y)), 3)
        
        # Draw particles
        for p in self.particles:
            px = p['x'] - offset_x
            py = p['y'] - offset_y
            alpha = int(255 * (p['lifetime'] / 60))
            particle_color = (200, 150, 255)
            pygame.draw.circle(window, particle_color, (int(px), int(py)), 3)
        
        # Draw "ENTER" text
        font = pygame.font.SysFont('consolas', 16, bold=True)
        text = font.render("ENTER", True, (255, 200, 255))
        text_rect = text.get_rect(center=(self.rect.centerx - offset_x, self.rect.bottom - offset_y + 20))
        window.blit(text, text_rect)


# BOSS CLASS - KNIGHT BOSS (Medieval Europe)

class KnightBoss:
    """An AI-powered Medieval Knight boss at the end of the Medieval level."""
    
    # Pre-written dialogue for when AI is unavailable
    FALLBACK_DIALOGUE = {
        'intro': [
            "Halt, interloper! Thou hast entered the domain of Sir Aldric the Unyielding!",
            "I am sworn protector of this realm, and none shall pass whilst I draw breath!",
            "Prepare thyself for honorable combat, for I shall show no quarter!"
        ],
        'taunt': [
            "Thy skills are lacking! Hast thou never held a sword before?",
            "My squire fights with more conviction than thee!",
            "The King himself bestowed upon me this sacred duty. I shall not fail!",
            "Stand and fight, coward! Or flee like the peasant thou art!",
            "By the grace of God and Crown, I shall smite thee!"
        ],
        'damaged': [
            "A glancing blow! 'Twill take more than that to fell a true knight!",
            "Thou fights with unexpected cunning... but 'tis not enough!",
            "Argh! Thou hast found a chink in mine armor!",
            "By the saints! Thou art more formidable than I presumed!"
        ],
        'low_health': [
            "Nay... This cannot be... I have never known defeat!",
            "My strength wanes... but my honor shall never falter!",
            "The realm... I have failed thee... but I fight on!"
        ],
        'defeat': [
            "Thou... hast bested me... A worthy opponent indeed...",
            "My vigil ends... The realm passes to thy protection now...",
            "Go forth, champion... Greater darkness awaits beyond these walls..."
        ]
    }
    
    def __init__(self, x, y, max_x):
        self.x = x
        self.y = y
        self.width = 120
        self.height = 150
        self.rect = pygame.Rect(x, y, self.width, self.height)
        
        # Boss stats
        self.max_health = 100
        self.health = self.max_health
        self.is_alive = True
        self.is_defeated = False
        self.phase = 1  # Boss phases for increasing difficulty
        
        # Movement
        self.start_x = x
        self.move_range = 200
        self.speed = 2
        self.direction = 1
        self.hover_offset = 0
        self.hover_speed = 0.03
        
        # Combat
        self.attack_cooldown = 0
        self.attack_pattern = 0
        self.projectiles = []
        self.is_vulnerable = True
        self.invincibility_frames = 0
        
        # Dialogue system
        self.current_dialogue = ""
        self.dialogue_timer = 0
        self.dialogue_queue = queue.Queue()
        self.has_introduced = False
        self.last_taunt_time = 0
        
        # AI dialogue - uses Ollama (free local AI)
        self.ai_thread = None
        self.ai_available = OLLAMA_AVAILABLE
        
        # System prompt for the Knight character
        self.system_prompt = """You are Sir Aldric the Unyielding, a medieval knight who has sworn to protect a sacred castle for decades. 
You speak in archaic medieval English befitting a noble knight. Use 'thee', 'thou', 'thy', 'hast', 'doth', 'shalt' etc.
Reference God, the Crown, chivalry, honor, swords, shields, and medieval concepts.
Keep responses to 1-2 sentences maximum. Be dramatic and honorable. Do not use quotation marks."""
        
        # Animation
        self.animation_count = 0
        self.glow_intensity = 0
        
        # Create boss visual
        self.create_boss_sprite()
    
    def create_boss_sprite(self):
        """Create the Knight boss sprite procedurally."""
        self.image = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        
        # Armor colors
        steel_color = (160, 170, 180)
        steel_dark = (100, 110, 120)
        steel_light = (200, 210, 220)
        cape_color = (150, 30, 30)  # Royal red cape
        gold_trim = (255, 215, 0)
        
        # Cape (behind body)
        cape_points = [(30, 50), (90, 50), (100, 140), (20, 140)]
        pygame.draw.polygon(self.image, cape_color, cape_points)
        pygame.draw.polygon(self.image, (120, 20, 20), cape_points, 2)
        
        # Body - plate armor
        pygame.draw.rect(self.image, steel_color, (35, 50, 50, 70), border_radius=5)
        # Armor details
        pygame.draw.line(self.image, steel_dark, (60, 55), (60, 115), 2)
        pygame.draw.line(self.image, steel_light, (45, 70), (75, 70), 2)
        pygame.draw.line(self.image, steel_light, (45, 90), (75, 90), 2)
        
        # Helmet
        pygame.draw.ellipse(self.image, steel_color, (38, 15, 44, 45))
        # Visor slit
        pygame.draw.rect(self.image, (20, 20, 30), (45, 32, 30, 8))
        # Helmet crest
        pygame.draw.polygon(self.image, cape_color, [(60, 5), (55, 20), (65, 20)])
        
        # Glowing eyes behind visor
        pygame.draw.rect(self.image, (100, 150, 255), (50, 34, 6, 4))
        pygame.draw.rect(self.image, (100, 150, 255), (64, 34, 6, 4))
        
        # Pauldrons (shoulder armor)
        pygame.draw.ellipse(self.image, steel_color, (15, 45, 25, 20))
        pygame.draw.ellipse(self.image, steel_color, (80, 45, 25, 20))
        pygame.draw.ellipse(self.image, steel_dark, (15, 45, 25, 20), 2)
        pygame.draw.ellipse(self.image, steel_dark, (80, 45, 25, 20), 2)
        
        # Arms with gauntlets
        pygame.draw.rect(self.image, steel_color, (15, 60, 20, 45), border_radius=3)
        pygame.draw.rect(self.image, steel_color, (85, 60, 20, 45), border_radius=3)
        
        # Sword in right hand
        sword_color = (180, 190, 200)
        pygame.draw.rect(self.image, sword_color, (95, 20, 6, 90))  # Blade
        pygame.draw.rect(self.image, gold_trim, (90, 100, 16, 6))  # Crossguard
        pygame.draw.rect(self.image, (80, 50, 20), (95, 106, 6, 15))  # Handle
        
        # Shield in left hand
        shield_color = (100, 110, 130)
        pygame.draw.ellipse(self.image, shield_color, (5, 70, 25, 40))
        # Cross emblem on shield
        pygame.draw.rect(self.image, gold_trim, (15, 75, 5, 30))
        pygame.draw.rect(self.image, gold_trim, (8, 87, 19, 5))
        
        # Legs
        pygame.draw.rect(self.image, steel_color, (40, 115, 15, 30), border_radius=3)
        pygame.draw.rect(self.image, steel_color, (65, 115, 15, 30), border_radius=3)
        
        # Gold trim on armor
        pygame.draw.line(self.image, gold_trim, (35, 50), (85, 50), 2)
        
        self.mask = pygame.mask.from_surface(self.image)
    
    def get_ai_dialogue(self, context):
        """Get dialogue from Ollama AI in a separate thread."""
        if not self.ai_available:
            return
        
        def fetch_dialogue():
            try:
                prompt = f"{self.system_prompt}\n\nSituation: {context}\n\nRespond as Sir Aldric:"
                
                data = json.dumps({
                    "model": "neural-chat:latest",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.5,
                        "num_predict": 12,
                        "top_k": 10,
                        "top_p": 0.8
                    }
                }).encode('utf-8')
                
                req = urllib.request.Request(
                    OLLAMA_URL,
                    data=data,
                    headers={'Content-Type': 'application/json'},
                    method='POST'
                )
                
                with urllib.request.urlopen(req, timeout=25) as response:
                    result = json.loads(response.read().decode('utf-8'))
                    dialogue = result.get('response', '').strip()
                    dialogue = dialogue.replace('"', '').replace("'", "'")
                    if dialogue and len(dialogue) > 5:
                        self.dialogue_queue.put(dialogue)
                        print(f"✓ Knight AI dialogue: {dialogue[:60]}...")
            except Exception as e:
                print(f"✗ Knight AI error: {e}")
        
        self.ai_thread = threading.Thread(target=fetch_dialogue, daemon=True)
        self.ai_thread.start()
    
    def get_fallback_dialogue(self, category):
        """Get pre-written dialogue when AI is unavailable."""
        dialogues = self.FALLBACK_DIALOGUE.get(category, self.FALLBACK_DIALOGUE['taunt'])
        return random.choice(dialogues)
    
    def introduce(self):
        """Boss introduction sequence."""
        if not self.has_introduced:
            self.has_introduced = True
            if self.ai_available:
                self.get_ai_dialogue("The hero has just arrived at your castle. Give a dramatic introduction declaring who you are and challenging them to honorable combat.")
                self.current_dialogue = self.get_fallback_dialogue('intro')
                self.dialogue_timer = 180
            else:
                self.current_dialogue = self.get_fallback_dialogue('intro')
                self.dialogue_timer = 180
    
    def taunt(self):
        """Random taunts during battle."""
        current_time = pygame.time.get_ticks()
        if current_time - self.last_taunt_time > 5000:
            self.last_taunt_time = current_time
            if self.ai_available and random.random() < 0.5:
                self.get_ai_dialogue("Taunt the hero during battle. Reference your knightly honor and skill.")
            else:
                self.current_dialogue = self.get_fallback_dialogue('taunt')
                self.dialogue_timer = 120
    
    def on_damaged(self, damage):
        """Handle taking damage."""
        if not self.is_vulnerable or self.invincibility_frames > 0:
            return False
        
        self.health -= damage
        self.invincibility_frames = 60
        
        if self.health <= 30:
            self.phase = 3
            self.speed = 4
        elif self.health <= 60:
            self.phase = 2
            self.speed = 3
        
        if self.health <= 0:
            self.is_defeated = True
            self.is_alive = False
            if self.ai_available:
                self.get_ai_dialogue("You have been defeated by the hero. Give dying words acknowledging their victory with honor.")
            self.current_dialogue = self.get_fallback_dialogue('defeat')
            self.dialogue_timer = 300
        elif self.health <= 30:
            if self.ai_available:
                self.get_ai_dialogue("You are badly wounded and near defeat. Express that your honor is at stake.")
            else:
                self.current_dialogue = self.get_fallback_dialogue('low_health')
                self.dialogue_timer = 120
        else:
            if self.ai_available:
                self.get_ai_dialogue("You just took damage from the hero. React with knightly determination.")
            else:
                self.current_dialogue = self.get_fallback_dialogue('damaged')
                self.dialogue_timer = 90
        
        return True
    
    def create_projectile(self):
        """Create an attack projectile (throwing sword/mace)."""
        proj = {
            'x': self.rect.centerx,
            'y': self.rect.centery,
            'dx': -8 if self.direction < 0 else -8,
            'dy': random.uniform(-2, 2),
            'size': 25,
            'lifetime': 180,
            'angle': 0
        }
        self.projectiles.append(proj)
    
    def update(self, player_x):
        """Update boss state."""
        if self.is_defeated:
            return
        
        try:
            while True:
                dialogue = self.dialogue_queue.get_nowait()
                self.current_dialogue = dialogue
                self.dialogue_timer = 150
        except queue.Empty:
            pass
        
        if self.dialogue_timer > 0:
            self.dialogue_timer -= 1
        else:
            self.current_dialogue = ""
        
        if self.invincibility_frames > 0:
            self.invincibility_frames -= 1
        
        # slight bob - smaller than pharaoh (3px vs 10) since knight is more grounded
        self.hover_offset = math.sin(self.animation_count * self.hover_speed) * 3
        self.animation_count += 1
        
        # pulsing glow effect
        self.glow_intensity = (math.sin(self.animation_count * 0.1) + 1) * 0.5
        
        if abs(player_x - self.rect.centerx) > 100:
            if player_x < self.rect.centerx:
                self.rect.x -= self.speed
            else:
                self.rect.x += self.speed
        
        if self.rect.x < self.start_x - self.move_range:
            self.rect.x = self.start_x - self.move_range
        elif self.rect.x > self.start_x + self.move_range:
            self.rect.x = self.start_x + self.move_range
        
        self.attack_cooldown -= 1
        if self.attack_cooldown <= 0:
            self.create_projectile()
            self.attack_cooldown = max(30, 90 - self.phase * 20)
        
        for proj in self.projectiles[:]:
            proj['x'] += proj['dx']
            proj['y'] += proj['dy']
            proj['angle'] += 15  # Spinning projectile
            proj['lifetime'] -= 1
            if proj['lifetime'] <= 0 or proj['x'] < self.start_x - 500:
                self.projectiles.remove(proj)
        
        if self.has_introduced:
            self.taunt()
    
    def check_projectile_collision(self, player):
        """Check if any projectiles hit the player."""
        player_rect = player.rect
        for proj in self.projectiles[:]:
            proj_rect = pygame.Rect(proj['x'] - proj['size']//2, proj['y'] - proj['size']//2, 
                                   proj['size'], proj['size'])
            if player_rect.colliderect(proj_rect):
                self.projectiles.remove(proj)
                return True
        return False
    
    def check_player_attack(self, player):
        """Check if player is attacking the boss (jumping on head)."""
        if player.y_vel > 0:
            head_rect = pygame.Rect(self.rect.x + 20, self.rect.y, self.rect.width - 40, 30)
            feet_rect = pygame.Rect(player.rect.x + 5, player.rect.bottom - 10, player.rect.width - 10, 15)
            
            if feet_rect.colliderect(head_rect):
                return True
        return False
    
    def draw(self, window, offset_x, offset_y):
        """Draw the boss and its effects."""
        if self.is_defeated and self.dialogue_timer <= 0:
            return
        
        screen_x = self.rect.x - offset_x
        screen_y = self.rect.y - offset_y + int(self.hover_offset)
        
        # Draw subtle glow effect (bluish for knight)
        if self.is_alive:
            glow_size = int(20 + self.glow_intensity * 15)
            glow_surface = pygame.Surface((self.width + glow_size*2, self.height + glow_size*2), pygame.SRCALPHA)
            glow_color = (100, 150, 255, int(30 + self.glow_intensity * 30))
            pygame.draw.ellipse(glow_surface, glow_color, glow_surface.get_rect())
            window.blit(glow_surface, (screen_x - glow_size, screen_y - glow_size))
        
        if self.invincibility_frames > 0 and self.invincibility_frames % 6 < 3:
            tinted = self.image.copy()
            tinted.fill((255, 100, 100, 100), special_flags=pygame.BLEND_RGBA_MULT)
            window.blit(tinted, (screen_x, screen_y))
        else:
            window.blit(self.image, (screen_x, screen_y))
        
        # Draw health bar
        if self.is_alive:
            bar_width = 100
            bar_height = 12
            bar_x = screen_x + (self.width - bar_width) // 2
            bar_y = screen_y - 25
            
            pygame.draw.rect(window, (40, 40, 40), (bar_x - 2, bar_y - 2, bar_width + 4, bar_height + 4), border_radius=3)
            pygame.draw.rect(window, (80, 0, 0), (bar_x, bar_y, bar_width, bar_height), border_radius=2)
            
            health_width = int(bar_width * (self.health / self.max_health))
            if health_width > 0:
                health_color = (0, 200, 0) if self.health > 60 else (255, 200, 0) if self.health > 30 else (255, 50, 50)
                pygame.draw.rect(window, health_color, (bar_x, bar_y, health_width, bar_height), border_radius=2)
            
            font = pygame.font.SysFont('arial', 14, bold=True)
            name_text = font.render("SIR ALDRIC the Unyielding", True, (150, 180, 255))
            name_x = screen_x + (self.width - name_text.get_width()) // 2
            window.blit(name_text, (name_x, bar_y - 18))
        
        # draw spinning mace projectiles
        for proj in self.projectiles:
            proj_x = proj['x'] - offset_x
            proj_y = proj['y'] - offset_y
            # mace body
            pygame.draw.circle(window, (100, 110, 130), (int(proj_x), int(proj_y)), proj['size']//2)
            pygame.draw.circle(window, (150, 160, 170), (int(proj_x), int(proj_y)), proj['size']//2 - 4)
            # 4 spikes in a cross pattern - they spin as proj['angle'] increases
            for i in range(4):
                # convert angle to radians, offset each spike by 90 degrees
                angle = math.radians(proj['angle'] + i * 90)
                # cos/sin give us x,y position on the circle around the mace
                spike_x = proj_x + math.cos(angle) * (proj['size']//2 + 5)
                spike_y = proj_y + math.sin(angle) * (proj['size']//2 + 5)
                pygame.draw.circle(window, (80, 80, 90), (int(spike_x), int(spike_y)), 4)
        
        if self.current_dialogue:
            self.draw_dialogue(window, screen_x, screen_y)
    
    def draw_dialogue(self, window, boss_x, boss_y):
        """Draw the boss dialogue bubble."""
        font = pygame.font.SysFont('arial', 16, bold=True)
        
        words = self.current_dialogue.split()
        lines = []
        current_line = ""
        max_width = 300
        
        for word in words:
            test_line = current_line + " " + word if current_line else word
            if font.size(test_line)[0] < max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        
        if not lines:
            return
        
        padding = 15
        line_height = 22
        bubble_width = max(font.size(line)[0] for line in lines) + padding * 2
        bubble_height = len(lines) * line_height + padding * 2
        
        bubble_x = boss_x + self.width // 2 - bubble_width // 2
        bubble_y = boss_y - bubble_height - 30
        
        win_width = window.get_width()
        if bubble_x < 10:
            bubble_x = 10
        if bubble_x + bubble_width > win_width - 10:
            bubble_x = win_width - bubble_width - 10
        if bubble_y < 10:
            bubble_y = boss_y + self.height + 10
        
        bubble_surface = pygame.Surface((bubble_width, bubble_height), pygame.SRCALPHA)
        pygame.draw.rect(bubble_surface, (20, 20, 40, 230), bubble_surface.get_rect(), border_radius=10)
        window.blit(bubble_surface, (bubble_x, bubble_y))
        pygame.draw.rect(window, (100, 150, 255), (bubble_x, bubble_y, bubble_width, bubble_height), 3, border_radius=10)
        
        for i, line in enumerate(lines):
            text_surface = font.render(line, True, (200, 220, 255))
            window.blit(text_surface, (bubble_x + padding, bubble_y + padding + i * line_height))


# BOSS CLASS - ALIEN BOSS (Outer Space)
# The third boss - an alien commander using the image.png sprite

class AlienBoss:
    """An AI-powered Alien boss at the end of the Space level."""
    
    # Pre-written dialogue for when AI is unavailable
    FALLBACK_DIALOGUE = {
        'intro': [
            "GREETINGS, EARTHLING. I AM COMMANDER ZYX-9 OF THE GALACTIC FEDERATION.",
            "YOUR PRIMITIVE SPECIES HAS VENTURED TOO FAR INTO THE COSMOS.",
            "PREPARE FOR ASSIMILATION. RESISTANCE IS... INADVISABLE."
        ],
        'taunt': [
            "YOUR BIOLOGICAL REFLEXES ARE... INADEQUATE.",
            "I HAVE COMPUTED 47,392 WAYS TO DEFEAT YOU. THIS IS NUMBER 12.",
            "THE STARS THEMSELVES TREMBLE AT MY APPROACH!",
            "YOUR PLANET WILL MAKE AN EXCELLENT MINING COLONY.",
            "FASCINATING. YOU STILL FUNCTION. TEMPORARILY."
        ],
        'damaged': [
            "CRITICAL ERROR! HOW DID YOU BREACH MY SHIELDS?!",
            "RECALIBRATING... YOUR LUCK CANNOT PERSIST.",
            "IMPOSSIBLE! MY CALCULATIONS WERE PERFECT!",
            "SYSTEM DAMAGE DETECTED. INITIATING COUNTERMEASURES."
        ],
        'low_health': [
            "PRIMARY SYSTEMS FAILING... THIS WAS NOT... PREDICTED...",
            "THE FEDERATION... WILL AVENGE... MY DEFEAT...",
            "YOUR SPECIES... IS MORE DANGEROUS... THAN WE CALCULATED..."
        ],
        'defeat': [
            "SYSTEMS... CRITICAL... YOU HAVE... WON... THIS BATTLE...",
            "TRANSMITTING... FINAL... REPORT... TO HOMEWORLD...",
            "PERHAPS... YOUR KIND... DESERVES... THE STARS... AFTER ALL..."
        ]
    }
    
    def __init__(self, x, y, max_x):
        self.x = x
        self.y = y
        self.width = 120
        self.height = 150
        self.rect = pygame.Rect(x, y, self.width, self.height)
        
        # Boss stats
        self.max_health = 100
        self.health = self.max_health
        self.is_alive = True
        self.is_defeated = False
        self.phase = 1
        
        # Movement
        self.start_x = x
        self.move_range = 200
        self.speed = 3  # faster than other bosses
        self.direction = 1
        self.hover_offset = 0
        self.hover_speed = 0.06
        
        # Combat
        self.attack_cooldown = 0
        self.attack_pattern = 0
        self.projectiles = []
        self.is_vulnerable = True
        self.invincibility_frames = 0
        
        # Dialogue system
        self.current_dialogue = ""
        self.dialogue_timer = 0
        self.dialogue_queue = queue.Queue()
        self.has_introduced = False
        self.last_taunt_time = 0
        
        # AI dialogue
        self.ai_thread = None
        self.ai_available = OLLAMA_AVAILABLE
        
        self.system_prompt = """You are Commander Zyx-9, an alien from the Galactic Federation. 
You speak in robotic, cold, calculated tones. Use technical/sci-fi language.
Reference space, galaxies, computations, systems, federation, and alien concepts.
Keep responses to 1-2 sentences maximum. Be intimidating and otherworldly. Do not use quotation marks."""
        
        # Animation
        self.animation_count = 0
        self.glow_intensity = 0
        
        # Load the alien sprite
        self.load_boss_sprite()
    
    def load_boss_sprite(self):
        """Load the alien boss sprite from image.png."""
        try:
            path = join("assets", "MainCharacters", "image.png")
            self.image = pygame.image.load(path).convert_alpha()
            self.image = pygame.transform.scale(self.image, (self.width, self.height))
        except:
            # fallback: create procedural sprite
            self.create_fallback_sprite()
        self.mask = pygame.mask.from_surface(self.image)
    
    def create_fallback_sprite(self):
        """Create a procedural alien sprite if image.png fails to load."""
        self.image = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        
        # Alien body - green/grey
        body_color = (100, 150, 100)
        pygame.draw.ellipse(self.image, body_color, (20, 40, 80, 100))
        
        # Big alien head
        head_color = (120, 180, 120)
        pygame.draw.ellipse(self.image, head_color, (15, 5, 90, 60))
        
        # Big black eyes
        pygame.draw.ellipse(self.image, (10, 10, 20), (25, 20, 25, 30))
        pygame.draw.ellipse(self.image, (10, 10, 20), (70, 20, 25, 30))
        # Eye shine
        pygame.draw.ellipse(self.image, (50, 100, 50), (30, 25, 8, 10))
        pygame.draw.ellipse(self.image, (50, 100, 50), (75, 25, 8, 10))
        
        # Thin arms
        pygame.draw.line(self.image, body_color, (25, 60), (5, 100), 6)
        pygame.draw.line(self.image, body_color, (95, 60), (115, 100), 6)
        
        # Thin legs
        pygame.draw.line(self.image, body_color, (45, 130), (35, 145), 5)
        pygame.draw.line(self.image, body_color, (75, 130), (85, 145), 5)
        
        self.mask = pygame.mask.from_surface(self.image)
    
    def get_ai_dialogue(self, context):
        """Get dialogue from Ollama AI in a separate thread."""
        if not self.ai_available:
            return
        
        def fetch_dialogue():
            try:
                prompt = f"{self.system_prompt}\n\nSituation: {context}\n\nRespond as Commander Zyx-9:"
                
                data = json.dumps({
                    "model": "neural-chat:latest",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.5,
                        "num_predict": 12,
                        "top_k": 10,
                        "top_p": 0.8
                    }
                }).encode('utf-8')
                
                req = urllib.request.Request(
                    OLLAMA_URL,
                    data=data,
                    headers={'Content-Type': 'application/json'},
                    method='POST'
                )
                
                with urllib.request.urlopen(req, timeout=25) as response:
                    result = json.loads(response.read().decode('utf-8'))
                    dialogue = result.get('response', '').strip()
                    dialogue = dialogue.replace('"', '').replace("'", "'")
                    if dialogue and len(dialogue) > 5:
                        self.dialogue_queue.put(dialogue)
                        print(f"✓ Alien AI dialogue: {dialogue[:60]}...")
            except Exception as e:
                print(f"✗ Alien AI error: {e}")
        
        self.ai_thread = threading.Thread(target=fetch_dialogue, daemon=True)
        self.ai_thread.start()
    
    def get_fallback_dialogue(self, category):
        """Get pre-written dialogue when AI is unavailable."""
        dialogues = self.FALLBACK_DIALOGUE.get(category, self.FALLBACK_DIALOGUE['taunt'])
        return random.choice(dialogues)
    
    def introduce(self):
        """Boss introduction sequence."""
        if not self.has_introduced:
            self.has_introduced = True
            if self.ai_available:
                self.get_ai_dialogue("The hero has arrived in your spacecraft. Give a dramatic introduction as an alien commander.")
            self.current_dialogue = self.get_fallback_dialogue('intro')
            self.dialogue_timer = 180
    
    def taunt(self):
        """Random taunts during battle."""
        current_time = pygame.time.get_ticks()
        if current_time - self.last_taunt_time > 5000:
            self.last_taunt_time = current_time
            if self.ai_available and random.random() < 0.5:
                self.get_ai_dialogue("Taunt the human during battle. Reference your superior technology.")
            else:
                self.current_dialogue = self.get_fallback_dialogue('taunt')
                self.dialogue_timer = 120
    
    def on_damaged(self, damage):
        """Handle taking damage."""
        if not self.is_vulnerable or self.invincibility_frames > 0:
            return False
        
        self.health -= damage
        self.invincibility_frames = 60
        
        if self.health <= 30:
            self.phase = 3
            self.speed = 5
        elif self.health <= 60:
            self.phase = 2
            self.speed = 4
        
        if self.health <= 0:
            self.is_defeated = True
            self.is_alive = False
            if self.ai_available:
                self.get_ai_dialogue("You have been defeated. Give dying words acknowledging the human's victory.")
            self.current_dialogue = self.get_fallback_dialogue('defeat')
            self.dialogue_timer = 300
        elif self.health <= 30:
            if self.ai_available:
                self.get_ai_dialogue("You are badly damaged. Express system failures and disbelief.")
            else:
                self.current_dialogue = self.get_fallback_dialogue('low_health')
                self.dialogue_timer = 120
        else:
            if self.ai_available:
                self.get_ai_dialogue("You took damage. React with cold calculation and surprise.")
            else:
                self.current_dialogue = self.get_fallback_dialogue('damaged')
                self.dialogue_timer = 90
        
        return True
    
    def create_projectile(self):
        """Create a plasma projectile."""
        proj = {
            'x': self.rect.centerx,
            'y': self.rect.centery,
            'dx': -10,  # faster projectiles
            'dy': random.uniform(-3, 3),
            'size': 22,
            'lifetime': 180,
            'angle': 0
        }
        self.projectiles.append(proj)
    
    def update(self, player_x):
        """Update boss state."""
        if self.is_defeated:
            return
        
        try:
            while True:
                dialogue = self.dialogue_queue.get_nowait()
                self.current_dialogue = dialogue
                self.dialogue_timer = 150
        except queue.Empty:
            pass
        
        if self.dialogue_timer > 0:
            self.dialogue_timer -= 1
        else:
            self.current_dialogue = ""
        
        if self.invincibility_frames > 0:
            self.invincibility_frames -= 1
        
        # hover effect - slightly more floaty for alien
        self.hover_offset = math.sin(self.animation_count * self.hover_speed) * 12
        self.animation_count += 1
        
        # pulsing glow
        self.glow_intensity = (math.sin(self.animation_count * 0.1) + 1) * 0.5
        
        # move toward player
        if abs(player_x - self.rect.centerx) > 100:
            if player_x < self.rect.centerx:
                self.rect.x -= self.speed
            else:
                self.rect.x += self.speed
        
        if self.rect.x < self.start_x - self.move_range:
            self.rect.x = self.start_x - self.move_range
        elif self.rect.x > self.start_x + self.move_range:
            self.rect.x = self.start_x + self.move_range
        
        # attack pattern - faster in later phases
        self.attack_cooldown -= 1
        if self.attack_cooldown <= 0:
            self.create_projectile()
            self.attack_cooldown = max(20, 70 - self.phase * 20)
        
        # update projectiles with spinning
        for proj in self.projectiles[:]:
            proj['x'] += proj['dx']
            proj['y'] += proj['dy']
            proj['angle'] += 15
            proj['lifetime'] -= 1
            if proj['lifetime'] <= 0 or proj['x'] < self.start_x - 500:
                self.projectiles.remove(proj)
        
        if self.has_introduced:
            self.taunt()
    
    def check_projectile_collision(self, player):
        """Check if any projectiles hit the player."""
        player_rect = player.rect
        for proj in self.projectiles[:]:
            proj_rect = pygame.Rect(proj['x'] - proj['size']//2, proj['y'] - proj['size']//2, 
                                   proj['size'], proj['size'])
            if player_rect.colliderect(proj_rect):
                self.projectiles.remove(proj)
                return True
        return False
    
    def check_player_attack(self, player):
        """Check if player is attacking the boss (jumping on head)."""
        if player.y_vel > 0:
            head_rect = pygame.Rect(self.rect.x + 20, self.rect.y, self.rect.width - 40, 30)
            feet_rect = pygame.Rect(player.rect.x + 5, player.rect.bottom - 10, player.rect.width - 10, 15)
            if feet_rect.colliderect(head_rect):
                return True
        return False
    
    def draw(self, window, offset_x, offset_y):
        """Draw the boss and its effects."""
        if self.is_defeated and self.dialogue_timer <= 0:
            return
        
        screen_x = self.rect.x - offset_x
        screen_y = self.rect.y - offset_y + int(self.hover_offset)
        
        # Draw green glow effect
        if self.is_alive:
            glow_size = int(30 + self.glow_intensity * 20)
            glow_surface = pygame.Surface((self.width + glow_size*2, self.height + glow_size*2), pygame.SRCALPHA)
            glow_color = (50, 255, 100, int(50 + self.glow_intensity * 50))
            pygame.draw.ellipse(glow_surface, glow_color, glow_surface.get_rect())
            window.blit(glow_surface, (screen_x - glow_size, screen_y - glow_size))
        
        # Flash when invincible
        if self.invincibility_frames > 0 and self.invincibility_frames % 6 < 3:
            tinted = self.image.copy()
            tinted.fill((100, 255, 100, 100), special_flags=pygame.BLEND_RGBA_MULT)
            window.blit(tinted, (screen_x, screen_y))
        else:
            window.blit(self.image, (screen_x, screen_y))
        
        # Draw health bar
        if self.is_alive:
            bar_width = 100
            bar_height = 12
            bar_x = screen_x + (self.width - bar_width) // 2
            bar_y = screen_y - 25
            
            pygame.draw.rect(window, (40, 40, 40), (bar_x - 2, bar_y - 2, bar_width + 4, bar_height + 4), border_radius=3)
            pygame.draw.rect(window, (80, 0, 0), (bar_x, bar_y, bar_width, bar_height), border_radius=2)
            
            health_width = int(bar_width * (self.health / self.max_health))
            if health_width > 0:
                health_color = (0, 200, 0) if self.health > 60 else (255, 200, 0) if self.health > 30 else (255, 50, 50)
                pygame.draw.rect(window, health_color, (bar_x, bar_y, health_width, bar_height), border_radius=2)
            
            font = pygame.font.SysFont('arial', 14, bold=True)
            name_text = font.render("COMMANDER ZYX-9", True, (100, 255, 100))
            name_x = screen_x + (self.width - name_text.get_width()) // 2
            window.blit(name_text, (name_x, bar_y - 18))
        
        # Draw plasma projectiles (glowing green orbs)
        for proj in self.projectiles:
            proj_x = proj['x'] - offset_x
            proj_y = proj['y'] - offset_y
            # outer glow
            pygame.draw.circle(window, (50, 200, 50), (int(proj_x), int(proj_y)), proj['size']//2 + 4)
            # inner plasma
            pygame.draw.circle(window, (100, 255, 100), (int(proj_x), int(proj_y)), proj['size']//2)
            pygame.draw.circle(window, (200, 255, 200), (int(proj_x), int(proj_y)), proj['size']//2 - 4)
        
        # Draw dialogue
        if self.current_dialogue:
            self.draw_dialogue(window, screen_x, screen_y)
    
    def draw_dialogue(self, window, boss_x, boss_y):
        """Draw the boss dialogue bubble."""
        font = pygame.font.SysFont('arial', 16, bold=True)
        
        words = self.current_dialogue.split()
        lines = []
        current_line = ""
        max_width = 300
        
        for word in words:
            test_line = current_line + " " + word if current_line else word
            if font.size(test_line)[0] < max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        
        if not lines:
            return
        
        padding = 15
        line_height = 22
        bubble_width = max(font.size(line)[0] for line in lines) + padding * 2
        bubble_height = len(lines) * line_height + padding * 2
        
        bubble_x = boss_x + self.width // 2 - bubble_width // 2
        bubble_y = boss_y - bubble_height - 30
        
        win_width = window.get_width()
        if bubble_x < 10:
            bubble_x = 10
        if bubble_x + bubble_width > win_width - 10:
            bubble_x = win_width - bubble_width - 10
        if bubble_y < 10:
            bubble_y = boss_y + self.height + 10
        
        bubble_surface = pygame.Surface((bubble_width, bubble_height), pygame.SRCALPHA)
        pygame.draw.rect(bubble_surface, (10, 30, 10, 230), bubble_surface.get_rect(), border_radius=10)
        window.blit(bubble_surface, (bubble_x, bubble_y))
        pygame.draw.rect(window, (100, 255, 100), (bubble_x, bubble_y, bubble_width, bubble_height), 3, border_radius=10)
        
        for i, line in enumerate(lines):
            text_surface = font.render(line, True, (150, 255, 150))
            window.blit(text_surface, (bubble_x + padding, bubble_y + padding + i * line_height))


# ==============================================================================
#                       PLATFORM GENERATION
# ==============================================================================
# Procedural level generation system that creates varied platforming challenges.
#
# The system generates different patterns of blocks to create interesting
# gameplay variety without hand-designed levels. Patterns include:
#
#   single:      One block at a random height (easy jump)
#   double_jump: One block high up (requires double jump to reach)
#   stack:       Two blocks stacked vertically (climbing challenge)
#   staircase:   Three blocks ascending (step climbing)
#   gap:         Two blocks with a gap between (precision jumping)
#
# The generator respects level boundaries and avoids overlapping objects.
# Each level style (Egypt, Medieval, Space) uses appropriate block textures.
# ==============================================================================


def generate_platforming_blocks(start_x, block_size, height_offset, style="egypt"):
    """
    Generate a random platforming pattern at the specified position.
    
    Creates a small cluster of blocks forming a platforming challenge.
    The pattern is randomly selected for variety.
    
    Args:
        start_x (int): X position to start generating blocks
        block_size (int): Size of each block in pixels
        height_offset (int): Vertical offset (unused, kept for compatibility)
        style (str): Visual style - "egypt", "medieval", or "space"
    
    Returns:
        list: List of Block objects forming the platform pattern
    
    Pattern Types:
        - single: One block 2-3 blocks above ground (reachable with single/double jump)
        - double_jump: A stepping-stone at height 2 leading to a block at height 3
        - stack: Two blocks, one low, one elevated (progressive climbing)
        - staircase: Three blocks forming ascending steps
        - gap: Two blocks separated by a gap (precision jumping)
        - bridge: A flat 2-3 block wide platform at low height (rest area)
    """
    blocks = []
    pattern = random.choice(['single', 'double_jump', 'stack', 'staircase', 'gap', 'bridge'])
    
    if pattern == 'single':
        y = Height - block_size * random.randint(2, 3)
        blocks.append(Block(start_x, y, block_size, style=style))
    elif pattern == 'double_jump':
        # Stepping stone at height 2, target at height 3 (reachable from step)
        blocks.append(Block(start_x, Height - block_size * 2, block_size, style=style))
        blocks.append(Block(start_x + block_size * 2, Height - block_size * 3, block_size, style=style))
    elif pattern == 'stack':
        blocks.append(Block(start_x, Height - block_size * 2, block_size, style=style))
        blocks.append(Block(start_x + block_size, Height - block_size * 3, block_size, style=style))
    elif pattern == 'staircase':
        for i in range(3):
            x = start_x + (i * block_size)
            y = Height - block_size * (2 + i)
            blocks.append(Block(x, y, block_size, style=style))
    elif pattern == 'gap':
        y = Height - block_size * 2
        blocks.append(Block(start_x, y, block_size, style=style))
        blocks.append(Block(start_x + block_size * 3, y, block_size, style=style))
    elif pattern == 'bridge':
        # Wide flat platform - gives the player a breather
        y = Height - block_size * 2
        width = random.randint(2, 3)
        for i in range(width):
            blocks.append(Block(start_x + i * block_size, y, block_size, style=style))
    
    return blocks

def generate_platforming_blocks_at_height(start_x, block_size, screen_height, style="egypt"):
    """Generate random platforming patterns at a specific screen height."""
    blocks = []
    pattern = random.choice(['single', 'double_jump', 'stack', 'staircase', 'gap', 'bridge'])
    
    if pattern == 'single':
        y = screen_height - block_size * random.randint(2, 3)
        blocks.append(Block(start_x, y, block_size, style=style))
    elif pattern == 'double_jump':
        # Stepping stone at height 2, target at height 3 (reachable from step)
        blocks.append(Block(start_x, screen_height - block_size * 2, block_size, style=style))
        blocks.append(Block(start_x + block_size * 2, screen_height - block_size * 3, block_size, style=style))
    elif pattern == 'stack':
        blocks.append(Block(start_x, screen_height - block_size * 2, block_size, style=style))
        blocks.append(Block(start_x + block_size, screen_height - block_size * 3, block_size, style=style))
    elif pattern == 'staircase':
        for i in range(3):
            x = start_x + (i * block_size)
            y = screen_height - block_size * (2 + i)
            blocks.append(Block(x, y, block_size, style=style))
    elif pattern == 'gap':
        y = screen_height - block_size * 2
        blocks.append(Block(start_x, y, block_size, style=style))
        blocks.append(Block(start_x + block_size * 3, y, block_size, style=style))
    elif pattern == 'bridge':
        # Wide flat platform - gives the player a breather
        y = screen_height - block_size * 2
        width = random.randint(2, 3)
        for i in range(width):
            blocks.append(Block(start_x + i * block_size, y, block_size, style=style))
    
    return blocks


def create_floor(block_size, start_range, end_range, style="egypt"):
    """
    Create a row of floor blocks spanning a range.
    
    The floor is the base terrain that the player walks on.
    Uses list comprehension for efficient block generation.
    
    Args:
        block_size (int): Size of each block in pixels
        start_range (int): Starting block index (can be negative)
        end_range (int): Ending block index (exclusive)
        style (str): Visual style for blocks
    
    Returns:
        list: List of Block objects forming the floor
    """
    return [Block(i * block_size, Height - block_size, block_size, style=style) for i in range(start_range, end_range)]


def create_floor_at_height(block_size, start_range, end_range, screen_height, style="egypt"):
    """
    Create a row of floor blocks at a specific screen height.
    
    Similar to create_floor but uses explicit height instead of global Height.
    Used when the screen height may differ from the global variable.
    
    Args:
        block_size (int): Size of each block in pixels
        start_range (int): Starting block index
        end_range (int): Ending block index (exclusive)
        screen_height (int): Height at which to place the floor
        style (str): Visual style for blocks
    
    Returns:
        list: List of Block objects forming the floor
    """
    return [Block(i * block_size, screen_height - block_size, block_size, style=style) for i in range(start_range, end_range)]


def generate_traps(block_size, max_x, objects):
    """
    Generate hazard traps throughout the level.
    
    Places various trap types at strategic positions while avoiding
    overlap with existing terrain blocks. Each trap type is placed
    at different intervals for variety.
    
    Args:
        block_size (int): Size of terrain blocks (for positioning)
        max_x (int): Maximum X coordinate for trap placement
        objects (list): Existing objects to avoid overlapping
    
    Returns:
        list: List of Trap objects (Spikes, Fire, Saw)
    
    Placement Strategy:
        - Spikes: Every 8 blocks, on floor level
        - Fire: Every 12 blocks, on floor level
        - Saw: Every 15 blocks, slightly elevated (in air)
    """
    traps = []
    trap_size = 48  # Standard trap size in pixels
    
    def is_clear(x, y, width, height):
        """
        Check if a position is clear of existing blocks.
        
        Uses rectangle collision to detect overlaps.
        
        Args:
            x, y: Position to check
            width, height: Size of the area to check
        
        Returns:
            bool: True if position is clear, False if blocked
        """
        trap_rect = pygame.Rect(x, y, width, height)
        for obj in objects:
            if trap_rect.colliderect(obj.rect):
                return False
        return True
    
    # Place spikes at various positions (on floor only, offset from platforms)
    for i in range(5, 45, 8):
        x = i * block_size + block_size // 2
        y = Height - block_size - trap_size
        if x < max_x and is_clear(x, y, trap_size, trap_size):
            traps.append(Spikes(x, y, trap_size, trap_size))
    
    # Place fire traps
    for i in range(8, 40, 12):
        x = i * block_size + block_size // 4
        y = Height - block_size - trap_size
        if x < max_x and is_clear(x, y, trap_size, trap_size):
            traps.append(Fire(x, y, trap_size, trap_size))
    
    # Place moving saws (in the air, between platforms)
    for i in range(12, 45, 15):
        x = i * block_size + block_size
        y = Height - block_size * 2 - trap_size
        if x < max_x and is_clear(x, y, trap_size, trap_size):
            traps.append(Saw(x, y, trap_size, trap_size, move_range=100))
    
    return traps

def generate_traps_at_height(block_size, max_x, objects, screen_height):
    """Generate traps throughout the level at a specific screen height."""
    traps = []
    trap_size = 48
    
    def is_clear(x, y, width, height):
        """Check if position is clear of existing blocks."""
        trap_rect = pygame.Rect(x, y, width, height)
        for obj in objects:
            if trap_rect.colliderect(obj.rect):
                return False
        return True
    
    # Leave a safe zone at the start for the tutorial area (first 3 blocks)
    safe_zone = 3 * block_size
    
    # Place spikes at moderate intervals
    for i in range(5, 80, 7):
        x = i * block_size + block_size // 2
        if x < safe_zone:
            continue  # Skip safe zone
        y = screen_height - block_size - trap_size
        if x < max_x and is_clear(x, y, trap_size, trap_size):
            # 50% chance to place a spike
            if random.random() < 0.5:
                traps.append(Spikes(x, y, trap_size, trap_size))
    
    # Place fire traps at wider intervals
    for i in range(8, 70, 10):
        x = i * block_size + block_size // 4
        if x < safe_zone:
            continue  # Skip safe zone
        y = screen_height - block_size - trap_size
        if x < max_x and is_clear(x, y, trap_size, trap_size):
            # 45% chance to place fire
            if random.random() < 0.45:
                traps.append(Fire(x, y, trap_size, trap_size))
    
    # Place moving saws sparingly (every 12 blocks)
    for i in range(12, 75, 12):
        x = i * block_size + block_size
        if x < safe_zone:
            continue  # Skip safe zone
        y = screen_height - block_size * 2 - trap_size
        if x < max_x and is_clear(x, y, trap_size, trap_size):
            # 40% chance for saws (they're harder to avoid)
            if random.random() < 0.4:
                traps.append(Saw(x, y, trap_size, trap_size, move_range=120))
    
    # Add occasional double spike traps for challenge variety
    for i in range(15, 60, 16):
        x = i * block_size
        if x < safe_zone:
            continue
        y = screen_height - block_size - trap_size
        if x < max_x and is_clear(x, y, trap_size * 2, trap_size):
            if random.random() < 0.35:
                traps.append(Spikes(x, y, trap_size, trap_size))
                if is_clear(x + trap_size + 10, y, trap_size, trap_size):
                    traps.append(Spikes(x + trap_size + 10, y, trap_size, trap_size))
    
    return traps


# ==============================================================================
#                        COLLISION HANDLERS
# ==============================================================================
# Physics collision detection and resolution for player movement.
#
# The collision system uses a two-phase approach:
#   1. Move player horizontally, check and resolve horizontal collisions
#   2. Move player vertically (via physics), check and resolve vertical collisions
#
# This separation prevents corner-clipping issues common in platformers.
# Each axis is handled independently to determine which side was hit.
#
# Collision Response:
#   - Horizontal: Player is pushed back to the edge of the block
#   - Vertical (falling): Player lands on top, jump count resets
#   - Vertical (rising): Player bounces off ceiling
# ==============================================================================


def handle_horizontal_collision(player, objects):
    """
    Handle horizontal movement and collision with terrain.
    
    Moves the player horizontally based on current velocity, then
    checks for collisions and resolves them by pushing the player
    back to the block edge.
    
    Args:
        player (Player): The player object to move
        objects (list): List of terrain objects to check collision with
    
    Collision Resolution:
        - Moving right: Snap player's right edge to block's left edge
        - Moving left: Snap player's left edge to block's right edge
    """
    player.rect.x += player.x_vel
    
    for obj in objects:
        if player.rect.colliderect(obj.rect):
            if player.x_vel > 0:
                # Moving right -> hit left side of block
                player.rect.right = obj.rect.left
            elif player.x_vel < 0:
                # Moving left -> hit right side of block
                player.rect.left = obj.rect.right
            player.x_vel = 0  # Stop horizontal movement


def handle_vertical_collision(player, objects, dy):
    """
    Handle vertical collision with terrain (landing/ceiling).
    
    Called after physics moves the player vertically. Checks for
    collisions and resolves them appropriately based on direction.
    
    Args:
        player (Player): The player object to check
        objects (list): List of terrain objects to check collision with
        dy (float): The vertical displacement that was applied
    
    Collision Resolution:
        - Falling (dy > 0): Land on platform, reset jump count
        - Rising (dy < 0): Hit ceiling, reverse/stop upward velocity
    """
    for obj in objects:
        if player.rect.colliderect(obj.rect):
            if dy > 0:
                # Falling down - land on top of block
                player.rect.bottom = obj.rect.top
                player.landed()  # Reset jump count and velocity
            elif dy < 0:
                # Jumping up - hit bottom of block (ceiling)
                player.rect.top = obj.rect.bottom
                player.hit_head()  # Bounce down


def handle_input(player, objects):
    """
    Process keyboard input for player movement.
    
    Reads the current keyboard state and sets player velocity.
    Called once per frame in the game loop.
    
    Args:
        player (Player): The player object to control
        objects (list): Unused (kept for compatibility)
    
    Controls:
        - Left Arrow: Move left
        - Right Arrow: Move right
    """
    keys = pygame.key.get_pressed()
    player.x_vel = 0  # Reset velocity each frame (no momentum)
    
    if keys[pygame.K_LEFT]:
        player.move_left(player_VEL)
    if keys[pygame.K_RIGHT]:
        player.move_right(player_VEL)


def handle_jump_input(player):
    """
    Handle jump key press.
    
    Allows jumping if the player has jumps remaining.
    Maximum of 2 jumps (ground jump + double jump).
    
    Args:
        player (Player): The player object to make jump
    """
    if player.jump_count < 2:
        player.jump()


def check_trap_collision(player, traps):
    """
    Check if the player is touching any active trap.
    
    Uses a two-phase collision check:
      1. Rectangle overlap (fast, coarse)
      2. Pixel mask overlap (slow, precise)
    
    Args:
        player (Player): The player to check
        traps (list): List of trap objects to check against
    
    Returns:
        bool: True if player is touching a deadly trap
    
    Special Cases:
        - Fire traps are ignored when in "off" state
    """
    for trap in traps:
        # Fire traps can be walked through when off
        if isinstance(trap, Fire) and not trap.is_on:
            continue
        
        # First check: rectangle overlap (fast)
        if player.rect.colliderect(trap.rect):
            # Second check: pixel-perfect mask overlap (precise)
            offset = (trap.rect.x - player.rect.x, trap.rect.y - player.rect.y)
            if player.mask and player.mask.overlap(trap.mask, offset):
                return True
    
    return False


def update_traps(traps):
    """
    Update all trap animations and movements.
    
    Calls the update() method on each trap that has one.
    This handles fire toggling, saw movement/spinning, etc.
    
    Args:
        traps (list): List of trap objects to update
    """
    for trap in traps:
        if hasattr(trap, 'update'):
            trap.update()


# ==============================================================================
#                            RENDERING
# ==============================================================================
# Drawing functions for all visual elements:
#
#   draw_tutorial_bubble: In-game tutorial instructions
#   draw_hud: Heads-up display (lives, deaths, progress, time)
#   draw_background: Parallax scrolling background
#   render_frame: Main rendering function that draws everything
#   update_camera: Smooth camera following player
#
# All drawing functions account for camera offset to create scrolling effect.
# Objects outside the visible area are culled for performance.
# ==============================================================================


def draw_tutorial_bubble(window, player_screen_x, player_screen_y, tutorial_step):
    """
    Draw a tutorial instruction bubble near the player.
    
    Displays progressive tutorial messages teaching the controls.
    Uses the same visual style as the HUD for consistency.
    
    Args:
        window (pygame.Surface): Surface to draw on
        player_screen_x (int): Player's X position on screen
        player_screen_y (int): Player's Y position on screen
        tutorial_step (int): Current tutorial step (0-4)
    
    Tutorial Steps:
        0: Move right instruction
        1: Move left instruction
        2: Jump instruction
        3: Double jump instruction
        4: Good luck message
    """
    # Color scheme matching HUD
    panel_bg = (15, 15, 25)
    border_color = (0, 220, 220)
    border_glow = (0, 180, 180, 100)
    gold_text = (255, 215, 0)
    cyan_text = (0, 230, 230)
    white_text = (240, 240, 240)
    
    # Progressive tutorial steps
    tutorial_steps = [
        {"instruction": "Press → to move RIGHT", "key": "right", "complete": False},
        {"instruction": "Press ← to move LEFT", "key": "left", "complete": False},
        {"instruction": "Press ↑ to JUMP", "key": "jump", "complete": False},
        {"instruction": "Press ↑ in air to DOUBLE JUMP!", "key": "double_jump", "complete": False},
        {"instruction": "Now avoid the traps! Good luck!", "key": "done", "complete": False},
    ]
    
    if tutorial_step >= len(tutorial_steps):
        return  # Tutorial complete
    
    current_step = tutorial_steps[tutorial_step]
    
    # Fonts matching HUD
    try:
        font_title = pygame.font.SysFont('consolas', 14, bold=True)
        font_instruction = pygame.font.SysFont('consolas', 20, bold=True)
    except:
        font_title = pygame.font.SysFont('arial', 14, bold=True)
        font_instruction = pygame.font.SysFont('arial', 20, bold=True)
    
    # Calculate bubble size
    padding = 15
    title_text = f"TUTORIAL ({tutorial_step + 1}/{len(tutorial_steps)})"
    instruction_text = current_step["instruction"]
    
    title_width = font_title.size(title_text)[0]
    instruction_width = font_instruction.size(instruction_text)[0]
    bubble_width = max(title_width, instruction_width) + padding * 2 + 20
    bubble_height = 70
    
    # Position bubble above and to the right of player
    bubble_x = player_screen_x + 60
    bubble_y = player_screen_y - bubble_height - 30
    
    # Keep bubble on screen
    win_width, win_height = window.get_size()
    if bubble_x + bubble_width > win_width - 10:
        bubble_x = player_screen_x - bubble_width - 20
    if bubble_y < 10:
        bubble_y = 10
    if bubble_x < 10:
        bubble_x = 10
    
    # Draw glow effect
    glow_surface = pygame.Surface((bubble_width + 6, bubble_height + 6), pygame.SRCALPHA)
    pygame.draw.rect(glow_surface, border_glow, glow_surface.get_rect(), border_radius=12)
    window.blit(glow_surface, (bubble_x - 3, bubble_y - 3))
    
    # Draw bubble background
    bubble_surface = pygame.Surface((bubble_width, bubble_height), pygame.SRCALPHA)
    pygame.draw.rect(bubble_surface, panel_bg + (240,), bubble_surface.get_rect(), border_radius=10)
    window.blit(bubble_surface, (bubble_x, bubble_y))
    
    # Draw border
    bubble_rect = pygame.Rect(bubble_x, bubble_y, bubble_width, bubble_height)
    pygame.draw.rect(window, border_color, bubble_rect, 3, border_radius=10)
    
    # Inner border accent
    inner_rect = pygame.Rect(bubble_x + 4, bubble_y + 4, bubble_width - 8, bubble_height - 8)
    pygame.draw.rect(window, (border_color[0]//3, border_color[1]//3, border_color[2]//3), inner_rect, 1, border_radius=8)
    
    # Draw pointer triangle
    pointer_points = [
        (bubble_x + 20, bubble_y + bubble_height),
        (bubble_x + 50, bubble_y + bubble_height),
        (min(player_screen_x + 25, bubble_x + 35), min(player_screen_y - 10, bubble_y + bubble_height + 30))
    ]
    pygame.draw.polygon(window, panel_bg, pointer_points)
    pygame.draw.lines(window, border_color, False, 
                      [pointer_points[0], pointer_points[2], pointer_points[1]], 3)
    
    # Draw title
    title_surface = font_title.render(title_text, True, gold_text)
    window.blit(title_surface, (bubble_x + padding, bubble_y + 10))
    
    # Draw instruction
    instruction_surface = font_instruction.render(instruction_text, True, cyan_text)
    window.blit(instruction_surface, (bubble_x + padding, bubble_y + 35))

def draw_hud(window, game_stats):
    """Draw the HUD with game statistics."""
    win_width, win_height = window.get_size()
    
    # Color scheme - Egyptian/retro theme
    panel_bg = (15, 15, 25)  # Dark blue-black
    border_color = (0, 220, 220)  # Cyan border
    border_glow = (0, 180, 180, 100)  # Subtle glow
    gold_text = (255, 215, 0)  # Gold for headers
    cyan_text = (0, 230, 230)  # Cyan for values
    white_text = (240, 240, 240)
    red_text = (255, 80, 80)
    
    # HUD fonts
    try:
        font_title = pygame.font.SysFont('consolas', 14, bold=True)
        font_value = pygame.font.SysFont('consolas', 20, bold=True)
        font_small = pygame.font.SysFont('consolas', 16, bold=True)
    except:
        font_title = pygame.font.SysFont('arial', 14, bold=True)
        font_value = pygame.font.SysFont('arial', 20, bold=True)
        font_small = pygame.font.SysFont('arial', 16, bold=True)
    
    # === MAIN STATS PANEL (top-left) ===
    panel_width = 220
    panel_height = 130
    panel_margin = 20
    panel_x = panel_margin
    panel_y = panel_margin
    
    # Draw panel with glow effect
    glow_rect = pygame.Rect(panel_x - 3, panel_y - 3, panel_width + 6, panel_height + 6)
    glow_surface = pygame.Surface((panel_width + 6, panel_height + 6), pygame.SRCALPHA)
    pygame.draw.rect(glow_surface, border_glow, glow_surface.get_rect(), border_radius=12)
    window.blit(glow_surface, (panel_x - 3, panel_y - 3))
    
    # Main panel background
    panel_surface = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
    pygame.draw.rect(panel_surface, panel_bg + (240,), panel_surface.get_rect(), border_radius=10)
    window.blit(panel_surface, (panel_x, panel_y))
    
    # Border
    panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
    pygame.draw.rect(window, border_color, panel_rect, 3, border_radius=10)
    
    # Inner border accent
    inner_rect = pygame.Rect(panel_x + 4, panel_y + 4, panel_width - 8, panel_height - 8)
    pygame.draw.rect(window, (border_color[0]//3, border_color[1]//3, border_color[2]//3), inner_rect, 1, border_radius=8)
    
    # Content positioning
    content_x = panel_x + 15
    content_y = panel_y + 12
    row_height = 28
    
    # === LIVES ===
    lives_label = font_title.render("LIVES", True, gold_text)
    window.blit(lives_label, (content_x, content_y))
    
    # Draw heart icons for lives
    heart_x = content_x + 60
    for i in range(3):
        if i < game_stats['lives']:
            heart_color = (255, 60, 80)  # Red heart
            pygame.draw.polygon(window, heart_color, [
                (heart_x + i * 22 + 8, content_y + 4),
                (heart_x + i * 22, content_y + 10),
                (heart_x + i * 22 + 8, content_y + 18),
                (heart_x + i * 22 + 16, content_y + 10)
            ])
            pygame.draw.circle(window, heart_color, (heart_x + i * 22 + 4, content_y + 8), 5)
            pygame.draw.circle(window, heart_color, (heart_x + i * 22 + 12, content_y + 8), 5)
        else:
            # Empty heart outline
            pygame.draw.polygon(window, (80, 80, 80), [
                (heart_x + i * 22 + 8, content_y + 4),
                (heart_x + i * 22, content_y + 10),
                (heart_x + i * 22 + 8, content_y + 18),
                (heart_x + i * 22 + 16, content_y + 10)
            ], 2)
    
    content_y += row_height
    
    # === DEATHS ===
    deaths_label = font_title.render("DEATHS", True, gold_text)
    window.blit(deaths_label, (content_x, content_y))
    deaths_value = font_value.render(str(game_stats['deaths']), True, cyan_text)
    window.blit(deaths_value, (content_x + 80, content_y - 2))
    content_y += row_height
    
    # === DISTANCE ===
    distance_label = font_title.render("DISTANCE", True, gold_text)
    window.blit(distance_label, (content_x, content_y))
    distance_value = font_value.render(f"{game_stats['distance']}m", True, cyan_text)
    window.blit(distance_value, (content_x + 90, content_y - 2))
    content_y += row_height
    
    # === TIME ===
    minutes = int(game_stats['time'] // 60)
    seconds = int(game_stats['time'] % 60)
    time_label = font_title.render("TIME", True, gold_text)
    window.blit(time_label, (content_x, content_y))
    time_value = font_value.render(f"{minutes:02d}:{seconds:02d}", True, cyan_text)
    window.blit(time_value, (content_x + 60, content_y - 2))
    
    # === PROGRESS BAR (top-right) ===
    progress_width = 180
    progress_height = 35
    progress_x = win_width - progress_width - panel_margin
    progress_y = panel_margin
    
    # Glow effect
    glow_surface2 = pygame.Surface((progress_width + 6, progress_height + 6), pygame.SRCALPHA)
    pygame.draw.rect(glow_surface2, border_glow, glow_surface2.get_rect(), border_radius=8)
    window.blit(glow_surface2, (progress_x - 3, progress_y - 3))
    
    # Background
    progress_surface = pygame.Surface((progress_width, progress_height), pygame.SRCALPHA)
    pygame.draw.rect(progress_surface, panel_bg + (240,), progress_surface.get_rect(), border_radius=6)
    window.blit(progress_surface, (progress_x, progress_y))
    
    # Border
    pygame.draw.rect(window, border_color, (progress_x, progress_y, progress_width, progress_height), 3, border_radius=6)
    
    # Progress label
    progress_label = font_title.render("PROGRESS", True, gold_text)
    window.blit(progress_label, (progress_x + 10, progress_y + 3))
    
    # Progress bar track
    bar_x = progress_x + 10
    bar_y = progress_y + 20
    bar_width = progress_width - 55
    bar_height = 10
    
    pygame.draw.rect(window, (40, 40, 50), (bar_x, bar_y, bar_width, bar_height), border_radius=5)
    
    # Progress fill with gradient effect
    progress_pct = min(1.0, game_stats['progress'])
    fill_width = int(bar_width * progress_pct)
    if fill_width > 0:
        # Create gradient fill
        for i in range(fill_width):
            ratio = i / max(1, fill_width)
            color = (int(0 + 100 * ratio), int(200 - 50 * ratio), int(150 + 50 * ratio))
            pygame.draw.line(window, color, (bar_x + i, bar_y + 2), (bar_x + i, bar_y + bar_height - 2))
        pygame.draw.rect(window, (100, 255, 200), (bar_x, bar_y, fill_width, bar_height), 2, border_radius=5)
    
    # Percentage text
    pct_text = font_small.render(f"{int(progress_pct * 100)}%", True, cyan_text)
    window.blit(pct_text, (progress_x + progress_width - 45, progress_y + 12))

def draw_background(window, bg_image, offset_x):
    """Tile the background image across the screen with parallax scrolling."""
    bg_width = bg_image.get_width()
    bg_height = bg_image.get_height()
    win_width, win_height = window.get_size()
    
    # wrap the offset so it loops seamlessly
    offset_mod = int(offset_x) % bg_width
    
    # draw enough tiles to cover the whole screen
    x = -offset_mod - bg_width
    while x <= win_width:
        y = -bg_height
        while y <= win_height:
            window.blit(bg_image, (x, y))
            y += bg_height
        x += bg_width

def render_frame(window, bg_image, player, objects, traps, offset_x, offset_y, tutorial_step=-1, game_stats=None, boss=None, portal=None):
    """Render a complete frame - only draw visible objects."""
    win_width, win_height = window.get_size()
    
    # Calculate visible area with margin
    visible_left = offset_x - 100
    visible_right = offset_x + win_width + 100
    visible_top = offset_y - 100
    visible_bottom = offset_y + win_height + 100
    
    window.fill((0, 0, 0))
    draw_background(window, bg_image, offset_x)
    
    # Only draw objects that are visible on screen
    for obj in objects:
        if (obj.rect.right >= visible_left and obj.rect.left <= visible_right and
            obj.rect.bottom >= visible_top and obj.rect.top <= visible_bottom):
            obj.draw(window, offset_x, offset_y)
    
    for trap in traps:
        if (trap.rect.right >= visible_left and trap.rect.left <= visible_right and
            trap.rect.bottom >= visible_top and trap.rect.top <= visible_bottom):
            trap.draw(window, offset_x, offset_y)
    
    # Draw portal if present and active
    if portal:
        portal.draw(window, offset_x, offset_y)
    
    # Draw boss if present
    if boss:
        boss.draw(window, offset_x, offset_y)
    
    player.draw(window, offset_x, offset_y)
    
    # Draw HUD
    if game_stats:
        draw_hud(window, game_stats)
    
    # Draw tutorial bubble if tutorial is active (step >= 0)
    if tutorial_step >= 0:
        player_screen_x = player.rect.x - offset_x
        player_screen_y = player.rect.y - offset_y
        draw_tutorial_bubble(window, player_screen_x, player_screen_y, tutorial_step)
    
    pygame.display.flip()

def update_camera(player, camera_x, camera_y):
    """Smoothly follow player with lerp (linear interpolation)."""
    # target = where we want the camera to be (centered on player)
    target_x = player.rect.centerx - Width // 2
    target_y = player.rect.centery - Height // 2
    
    # move 12% toward target each frame for smooth following
    camera_x += (target_x - camera_x) * 0.12
    camera_y += (target_y - camera_y) * 0.12
    
    # don't let camera show below the floor
    max_camera_y = MAX_HEIGHT - Height
    if camera_y > max_camera_y:
        camera_y = max_camera_y
    
    return camera_x, camera_y


# WORLD GENERATION
# Infinite scrolling world - generates more floor and platforms as player moves

def extend_floor(player, objects, floor_edge, direction, block_size, max_x, style="egypt"):
    """Extend floor blocks as player moves (strict limit at max_x)."""
    if direction == "right":
        while player.rect.right > floor_edge - MAX_WIDTH and floor_edge < max_x:
            objects.append(Block(floor_edge, MAX_HEIGHT - block_size, block_size, style=style))
            floor_edge += block_size
    elif direction == "left":
        while player.rect.left < floor_edge - MAX_WIDTH:
            floor_edge -= block_size
            if floor_edge >= 0:  # Don't go into negative space
                objects.append(Block(floor_edge, MAX_HEIGHT - block_size, block_size, style=style))
    return floor_edge

def extend_platforms(player, objects, last_platform_x, block_size, view_distance, max_x, style="egypt"):
    """Extend platforms as player moves (stop before max_x)."""
    while player.rect.right > last_platform_x - view_distance and last_platform_x + block_size * 6 < max_x:
        platform_blocks = generate_platforming_blocks_at_height(last_platform_x, block_size, MAX_HEIGHT, style=style)
        objects.extend(platform_blocks)
        last_platform_x += block_size * random.randint(5, 8)  # Randomized spacing to reduce clumping
    return last_platform_x


# ==============================================================================
#                          MAIN GAME LOOP
# ==============================================================================
# The core game execution functions that run each level and manage progression.
#
# Game Flow:
#   1. main_menu() - Show title screen, get level selection
#   2. show_intro_story() - Display narrative intro
#   3. run_level() - Execute gameplay for current level
#   4. show_level_transition() - Transition screen between levels
#   5. Repeat 3-4 until all levels complete or game over
#   6. show_final_victory_screen() or show_game_over_screen()
#
# Each level runs its own game loop with:
#   - Event handling (input, window resize)
#   - Physics updates (player, projectiles)
#   - Collision detection (terrain, traps, boss)
#   - Rendering (background, objects, player, HUD, boss)
#
# Level progression:
#   Egypt (Level 1) -> Medieval Europe (Level 2) -> Outer Space (Level 3)
# ==============================================================================


def run_level(window, level_num, game_stats):
    """Run one level: handle input, physics, collisions, rendering, and progression.

    Parameters:
        window (pygame.Surface) — window surface to draw to
        level_num (int) — level index (1=Egypt, 2=Medieval, 3=Space)
        game_stats (dict) — mutable game stats (lives, deaths, time, ...)

    Returns:
        (result, game_stats) where result is one of:
        "next_level", "quit", "game_over", or "game_complete".
    """
    global Width, Height
    
    # =========================================================================
    # LEVEL CONFIGURATION
    # =========================================================================
    # Set up level-specific assets: background, block style, boss type, music
    # =========================================================================
    
    if level_num == 1:
        # Egypt level - sandy desert with pyramids
        bg_image = create_egypt_background()
        style = "egypt"
        boss_class = PharaohBoss
        level_name = "Ancient Egypt"
    elif level_num == 2:
        # Medieval Europe level
        bg_image = create_medieval_background()
        style = "medieval"
        boss_class = KnightBoss
        level_name = "Medieval Europe"
        # Switch to Europe soundtrack for level 2
        try:
            pygame.mixer.music.load(os.path.join("assets", "europeSound.mp3"))
            pygame.mixer.music.set_volume(0.5)
            pygame.mixer.music.play(loops=-1, start=0.0, fade_ms=0)
        except Exception:
            pass  # Continue without music if file not found
    elif level_num == 3:
        # Outer Space level
        bg_image = get_space_background()
        style = "space"
        boss_class = AlienBoss
        level_name = "Outer Space"
        # Switch to space soundtrack for level 3
        try:
            pygame.mixer.music.load(os.path.join("assets", "spaceSound.mp3"))
            pygame.mixer.music.set_volume(0.5)
            pygame.mixer.music.play(loops=-1, start=0.0, fade_ms=0)
        except Exception:
            pass  # Continue without music if file not found
    else:
        return "game_complete", game_stats
    
    clock = pygame.time.Clock()
    block_size = 96
    
    # World size: scale based on maximum screen width for when user maximizes
    world_length = max(100, int(MAX_WIDTH * 2 / block_size))
    max_x = world_length * block_size
    
    # Initialize player and world - use MAX_HEIGHT for floor position
    player_start_x = 50
    player_start_y = MAX_HEIGHT - block_size - 100
    player = Player(player_start_x, player_start_y, 50, 50)
    
    # Progressive tutorial state (only for level 1)
    tutorial_step = 0 if level_num == 1 else -1
    tutorial_actions = {
        'moved_right': False,
        'moved_left': False,
        'jumped': False,
        'double_jumped': False
    }
    tutorial_complete_timer = 0
    
    # Create floor covering the full potential screen area
    floor_start = int(-MAX_WIDTH * 1.5 / block_size)
    floor_end = max(100, int(MAX_WIDTH * 3 / block_size))
    floor = create_floor_at_height(block_size, floor_start, floor_end, MAX_HEIGHT, style=style)
    objects = floor.copy()
    
    # Generate initial platforms using MAX_HEIGHT for positioning
    current_x = 4 * block_size
    while current_x + block_size * 6 < max_x:
        if current_x < max_x:
            platform_blocks = generate_platforming_blocks_at_height(current_x, block_size, MAX_HEIGHT, style=style)
            objects.extend(platform_blocks)
        current_x += block_size * random.randint(5, 8)  # Randomized spacing to reduce clumping
    
    # Generate traps (after objects are created to avoid overlaps)
    traps = generate_traps_at_height(block_size, max_x, objects, MAX_HEIGHT)
    
    # Create boss at the end of the level
    boss_x = max_x - 400
    boss_y = MAX_HEIGHT - block_size - 150
    boss = boss_class(boss_x, boss_y, max_x)
    boss_arena_start = max_x - 800
    in_boss_fight = False
    boss_defeated = False
    
    # Create portal (appears after boss defeat)
    portal = Portal(max_x - 200, MAX_HEIGHT - block_size - 130)
    portal_entered = False
    
    # Game state variables
    floor_left_edge = floor_start * block_size
    floor_right_edge = floor_end * block_size
    last_platform_x = current_x
    camera_x = 0.0
    camera_y = float(player_start_y - Height // 2)
    
    start_time = pygame.time.get_ticks()

    # Game loop
    run = True
    result = "quit"
    while run:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    handle_jump_input(player)
                    # Track tutorial progress for jump
                    if tutorial_step == 2 and not tutorial_actions['jumped']:
                        tutorial_actions['jumped'] = True
                        tutorial_step = 3
                    elif tutorial_step == 3 and player.jump_count >= 1:
                        tutorial_actions['double_jumped'] = True
                        tutorial_step = 4
                        tutorial_complete_timer = 120  # Show final message for 2 seconds
                elif event.key == pygame.K_RIGHT:
                    # Track tutorial progress for move right
                    if tutorial_step == 0 and not tutorial_actions['moved_right']:
                        tutorial_actions['moved_right'] = True
                        tutorial_step = 1
                elif event.key == pygame.K_LEFT:
                    # Track tutorial progress for move left
                    if tutorial_step == 1 and not tutorial_actions['moved_left']:
                        tutorial_actions['moved_left'] = True
                        tutorial_step = 2
                elif event.key == pygame.K_ESCAPE:
                    run = False
            elif event.type == pygame.VIDEORESIZE:
                # Update dimensions when window is resized/maximized
                Width = event.w
                Height = event.h
                window = pygame.display.set_mode((Width, Height), pygame.RESIZABLE)
                # Extend floor to cover new visible area
                new_floor_end = int((camera_x + Width * 2) / block_size)
                while floor_right_edge < new_floor_end * block_size and floor_right_edge < max_x:
                    objects.append(Block(floor_right_edge, MAX_HEIGHT - block_size, block_size))
                    floor_right_edge += block_size
        
        # Update tutorial timer for final message
        if tutorial_step == 4:
            tutorial_complete_timer -= 1
            if tutorial_complete_timer <= 0:
                tutorial_step = -1  # Hide tutorial

        # Update world (stops at max_x)
        if floor_right_edge < max_x:
            floor_right_edge = extend_floor(player, objects, floor_right_edge, "right", block_size, max_x, style=style)
        floor_left_edge = extend_floor(player, objects, floor_left_edge, "left", block_size, max_x, style=style)
        if last_platform_x < max_x:
            last_platform_x = extend_platforms(player, objects, last_platform_x, block_size, Width, max_x, style=style)

        # Update traps
        update_traps(traps)
        
        # Check trap collisions - respawn player if hit (not during boss defeat)
        if check_trap_collision(player, traps) and not boss_defeated:
            game_stats['deaths'] += 1
            game_stats['lives'] -= 1
            
            # Game over check
            if game_stats['lives'] <= 0:
                run = False
                continue
            
            # Respawn at boss arena if in boss fight, otherwise at start
            if in_boss_fight:
                player.rect.x = boss_arena_start + 50
                player.rect.y = MAX_HEIGHT - block_size - 100
            else:
                player.rect.x = player_start_x
                player.rect.y = player_start_y
            player.y_vel = 0
            player.x_vel = 0
            player.fall_count = 0
            player.jump_count = 0
            if not in_boss_fight:
                camera_x = 0.0
                camera_y = float(player_start_y - Height // 2)
        
        # === BOSS FIGHT LOGIC ===
        if not boss_defeated:
            # Check if player entered boss arena
            if player.rect.x >= boss_arena_start and not in_boss_fight:
                in_boss_fight = True
                boss.introduce()
            
            # Update boss if in arena
            if in_boss_fight and boss.is_alive:
                boss.update(player.rect.x)
                
                # Check if player attacks boss (jump on head)
                if boss.check_player_attack(player):
                    if boss.on_damaged(20):  # 20 damage per stomp
                        player.y_vel = -15  # Bounce off boss
                        player.jump_count = 1
                
                # Check if boss projectiles hit player
                if boss.check_projectile_collision(player):
                    game_stats['deaths'] += 1
                    game_stats['lives'] -= 1
                    
                    if game_stats['lives'] <= 0:
                        run = False
                        continue
                    
                    # Respawn in boss arena
                    player.rect.x = boss_arena_start + 50
                    player.rect.y = MAX_HEIGHT - block_size - 100
                    player.y_vel = 0
                    player.x_vel = 0
                
                # Check if boss is defeated
                if boss.is_defeated:
                    boss_defeated = True
                    portal.activate()  # Activate the portal when boss dies
        
        # Update portal if boss is defeated
        if boss_defeated:
            portal.update()
            # Check if player enters portal
            if portal.check_player_enter(player) and not portal_entered:
                portal_entered = True
                result = "next_level"
                run = False
        
        # Update game stats
        current_distance = max(0, (player.rect.x - player_start_x) // 50)  # Convert to meters
        game_stats['distance'] = current_distance
        game_stats['max_distance'] = max(game_stats['max_distance'], current_distance)
        game_stats['time'] = (pygame.time.get_ticks() - start_time) / 1000.0
        game_stats['progress'] = min(1.0, player.rect.x / max_x)

        # Update player
        handle_input(player, objects)
        handle_horizontal_collision(player, objects)
        player.apply_physics(FPS)
        handle_vertical_collision(player, objects, player.y_vel)

        # Update camera
        camera_x, camera_y = update_camera(player, camera_x, camera_y)
        offset_x = int(camera_x)
        offset_y = int(camera_y)
        
        # Update tutorial completion timer (show final message for 3 seconds)
        if tutorial_step == 4:
            if tutorial_complete_timer == 0:
                tutorial_complete_timer = pygame.time.get_ticks()
            elif pygame.time.get_ticks() - tutorial_complete_timer > 3000:
                tutorial_step = -1  # Tutorial complete

        # Render (include boss and portal)
        render_frame(window, bg_image, player, objects, traps, offset_x, offset_y, tutorial_step, game_stats, 
                     boss if in_boss_fight else None, portal if boss_defeated else None)
    
    return result, game_stats


def main(window, start_level=1):
    """Main game function that runs all levels."""
    # Game stats that persist across levels
    game_stats = {
        'lives': 3,
        'deaths': 0,
        'distance': 0,
        'max_distance': 0,
        'time': 0.0,
        'progress': 0.0,
        'level': start_level
    }
    
    current_level = start_level
    max_levels = 3  # Egypt, Medieval Europe, and Outer Space
    
    while current_level <= max_levels:
        result, game_stats = run_level(window, current_level, game_stats)
        
        if result == "next_level":
            # Show level transition screen
            show_level_transition(window, current_level, current_level + 1)
            current_level += 1
            game_stats['level'] = current_level
            game_stats['lives'] = 3  # Reset lives for new level
        elif result == "quit":
            break
        elif result == "game_over":
            show_game_over_screen(window, game_stats)
            break
    
    # Show final victory screen after beating all levels
    if current_level > max_levels:
        show_final_victory_screen(window, game_stats)
    
    pygame.quit()
    quit()


def show_intro_story(window):
    """Show the intro backstory screen."""
    font_large = pygame.font.SysFont('times new roman', 48, bold=True)
    font_medium = pygame.font.SysFont('times new roman', 28)
    font_small = pygame.font.SysFont('arial', 24)
    
    # Fill with dark background
    window.fill((10, 10, 20))
    
    # Title
    title_text = font_large.render("CLASSIFIED BRIEFING", True, (255, 215, 0))
    title_rect = title_text.get_rect(center=(Width // 2, Height // 6))
    
    # Shadow
    shadow_text = font_large.render("CLASSIFIED BRIEFING", True, (100, 80, 0))
    shadow_rect = shadow_text.get_rect(center=(Width // 2 + 3, Height // 6 + 3))
    window.blit(shadow_text, shadow_rect)
    window.blit(title_text, title_rect)
    
    # Story lines
    story_lines = [
        "Greetings, TimeMarine 067.",
        "",
        "Your mission is critical to the survival of existence itself.",
        "",
        "Three rogue Timekeepers have seized control of Timeline 041.",
        "Their interference threatens the imminent collapse of time.",
        "",
        "You must travel through Ancient Egypt, Medieval Europe,",
        "and the depths of Outer Space to defeat each Timekeeper.",
        "",
        "Failure is not an option. The fate of all timelines rests",
        "in your hands.",
        "",
        "Good luck, Marine. Time is running out."
    ]
    
    start_y = Height // 3 - 40
    for i, line in enumerate(story_lines):
        if line == "":
            continue
        line_text = font_medium.render(line, True, (180, 200, 220))
        line_rect = line_text.get_rect(center=(Width // 2, start_y + i * 32))
        window.blit(line_text, line_rect)
    
    # Continue prompt
    continue_text = font_small.render("Press any key to begin your mission...", True, (150, 150, 150))
    continue_rect = continue_text.get_rect(center=(Width // 2, Height - 80))
    window.blit(continue_text, continue_rect)
    
    pygame.display.flip()
    
    # Wait for keypress
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            elif event.type == pygame.KEYDOWN:
                waiting = False


def show_level_transition(window, from_level, to_level):
    """Show a transition screen between levels."""
    level_names = {
        1: "Ancient Egypt",
        2: "Medieval Europe",
        3: "Outer Space",
        4: "Beyond..."
    }
    
    font_large = pygame.font.SysFont('times new roman', 48, bold=True)
    font_medium = pygame.font.SysFont('times new roman', 32)
    font_small = pygame.font.SysFont('arial', 24)
    
    # Fill with dark background
    window.fill((15, 15, 25))
    
    # "Level Complete" text
    complete_text = font_large.render("Level Complete!", True, (255, 215, 0))
    complete_rect = complete_text.get_rect(center=(Width // 2, Height // 3))
    window.blit(complete_text, complete_rect)
    
    # From level name
    from_text = font_medium.render(f"Leaving: {level_names.get(from_level, 'Unknown')}", True, (200, 180, 140))
    from_rect = from_text.get_rect(center=(Width // 2, Height // 2 - 30))
    window.blit(from_text, from_rect)
    
    # To level name
    to_text = font_medium.render(f"Entering: {level_names.get(to_level, 'Unknown')}", True, (100, 200, 255))
    to_rect = to_text.get_rect(center=(Width // 2, Height // 2 + 30))
    window.blit(to_text, to_rect)
    
    # Continue prompt
    continue_text = font_small.render("Press any key to continue...", True, (150, 150, 150))
    continue_rect = continue_text.get_rect(center=(Width // 2, Height - 80))
    window.blit(continue_text, continue_rect)
    
    pygame.display.flip()
    
    # Wait for keypress
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            elif event.type == pygame.KEYDOWN:
                waiting = False


def show_game_over_screen(window, game_stats):
    """Display game over screen with level-specific death message."""
    font_large = pygame.font.SysFont('times new roman', 64, bold=True)
    font_medium = pygame.font.SysFont('times new roman', 28)
    font_small = pygame.font.SysFont('arial', 24)
    
    window.fill((30, 10, 10))
    
    # Game Over text
    game_over_text = font_large.render("MISSION FAILED", True, (200, 50, 50))
    game_over_rect = game_over_text.get_rect(center=(Width // 2, Height // 5))
    window.blit(game_over_text, game_over_rect)
    
    # Level-specific death messages
    current_level = game_stats.get('level', 1)
    death_messages = {
        1: [
            "The timeline has become trapped in Ancient Egypt.",
            "The sands of time have buried all hope.",
            "Pharaohs now rule for eternity... and so does darkness."
        ],
        2: [
            "The timeline is forever frozen in Medieval Europe.",
            "Knights and castles now reign across all of existence.",
            "The Dark Ages have become... eternal."
        ],
        3: [
            "The timeline is lost in the void of Outer Space.",
            "Stars flicker and die as time unravels into nothing.",
            "The cosmos has become an endless, silent tomb."
        ]
    }
    
    messages = death_messages.get(current_level, death_messages[1])
    message_start_y = Height // 3
    for i, msg in enumerate(messages):
        msg_text = font_medium.render(msg, True, (180, 100, 100))
        msg_rect = msg_text.get_rect(center=(Width // 2, message_start_y + i * 35))
        window.blit(msg_text, msg_rect)
    
    # Stats
    stats_y = Height // 2 + 60
    minutes = int(game_stats['time'] // 60)
    seconds = int(game_stats['time'] % 60)
    
    stats_lines = [
        f"Level Reached: {game_stats.get('level', 1)}",
        f"Time: {minutes:02d}:{seconds:02d}",
        f"Deaths: {game_stats['deaths']}"
    ]
    
    for i, line in enumerate(stats_lines):
        stat_text = font_small.render(line, True, (200, 200, 200))
        stat_rect = stat_text.get_rect(center=(Width // 2, stats_y + i * 35))
        window.blit(stat_text, stat_rect)
    
    # Continue prompt
    continue_text = font_small.render("Press any key to exit...", True, (150, 150, 150))
    continue_rect = continue_text.get_rect(center=(Width // 2, Height - 80))
    window.blit(continue_text, continue_rect)
    
    pygame.display.flip()
    
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                waiting = False
            elif event.type == pygame.KEYDOWN:
                waiting = False


def show_final_victory_screen(window, game_stats):
    """Display final victory screen after beating all levels."""
    font_large = pygame.font.SysFont('times new roman', 64, bold=True)
    font_medium = pygame.font.SysFont('times new roman', 32)
    font_small = pygame.font.SysFont('arial', 24)
    
    # Fill with dark background
    window.fill((15, 15, 25))
    
    # Victory text
    victory_text = font_large.render("MISSION COMPLETE", True, (255, 215, 0))
    victory_rect = victory_text.get_rect(center=(Width // 2, Height // 6))
    
    # Shadow
    shadow_text = font_large.render("MISSION COMPLETE", True, (100, 80, 0))
    shadow_rect = shadow_text.get_rect(center=(Width // 2 + 4, Height // 6 + 4))
    window.blit(shadow_text, shadow_rect)
    window.blit(victory_text, victory_rect)
    
    # Timeline saved message
    saved_lines = [
        "Timeline 041 has been secured.",
        "All three Timekeepers have been defeated.",
        "The flow of time has been restored."
    ]
    
    saved_start_y = Height // 4 + 20
    for i, line in enumerate(saved_lines):
        line_text = font_medium.render(line, True, (100, 255, 150))
        line_rect = line_text.get_rect(center=(Width // 2, saved_start_y + i * 40))
        window.blit(line_text, line_rect)
    
    # Subtitle
    subtitle = font_medium.render("Outstanding work, TimeMarine 067!", True, (200, 180, 140))
    subtitle_rect = subtitle.get_rect(center=(Width // 2, Height // 4 + 150))
    window.blit(subtitle, subtitle_rect)
    
    # Defeated bosses
    bosses_text = font_medium.render("Bosses Defeated:", True, (100, 200, 255))
    bosses_rect = bosses_text.get_rect(center=(Width // 2, Height // 2 - 60))
    window.blit(bosses_text, bosses_rect)
    
    boss_names = ["Pharaoh Netriljunakhil", "Sir Aldric the Unyielding", "Commander Zyx-9"]
    for i, boss_name in enumerate(boss_names):
        boss_text = font_small.render(f"✓ {boss_name}", True, (100, 255, 100))
        boss_rect = boss_text.get_rect(center=(Width // 2, Height // 2 - 30 + i * 30))
        window.blit(boss_text, boss_rect)
    
    # Stats
    stats_y = Height // 2 + 80
    minutes = int(game_stats['time'] // 60)
    seconds = int(game_stats['time'] % 60)
    
    stats_lines = [
        f"Total Time: {minutes:02d}:{seconds:02d}",
        f"Total Deaths: {game_stats['deaths']}"
    ]
    
    for i, line in enumerate(stats_lines):
        stat_text = font_small.render(line, True, (200, 200, 200))
        stat_rect = stat_text.get_rect(center=(Width // 2, stats_y + i * 35))
        window.blit(stat_text, stat_rect)
    
    # Continue prompt
    continue_text = font_small.render("Press any key to exit...", True, (150, 150, 150))
    continue_rect = continue_text.get_rect(center=(Width // 2, Height - 80))
    window.blit(continue_text, continue_rect)
    
    pygame.display.flip()
    
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                waiting = False
            elif event.type == pygame.KEYDOWN:
                waiting = False


# ==============================================================================
#                           ENTRY POINT
# ==============================================================================
# Main execution block when the game is run directly (not imported as module).
#
# Initialization Sequence:
#   1. Initialize database connection (if available)
#   2. Load saved settings (volume, preferences)
#   3. Display main menu and get level selection
#   4. Show intro story narrative
#   5. Start main game loop with selected level
#
# Error Handling:
#   - Unhandled exceptions are caught and logged
#   - Crash screen prompts user to submit error report
#   - Stack trace is preserved for debugging
#
# Cleanup:
#   - Game session is ended in database
#   - Session duration is logged
#   - Database connection is closed
# ==============================================================================

if __name__ == "__main__":
    # =========================================================================
    # DATABASE INITIALIZATION
    # =========================================================================
    # Set up the database connection for tracking statistics and crashes.
    # This is optional - game works without it.
    # =========================================================================
    session_id = None
    
    if DATABASE_AVAILABLE:
        try:
            # Start a new game session (tracks play time)
            session_id = db.get_database().start_session()
            
            # Restore user's saved audio settings
            saved_volume = db.get_setting("music_volume", 0.5)
            pygame.mixer.music.set_volume(saved_volume)
            
            # Log successful initialization
            db.log_event("SYSTEM", "Game initialized successfully")
        except Exception as e:
            # Non-fatal: log warning and continue without database
            db.log_error("INIT", "Failed to initialize database", e, severity=ErrorSeverity.WARNING)
    
    # =========================================================================
    # MAIN GAME EXECUTION
    # =========================================================================
    # Run the game with full exception handling for crash reports.
    # =========================================================================
    try:
        # Show main menu and get the player's level selection
        selected_level = main_menu(window)
        
        if selected_level:
            # Display the intro story/briefing before gameplay
            show_intro_story(window)
            
            # Log the level selection
            if DATABASE_AVAILABLE:
                db.set_setting("last_level_played", selected_level)
                db.log_event("GAME", f"Starting level: {selected_level}")
            
            # Start the game at the selected level
            main(window, selected_level)
            
    except Exception as e:
        # =====================================================================
        # CRASH HANDLING
        # =====================================================================
        # Capture the full stack trace and offer to send a crash report.
        # This helps developers identify and fix bugs.
        # =====================================================================
        tb_str = traceback.format_exc()
        
        if DATABASE_AVAILABLE:
            db.log_fatal("MAIN_LOOP", "Unhandled exception in main game", e, tb_str)
        
        # Show crash screen and ask for email to send report
        try:
            show_crash_screen(window, "CRASH", str(e), e, tb_str)
        except:
            # If crash screen itself fails, fall back to console output
            print(f"FATAL ERROR: {e}")
            print(tb_str)
        
        # Re-raise the exception for proper error propagation
        raise
        
    finally:
        # =====================================================================
        # CLEANUP
        # =====================================================================
        # Always run cleanup, even if an exception occurred.
        # This ensures the database is properly closed.
        # =====================================================================
        if DATABASE_AVAILABLE:
            db.log_event("SYSTEM", "Game shutting down")
            
            if session_id:
                try:
                    # End the session and log total play time
                    duration = db.get_database().end_session(session_id)
                    db.log_event("SYSTEM", f"Session ended. Duration: {duration} seconds")
                except:
                    pass  # Ignore cleanup errors
            
            # Close database connection
            db.close()



