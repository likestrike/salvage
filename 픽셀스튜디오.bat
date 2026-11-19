@echo off
rem Character pixel studio (tools/pixstudio.py). Closing this window stops the studio.
cd /d "%~dp0"
python -X utf8 tools\pixstudio.py %*
if errorlevel 1 pause
