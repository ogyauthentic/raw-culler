@echo off
setlocal enabledelayedexpansion
title RAW Culler — Build Installer
color 0A

echo.
echo  =====================================================
echo    RAW Culler ^| Build EXE + Installer
echo  =====================================================
echo.

:: ── 1. Check Python ──────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found.
    echo  Download: https://www.python.org/downloads/
    echo  Make sure to check "Add Python to PATH" during install.
    pause & exit /b 1
)
for /f "tokens=*" %%v in ('python --version') do set PYVER=%%v
echo  [OK] %PYVER% found.

:: ── 2. Install / upgrade build tools ─────────────────────────────────────────
echo.
echo  [1/4] Installing build tools...
pip install --quiet --upgrade pip pyinstaller rawpy imageio Pillow
if errorlevel 1 (
    echo  [ERROR] Failed to install dependencies.
    pause & exit /b 1
)
echo  [OK] Dependencies ready.

:: ── 3. Build EXE with PyInstaller ────────────────────────────────────────────
echo.
echo  [2/4] Building EXE (may take 1-3 minutes)...
if exist dist\RAW_Culler.exe del /f /q dist\RAW_Culler.exe
pyinstaller --clean --noconfirm raw_culler.spec
if errorlevel 1 (
    echo  [ERROR] PyInstaller failed. Check the log above.
    pause & exit /b 1
)
echo  [OK] dist\RAW_Culler.exe created successfully.

:: ── 4. Create installer with Inno Setup (optional) ───────────────────────────
echo.
echo  [3/4] Looking for Inno Setup to create installer...

set ISCC=""
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe"       set ISCC="C:\Program Files\Inno Setup 6\ISCC.exe"

if %ISCC%=="" (
    echo  [INFO] Inno Setup not found — skipping installer creation.
    echo         Download Inno Setup: https://jrsoftware.org/isdl.php
    echo         Then re-run this script to also generate the installer.
    echo.
    echo  [OK] Standalone EXE is ready at: dist\RAW_Culler.exe
    goto :done
)

echo  [OK] Inno Setup found.
echo.
echo  [4/4] Building RAW_Culler_Setup.exe...
%ISCC% installer.iss
if errorlevel 1 (
    echo  [ERROR] Inno Setup failed. Check installer.iss.
    pause & exit /b 1
)

:done
echo.
echo  =====================================================
echo   BUILD COMPLETE!
echo  =====================================================
if exist "Output\RAW_Culler_Setup.exe" (
    echo   Installer      : Output\RAW_Culler_Setup.exe
)
echo   Standalone EXE : dist\RAW_Culler.exe
echo.
echo   Share either file with users.
echo   No Python required on the target machine.
echo  =====================================================
echo.
pause
