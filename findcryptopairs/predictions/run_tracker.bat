@echo off
echo Starting Prediction Tracker...
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "track_predictions.ps1"
pause
