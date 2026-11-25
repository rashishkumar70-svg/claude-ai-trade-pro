@echo off
REM One-time setup: start the alert engine every weekday at 08:55.
schtasks /create /f /tn "Claude AI Trade Pro Alerts" /tr "\"%~dp0start_alerts.bat\"" /sc weekly /d MON,TUE,WED,THU,FRI /st 08:55
if %errorlevel%==0 (echo. & echo DONE - the engine will start by itself every weekday at 08:55.) else (echo. & echo FAILED - right-click this file and choose "Run as administrator".)
pause
