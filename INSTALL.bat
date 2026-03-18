@echo off
setlocal enabledelayedexpansion
title ChronoQuest Installer
color 0A

:: Get the directory where the batch file is located
cd /d "%~dp0"
set "GAME_DIR=%~dp0"

echo.
echo ============================================
echo     ChronoQuest: Fractures in Time
echo          Automated Installer
echo ============================================
echo.
echo This installer will:
echo  - Install Python 3.12 (if needed)
echo  - Download required packages (pygame)
echo  - Verify all game files
echo  - Create a launcher for easy gameplay
echo.
echo Game Directory: %GAME_DIR%
echo.

:: Check if Python is installed (try multiple methods)
echo [1/4] Checking for Python installation...
set "PYTHON_CMD="

:: Try 'python' command first
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=python"
    goto :python_found
)

:: Try 'py' launcher (Windows Python Launcher)
py --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=py"
    goto :python_found
)

:: Try common Python install locations
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    goto :python_found
)
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    goto :python_found
)
if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" (
    set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    goto :python_found
)

:: Python not found - need to install
echo Python not found! Downloading Python installer...
echo.

:: Create temp directory
if not exist "%TEMP%\chronoquest_install" mkdir "%TEMP%\chronoquest_install"

:: Download Python using PowerShell
echo Downloading Python 3.12.0 (this may take a few minutes)...
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe' -OutFile '%TEMP%\chronoquest_install\python_installer.exe'}"

if not exist "%TEMP%\chronoquest_install\python_installer.exe" (
    echo.
    echo ERROR: Failed to download Python installer.
    echo Please download Python manually from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation!
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Python installer will now open.
echo  
echo  IMPORTANT: CHECK THE BOX THAT SAYS
echo  "Add Python to PATH" at the BOTTOM!
echo ============================================
echo.
pause

:: Launch installer (not silent - let user see it)
start /wait "" "%TEMP%\chronoquest_install\python_installer.exe" InstallAllUsers=0 PrependPath=1

echo.
echo ============================================
echo  Python installation complete!
echo  
echo  IMPORTANT: You MUST close this window
echo  and run INSTALL.bat again to continue.
echo ============================================
echo.
pause
exit /b 0

:python_found
for /f "tokens=*" %%i in ('!PYTHON_CMD! --version 2^>^&1') do set PYVER=%%i
echo Found: !PYVER!
echo Using: !PYTHON_CMD!

echo.
echo [2/4] Upgrading pip...
"!PYTHON_CMD!" -m pip install --upgrade pip >nul 2>&1

echo.
echo [3/4] Installing required packages...
echo Installing pygame (required for game graphics)...
"!PYTHON_CMD!" -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to install packages from requirements.txt.
    echo Trying individual package installation...
    "!PYTHON_CMD!" -m pip install pygame
    if %errorlevel% neq 0 (
        echo.
        echo ERROR: Still failed. Please try running as Administrator.
        pause
        exit /b 1
    )
)
echo Packages installed successfully!

echo.
echo [4/4] Verifying game assets and creating launcher...

:: Check if essential game files exist
if not exist "%GAME_DIR%main.py" (
    echo ERROR: main.py not found! Game files are incomplete.
    pause
    exit /b 1
)

if not exist "%GAME_DIR%assets" (
    echo ERROR: assets folder not found! Game files are incomplete.
    pause
    exit /b 1
)

echo Game files verified successfully!

:: Create PLAY.bat launcher
(
echo @echo off
echo cd /d "%%~dp0"
echo title ChronoQuest: Fractures in Time
echo cls
echo.
echo       ====================================
echo       ChronoQuest: Fractures in Time
echo       ====================================
echo.
echo Loading game assets...
echo.
echo "!PYTHON_CMD!" main.py
echo.
echo if %%errorlevel%% neq 0 ^(
echo     echo.
echo     echo ERROR: Game crashed or encountered an error.
echo     echo Error code: %%errorlevel%%
echo     echo.
echo     echo Please check that all game files are present:
echo     echo  - main.py
echo     echo  - assets folder
echo     echo  - game_database.py
echo     echo.
echo     pause
echo ^)
) > "%GAME_DIR%PLAY.bat"

:: Create documentation file for judges
(
echo ChronoQuest: Fractures in Time - Installation Complete!
echo.
echo QUICK START:
echo ============
echo Double-click PLAY.bat to start the game.
echo.
echo ACCESSING GAME DATA ^(For Judges and Developers^):
echo ==================================================
echo All game data and code is stored in this folder structure:
echo.
echo - main.py              ^: Main game code with all game logic
echo - game_database.py     ^: Database module for stats tracking
echo - assets/              ^: All sprite graphics, backgrounds, and animations
echo - data/                ^: Game save data, high scores, player statistics
echo   ^|- high_scores.json  ^: Player high scores and records
echo   ^|- player_stats.json ^: Player statistics and progress tracking
echo   ^|- settings.json     ^: Game settings and user preferences
echo - logs/                ^: Error logs and debug information
echo - README.md            ^: Full documentation
echo - requirements.txt     ^: Python dependencies
echo.
echo TO VIEW ALL DATA IN AN IDE:
echo ===========================
echo 1. Open any Python IDE ^(VS Code, PyCharm, etc.^)
echo 2. Open the pythonPlatformer folder as a project
echo 3. Browse through the file structure to see:
echo    - Game code architecture
echo    - Sprite assets used
echo    - Game save data
echo    - High scores and player statistics
echo    - Boss AI dialogue logs ^(if applicable^)
echo.
echo PLAYING THE GAME:
echo =================
echo - Use Arrow Keys to move left/right
echo - Press Up Arrow to jump
echo - Double press Up Arrow for double jump
echo - Press ESC to pause or access menu
echo - Select levels 1, 2, or 3 from menu
echo - Defeat the boss at end of each level!
echo.
echo ADVANCED FEATURES:
echo ==================
echo - Optional AI boss dialogue: Install Ollama ^(https://ollama.ai^)
echo - Run: ollama pull mistral
echo - Start: ollama serve
echo - Game will auto-detect and use AI if available
echo.
echo Installation successful! Enjoy the game!
) > "%GAME_DIR%INSTALLATION_GUIDE.txt"

echo.
echo ============================================
echo      Installation Successful!
echo ============================================
echo.
echo Your game is ready to play!
echo.
echo TO START PLAYING:
echo   1. Close this window
echo   2. Double-click "PLAY.bat" in this folder
echo.
echo IMPORTANT FILES:
echo   - PLAY.bat              ^: Click to start the game
echo   - INSTALLATION_GUIDE.txt ^: View this file for detailed instructions
echo   - README.md             ^: Full game documentation
echo.
echo Game location: %GAME_DIR%
echo.
echo Press any key to open the game now...
pause

:: Automatically launch the game
echo.
echo Launching ChronoQuest...
echo.
start "" "%GAME_DIR%PLAY.bat"
exit /b 0
