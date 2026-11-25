#!/usr/bin/env python3
# ============================================================
# 🔔 CLAUDE AI TRADE PRO — PC ALERT ENGINE (no Streamlit page, no browser)
# ------------------------------------------------------------
# Runs the SAME 🚀/💎/🔥/🔄/🎯 hot-alert engine as the app's HOT MOVERS tab,
# on the same timing, but headless — market hours only:
#   09:00–09:14  pre-open warm-up (caches history → fast first sweep)
#   09:15–15:25  live sweeps → Telegram alerts (every 1 min till 09:25,
#                then every 2 min — same cadence as the tab)
#   15:30–16:45  honest scoring + 📊 daily scorecard to Telegram, then EXIT
# Weekends and NSE holidays: exits immediately.
#
# START:   double-click start_alerts.bat   (or: python alert_runner.py)
# AUTO:    double-click install_task.bat once → starts every weekday 08:55
# STOP:    close the window (or Ctrl+C)
#
# Credentials come from .streamlit/secrets.toml in THIS folder (see
# .streamlit/secrets.toml.example). That file is git-ignored — it never
# goes to GitHub.
# ============================================================
import logging
import os
import socket
import sys
import time
import traceback
import warnings
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)                         # secrets + runtime files live in this folder
sys.path.insert(0, HERE)
warnings.filterwarnings("ignore")
logging.getLogger("streamlit").setLevel(logging.ERROR)
for _n in ("streamlit.runtime", "streamlit.runtime.caching",
           "streamlit.runtime.scriptrunner_utils", "streamlit.runtime.state"):
    logging.getLogger(_n).setLevel(logging.ERROR)

LOG_FILE = os.path.join(HERE, "alert_runner.log")
LOCK_PORT = 47613                      # one engine at a time (no duplicate alerts)


def log(msg):
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def keep_awake(on=True):
    """Windows: stop the PC from sleeping while the engine runs."""
    if os.name != "nt":
        return
    try:
        import ctypes
        ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
        ctypes.windll.kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | (ES_SYSTEM_REQUIRED if on else 0))
    except Exception:
        pass


def single_instance():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", LOCK_PORT))
        s.listen(1)
        return s
    except OSError:
        return None


def alerts_file():
    return os.path.join(HERE, f"alerts_{datetime.now().strftime('%Y-%m-%d')}.txt")


def console_alerts(A):
    """No Telegram configured → print each message here instead, beep, and
    append it to alerts_YYYY-MM-DD.txt. Returns True so the app records the
    alert exactly as if it had been sent (follow-ups + honest scoring work)."""
    import html as _html
    import re as _re

    def _show(text, buttons=None, keep=False):
        plain = _html.unescape(_re.sub(r"<[^>]+>", "", str(text))).strip()
        bar = "─" * 60
        block = f"\n{bar}\n{plain}\n{bar}"
        try:
            print(block, flush=True)
        except Exception:
            print(block.encode("ascii", "replace").decode(), flush=True)
        try:
            with open(alerts_file(), "a", encoding="utf-8") as f:
                f.write(f"{datetime.now().strftime('%H:%M:%S')}\n{plain}\n\n")
        except Exception:
            pass
        if os.name == "nt":
            try:
                import winsound
                winsound.MessageBeep()
            except Exception:
                pass
        return True
    A.tg_send = _show


def mins(n):
    return n.hour * 60 + n.minute


def main():
    lock = single_instance()
    if not lock:
        log("⚠️ Another alert engine is already running on this PC — exiting (no duplicate alerts).")
        return 1
    if not os.path.exists(os.path.join(HERE, ".streamlit", "secrets.toml")):
        log("❌ Missing .streamlit/secrets.toml — copy .streamlit/secrets.toml.example to "
            ".streamlit/secrets.toml and fill in your NEW Upstox + Telegram details.")
        return 1

    log("Loading app engine…")
    import claude_ai_trade_pro as A    # imports the app's functions; the page itself is NOT started

    n = A.now_ist()
    day = n.strftime("%Y-%m-%d")
    hol = A.NSE_HOLIDAYS.get(day)
    if n.weekday() >= 5 or hol:
        log(f"Market closed today ({hol or 'weekend'}) — nothing to do. Bye.")
        return 0
    if mins(n) > 16 * 60 + 45:
        log("After 16:45 — today's session is over. Bye.")
        return 0

    # ── health check → Telegram ─────────────────────────────
    tok = A.up_auth_token()
    tg = A.tg_load()
    if not (tg.get("token") and tg.get("chat")):
        console_alerts(A)                # 🖥️ no Telegram → alerts on this screen
        log("ℹ️ Telegram not set — SCREEN MODE: every alert is shown in this window "
            f"(with a beep) and saved to {os.path.basename(alerts_file())}.")
    up_ok = False
    if tok:
        q = A._up_quotes([A.HQ_NIFTY_KEY], tok)
        up_ok = bool(q)
    exp = A.up_load().get("aexp") or "?"
    if up_ok:
        A.tg_send(f"✅ <b>PC ALERT ENGINE STARTED</b> · {A.APP_VERSION}\n"
                  f"Upstox token OK (expires {exp})\n"
                  f"Runs till ~16:45 today, then stops by itself.")
        log(f"✅ Health OK — Upstox token valid (expires {exp}).")
    else:
        A.tg_send("❌ <b>PC ALERT ENGINE — UPSTOX TOKEN NOT WORKING</b>\n"
                  "Make a new Analytics Token in the Upstox developer portal and put it in "
                  ".streamlit/secrets.toml, then restart the engine.")
        log("❌ Upstox token missing/invalid — fix secrets.toml. Exiting.")
        return 1

    keep_awake(True)
    last_sweep = last_warm = last_eval = 0.0
    errors = 0
    try:
        while True:
            n = A.now_ist()
            m = mins(n)
            nowt = time.time()

            if m < 9 * 60:                                   # before 09:00 → wait
                time.sleep(30)
                continue

            if 9 * 60 <= m <= 9 * 60 + 14:                    # pre-open warm-up
                if nowt - last_warm >= 120:
                    try:
                        w = A._warmup_tick() or {}
                        log(f"🔥 warm-up {w.get('done', '?')}/{w.get('total', '?')}"
                            + (" — complete" if w.get("fin") else ""))
                    except Exception as e:
                        log(f"warm-up error: {type(e).__name__}: {e}")
                    last_warm = nowt

            elif 9 * 60 + 15 <= m <= 15 * 60 + 25:            # live market → sweeps
                fast0 = m <= 9 * 60 + 25
                gap = 60 if fast0 else 120          # 1 min till 09:25, then every 2 min
                if nowt - last_sweep >= gap:
                    t0 = time.time()
                    try:
                        hot = A.hot_scan(tg=True)
                        if hot and not hot.get("err"):
                            A.rt_save("hot", last=hot, sw=time.time())
                            errors = 0
                            log(f"🚀 sweep ok in {time.time() - t0:.0f}s")
                        else:
                            errors += 1
                            log(f"⚠️ sweep problem: {(hot or {}).get('err')}")
                    except Exception as e:
                        errors += 1
                        log(f"⚠️ sweep error: {type(e).__name__}: {e}")
                        log(traceback.format_exc(limit=3))
                    last_sweep = nowt
                    if errors == 5:
                        A.tg_send("⚠️ <b>PC ALERT ENGINE</b> — 5 sweeps in a row failed "
                                  "(internet / Upstox?). Still retrying.")

            elif m >= 15 * 60 + 30:                           # after close → score + report
                if nowt - last_eval >= 120:
                    try:
                        k = A.hot_eval_pending()
                        if k:
                            log(f"🏅 scored {k} alerts")
                        A.maybe_daily_scorecard()           # sends once, 15:45–16:59
                    except Exception as e:
                        log(f"scoring error: {type(e).__name__}: {e}")
                    last_eval = nowt
                done = (A.rt_load().get("scorecard") or {}).get("day") == day
                if (done and m >= 15 * 60 + 46) or m >= 16 * 60 + 45:
                    log("📊 Day complete" + (" — scorecard sent." if done else
                                            " (no scorecard: no alerts today).") + " Bye.")
                    break

            time.sleep(10)
    except KeyboardInterrupt:
        log("Stopped by you (Ctrl+C).")
    finally:
        keep_awake(False)
        try:
            lock.close()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
