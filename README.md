# AI Trader Pro v14 — Precision

Streamlit app: NSE live boards, Hot-Movers alerts (Upstox data) and Telegram pings.

## Files
| File | What it is |
|---|---|
| `streamlit_app.py` | The app (Streamlit Cloud main file) |
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

## Backtest (on your PC)
```
set UPSTOX_TOKEN=your_token
python hot_backtest.py --days 40
```
