# Claude AI Trade Pro (v14 — Precision)

Streamlit app: NSE live boards, Hot-Movers alerts (Upstox data) and Telegram pings.

## Files
| File | What it is |
|---|---|
| `claude_ai_trade_pro.py` | The app (Streamlit Cloud main file) |
| `alert_runner.py` | **PC alert engine** — hot alerts to Telegram during market hours, no browser |
| `start_app.bat` | **Full app with all 4 tabs** in your browser (localhost:8501) |
| `start_alerts.bat` / `install_task.bat` / `remove_task.bat` | Windows: start now / auto-start weekdays 08:55 / remove auto-start |
| `hot_backtest.py` | Run on your PC to backtest the hot-alert rules on Upstox 1-min data |
| `requirements.txt` | Packages Streamlit Cloud installs |
| `.streamlit/secrets.toml.example` | Template for Streamlit **Secrets** (no real values) |

## Secrets (never in GitHub)
Streamlit Cloud → app → **Settings → Secrets** → paste the template from
`.streamlit/secrets.toml.example` and fill in real values.

## v14 changes
- 🏅 Quality grade (A+/A/B/C) on every hot alert from live Upstox quote data
  (VWAP, circuit room, spread, order book, strength vs NIFTY, NIFTY mood, time)
- Minimum-grade filter in the Hot tab (ALL / A / A+)
- Honest first-touch scoring of every alert from its real send price
- Only finished 1-min candles are used in alert rules
- Fixed Supertrend (was always bullish), journal/EOD win scoring, UTC clock bug
- Telegram token moved out of the code into Secrets

## Run the alerts on your PC (no Streamlit, market hours only)
**Easiest:** double-click `setup_windows.bat` — it installs Python + packages, opens the secrets file for you, and sets up auto-start. Or do it by hand:

1. Install Python 3.11+ from python.org (tick **Add Python to PATH**).
2. In this folder: `pip install -r requirements.txt`
3. Copy `.streamlit/secrets.toml.example` → `.streamlit/secrets.toml` and fill in your NEW Upstox + Telegram details.
4. Double-click `start_alerts.bat` (test), then double-click `install_task.bat` once (auto-start every weekday 08:55).

It warms up 09:00, sends alerts 09:15–15:20, sends the daily scorecard ~15:46, then stops by itself.
Weekends/NSE holidays it exits immediately. Log: `alert_runner.log`.
Want the screen too? Double-click `start_app.bat` — all 4 tabs open in your browser. When the engine is
running, the Hot tab just SHOWS the engine's results (refreshes every 2 min) and never double-sends.
Don't run Streamlit Cloud alerts at the same time — otherwise every alert arrives twice.

## Backtest (on your PC)
```
set UPSTOX_TOKEN=your_token
python hot_backtest.py --days 40
```
