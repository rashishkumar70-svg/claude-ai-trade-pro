@echo off
title Claude AI Trade Pro - One-time setup
cd /d "%~dp0"
echo ============================================================
echo   CLAUDE AI TRADE PRO - ONE-TIME SETUP
echo ============================================================
echo.

REM ---- 1. Python ----------------------------------------------
where python >nul 2>nul
if %errorlevel% neq 0 (
  echo [1/4] Python not found - installing Python 3.12 ...
  winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
  echo.
  echo Python installed. CLOSE this window and double-click setup_windows.bat AGAIN.
  pause
  exit /b
)
echo [1/4] Python found:
python --version

REM ---- 2. Packages --------------------------------------------
echo.
echo [2/4] Installing packages (2-5 minutes the first time) ...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
  echo.
  echo Package install FAILED - send a screenshot of this window to Claude.
  pause
  exit /b
)

REM ---- 3. Secrets file ----------------------------------------
echo.
if not exist ".streamlit\secrets.toml" (
  copy ".streamlit\secrets.toml.example" ".streamlit\secrets.toml" >nul
  echo [3/4] Created .streamlit\secrets.toml - Notepad will open now.
  echo       Fill in your NEW Upstox token + expiry and NEW Telegram bot token + chat IDs,
  echo       then SAVE and CLOSE Notepad to continue.
  notepad ".streamlit\secrets.toml"
) else (
  echo [3/4] .streamlit\secrets.toml already exists - keeping it.
)

REM ---- 4. Auto-start ------------------------------------------
echo.
set /p AUTO=[4/4] Start the alert engine automatically every weekday at 08:55? (Y/N): 
if /i "%AUTO%"=="Y" (
  schtasks /create /f /tn "Claude AI Trade Pro Alerts" /tr "\"%~dp0start_alerts.bat\"" /sc weekly /d MON,TUE,WED,THU,FRI /st 08:55
)

echo.
echo ============================================================
echo   SETUP DONE
echo   - start_app.bat     : open the full app (all tabs) in your browser
echo   - start_alerts.bat  : start the Telegram alert engine now
echo ============================================================
pause
