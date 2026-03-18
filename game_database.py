"""game_database — simple SQLite helper for settings, sessions, and logs.

Handles DB connections, basic tables, and logging for the game.
"""

import sqlite3
import os
import datetime
import threading
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from enum import Enum, auto


# ============================================================================
# ERROR SEVERITY LEVELS - Distinguishes recoverable from non-recoverable errors
# ============================================================================

class ErrorSeverity(Enum):
    """Error severity levels used by the logging system.

    Levels: WARNING, ERROR, CRITICAL, FATAL
    """
    WARNING = auto()   # Recoverable - Minor issues, continue normally
    ERROR = auto()     # Recoverable - Problems, but can continue with fallback
    CRITICAL = auto()  # Partially recoverable - May need user action
    FATAL = auto()     # Non-recoverable - Must restart game


def is_recoverable(severity):
    """Return True if the severity is recoverable (not FATAL)."""
    return severity in (ErrorSeverity.WARNING, ErrorSeverity.ERROR, ErrorSeverity.CRITICAL)


def get_severity_label(severity):
    """
    Get a human-readable label for an error severity.
    
    Args:
        severity (ErrorSeverity): The severity level
    
    Returns:
        str: Formatted label like "[WARNING]", "[ERROR]", etc.
    """
    return f"[{severity.name}]"


# ============================================================================
# FILE PATHS - Database and log file locations
# ============================================================================
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "game_data.db")
ERROR_LOG_PATH = os.path.join(os.path.dirname(__file__), "logs", "errors.log")
EVENTS_LOG_PATH = os.path.join(os.path.dirname(__file__), "logs", "events.log")

# Thread-local storage for database connections (one per thread)
_local = threading.local()


# ============================================================================
# DATABASE CONNECTION MANAGEMENT
# ============================================================================

def _ensure_directories():
    """Create data/ and logs/ directories if they don't exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(ERROR_LOG_PATH), exist_ok=True)

def _get_connection():
    """Return a thread-local sqlite3 connection, creating it if needed."""
    if not hasattr(_local, 'connection') or _local.connection is None:
        _ensure_directories()
        _local.connection = sqlite3.connect(DB_PATH, check_same_thread=False)
        _local.connection.row_factory = sqlite3.Row
    return _local.connection

def _init_database():
    """Create DB tables if missing (settings, sessions, events)."""
    conn = _get_connection()
    cursor = conn.cursor()
    
    # Settings table for runtime configuration
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Sessions table to track game sessions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP,
            duration_seconds INTEGER
        )
    ''')
    
    # Events table for system events
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            category TEXT,
            message TEXT,
            details TEXT
        )
    ''')
    
    conn.commit()

# Initialize on module load
_ensure_directories()
_init_database()


# ============================================================================
# GAME DATABASE CLASS - Core Database Operations
# ============================================================================

class GameDatabase:
    """
    Main database class for game data management.
    
    Provides thread-safe access to database operations including:
        • Game session tracking (start/end times)
        • Settings management
        • Event logging
        • Error logging
    
    Thread Safety:
        Uses threading.Lock() to serialize critical database operations
        and prevent race conditions in multi-threaded game loops.
    
    Attributes:
        _lock (threading.Lock): Protects database writes from race conditions
    
    Examples:
        db = GameDatabase()
        session_id = db.start_session()
        # ... play game ...
        duration = db.end_session(session_id)
    """
    
    def __init__(self):
        """Initialize GameDatabase with a thread-safe lock for operations."""
        self._lock = threading.Lock()
    
    def start_session(self):
        """
        Start a new game session and record the start time.
        
        Purpose:
            Marks the beginning of a player's gameplay session. This creates
            a session record in the database that can be ended later to
            calculate total playtime.
        
        Process:
            1. Acquires thread-safe lock
            2. Inserts new row into sessions table with current timestamp
            3. Returns the auto-generated session ID
        
        Returns:
            int: Unique session ID that can be used to end the session later
        
        Thread Safety:
            Uses threading.Lock to ensure database write is atomic
        
        Examples:
            session_id = db.start_session()
            print(f"Session {session_id} started")
        """
        with self._lock:
            conn = _get_connection()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO sessions (start_time) VALUES (?)', 
                          (datetime.datetime.now(),))
            conn.commit()
            return cursor.lastrowid
    
    def end_session(self, session_id):
        """
        End a game session and calculate total duration.
        
        Purpose:
            Marks the end of a player's gameplay session. Calculates the
            time elapsed between session start and end, storing the duration
            in seconds.
        
        Process:
            1. Acquires thread-safe lock
            2. Fetches the session's start_time from database
            3. Calculates duration = end_time - start_time (in seconds)
            4. Updates session record with end_time and duration_seconds
            5. Returns duration in seconds (or None if session not found)
        
        Args:
            session_id (int): The session ID returned from start_session()
        
        Returns:
            int: Duration of session in seconds (e.g., 1800 = 30 minutes)
            None: If session_id not found in database
        
        Thread Safety:
            Uses threading.Lock to prevent concurrent writes
        
        Examples:
            session_id = db.start_session()
            time.sleep(5)
            duration = db.end_session(session_id)
            print(f"Session lasted {duration} seconds")
        """
        with self._lock:
            conn = _get_connection()
            cursor = conn.cursor()
            end_time = datetime.datetime.now()
            
            # Get start time
            cursor.execute('SELECT start_time FROM sessions WHERE id = ?', (session_id,))
            row = cursor.fetchone()
            if row:
                start_time = datetime.datetime.fromisoformat(row['start_time'])
                duration = int((end_time - start_time).total_seconds())
                cursor.execute('''
                    UPDATE sessions 
                    SET end_time = ?, duration_seconds = ? 
                    WHERE id = ?
                ''', (end_time, duration, session_id))
                conn.commit()

# ============================================================================
# SINGLETON PATTERN - Global Database Instance
# ============================================================================
# Implements singleton pattern with double-check locking for thread safety.
# Ensures only one GameDatabase instance exists across entire application.

_database_instance = None
_instance_lock = threading.Lock()

def get_database():
    """
    Get the singleton GameDatabase instance.
    
    Purpose:
        Returns the single global GameDatabase instance. If it doesn't exist,
        creates it using thread-safe double-check locking pattern.
    
    Thread Safety:
        Uses threading.Lock with double-check pattern:
            1. First check without lock (fast path)
            2. Acquire lock
            3. Second check after acquiring lock (to prevent race condition)
            4. Create instance if still None
        This minimizes lock contention while ensuring thread safety.
    
    Returns:
        GameDatabase: The singleton database instance
    
    Examples:
        db = get_database()
        session_id = db.start_session()
        
        # Later in different thread:
        db = get_database()  # Returns SAME instance
        duration = db.end_session(session_id)
    """
    global _database_instance
    if _database_instance is None:
        with _instance_lock:
            if _database_instance is None:
                _database_instance = GameDatabase()
    return _database_instance


# ============================================================================
# SETTINGS FUNCTIONS - Runtime Configuration Management
# ============================================================================
# Settings are stored as key-value pairs in the database.
# All values are stored as strings but can be retrieved as typed values.

def get_setting(key, default=None):
    """
    Retrieve a setting value from the database with automatic type conversion.
    
    Purpose:
        Fetches a configuration value by key from the settings table.
        Automatically converts string values back to their likely types
        (int, float, bool, or string).
    
    Type Conversion Logic:
        • "123" → int(123)
        • "3.14" → float(3.14)
        • "true"/"false" → bool(True/False) [case-insensitive]
        • "hello world" → str("hello world")
    
    Args:
        key (str): The setting key to retrieve (e.g., "sound_volume", "fps_limit")
        default: Value to return if key not found (default: None)
    
    Returns:
        The setting value with automatic type conversion, or default if not found
    
    Error Handling:
        Catches all exceptions and logs them. Returns default value on any error
        to prevent crashes from database issues.
    
    Examples:
        volume = get_setting("sound_volume", default=80)
        fullscreen = get_setting("fullscreen", default=False)
        server_port = get_setting("server_port", default=8080)
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        row = cursor.fetchone()
        if row:
            # Try to convert to appropriate type
            value = row['value']
            try:
                # Try float first (handles both int and float)
                if '.' in value:
                    return float(value)
                return int(value)
            except (ValueError, TypeError):
                if value.lower() == 'true':
                    return True
                elif value.lower() == 'false':
                    return False
                return value
        return default
    except Exception as e:
        log_error("DATABASE", f"Failed to get setting '{key}'", e)
        return default

def set_setting(key, value):
    """
    Store or update a setting value in the database.
    
    Purpose:
        Stores a configuration value as a key-value pair. If key already exists,
        updates the existing value. If key doesn't exist, creates new entry.
        Uses SQLite "INSERT OR REPLACE" to handle both cases atomically.
    
    Args:
        key (str): The setting key (e.g., "sound_volume", "player_name")
        value: The value to store (automatically converted to string)
    
    Returns:
        bool: True if setting was saved successfully, False on error
    
    Details:
        • All values are stored as TEXT in database (as strings)
        • updated_at timestamp is automatically set to current time
        • Returns False if database write fails (with error logged)
    
    Error Handling:
        Catches exceptions and logs them. Returns False on any error.
    
    Examples:
        if set_setting("sound_volume", 85):
            print("Setting saved successfully")
        else:
            print("Failed to save setting")
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO settings (key, value, updated_at) 
            VALUES (?, ?, ?)
        ''', (key, str(value), datetime.datetime.now()))
        conn.commit()
        return True
    except Exception as e:
        log_error("DATABASE", f"Failed to set setting '{key}'", e)
        return False

def get_all_settings():
    """
    Retrieve all settings as a dictionary.
    
    Purpose:
        Fetches every key-value pair from the settings table.
        Useful for dumping all configuration or backup purposes.
    
    Returns:
        dict: Dictionary mapping all setting keys to their values
              Returns empty dict {} if query fails
    
    Examples:
        settings = get_all_settings()
        for key, value in settings.items():
            print(f"{key} = {value}")
    
    Error Handling:
        Catches exceptions and logs them. Returns empty dict on error.
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT key, value FROM settings')
        return {row['key']: row['value'] for row in cursor.fetchall()}
    except Exception as e:
        log_error("DATABASE", "Failed to get all settings", e)
        return {}


# ============================================================================
# EVENT LOGGING FUNCTIONS - System Event Recording
# ============================================================================
# Logs game events and errors to both database and log files.
# Provides redundancy and accessibility in multiple formats.

def _write_to_file(filepath, message):
    """
    Write a message to a log file with utf-8 encoding.
    
    Purpose:
        Low-level file write operation used by event and error logging.
        Ensures directories exist before writing.
    
    Args:
        filepath (str): Absolute path to log file
        message (str): Message to append to file
    
    Details:
        • Opens file in append mode ('a') to preserve existing content
        • Uses utf-8 encoding for Unicode character support
        • Silently fails if unable to write (doesn't crash the game)
    
    Error Handling:
        Catches all exceptions silently. Prevents logging errors from
        crashing the main game loop.
    """
    try:
        _ensure_directories()
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(message + '\n')
    except Exception:
        pass  # Silently fail if we can't write to file

def log_event(category, message, details=None):
    """
    Log a system event to both database and events log file.
    
    Purpose:
        Records gameplay and system events for debugging, analytics,
        and audit trails. Provides dual storage (database + file).
    
    Args:
        category (str): Event category/type (e.g., "PLAYER_JUMP", "ITEM_COLLECTED")
        message (str): Human-readable event description
        details (str, optional): Additional context info about the event
    
    Database Schema (events table):
        • timestamp: When event occurred (auto-set to now)
        • category: Event type classification
        • message: Main event description
        • details: Optional additional info
    
    Log File Format:
        [2026-01-15T14:30:45.123456] [PLAYER_JUMP] Player jumped from platform | details
    
    Details:
        • Writes to both database AND events.log for redundancy
        • Automatically includes ISO format timestamp
        • Silently catches database errors (continues on failure)
    
    Examples:
        log_event("ITEM_COLLECTED", "Player collected coin", "coins_total=42")
        log_event("LEVEL_COMPLETE", "Level 1 completed", f"time=300s")
        log_event("ERROR", "Collision system warning", "null_physics_body")
    """
    timestamp = datetime.datetime.now()
    
    # Write to database
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO events (timestamp, category, message, details) 
            VALUES (?, ?, ?, ?)
        ''', (timestamp, category, message, details))
        conn.commit()
    except Exception:
        pass  # Don't let logging errors crash the game
    
    # Also write to events log file
    log_line = f"[{timestamp.isoformat()}] [{category}] {message}"
    if details:
        log_line += f" | {details}"
    _write_to_file(EVENTS_LOG_PATH, log_line)

def log_error(category, message, exception=None, traceback_str=None, severity=None):
    """
    Log an error with full details to dedicated error log file.
    
    Purpose:
        Records detailed error information for debugging and crash analysis.
        Includes stack traces, exception types, timestamps, and severity.
        Written to errors.log AND events table for maximum visibility.
    
    Args:
        category (str): Error category (e.g., "PHYSICS", "RENDERING", "DATABASE")
        message (str): Human-readable error description
        exception (Exception, optional): The caught exception object
        traceback_str (str, optional): Full traceback from sys.exc_info()
        severity (ErrorSeverity, optional): Error severity level. Defaults to ERROR.
            Use ErrorSeverity.WARNING for minor issues
            Use ErrorSeverity.ERROR for recoverable problems (default)
            Use ErrorSeverity.CRITICAL for serious issues needing attention
            Use ErrorSeverity.FATAL for non-recoverable errors
    
    Returns:
        bool: True if error is recoverable (WARNING/ERROR/CRITICAL)
              False if error is non-recoverable (FATAL)
    
    Error Log Format (errors.log):
        ============================================================
        TIMESTAMP: 2026-01-15T14:30:45.123456
        SEVERITY:  [ERROR]
        CATEGORY:  PHYSICS
        MESSAGE:   Failed to update collision bounds
        RECOVERABLE: Yes
        EXCEPTION: ValueError: Invalid bounds rectangle
        TRACEBACK:
          File "main.py", line 234, in update_physics
            self.bounds.update(invalid_rect)
        ============================================================
    
    Process:
        1. Builds detailed error message with all context including severity
        2. Writes to errors.log file with formatting
        3. Logs to database events table with prefix "ERROR:<severity>:<category>"
        4. Both writes silently fail on error (prevents crash loop)
        5. Returns whether error is recoverable for caller to handle
    
    Examples:
        try:
            physics_engine.update()
        except Exception as e:
            import traceback
            recoverable = log_error("PHYSICS", "Failed to update physics", 
                     exception=e, traceback_str=traceback.format_exc(),
                     severity=ErrorSeverity.ERROR)
            if recoverable:
                use_fallback_physics()
            else:
                sys.exit(1)
    """
    # Default to ERROR severity if not specified
    if severity is None:
        severity = ErrorSeverity.ERROR
    
    timestamp = datetime.datetime.now()
    recoverable = is_recoverable(severity)
    
    # Build error message
    error_lines = [
        "=" * 60,
        f"TIMESTAMP:   {timestamp.isoformat()}",
        f"SEVERITY:    {get_severity_label(severity)}",
        f"CATEGORY:    {category}",
        f"MESSAGE:     {message}",
        f"RECOVERABLE: {'Yes' if recoverable else 'NO - REQUIRES RESTART'}"
    ]
    
    if exception:
        error_lines.append(f"EXCEPTION:   {type(exception).__name__}: {str(exception)}")
    
    if traceback_str:
        error_lines.append("TRACEBACK:")
        error_lines.append(traceback_str)
    
    error_lines.append("=" * 60)
    
    # Write to error log file
    _write_to_file(ERROR_LOG_PATH, '\n'.join(error_lines))
    
    # Also log as an event in the database with severity prefix
    details = str(exception) if exception else None
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO events (timestamp, category, message, details) 
            VALUES (?, ?, ?, ?)
        ''', (timestamp, f"ERROR:{severity.name}:{category}", message, details))
        conn.commit()
    except Exception:
        pass
    
    # Return whether this error is recoverable
    return recoverable


# ============================================================================
# SEVERITY-SPECIFIC LOGGING HELPERS
# ============================================================================
# Convenience functions for logging at specific severity levels.

def log_warning(category, message, exception=None, traceback_str=None):
    """
    Log a WARNING-level error (minor issue, game continues normally).
    
    Use for:
        • Missing optional assets or features
        • Minor performance issues
        • Non-critical configuration problems
        • Deprecated feature usage
    
    Args:
        category (str): Error category
        message (str): Error description
        exception (Exception, optional): Exception object if available
        traceback_str (str, optional): Traceback string if available
    
    Returns:
        bool: Always True (warnings are always recoverable)
    
    Examples:
        log_warning("AUDIO", "Optional sound effect not found")
        log_warning("CONFIG", "Using default settings", config_error)
    """
    return log_error(category, message, exception, traceback_str, 
                     severity=ErrorSeverity.WARNING)


def log_critical(category, message, exception=None, traceback_str=None):
    """
    Log a CRITICAL-level error (serious issue, may need user attention).
    
    Use for:
        • Database corruption or access issues
        • Level data missing or corrupted
        • Save game corruption
        • Network connectivity problems
    
    Args:
        category (str): Error category
        message (str): Error description
        exception (Exception, optional): Exception object if available
        traceback_str (str, optional): Traceback string if available
    
    Returns:
        bool: True (critical errors are still technically recoverable)
    
    Examples:
        log_critical("DATABASE", "Failed to save game progress", e)
        log_critical("LEVEL", "Level 3 data corrupted, skipping", e, tb)
    """
    return log_error(category, message, exception, traceback_str, 
                     severity=ErrorSeverity.CRITICAL)


def log_fatal(category, message, exception=None, traceback_str=None):
    """
    Log a FATAL-level error (non-recoverable, game must restart).
    
    Use for:
        • Core engine failures
        • Required asset completely missing
        • Unhandled exceptions in main loop
        • Memory corruption or out-of-memory
        • Display/graphics system failure
    
    Args:
        category (str): Error category
        message (str): Error description
        exception (Exception, optional): Exception object if available
        traceback_str (str, optional): Traceback string if available
    
    Returns:
        bool: Always False (fatal errors are never recoverable)
    
    Note:
        After calling this, you should typically show an error screen
        and exit the game gracefully.
    
    Examples:
        if not log_fatal("ENGINE", "Graphics system failed", e, tb):
            show_crash_dialog()
            sys.exit(1)
    """
    return log_error(category, message, exception, traceback_str, 
                     severity=ErrorSeverity.FATAL)


# ============================================================================
# UTILITY FUNCTIONS - Database Queries and Maintenance
# ============================================================================

def get_recent_events(limit=50):
    """
    Retrieve the most recent events from the database.
    
    Purpose:
        Fetches latest logged events in reverse chronological order.
        Useful for debugging, monitoring, and event playback.
    
    Args:
        limit (int): Maximum number of events to return (default: 50)
    
    Returns:
        list[dict]: List of event dictionaries with keys:
            • timestamp: When event occurred (ISO format string)
            • category: Event type
            • message: Event description
            • details: Additional info (may be None)
        Returns empty list [] if query fails
    
    Ordering:
        Events are returned newest-first (ORDER BY timestamp DESC)
    
    Examples:
        recent = get_recent_events(limit=20)
        for event in recent:
            print(f"{event['timestamp']} [{event['category']}] {event['message']}")
    
    Error Handling:
        Catches exceptions and logs them. Returns empty list on error.
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT timestamp, category, message, details 
            FROM events 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (limit,))
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        log_error("DATABASE", "Failed to get recent events", e)
        return []

def get_session_stats():
    """
    Get aggregate statistics about all game sessions.
    
    Purpose:
        Retrieves statistics across all completed sessions for analytics,
        reporting, and session analysis.
    
    Returns:
        dict: Statistics dictionary with keys:
            • total_sessions: Total number of sessions recorded
            • total_playtime: Sum of all session durations (seconds)
            • avg_session_length: Average duration per session (seconds)
        Returns empty dict {} if query fails
    
    Details:
        Only counts sessions where duration_seconds IS NOT NULL
        (i.e., completed sessions, excludes ongoing sessions)
    
    Examples:
        stats = get_session_stats()
        hours = stats['total_playtime'] / 3600 if stats else 0
        print(f"Total playtime: {hours:.1f} hours")
        print(f"Sessions: {stats.get('total_sessions', 0)}")
    
    Error Handling:
        Catches exceptions and logs them. Returns empty dict on error.
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                COUNT(*) as total_sessions,
                SUM(duration_seconds) as total_playtime,
                AVG(duration_seconds) as avg_session_length
            FROM sessions 
            WHERE duration_seconds IS NOT NULL
        ''')
        row = cursor.fetchone()
        return dict(row) if row else {}
    except Exception as e:
        log_error("DATABASE", "Failed to get session stats", e)
        return {}

def close():
    """
    Close the thread-local database connection.
    
    Purpose:
        Explicitly closes the SQLite connection for this thread.
        Should be called when shutting down the application to prevent
        resource leaks and ensure proper file closure.
    
    Details:
        • Only closes if connection exists for this thread
        • Resets connection to None after closing
        • Safe to call even if already closed
        • Each thread has its own connection (thread-local)
    
    Examples:
        # At end of main game loop or on app shutdown:
        game_db.close()
    """
    if hasattr(_local, 'connection') and _local.connection:
        _local.connection.close()
        _local.connection = None


# ============================================================================
# CRASH REPORT EMAIL SYSTEM
# ============================================================================
# Allows users to submit crash reports via email when fatal errors occur.
# Uses a free email service or SMTP relay for sending reports.

# Email configuration - using a web form submission approach for simplicity
# This avoids requiring SMTP credentials in the game
CRASH_REPORT_URL = "https://formsubmit.co/ajax/"
DEVELOPER_EMAIL = "chronoquest.crashes@example.com"  # Replace with your email

def get_user_email():
    """
    Get the user's saved email address for crash reports.
    
    Returns:
        str: The user's email address, or None if not set
    """
    return get_setting("user_crash_report_email", None)


def set_user_email(email):
    """
    Save the user's email address for crash reports.
    
    Args:
        email (str): The user's email address
    
    Returns:
        bool: True if saved successfully
    """
    return set_setting("user_crash_report_email", email)


def build_crash_report(category, message, exception=None, traceback_str=None):
    """
    Build a detailed crash report string.
    
    Args:
        category (str): Error category
        message (str): Error message
        exception (Exception, optional): The exception object
        traceback_str (str, optional): Full traceback
    
    Returns:
        str: Formatted crash report
    """
    import platform
    import sys
    
    report_lines = [
        "=" * 60,
        "CHRONOQUEST CRASH REPORT",
        "=" * 60,
        "",
        f"Timestamp: {datetime.datetime.now().isoformat()}",
        f"Category:  {category}",
        f"Message:   {message}",
        "",
        "--- SYSTEM INFO ---",
        f"OS: {platform.system()} {platform.release()}",
        f"Python: {sys.version}",
        f"Platform: {platform.platform()}",
        "",
    ]
    
    if exception:
        report_lines.extend([
            "--- EXCEPTION ---",
            f"Type: {type(exception).__name__}",
            f"Message: {str(exception)}",
            "",
        ])
    
    if traceback_str:
        report_lines.extend([
            "--- TRACEBACK ---",
            traceback_str,
            "",
        ])
    
    # Add recent events from log
    try:
        recent = get_recent_events(limit=20)
        if recent:
            report_lines.append("--- RECENT EVENTS (last 20) ---")
            for event in recent:
                report_lines.append(
                    f"[{event.get('timestamp', 'N/A')}] [{event.get('category', 'N/A')}] "
                    f"{event.get('message', 'N/A')}"
                )
            report_lines.append("")
    except:
        pass
    
    # Add session stats
    try:
        stats = get_session_stats()
        if stats:
            report_lines.extend([
                "--- SESSION STATS ---",
                f"Total Sessions: {stats.get('total_sessions', 0)}",
                f"Total Playtime: {stats.get('total_playtime', 0)} seconds",
                "",
            ])
    except:
        pass
    
    report_lines.append("=" * 60)
    return "\n".join(report_lines)


def send_crash_report_email(user_email, crash_report):
    """
    Send a crash report via email using HTTP form submission.
    
    This uses a free service (formsubmit.co) to avoid requiring
    SMTP credentials in the game. The report is sent as a web form.
    
    Args:
        user_email (str): The user's email for follow-up
        crash_report (str): The full crash report text
    
    Returns:
        bool: True if the report was sent successfully
    """
    import urllib.request
    import urllib.parse
    import json
    
    try:
        # Save the crash report locally as backup
        crash_report_path = os.path.join(
            os.path.dirname(__file__), "logs", 
            f"crash_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        _ensure_directories()
        with open(crash_report_path, 'w', encoding='utf-8') as f:
            f.write(f"User Email: {user_email}\n\n")
            f.write(crash_report)
        
        log_event("CRASH_REPORT", f"Crash report saved locally", crash_report_path)
        
        # Try to send via HTTP POST (formsubmit.co or similar service)
        # Note: You would replace this URL with your actual crash report endpoint
        form_data = {
            'email': DEVELOPER_EMAIL,
            '_replyto': user_email,
            '_subject': 'ChronoQuest Crash Report',
            'message': crash_report,
            'user_email': user_email
        }
        
        # Encode and send
        data = urllib.parse.urlencode(form_data).encode('utf-8')
        req = urllib.request.Request(
            f"{CRASH_REPORT_URL}{DEVELOPER_EMAIL}",
            data=data,
            method='POST',
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    log_event("CRASH_REPORT", "Crash report sent successfully", user_email)
                    return True
        except Exception as e:
            # If online submission fails, the local copy is still saved
            log_event("CRASH_REPORT", f"Online submission failed (local copy saved)", str(e))
        
        return True  # Local save succeeded
        
    except Exception as e:
        # Log the failure but don't crash again
        try:
            log_event("CRASH_REPORT", f"Failed to save crash report", str(e))
        except:
            pass
        return False


def submit_crash_report(category, message, exception=None, traceback_str=None, user_email=None):
    """
    Build and submit a crash report.
    
    This is the main function to call when a fatal error occurs.
    It builds the crash report and attempts to send it.
    
    Args:
        category (str): Error category
        message (str): Error message
        exception (Exception, optional): The exception object
        traceback_str (str, optional): Full traceback
        user_email (str, optional): User's email. If None, tries to get saved email.
    
    Returns:
        bool: True if report was submitted/saved successfully
    """
    # Use saved email if not provided
    if not user_email:
        user_email = get_user_email()
    
    if not user_email:
        return False  # No email available
    
    # Build the crash report
    crash_report = build_crash_report(category, message, exception, traceback_str)
    
    # Send it
    return send_crash_report_email(user_email, crash_report)
