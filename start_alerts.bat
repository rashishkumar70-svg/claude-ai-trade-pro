@echo off
title Claude AI Trade Pro - Alert Engine
cd /d "%~dp0"
python alert_runner.py
echo.
echo Engine stopped. This window closes in 60 seconds.
timeout /t 60
