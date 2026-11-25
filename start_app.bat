@echo off
title Claude AI Trade Pro - App (all tabs)
cd /d "%~dp0"
python -m streamlit run claude_ai_trade_pro.py --server.headless false --browser.gatherUsageStats false
pause
