@echo off
echo === Stream Deck Profile Generator - Build ===
echo.

pip install pyinstaller >nul 2>&1

echo Building EXE...
pyinstaller StreamDeckProfileGenerator.spec --noconfirm

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Build OK: dist\StreamDeckProfileGenerator.exe
) else (
    echo.
    echo Build FAILED
)
pause
