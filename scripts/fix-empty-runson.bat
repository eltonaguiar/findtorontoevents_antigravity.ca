@echo off
:: Fix Empty runs-on Expressions in GitHub Actions Workflows
:: Usage: scripts\fix-empty-runson.bat

echo ========================================
echo   Fix Empty runs-on Expressions
echo ========================================
echo.

:: Check if running from repo root
if not exist ".github\workflows" (
    echo ERROR: Not in repository root directory
    echo Please run from the project root
    exit /b 1
)

:: Show what would be fixed first
echo Checking for empty runs-on expressions...
echo.

powershell -ExecutionPolicy Bypass -Command "& {.\scripts\fix-empty-runson.ps1 -WhatIf}"

echo.
choice /C YN /M "Do you want to apply these fixes"
if errorlevel 2 goto :cancel
if errorlevel 1 goto :apply

:apply
powershell -ExecutionPolicy Bypass -Command "& {.\scripts\fix-empty-runson.ps1}"
echo.
echo Done! Review changes with: git diff --stat
pause
goto :eof

:cancel
echo Cancelled. No changes made.
pause
goto :eof
