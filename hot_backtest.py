#!/usr/bin/env python3
# ============================================================
# 🔬 HOT-ALERT BACKTESTER (Upstox data) — companion to combo_cloud_v14.py
# ------------------------------------------------------------
# Replays the app's 🚀 HOT ALERT rule and 🔥 GREEN-6 BIG-MOVER rule on past
# 1-minute candles and scores every alert HONESTLY:
#   • entry  = close of the candle when the alert would have been SENT
#              (+ optional sweep delay), not the earlier cross price
#   • result = FIRST TOUCH of +T% target vs −S% stop on later 1-min candles
#              (both inside one candle → LOSS), else exit at 15:20
#   • costs  = round-trip % deducted (brokerage + STT + slippage)
# Also grades each alert with the checks that exist in history (VWAP
# stretch, strength vs NIFTY, NIFTY mood, time of day) and shows which ones
# actually separate winners from losers.
#
# RUN (on your PC — needs your Upstox analytics/access token):
#   pip install pandas
#   set UPSTOX_TOKEN=your_token            (Windows)   |  export UPSTOX_TOKEN=...  (Linux/Mac)
#   python hot_backtest.py --days 40
#   python hot_backtest.py --days 40 --max-stocks 300 --delay 2
# Results: printed tables + hot_backtest_trades.csv. Downloads are cached in
# ./bt_cache so re-runs (different targets/filters) are instant.
#
# LIMITS — read before trusting a number:
#   • The live app only checks the top ~25 rupee-movers per sweep; this
#     checks every stock → more alerts than live (same rule, wider net).
#   • Spread / order-book / circuit checks need live depth → not in history.
#   • Need 200+ alerts before a win-rate means much (±7% noise at 200).
#   • Breakeven win-rate for +T/−S with costs C is (S+C)/(T+S). For the
#     default +1.5/−1.0 and 0.10% costs that is 44%. Below it = losing.
# ============================================================
import argparse
import gzip
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta

try:
    import pandas as pd
except ImportError:
    sys.exit("pip install pandas")

API = "https://api.upstox.com"
NIFTY_KEY = "NSE_INDEX|Nifty 50"
UA = "Mozilla/5.0 hot-backtest"


class Upstox:
    def __init__(self, token, sleep=0.9, cache="bt_cache"):
        self.tok, self.sleep, self.cache = token, sleep, cache
        os.makedirs(cache, exist_ok=True)
        self.calls = 0

    def _get(self, url, cache_key=None):
        fn = os.path.join(self.cache, cache_key) if cache_key else None
        if fn and os.path.exists(fn):
            with open(fn, encoding="utf-8") as f:
                return json.load(f)
        for attempt in range(4):
            try:
                rq = urllib.request.Request(url, headers={
                    "Accept": "application/json", "User-Agent": UA,
                    "Authorization": f"Bearer {self.tok}"})
                data = json.loads(urllib.request.urlopen(rq, timeout=30).read().decode("utf-8"))
                self.calls += 1
                time.sleep(self.sleep)
                if fn:
                    with open(fn, "w", encoding="utf-8") as f:
                        json.dump(data, f)
                return data
            except urllib.error.HTTPError as e:
                if e.code == 429:                 # rate limit → wait and retry
                    time.sleep(60)
                    continue
                if e.code in (400, 404):
                    return {}
                time.sleep(5)
            except Exception:
                time.sleep(5)
        return {}

    def universe(self):
        raw = urllib.request.urlopen(urllib.request.Request(
            "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz",
            headers={"User-Agent": UA}), timeout=60).read()
        out = {}
        for r in json.loads(gzip.decompress(raw)):
            if (r.get("segment") == "NSE_EQ" and r.get("instrument_type") == "EQ"
                    and r.get("trading_symbol") and r.get("instrument_key")):
                out[r["trading_symbol"]] = r["instrument_key"]
        return out

    def quotes(self, keys):
        out = {}
        for i in range(0, len(keys), 450):
            q = ",".join(urllib.parse.quote(k, safe="") for k in keys[i:i + 450])
            d = self._get(f"{API}/v2/market-quote/quotes?instrument_key={q}") or {}
            for v in (d.get("data") or {}).values():
                if isinstance(v, dict) and v.get("instrument_token"):
                    out[v["instrument_token"]] = v
        return out

    def candles(self, key, unit, interval, frm, to):
        k = urllib.parse.quote(key, safe="")
        ck = f"{key.replace('|', '_').replace(' ', '_')}_{unit}{interval}_{frm}_{to}.json"
        d = self._get(f"{API}/v3/historical-candle/{k}/{unit}/{interval}/{to}/{frm}", ck)
        cd = ((d or {}).get("data") or {}).get("candles") or []
        return sorted(cd, key=lambda c: c[0])          # oldest first


# ---------------------------------------------------------------- rules
def hot_rule(day, pc, avg20, lo_band=100.0, hi_band=1000.0):
    """🚀 app rule: first SUSTAINED close ≥ open + max(₹3, 1%) on two
    consecutive candles; gap < 4%; liquid; ₹ band. Returns index of the
    confirming candle or None."""
    if not day or avg20 < 100000:
        return None
    op = float(day[0][1])
    if not (lo_band <= op <= hi_band) or (pc and (op / pc - 1) * 100 >= 4.0):
        return None
    thr = max(3.0, 0.01 * op)
    for i in range(len(day) - 1):
        if float(day[i][4]) >= op + thr and float(day[i + 1][4]) >= op + thr:
            return i + 1
    return None


def green6_rule(day, pc, avg20, lo_band=100.0, hi_band=1000.0):
    """🔥 app rule: 6 straight green 1-min candles, staircase volume ≥1.5×
    earlier pace, ≥5/6 closes in the upper half, ≥ open + max(₹1.5, 0.5%),
    ≥1% above open, gap < 4%, from 09:30. Returns first index or None."""
    if not day or avg20 < 100000:
        return None
    op = float(day[0][1])
    if not (lo_band <= op <= hi_band) or (pc and (op / pc - 1) * 100 >= 4.0):
        return None
    for i in range(11, len(day)):
        if str(day[i][0])[11:16] < "09:30":
            continue
        q6, pr = day[i - 5:i + 1], day[:i - 5]
        if not all(float(c[4]) > float(c[1]) for c in q6):
            continue
        if len(pr) >= 5:
            pv = sum(float(c[5]) for c in pr) / len(pr)
            if pv and sum(float(c[5]) for c in q6) / 6.0 < 1.5 * pv:
                continue
        wk = sum(1 for c in q6 if float(c[2]) <= float(c[3])
                 or (float(c[4]) - float(c[3])) / (float(c[2]) - float(c[3])) >= 0.5)
        last = float(day[i][4])
        if wk >= 5 and last >= op + max(1.5, 0.005 * op) and last >= op * 1.01:
            return i
    return None


def first_touch(day, i_entry, tgt, stop, exit_hm="15:20"):
    ps = float(day[i_entry][4])
    up, dn = ps * (1 + tgt / 100), ps * (1 - stop / 100)
    last, mfe, mae = ps, 0.0, 0.0
    for c in day[i_entry + 1:]:
        if str(c[0])[11:16] > exit_hm:
            break
        h, l, cl = float(c[2]), float(c[3]), float(c[4])
        mfe, mae, last = max(mfe, (h / ps - 1) * 100), min(mae, (l / ps - 1) * 100), cl
        if l <= dn:
            return "LOSS", -stop, mfe, mae
        if h >= up:
            return "WIN", tgt, mfe, mae
    return "OPEN", (last / ps - 1) * 100, mfe, mae


def features(day, i, pc, nifty_day, nifty_pc):
    """Checks available in history (same thresholds as the live 🏅 grade)."""
    tp_v = sum((float(c[2]) + float(c[3]) + float(c[4])) / 3 * float(c[5]) for c in day[:i + 1])
    v = sum(float(c[5]) for c in day[:i + 1])
    px = float(day[i][4])
    f = {"t": str(day[i][0])[11:16], "px": px}
    f["vwap_ext"] = (px / (tp_v / v) - 1) * 100 if v else None
    f["chg"] = (px / pc - 1) * 100 if pc else None
    f["nifty_chg"] = None
    if nifty_day and nifty_pc:
        nc = [c for c in nifty_day if str(c[0])[11:16] <= f["t"]]
        if nc:
            f["nifty_chg"] = (float(nc[-1][4]) / nifty_pc - 1) * 100
    fails = []
    if f["vwap_ext"] is not None and not (0.0 <= f["vwap_ext"] <= 2.0):
        fails.append("VWAP")
    if f["chg"] is not None and f["nifty_chg"] is not None and f["chg"] - f["nifty_chg"] < 1.0:
        fails.append("RS")
    if f["nifty_chg"] is not None and f["nifty_chg"] <= -0.50:
        fails.append("NIFTY")
    if not ("09:16" <= f["t"] <= "14:30"):
        fails.append("time")
    f["fails"] = fails
    f["grade"] = "A+" if not fails else "A" if len(fails) == 1 else "B" if len(fails) == 2 else "C"
    return f


def by_day(cd):
    out = {}
    for c in cd:
        out.setdefault(str(c[0])[:10], []).append(c)
    return out


def summarize(df, cost, label):
    if df.empty:
        print(f"\n{label}: no alerts")
        return
    rows = []

    def agg(name, d):
        w, l = (d.res == "WIN").sum(), (d.res == "LOSS").sum()
        rows.append({"group": name, "alerts": len(d), "win": w, "loss": l,
                     "open": len(d) - w - l,
                     "win%": round(100 * w / (w + l), 1) if (w + l) else None,
                     "avg net %": round(d.pnl.mean() - cost, 3),
                     "avg MFE %": round(d.mfe.mean(), 2), "avg MAE %": round(d.mae.mean(), 2)})
    agg("ALL", df)
    for r in sorted(df.rule.unique()):
        agg(f"rule {r}", df[df.rule == r])
    for g in ["A+", "A", "B", "C"]:
        if (df.grade == g).any():
            agg(f"grade {g}", df[df.grade == g])
    for chk in ["VWAP", "RS", "NIFTY", "time"]:
        m = df.fails.apply(lambda x: chk in x)
        if m.any():
            agg(f"failed {chk}", df[m])
            agg(f"passed {chk}", df[~m])
    for lo, hi in [("09:15", "09:45"), ("09:45", "11:00"), ("11:00", "13:00"), ("13:00", "15:30")]:
        m = (df.t >= lo) & (df.t < hi)
        if m.any():
            agg(f"time {lo}-{hi}", df[m])
    print(f"\n==== {label} ====")
    print(pd.DataFrame(rows).to_string(index=False))


def main():
    ap = argparse.ArgumentParser(description="Backtest the app's hot-alert rules on Upstox 1-min data")
    ap.add_argument("--token", default=os.environ.get("UPSTOX_TOKEN", ""))
    ap.add_argument("--days", type=int, default=40, help="calendar days back (max ~ 90 recommended)")
    ap.add_argument("--max-stocks", type=int, default=500, help="most-traded stocks in the ₹ band")
    ap.add_argument("--symbols", default="", help="comma list, e.g. SUZLON,IDEA (skips auto-universe)")
    ap.add_argument("--band", default="100,1000", help="price band, e.g. 100,1000")
    ap.add_argument("--target", type=float, default=1.5)
    ap.add_argument("--stop", type=float, default=1.0)
    ap.add_argument("--cost", type=float, default=0.10, help="round-trip cost %")
    ap.add_argument("--delay", type=int, default=1, help="minutes from rule-trigger to your entry")
    ap.add_argument("--sleep", type=float, default=0.9, help="seconds between API calls (rate limit)")
    a = ap.parse_args()
    if not a.token:
        sys.exit("Give your Upstox token: --token XXX or env UPSTOX_TOKEN")
    lo_b, hi_b = (float(x) for x in a.band.split(","))
    up = Upstox(a.token, a.sleep)
    to_d = date.today() - timedelta(days=1)
    fr_d = to_d - timedelta(days=a.days)

    print("📥 instrument master…")
    uni = up.universe()
    if a.symbols:
        syms = [x.strip().upper() for x in a.symbols.split(",") if x.strip().upper() in uni]
    else:
        print("📥 live quotes to pick the most-traded stocks in the band…")
        q = up.quotes(list(uni.values()))
        inv = {v: k for k, v in uni.items()}
        liq = []
        for k, v in q.items():
            px, vol = float(v.get("last_price") or 0), float(v.get("volume") or 0)
            if lo_b <= px <= hi_b and k in inv:
                liq.append((px * vol, inv[k]))
        syms = [s for _, s in sorted(liq, reverse=True)[:a.max_stocks]]
    print(f"   {len(syms)} stocks · {fr_d} → {to_d}")

    nifty_d = by_day(up.candles(NIFTY_KEY, "days", 1, str(fr_d - timedelta(days=10)), str(to_d)))
    nifty_dates = sorted(nifty_d)
    nifty_1m = {}
    d0 = fr_d
    while d0 <= to_d:                                   # 1-min data: ≤1 month per call
        d1 = min(d0 + timedelta(days=27), to_d)
        nifty_1m.update(by_day(up.candles(NIFTY_KEY, "minutes", 1, str(d0), str(d1))))
        d0 = d1 + timedelta(days=1)

    trades = []
    for n, s in enumerate(syms, 1):
        key = uni[s]
        daily = up.candles(key, "days", 1, str(fr_d - timedelta(days=45)), str(to_d))
        if len(daily) < 25:
            continue
        dmap = {str(c[0])[:10]: (i, c) for i, c in enumerate(daily)}
        # pre-filter with DAILY candles → only fetch 1-min where a rule COULD fire
        cand = []
        for dd, (i, c) in dmap.items():
            if dd < str(fr_d) or i < 21:
                continue
            o, h = float(c[1]), float(c[2])
            pc = float(daily[i - 1][4])
            avg20 = sum(float(x[5]) for x in daily[i - 20:i]) / 20
            if (lo_b <= o <= hi_b and avg20 >= 100000 and (o / pc - 1) * 100 < 4.0
                    and h >= o + min(max(3.0, 0.01 * o), max(1.5, 0.01 * o))):
                cand.append((dd, pc, avg20))
        if not cand:
            continue
        mins = {}
        d0 = fr_d
        while d0 <= to_d:
            d1 = min(d0 + timedelta(days=27), to_d)
            if any(str(d0) <= dd <= str(d1) for dd, _, _ in cand):
                mins.update(by_day(up.candles(key, "minutes", 1, str(d0), str(d1))))
            d0 = d1 + timedelta(days=1)
        for dd, pc, avg20 in cand:
            day = mins.get(dd) or []
            if len(day) < 30:
                continue
            ni = nifty_dates.index(dd) if dd in nifty_dates else -1
            npc = float(nifty_d[nifty_dates[ni - 1]][0][4]) if ni > 0 else None
            for rule, fn in (("HOT", hot_rule), ("GREEN6", green6_rule)):
                i = fn(day, pc, avg20, lo_b, hi_b)
                if i is None:
                    continue
                ie = min(i + a.delay, len(day) - 1)
                if str(day[ie][0])[11:16] > "15:10":
                    continue
                res, pnl, mfe, mae = first_touch(day, ie, a.target, a.stop)
                f = features(day, ie, pc, nifty_1m.get(dd), npc)
                trades.append({"date": dd, "sym": s, "rule": rule, **f,
                               "res": res, "pnl": pnl, "mfe": mfe, "mae": mae})
        if n % 25 == 0:
            print(f"   …{n}/{len(syms)} stocks · {len(trades)} alerts · {up.calls} API calls")

    df = pd.DataFrame(trades)
    if df.empty:
        print("No alerts found — try more --days or --max-stocks.")
        return
    df.to_csv("hot_backtest_trades.csv", index=False)
    be = 100 * (a.stop + a.cost) / (a.target + a.stop)
    print(f"\nTarget +{a.target}% / stop −{a.stop}% / costs {a.cost}% → BREAKEVEN win% ≈ {be:.0f}%"
          f" (above it = profitable, below it = losing)")
    summarize(df, a.cost, f"{len(df)} alerts · {df.date.nunique()} days · entry {a.delay} min after trigger")
    print("\nTip: compare targets/stops exactly by re-running with --target / --stop "
          "(downloads are cached in ./bt_cache, so re-runs are fast).")
    print("\nSaved every alert to hot_backtest_trades.csv")


if __name__ == "__main__":
    main()
