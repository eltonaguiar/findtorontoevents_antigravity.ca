@echo off
echo Running analyze_quality.py...
python audit_dashboard/analyze_quality.py
echo.
echo Heartbeat Log from audit_dashboard/data/heartbeat_log.txt:
type audit_dashboard\data\heartbeat_log.txt
echo.
