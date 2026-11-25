@echo off
title Claude AI Trade Pro - App (all tabs)
cd /d "%~dp0"
REM skip Streamlit first-run email question (it silently blocks the start)
if not exist "%USERPROFILE%\.streamlit" mkdir "%USERPROFILE%\.streamlit"
if not exist "%USERPROFILE%\.streamlit\credentials.toml" (echo [general]& echo email = "") > "%USERPROFILE%\.streamlit\credentials.toml"
echo Starting the app... your browser will open at http://localhost:8501
echo KEEP THIS WINDOW OPEN while you use the app. Close it to stop the app.
start "" cmd /c "timeout /t 8 /nobreak >nul & start http://localhost:8501"
python -m streamlit run claude_ai_trade_pro.py --server.headless true --server.port 8501 --browser.gatherUsageStats false
echo.
echo The app stopped. If you see an error above, send a screenshot to Claude.
pause
