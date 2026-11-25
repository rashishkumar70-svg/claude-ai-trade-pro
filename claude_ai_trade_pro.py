# ============================================================
# AI TRADER PRO v13.6 — "PRO TERMINAL · 500 LIVE" (single file)
# YOUR v13 app EXACTLY as it was + ONE new separate tab:
#   🔴 LIVE 500-STOCK DASHBOARD — one common board that shows which
#   stocks are in an UPTREND right now, auto-analysing up to 500
#   stocks in fast batches, auto-refreshing while you watch.
# Everything else (Analyze · Scanner · Search · Below-100 · Journal
# · Guide · 4 pivot systems · ML · reports) is unchanged from v13.
# ------------------------------------------------------------
# pip install streamlit yfinance pandas numpy ta plotly scikit-learn scipy python-docx streamlit-autorefresh
# streamlit run ai_trader_v13_500.py
# (streamlit-autorefresh = smooth LIVE auto-refresh; without it you
#  get a fallback auto-refresh + a manual 🔄 button. All optional.)
# ============================================================

import streamlit as st

# ── cross-version layout kwarg ──────────────────────────────────────────────
# New Streamlit (2026) REMOVED `use_container_width`; older versions don't know
# `width="stretch"`. This picks the right one at startup, so the app runs on
# BOTH old and new Streamlit (PC + Streamlit Cloud) without layout errors.
try:
    _sv = tuple(int(x) for x in st.__version__.split(".")[:2] if x.isdigit())
    STRETCH = {"width": "stretch"} if _sv >= (1, 46) else {"use_container_width": True}
except Exception:
    STRETCH = {"use_container_width": True}

# ── price range: owner trades affordable stocks only — every board/scan/
#    ranking keeps ₹100–₹1000 (manual Search/Analyze stays exempt, any price) ──
MIN_PRICE = 100.0
MAX_PRICE = 1000.0
PREM_MIN = 1000.0    # 💎 premium movers band (₹1000–3000) — kept SEPARATE
PREM_MAX = 3000.0

# ── 🔔 Telegram (owner's bot — preconfigured; can be overridden in the app) ──
#    🔐 v14: NO secrets in the code — read from Streamlit Cloud → Settings →
#    Secrets ([telegram] token = "...", chat = "id1,id2"). Missing → alerts off
#    until set (or until entered in the app's Telegram settings).
def _secret(section, key, default=""):
    try:
        return str((st.secrets.get(section) or {}).get(key) or default)
    except Exception:
        return default


TG_DEFAULT_TOKEN = _secret("telegram", "token")
TG_DEFAULT_CHAT = _secret("telegram", "chat")


def _H(html):
    """Normalize HTML for st.markdown: newer Streamlit renders 4-space-indented
    lines as CODE BLOCKS (raw tags as text!). Collapse all whitespace so the
    whole markup stays ONE html block on every Streamlit version."""
    try:
        return " ".join(str(html).split())
    except Exception:
        return html
import yfinance as yf
import pandas as pd
import numpy as np
import ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
import time
import io
import re
import urllib.request
from datetime import datetime
from datetime import time as dtime
from datetime import timezone as _dts, timedelta as _dtd

# ── IST clock: cloud servers run on UTC — every time in this app is IST ──
TZ_IST = _dts(_dtd(hours=5, minutes=30))


def now_ist():
    try:
        return datetime.now(TZ_IST)
    except Exception:
        return datetime.now()


def _dist(ix):
    """IST calendar-date of a candle timestamp (yfinance sends IST-aware stamps)."""
    try:
        return ix.astimezone(TZ_IST).date() if getattr(ix, "tzinfo", None) else ix.date()
    except Exception:
        return ix.date()
import concurrent.futures

warnings.filterwarnings('ignore')

st.set_page_config(page_title="Claude AI Trade Pro", page_icon="🎯",
                   layout="wide", initial_sidebar_state="collapsed")

# ============================================================
# CSS — PREMIUM LIGHT THEME (+ dashboard components)
# ============================================================
st.markdown(_H("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
*{font-family:'Inter',sans-serif;box-sizing:border-box;}
.stApp{background:#0a1120;color:#dbe4f0;}
.stApp h1,.stApp h2,.stApp h3,.stApp h4{color:#f1f5f9;}
.stApp p,.stApp li,.stApp label{color:#cbd5e1;}
[data-testid="stCaptionContainer"]{color:#8fa3bd;}
.navbar{background:linear-gradient(135deg,#0d1b6e 0%,#1565c0 60%,#0288d1 100%);
  border-radius:20px;padding:18px 28px;margin-bottom:22px;box-shadow:0 8px 32px rgba(0,0,0,0.5);
  border:1px solid #1e3a5f;}
.input-row{background:#0f1a2e;border-radius:16px;padding:20px 24px;margin-bottom:18px;
  border:1px solid #1e293b;box-shadow:0 2px 12px rgba(0,0,0,0.35);}
.sig-buy{background:linear-gradient(135deg,#052e16,#0b3a1f);border:3px solid #16a34a;
  border-radius:20px;padding:28px;box-shadow:0 8px 32px rgba(22,163,74,0.2);}
.sig-sell{background:linear-gradient(135deg,#2a0e0e,#3d1420);border:3px solid #dc2626;
  border-radius:20px;padding:28px;box-shadow:0 8px 32px rgba(220,38,38,0.2);}
.sig-wait{background:linear-gradient(135deg,#3a2a06,#33200a);border:3px solid #d97706;
  border-radius:20px;padding:28px;box-shadow:0 8px 32px rgba(217,119,6,0.18);}
.mc-blue{background:linear-gradient(135deg,#16233d,#1e3a5f);border:2px solid #3b82f6;
  border-radius:16px;padding:18px;text-align:center;box-shadow:0 4px 16px rgba(59,130,246,0.15);}
.mc-green{background:linear-gradient(135deg,#052e16,#0b3a1f);border:2px solid #16a34a;
  border-radius:16px;padding:18px;text-align:center;box-shadow:0 4px 16px rgba(22,163,74,0.15);}
.mc-red{background:linear-gradient(135deg,#2a0e0e,#3d1420);border:2px solid #dc2626;
  border-radius:16px;padding:18px;text-align:center;box-shadow:0 4px 16px rgba(220,38,38,0.15);}
.mc-purple{background:linear-gradient(135deg,#1e1b3a,#241b45);border:2px solid #9333ea;
  border-radius:16px;padding:18px;text-align:center;box-shadow:0 4px 16px rgba(147,51,234,0.15);}
.mc-orange{background:linear-gradient(135deg,#2b1c0c,#33200a);border:2px solid #ea580c;
  border-radius:16px;padding:18px;text-align:center;box-shadow:0 4px 16px rgba(234,88,12,0.15);}
.mc-white{background:#0f1a2e;border:1px solid #1e293b;border-radius:16px;padding:18px;
  text-align:center;box-shadow:0 2px 10px rgba(0,0,0,0.3);}
.lv-r{background:linear-gradient(90deg,#2a0e0e,#0f1a2e);border-left:5px solid #ef4444;
  border-radius:0 12px 12px 0;padding:11px 18px;margin:3px 0;box-shadow:0 1px 6px rgba(0,0,0,0.3);}
.lv-s{background:linear-gradient(90deg,#052e16,#0f1a2e);border-left:5px solid #22c55e;
  border-radius:0 12px 12px 0;padding:11px 18px;margin:3px 0;box-shadow:0 1px 6px rgba(0,0,0,0.3);}
.lv-p{background:linear-gradient(90deg,#3a2a06,#0f1a2e);border-left:5px solid #f59e0b;
  border-radius:0 12px 12px 0;padding:11px 18px;margin:3px 0;box-shadow:0 1px 6px rgba(0,0,0,0.3);}
.lv-fib{background:linear-gradient(90deg,#1e1b3a,#0f1a2e);border-left:5px solid #a855f7;
  border-radius:0 12px 12px 0;padding:11px 18px;margin:3px 0;box-shadow:0 1px 6px rgba(0,0,0,0.3);}
.lv-cur{background:linear-gradient(90deg,#16233d,#0f1a2e);border-left:5px solid #3b82f6;
  border-radius:0 12px 12px 0;padding:11px 18px;margin:3px 0;box-shadow:0 2px 8px rgba(0,0,0,0.3);}
.sh{display:flex;align-items:center;gap:10px;background:linear-gradient(90deg,#16233d,transparent);
  border-left:5px solid #3b82f6;padding:10px 18px;border-radius:0 12px 12px 0;margin:26px 0 14px;
  font-size:15px;font-weight:800;color:#60a5fa;letter-spacing:0.3px;}
.sc-r{background:#0f1a2e;border:1px solid #1e293b;border-radius:14px;padding:16px;margin:6px 0;
  box-shadow:0 2px 8px rgba(0,0,0,0.3);}
.pbar-container{background:#1e293b;border-radius:20px;height:10px;overflow:hidden;}
.pbar-buy{background:linear-gradient(90deg,#16a34a,#22c55e);height:10px;border-radius:20px;}
.pbar-sell{background:linear-gradient(90deg,#dc2626,#ef4444);height:10px;border-radius:20px;}
[data-testid="stMetric"]{background:#0f1a2e !important;border:1px solid #1e293b !important;border-radius:14px !important;
  padding:14px !important;box-shadow:0 2px 8px rgba(0,0,0,0.3) !important;}
[data-testid="stMetricValue"]{color:#f1f5f9 !important;font-weight:800 !important;font-size:22px !important;}
[data-testid="stMetricLabel"]{color:#8fa3bd !important;font-size:11px !important;font-weight:600 !important;}
[data-testid="stExpander"]{background:#0f1a2e;border:1px solid #1e293b;border-radius:14px;}
[data-testid="stExpanderDetails"]{color:#cbd5e1;}
[data-testid="stDataFrame"]{background:#0f1a2e;border:1px solid #1e293b;border-radius:12px;}
.stTabs [data-baseweb="tab"]{color:#94a3b8;}
.stTabs [aria-selected="true"]{color:#60a5fa !important;}
.stButton>button{background:linear-gradient(135deg,#60a5fa,#3b82f6) !important;color:white !important;
  border:none !important;border-radius:12px !important;font-weight:700 !important;padding:10px 24px !important;
  font-size:14px !important;box-shadow:0 4px 12px rgba(29,78,216,0.4) !important;}
.stButton>button:hover{background:linear-gradient(135deg,#1e40af,#2563eb) !important;transform:translateY(-1px) !important;}
div[data-testid="stTextInput"]>div>div>input{background:#0f1a2e !important;border:2px solid #1e293b !important;
  border-radius:12px !important;color:#e2e8f0 !important;font-size:14px !important;font-weight:500 !important;}
[data-testid="stSidebar"]{display:none !important;}
#MainMenu{visibility:hidden;}footer{visibility:hidden;}header{visibility:hidden;}
::-webkit-scrollbar{width:6px;}::-webkit-scrollbar-thumb{background:#334155;border-radius:3px;}
/* ---- dashboard components ---- */
.breadth{display:flex;height:18px;border-radius:10px;overflow:hidden;border:1px solid #1e293b;background:#0f1a2e;}
.b-up{background:linear-gradient(90deg,#16a34a,#22c55e);height:100%;}
.b-dn{background:linear-gradient(90deg,#dc2626,#ef4444);height:100%;}
.b-fl{background:#334155;height:100%;}
.uchip{display:inline-block;background:#052e16;border:1.5px solid #16a34a;color:#4ade80;font-weight:800;
  font-size:12px;padding:5px 12px;border-radius:20px;margin:3px 3px 3px 0;}
.dchip{display:inline-block;background:#2a0e0e;border:1.5px solid #dc2626;color:#f87171;font-weight:800;
  font-size:12px;padding:5px 12px;border-radius:20px;margin:3px 3px 3px 0;}
.nchip{display:inline-block;background:#16233d;border:1.5px solid #334155;color:#94a3b8;font-weight:700;
  font-size:12px;padding:5px 12px;border-radius:20px;margin:3px 3px 3px 0;}
.achip{display:inline-block;background:#3a2a06;border:1.5px solid #f59e0b;color:#fbbf24;font-size:11.5px;
  padding:4px 10px;border-radius:9px;margin:3px 3px 3px 0;font-weight:700;}
.ucard{background:#0f1a2e;border:1px solid #14532d;border-left:5px solid #16a34a;border-radius:12px;
  padding:12px 14px;margin:4px 0;box-shadow:0 2px 8px rgba(0,0,0,0.3);}
.ucard .nm{font-weight:900;font-size:14px;color:#f1f5f9;}
.ucard .pr{font-weight:900;font-size:18px;color:#60a5fa;}
.badge{display:inline-block;border-radius:20px;padding:2px 10px;font-size:10.5px;font-weight:800;color:white;}
.dashhead{background:linear-gradient(135deg,#7c2d12,#fbbf24,#d97706);border-radius:18px;padding:18px 24px;
  margin-bottom:16px;box-shadow:0 8px 28px rgba(180,83,9,0.25);border:1px solid #fbbf24;}
</style>
"""), unsafe_allow_html=True)

# ============================================================
# CURATED STOCK DATABASE + LIVE FULL NSE UNIVERSE
# ============================================================
NIFTY50 = {
    "RELIANCE":"RELIANCE.NS","TCS":"TCS.NS","HDFCBANK":"HDFCBANK.NS","INFY":"INFY.NS",
    "ICICIBANK":"ICICIBANK.NS","HINDUNILVR":"HINDUNILVR.NS","ITC":"ITC.NS","SBIN":"SBIN.NS",
    "BHARTIARTL":"BHARTIARTL.NS","KOTAKBANK":"KOTAKBANK.NS","LT":"LT.NS","AXISBANK":"AXISBANK.NS",
    "ASIANPAINT":"ASIANPAINT.NS","MARUTI":"MARUTI.NS","SUNPHARMA":"SUNPHARMA.NS","TITAN":"TITAN.NS",
    "BAJFINANCE":"BAJFINANCE.NS","HCLTECH":"HCLTECH.NS","TMPV":"TMPV.NS","TATASTEEL":"TATASTEEL.NS",
    "NTPC":"NTPC.NS","ONGC":"ONGC.NS","POWERGRID":"POWERGRID.NS","COALINDIA":"COALINDIA.NS",
    "ADANIENT":"ADANIENT.NS","ADANIPORTS":"ADANIPORTS.NS","JSWSTEEL":"JSWSTEEL.NS","TECHM":"TECHM.NS",
    "INDUSINDBK":"INDUSINDBK.NS","DRREDDY":"DRREDDY.NS","BAJAJ-AUTO":"BAJAJ-AUTO.NS","NESTLEIND":"NESTLEIND.NS",
    "CIPLA":"CIPLA.NS","BRITANNIA":"BRITANNIA.NS","TATAPOWER":"TATAPOWER.NS","APOLLOHOSP":"APOLLOHOSP.NS",
    "BAJAJFINSV":"BAJAJFINSV.NS","ULTRACEMCO":"ULTRACEMCO.NS","HINDALCO":"HINDALCO.NS","M&M":"M&M.NS",
    "WIPRO":"WIPRO.NS","EICHERMOT":"EICHERMOT.NS","HEROMOTOCO":"HEROMOTOCO.NS","BPCL":"BPCL.NS",
    "TATACONSUM":"TATACONSUM.NS","DIVISLAB":"DIVISLAB.NS","SBILIFE":"SBILIFE.NS","HDFCLIFE":"HDFCLIFE.NS",
    "SHRIRAMFIN":"SHRIRAMFIN.NS","GRASIM":"GRASIM.NS",
}
NEXT50 = {
    "ETERNAL (ZOMATO)":"ETERNAL.NS","JIOFIN":"JIOFIN.NS","ADANIGREEN":"ADANIGREEN.NS","ADANIPOWER":"ADANIPOWER.NS","IRFC":"IRFC.NS",
    "RVNL":"RVNL.NS","HAL":"HAL.NS","BEL":"BEL.NS","DLF":"DLF.NS","VEDL":"VEDL.NS","NHPC":"NHPC.NS",
    "SJVN":"SJVN.NS","IRCTC":"IRCTC.NS","BANKBARODA":"BANKBARODA.NS","PNB":"PNB.NS","CANBK":"CANBK.NS",
    "BHEL":"BHEL.NS","SAIL":"SAIL.NS","GAIL":"GAIL.NS","IOC":"IOC.NS","HINDPETRO":"HINDPETRO.NS",
    "LICI":"LICI.NS","AMBUJACEM":"AMBUJACEM.NS","HDFCAMC":"HDFCAMC.NS","PIDILITIND":"PIDILITIND.NS",
    "SIEMENS":"SIEMENS.NS","ABB":"ABB.NS","POLYCAB":"POLYCAB.NS","DIXON":"DIXON.NS",
    "GODREJPROP":"GODREJPROP.NS","TRENT":"TRENT.NS","VBL":"VBL.NS","MARICO":"MARICO.NS",
    "DABUR":"DABUR.NS","COLPAL":"COLPAL.NS","DMART":"DMART.NS","NAUKRI":"NAUKRI.NS",
    "PAGEIND":"PAGEIND.NS","MRF":"MRF.NS","BOSCHLTD":"BOSCHLTD.NS","HAVELLS":"HAVELLS.NS",
    "MUTHOOTFIN":"MUTHOOTFIN.NS","CHOLAFIN":"CHOLAFIN.NS","TATAELXSI":"TATAELXSI.NS",
    "RECLTD":"RECLTD.NS","PFC":"PFC.NS","HUDCO":"HUDCO.NS","NMDC":"NMDC.NS",
}
MIDCAP = {
    "RAYMONDREL":"RAYMONDREL.NS","ELECON":"ELECON.NS","OMNI":"OMNI.NS","PERSISTENT":"PERSISTENT.NS","COFORGE":"COFORGE.NS","MPHASIS":"MPHASIS.NS","KPITTECH":"KPITTECH.NS",
    "LTTS":"LTTS.NS","ANGELONE":"ANGELONE.NS","MCX":"MCX.NS","CDSL":"CDSL.NS","COCHINSHIP":"COCHINSHIP.NS",
    "MAZDOCK":"MAZDOCK.NS","GRSE":"GRSE.NS","BDL":"BDL.NS","BEML":"BEML.NS","IRCON":"IRCON.NS",
    "KEI":"KEI.NS","APLAPOLLO":"APLAPOLLO.NS","INOXWIND":"INOXWIND.NS","JSWENERGY":"JSWENERGY.NS",
    "WAAREEENER":"WAAREEENER.NS","DEEPAKNTR":"DEEPAKNTR.NS","SRF":"SRF.NS","KALYANKJIL":"KALYANKJIL.NS",
    "SENCO":"SENCO.NS","INDHOTEL":"INDHOTEL.NS","APOLLOTYRE":"APOLLOTYRE.NS","CEATLTD":"CEATLTD.NS",
    "TVSMOTOR":"TVSMOTOR.NS","BHARATFORG":"BHARATFORG.NS","MOTHERSON":"MOTHERSON.NS","MANAPPURAM":"MANAPPURAM.NS",
    "NBCC":"NBCC.NS","NCC":"NCC.NS","IRB":"IRB.NS","ATGL":"ATGL.NS","PIIND":"PIIND.NS",
    "ZYDUSLIFE":"ZYDUSLIFE.NS","LAURUSLABS":"LAURUSLABS.NS","ZENSARTECH":"ZENSARTECH.NS",
    "FEDERALBNK":"FEDERALBNK.NS","AUBANK":"AUBANK.NS","MAXHEALTH":"MAXHEALTH.NS",
    "METROPOLIS":"METROPOLIS.NS","LALPATHLAB":"LALPATHLAB.NS",
}
BELOW100 = {
    "YESBANK":"YESBANK.NS","IDEA":"IDEA.NS","SUZLON":"SUZLON.NS","NHPC":"NHPC.NS","SJVN":"SJVN.NS",
    "RPOWER":"RPOWER.NS","JPPOWER":"JPPOWER.NS","PNB":"PNB.NS","UCOBANK":"UCOBANK.NS","IOB":"IOB.NS",
    "SAIL":"SAIL.NS","NMDC":"NMDC.NS","TRIDENT":"TRIDENT.NS","NETWORK18":"NETWORK18.NS",
    "TV18BRDCST":"TV18BRDCST.NS","SOUTHBANK":"SOUTHBANK.NS","UJJIVANSFB":"UJJIVANSFB.NS",
    "EQUITASBNK":"EQUITASBNK.NS","ESAFSFB":"ESAFSFB.NS","SPICEJET":"SPICEJET.NS","NFL":"NFL.NS",
    "CANBK":"CANBK.NS","BHEL":"BHEL.NS","IOC":"IOC.NS","HINDPETRO":"HINDPETRO.NS",
}
IT_S    = {"TCS":"TCS.NS","INFY":"INFY.NS","WIPRO":"WIPRO.NS","HCLTECH":"HCLTECH.NS","TECHM":"TECHM.NS",
           "LTTS":"LTTS.NS","PERSISTENT":"PERSISTENT.NS","COFORGE":"COFORGE.NS","ZENSARTECH":"ZENSARTECH.NS","MPHASIS":"MPHASIS.NS"}
BANK_S  = {"HDFCBANK":"HDFCBANK.NS","ICICIBANK":"ICICIBANK.NS","SBIN":"SBIN.NS","KOTAKBANK":"KOTAKBANK.NS",
           "AXISBANK":"AXISBANK.NS","PNB":"PNB.NS","BANKBARODA":"BANKBARODA.NS","FEDERALBNK":"FEDERALBNK.NS","YESBANK":"YESBANK.NS"}
POWER_S = {"NTPC":"NTPC.NS","POWERGRID":"POWERGRID.NS","ADANIGREEN":"ADANIGREEN.NS","ADANIPOWER":"ADANIPOWER.NS",
           "TATAPOWER":"TATAPOWER.NS","SUZLON":"SUZLON.NS","NHPC":"NHPC.NS","SJVN":"SJVN.NS",
           "JSWENERGY":"JSWENERGY.NS","RPOWER":"RPOWER.NS","PFC":"PFC.NS"}
DEF_S   = {"HAL":"HAL.NS","BEL":"BEL.NS","BDL":"BDL.NS","GRSE":"GRSE.NS","MAZDOCK":"MAZDOCK.NS",
           "COCHINSHIP":"COCHINSHIP.NS","BEML":"BEML.NS"}
AUTO_S  = {"MARUTI":"MARUTI.NS","TMPV":"TMPV.NS","M&M":"M&M.NS","BAJAJ-AUTO":"BAJAJ-AUTO.NS",
           "HEROMOTOCO":"HEROMOTOCO.NS","TVSMOTOR":"TVSMOTOR.NS","EICHERMOT":"EICHERMOT.NS","MRF":"MRF.NS","APOLLOTYRE":"APOLLOTYRE.NS"}
PHARMA_S= {"SUNPHARMA":"SUNPHARMA.NS","DRREDDY":"DRREDDY.NS","CIPLA":"CIPLA.NS","DIVISLAB":"DIVISLAB.NS",
           "LUPIN":"LUPIN.NS","AUROPHARMA":"AUROPHARMA.NS","APOLLOHOSP":"APOLLOHOSP.NS","MAXHEALTH":"MAXHEALTH.NS"}

ALL_STOCKS = {}
for _db in [NIFTY50,NEXT50,MIDCAP,BELOW100,IT_S,BANK_S,POWER_S,DEF_S,AUTO_S,PHARMA_S]:
    ALL_STOCKS.update(_db)
_seen=set();_clean={}
for _n,_s in ALL_STOCKS.items():
    if _s not in _seen:_seen.add(_s);_clean[_n]=_s
ALL_STOCKS=_clean

FAMOUS = {
    "RELIANCE": "RELIANCE.NS", "TCS": "TCS.NS", "HDFCBANK": "HDFCBANK.NS", "INFY": "INFY.NS",
    "ICICIBANK": "ICICIBANK.NS", "SBIN": "SBIN.NS", "AXISBANK": "AXISBANK.NS", "KOTAKBANK": "KOTAKBANK.NS",
    "BHARTIARTL": "BHARTIARTL.NS", "ITC": "ITC.NS", "LT": "LT.NS", "HINDUNILVR": "HINDUNILVR.NS",
    "BAJFINANCE": "BAJFINANCE.NS", "MARUTI": "MARUTI.NS", "TMPV": "TMPV.NS",
    "TATASTEEL": "TATASTEEL.NS", "JSWSTEEL": "JSWSTEEL.NS", "SUNPHARMA": "SUNPHARMA.NS",
    "TITAN": "TITAN.NS", "HCLTECH": "HCLTECH.NS", "WIPRO": "WIPRO.NS", "TECHM": "TECHM.NS",
    "NTPC": "NTPC.NS", "POWERGRID": "POWERGRID.NS", "ONGC": "ONGC.NS", "COALINDIA": "COALINDIA.NS",
    "TATAPOWER": "TATAPOWER.NS", "ADANIENT": "ADANIENT.NS", "ADANIPORTS": "ADANIPORTS.NS",
    "ADANIPOWER": "ADANIPOWER.NS", "ADANIGREEN": "ADANIGREEN.NS", "M&M": "M&M.NS",
    "BAJAJ-AUTO": "BAJAJ-AUTO.NS", "HEROMOTOCO": "HEROMOTOCO.NS", "TVSMOTOR": "TVSMOTOR.NS",
    "ULTRACEMCO": "ULTRACEMCO.NS", "ASIANPAINT": "ASIANPAINT.NS", "NESTLEIND": "NESTLEIND.NS",
    "BAJAJFINSV": "BAJAJFINSV.NS", "DRREDDY": "DRREDDY.NS", "CIPLA": "CIPLA.NS",
    "HAL": "HAL.NS", "BEL": "BEL.NS", "IRFC": "IRFC.NS", "RVNL": "RVNL.NS", "ETERNAL": "ETERNAL.NS", "JIOFIN": "JIOFIN.NS",
    "DLF": "DLF.NS", "VEDL": "VEDL.NS", "HINDALCO": "HINDALCO.NS", "GAIL": "GAIL.NS",
    "IOC": "IOC.NS", "BPCL": "BPCL.NS", "PNB": "PNB.NS", "BANKBARODA": "BANKBARODA.NS",
    "CANBK": "CANBK.NS", "INDUSINDBK": "INDUSINDBK.NS", "TRENT": "TRENT.NS", "DMART": "DMART.NS",
    "LICI": "LICI.NS", "SBILIFE": "SBILIFE.NS", "HDFCLIFE": "HDFCLIFE.NS", "SIEMENS": "SIEMENS.NS",
    "SUZLON": "SUZLON.NS", "IREDA": "IREDA.NS", "YESBANK": "YESBANK.NS", "IDEA": "IDEA.NS",
    "SAIL": "SAIL.NS", "NMDC": "NMDC.NS", "PFC": "PFC.NS", "RECLTD": "RECLTD.NS",
}

CAT_MAP = {
    "⭐ FAMOUS / MOST-TRADED": FAMOUS,
    "🌐 ALL NSE (live · every stock)": None,
    "🏅 NIFTY 50": NIFTY50, "📈 NEXT 50": NEXT50, "💎 MIDCAP": MIDCAP,
    "💰 BELOW ₹100": BELOW100, "🏆 ALL CURATED": ALL_STOCKS, "💻 IT": IT_S,
    "🏦 BANKING": BANK_S, "⚡ POWER": POWER_S, "🛡️ DEFENCE": DEF_S,
    "🚗 AUTO": AUTO_S, "💊 PHARMA": PHARMA_S,
}

ALIASES = {
    "SBI":"SBIN.NS","STATE BANK":"SBIN.NS","HDFC BANK":"HDFCBANK.NS","ICICI BANK":"ICICIBANK.NS",
    "INFOSYS":"INFY.NS","TATA MOTORS":"TMPV.NS","ETERNAL (ZOMATO)":"ETERNAL.NS","TATA STEEL":"TATASTEEL.NS","TATA POWER":"TATAPOWER.NS",
    "COAL INDIA":"COALINDIA.NS","MAHINDRA":"M&M.NS","BAJAJ FINANCE":"BAJFINANCE.NS","ASIAN PAINTS":"ASIANPAINT.NS",
    "AIRTEL":"BHARTIARTL.NS","HUL":"HINDUNILVR.NS","L&T":"LT.NS","KOTAK":"KOTAKBANK.NS","AXIS BANK":"AXISBANK.NS",
    "YES BANK":"YESBANK.NS","VODAFONE":"IDEA.NS","NESTLE":"NESTLEIND.NS","LIC":"LICI.NS","HDFC LIFE":"HDFCLIFE.NS",
    "SBI LIFE":"SBILIFE.NS","DR REDDY":"DRREDDY.NS","INOX WIND":"INOXWIND.NS","WAAREE":"WAAREEENER.NS",
    "REC":"RECLTD.NS","ZENSAR":"ZENSARTECH.NS","OIL INDIA":"OIL.NS","VEDANTA":"VEDL.NS",
    "BOSCH":"BOSCHLTD.NS","HERO":"HEROMOTOCO.NS","TVS":"TVSMOTOR.NS","EICHER":"EICHERMOT.NS",
}


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_universe():
    """Full live NSE equity list (~2000 symbols) — searchable by name/ticker."""
    url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            raw = r.read().decode("utf-8", "ignore")
        udf = pd.read_csv(io.StringIO(raw))
        udf.columns = [c.strip() for c in udf.columns]
        name_map, sym_map = {}, {}
        for _, row in udf.iterrows():
            sym = str(row.get("SYMBOL", "")).strip().upper()
            nm = str(row.get("NAME OF COMPANY", "")).strip()
            if sym:
                sym_map[sym] = sym + ".NS"
                name_map[f"{nm} ({sym})"] = sym + ".NS"
        if sym_map:
            return {"name_map": name_map, "sym_map": sym_map,
                    "count": len(sym_map), "live": True}
    except Exception:
        pass
    return {"name_map": {k: v for k, v in ALL_STOCKS.items()},
            "sym_map": {k.upper(): v for k, v in ALL_STOCKS.items()},
            "count": len(ALL_STOCKS), "live": False}


def universe_search(query, limit=40):
    from difflib import SequenceMatcher
    q = query.strip().upper()
    if len(q) < 2:
        return {}
    uni = fetch_universe()["name_map"]
    qtokens = [t for t in re.split(r"[^A-Z0-9&]+", q) if t]

    def word_hit(tok, words):
        for w in words:
            if not w:
                continue
            if w.startswith(tok) or tok.startswith(w):
                return 1.0
            if len(tok) >= 3 and tok in w:
                return 0.92
            if SequenceMatcher(None, tok, w).ratio() >= 0.8:
                return 0.85
        return 0.0

    scored = []
    for disp, sym in uni.items():
        du = disp.upper()
        base = sym.replace(".NS", "").replace(".BO", "")
        if q == base or q == du:
            scored.append((3.0, disp, sym)); continue
        words = [w for w in re.split(r"[^A-Z0-9&]+", du) if w]
        hits = [word_hit(t, words) for t in qtokens]
        if hits and all(h > 0 for h in hits):
            score = sum(hits) / len(hits)
            if q in du:
                score += 0.5
            if base.startswith(q):
                score += 0.3
            scored.append((score, disp, sym))
    scored.sort(key=lambda x: (-x[0], len(x[1])))
    return {d: s for _, d, s in scored[:limit]}


# ============================================================
# UTILITIES
# ============================================================
# ── 📅 NSE TRADING HOLIDAYS 2026 (official NSE circular list) — update
#    each December/January when NSE publishes the new year's calendar ──
NSE_HOLIDAYS = {
    "2026-01-15": "Maharashtra Municipal Election",
    "2026-01-26": "Republic Day",
    "2026-03-03": "Holi",
    "2026-03-26": "Shri Ram Navami",
    "2026-03-31": "Shri Mahavir Jayanti",
    "2026-04-03": "Good Friday",
    "2026-04-14": "Dr. Ambedkar Jayanti",
    "2026-05-01": "Maharashtra Day",
    "2026-05-28": "Bakri Id",
    "2026-06-26": "Muharram",
    "2026-09-14": "Ganesh Chaturthi",
    "2026-10-02": "Mahatma Gandhi Jayanti",
    "2026-10-20": "Dussehra",
    "2026-11-10": "Diwali-Balipratipada",
    "2026-11-24": "Guru Nanak Jayanti",
    "2026-12-25": "Christmas",
}


def _next_trading_day(d):
    """Next date that is NOT a weekend and NOT an NSE holiday."""
    d = d + _dtd(days=1)
    while d.weekday() >= 5 or d.strftime("%Y-%m-%d") in NSE_HOLIDAYS:
        d += _dtd(days=1)
    return d


def mkt_status():
    n = now_ist()
    _hol = NSE_HOLIDAYS.get(n.strftime("%Y-%m-%d"))
    if _hol:
        _d = _next_trading_day(n.date())
        return "closed", f"🔴 HOLIDAY · {_hol}", f"Opens {_d.strftime('%A %d %b')} 9:15 AM"
    if n.weekday() >= 5:
        _d = _next_trading_day(n.date())
        return "closed", "🔴 CLOSED", f"Opens {_d.strftime('%A %d %b')} 9:15 AM"
    t = n.time()
    if t < dtime(9, 0):    return "pre",  "🌅 PRE-MARKET", "Opens today 9:15 AM"
    if t < dtime(9, 15):   return "pre",  "🌅 PRE-OPEN",   "Opens very soon!"
    if t <= dtime(15, 30): return "open", "🟢 MARKET LIVE","Closes 3:30 PM"
    # after close → the NEXT TRADING day (skips weekends AND NSE holidays)
    _d = _next_trading_day(n.date())
    return "closed", "🔴 CLOSED", f"Opens {_d.strftime('%A %d %b')} 9:15 AM"


def session_time_context():
    n = now_ist()
    t = n.time()
    close = n.replace(hour=15, minute=30, second=0, microsecond=0)
    sqoff = n.replace(hour=15, minute=15, second=0, microsecond=0)
    mins_left = max(int((close - n).total_seconds() // 60), 0)
    mins_sq = max(int((sqoff - n).total_seconds() // 60), 0)
    hh, mm = mins_sq // 60, mins_sq % 60
    left_txt = (f"{hh}h {mm}m" if hh else f"{mm}m") + " to square-off (3:15 PM)"
    if t <= dtime(11, 0):
        phase = "early"; can_enter = True; main_t = "T2"
        note = f"Early session · plenty of time ({left_txt}). Fresh entries fine — aim T2/T3."
    elif t <= dtime(13, 0):
        phase = "mid"; can_enter = True; main_t = "T2"
        note = f"Midday · about half the session left ({left_txt}). Enter only on confirmation, aim T1–T2."
    elif t <= dtime(14, 30):
        phase = "late"; can_enter = True; main_t = "T1"
        note = f"Late session · only {left_txt}. Quick trade only — take T1, don't wait for T2/T3. Trail tight."
    elif t <= dtime(15, 15):
        phase = "closing"; can_enter = False; main_t = "T1"
        note = f"⏰ Closing hour · {left_txt}. Too late for a fresh intraday buy — manage/exit what you hold, square off by 3:15."
    else:
        phase = "done"; can_enter = False; main_t = "T1"
        note = "Session basically over — this plan is for TOMORROW. Nothing to enter now."
    return {"phase": phase, "mins_left": mins_left, "mins_sq": mins_sq,
            "left_txt": left_txt, "note": note, "can_enter": can_enter, "main_t": main_t}


def safe(x, d=np.nan):
    try:
        v = float(x)
        return d if (np.isnan(v) or np.isinf(v)) else v
    except Exception:
        return d


def fmt_num(n, prefix="₹"):
    if abs(n) >= 1e7:  return f"{prefix}{n/1e7:.2f}Cr"
    if abs(n) >= 1e5:  return f"{prefix}{n/1e5:.2f}L"
    if abs(n) >= 1000: return f"{prefix}{n:,.0f}"
    return f"{prefix}{n:.2f}"


@st.cache_data(ttl=300, show_spinner=False)
def do_search(q):
    q = q.strip().upper()
    out = {}
    if len(q) < 1:
        return out
    hits = universe_search(q, limit=10)
    cands = list(hits.items())
    for alias, sym in ALIASES.items():
        if q in alias:
            cands.insert(0, (alias, sym))
    for sfx in ['.NS', '.BO', '']:
        cands.append((q, q.replace(' ', '') + sfx))
    seen = set()
    for label, sym in cands:
        if sym in seen:
            continue
        seen.add(sym)
        try:
            info = yf.Ticker(sym).info
            p = (info.get('regularMarketPrice') or info.get('currentPrice')
                 or info.get('previousClose', 0))
            if p and float(p) > 0:
                nm = info.get('longName', info.get('shortName', sym))
                out[f"{nm} [{sym}]"] = {'sym': sym, 'name': nm, 'price': float(p)}
        except Exception:
            pass
        if len(out) >= 8:
            break
    return out


# ============================================================
# PROFIT CALCULATOR (from your v13 — kept as-is)
# ============================================================
def calc_money(price, capital, sl, t1, t2, t3):
    if price <= 0 or capital <= 0:
        return {}
    qty = int(capital / price)
    if qty <= 0:
        return {}
    invested = round(qty * price, 2)
    leftover = round(capital - invested, 2)

    def pnl(t): return round(qty * (t - price), 2)
    def move(t): return round(t - price, 2)
    def pct(t): return round((t - price) / price * 100, 2) if price > 0 else 0
    def roi(t): return round(pnl(t) / capital * 100, 2) if capital > 0 else 0
    def sv(t): return round(qty * t, 2)

    loss = round(qty * (price - sl), 2)
    loss_pct = round((price - sl) / price * 100, 2) if price > 0 else 0
    loss_roi = round(loss / capital * 100, 2) if capital > 0 else 0
    return {
        'qty': qty, 'invested': invested, 'leftover': leftover,
        'p1': pnl(t1), 'p2': pnl(t2), 'p3': pnl(t3), 'loss': loss,
        'mv1': move(t1), 'mv2': move(t2), 'mv3': move(t3), 'mv_sl': round(price - sl, 2),
        'pct1': pct(t1), 'pct2': pct(t2), 'pct3': pct(t3), 'pct_sl': loss_pct,
        'roi1': roi(t1), 'roi2': roi(t2), 'roi3': roi(t3), 'roi_loss': loss_roi,
        'sv1': sv(t1), 'sv2': sv(t2), 'sv3': sv(t3), 'sv_sl': sv(sl),
        't1': t1, 't2': t2, 't3': t3, 'sl': sl,
    }


def target_feasibility(money, target):
    if not money or money.get('qty', 0) == 0:
        return {'label': '❌ SKIP', 'color': '#dc2626', 'bg': '#2a0e0e',
                'msg': 'Cannot buy even 1 share. Choose cheaper stock.', 'at': None}
    p1, p2, p3 = money['p1'], money['p2'], money['p3']
    if p1 >= target:
        return {'label': '🟢 EASY', 'color': '#16a34a', 'bg': '#052e16',
                'msg': f"T1 gives ₹{p1:.0f}! ₹{round(p1-target,0):.0f} more than target!", 'at': 'T1', 'ap': p1}
    if p2 >= target:
        return {'label': '🔵 ACHIEVABLE', 'color': '#2563eb', 'bg': '#16233d',
                'msg': f"T2 gives ₹{p2:.0f}. Need {money['pct2']:.1f}% move.", 'at': 'T2', 'ap': p2}
    if p3 >= target:
        return {'label': '🟣 STRETCH', 'color': '#9333ea', 'bg': '#1e1b3a',
                'msg': f"T3 gives ₹{p3:.0f}. Need {money['pct3']:.1f}% move.", 'at': 'T3', 'ap': p3}
    return {'label': '❌ NOT ENOUGH', 'color': '#dc2626', 'bg': '#2a0e0e',
            'msg': f"Max profit ₹{p3:.0f}. Need cheaper stock or more capital.", 'at': None, 'ap': p3}


# ============================================================
# LEVEL CALCULATORS — Fibonacci + Standard/Camarilla/Woodie pivots
# ============================================================
def calc_fibonacci(high, low):
    diff = high - low
    levels = {
        '0% (High)': round(high, 2), '23.6%': round(high - 0.236 * diff, 2),
        '38.2%': round(high - 0.382 * diff, 2), '50%': round(high - 0.5 * diff, 2),
        '61.8%': round(high - 0.618 * diff, 2), '78.6%': round(high - 0.786 * diff, 2),
        '100% (Low)': round(low, 2),
    }
    ext = {'127.2%': round(high + 0.272 * diff, 2), '161.8%': round(high + 0.618 * diff, 2),
           '261.8%': round(high + 1.618 * diff, 2)}
    return levels, ext


def calc_all_pivots(ph, pl, pc):
    d = max(ph - pl, 0.01)
    pp = (ph + pl + pc) / 3
    standard = {
        'R3': round(pp + 2 * d, 2), 'R2': round(pp + d, 2), 'R1': round(2 * pp - pl, 2),
        'PP': round(pp, 2),
        'S1': round(2 * pp - ph, 2), 'S2': round(pp - d, 2), 'S3': round(pp - 2 * d, 2),
    }
    camarilla = {
        'R4': round(pc + d * 1.1 / 2, 2), 'R3': round(pc + d * 1.1 / 4, 2),
        'R2': round(pc + d * 1.1 / 6, 2), 'R1': round(pc + d * 1.1 / 12, 2),
        'PP': round(pp, 2),
        'S1': round(pc - d * 1.1 / 12, 2), 'S2': round(pc - d * 1.1 / 6, 2),
        'S3': round(pc - d * 1.1 / 4, 2), 'S4': round(pc - d * 1.1 / 2, 2),
    }
    wp = (ph + pl + 2 * pc) / 4
    woodie = {
        'R2': round(wp + d, 2), 'R1': round(2 * wp - pl, 2), 'PP': round(wp, 2),
        'S1': round(2 * wp - ph, 2), 'S2': round(wp - d, 2),
    }
    return {'Standard': standard, 'Camarilla': camarilla, 'Woodie': woodie}


def demark_pivot(ph, pl, pc, po):
    try:
        if pc < po:   x = ph + 2 * pl + pc
        elif pc > po: x = 2 * ph + pl + pc
        else:         x = ph + pl + 2 * pc
        pp = x / 4
        return {"PP": round(pp, 2), "R1": round(x / 2 - pl, 2), "S1": round(x / 2 - ph, 2)}
    except Exception:
        return None


# ============================================================
# NSE LIVE EXTRAS — circuit limits · pre-open (IEP) · HTF trend
# ============================================================
def _nse_open():
    import http.cookiejar, urllib.request
    h = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"),
         "Accept": "application/json, text/plain, */*", "Accept-Language": "en-US,en;q=0.9"}
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.open(urllib.request.Request("https://www.nseindia.com", headers=h), timeout=8).read()
    return op, h


def _num(x):
    try:
        s = str(x).replace(",", "").strip()
        return float(s) if s not in ("", "-", "None") else None
    except Exception:
        return None


@st.cache_data(ttl=120, show_spinner=False)
def get_nse_quote(sym):
    if sym.startswith("^"):
        return None
    ns = sym.replace(".NS", "").replace(".BO", "").upper()
    try:
        import json, urllib.request
        op, h = _nse_open()
        h = {**h, "Referer": f"https://www.nseindia.com/get-quotes/equity?symbol={ns}"}
        url = f"https://www.nseindia.com/api/quote-equity?symbol={ns}"
        raw = op.open(urllib.request.Request(url, headers=h), timeout=8).read().decode("utf-8", "ignore")
        d = json.loads(raw)
        pi = d.get("priceInfo", {}) or {}
        pm = d.get("preOpenMarket", {}) or {}
        prev = _num(pi.get("previousClose"))
        ltp = _num(pi.get("lastPrice"))
        uc = _num(pi.get("upperCP")); lc = _num(pi.get("lowerCP"))
        band = str(pi.get("pPriceBand", "")).strip()
        iep = _num(pm.get("IEP"))
        pchg = _num(pm.get("Change"))
        ppct = _num(pm.get("perChange"))
        whl = pi.get("weekHighLow", {}) or {}
        wk_hi = _num(whl.get("max")); wk_lo = _num(whl.get("min"))
        if iep and pchg is None and prev:
            pchg = round(iep - prev, 2); ppct = round((iep - prev) / prev * 100, 2)
        no_band = band.lower().startswith("no") or band == ""
        band_num = None if no_band else _num(band)

        def tick(x):
            return round(round(x / 0.05) * 0.05, 2) if x else x

        upper = lower = None
        if not no_band and prev and band_num:
            upper_calc = tick(prev * (1 + band_num / 100))
            lower_calc = tick(prev * (1 - band_num / 100))
            upper = uc if (uc and abs(uc - upper_calc) / upper_calc < 0.02) else upper_calc
            lower = lc if (lc and abs(lc - lower_calc) / lower_calc < 0.02) else lower_calc
        elif not no_band:
            upper, lower = uc, lc
            if uc is None and lc is None:
                no_band = True
        return {
            "prev": prev, "upper": upper, "lower": lower,
            "band": "No band" if no_band else (f"{band_num:g}%" if band_num else band),
            "no_band": no_band, "iep": iep, "iep_chg": pchg, "iep_pct": ppct,
            "wk_hi": wk_hi, "wk_lo": wk_lo, "ltp": ltp,
        }
    except Exception:
        return None


@st.cache_data(ttl=180, show_spinner=False)
def htf_trend(sym, iv):
    nxt = {"1m": ("15m", "15-min"), "5m": ("1h", "1-hour"), "15m": ("1h", "1-hour"),
           "30m": ("1d", "daily"), "1h": ("1d", "daily"), "1d": ("1wk", "weekly")}
    per = {"15m": "1mo", "1h": "3mo", "1d": "1y", "1wk": "2y"}
    hi, lbl = nxt.get(iv, ("1d", "daily"))
    try:
        d = yf.Ticker(sym).history(period=per.get(hi, "3mo"), interval=hi).dropna()
        if len(d) < 55:
            return {"trend": None, "label": lbl}
        c = d["Close"]
        e20 = ta.trend.ema_indicator(c, 20); e50 = ta.trend.ema_indicator(c, 50)
        p = float(c.iloc[-1]); a = float(e20.iloc[-1]); b = float(e50.iloc[-1])
        t = "UP" if (a > b and p > a) else "DOWN" if (a < b and p < a) else "FLAT"
        return {"trend": t, "label": lbl}
    except Exception:
        return {"trend": None, "label": lbl}


# ============================================================
# DAILY SERIES FOR LEVELS / ML
# ============================================================
@st.cache_data(ttl=1800, show_spinner=False)
def _daily_for_ml(sym, years="2y"):
    try:
        d = yf.Ticker(sym).history(period=years, interval="1d").dropna()
        return d if len(d) >= 120 else None
    except Exception:
        return None


def get_sr_fib(sym, price, atr, circuit=None):
    try:
        daily = _daily_for_ml(sym)
        if daily is None or len(daily) < 20:
            daily = yf.Ticker(sym).history(period="6mo", interval="1d").dropna()
        if daily is None or len(daily) < 5:
            return None
        daily = daily[daily['Low'] > 0].copy()
        rng_ok = (daily['High'] - daily['Low']) < daily['Close'] * 0.5
        if rng_ok.sum() >= len(daily) * 0.7:
            daily = daily[rng_ok]
        ph = float(daily['High'].iloc[-1]); pl = float(daily['Low'].iloc[-1])
        pc = float(daily['Close'].iloc[-1])
        prev_close = float(daily['Close'].iloc[-2]) if len(daily) >= 2 else pc
        gap_pct = (price - prev_close) / prev_close * 100 if prev_close > 0 else 0
        wk = daily.tail(252)
        hi52 = float(wk['High'].max()); lo52 = float(wk['Low'].min())
        sw5_hi = float(daily['High'].tail(5).max());  sw5_lo = float(daily['Low'].tail(5).min())
        sw20_hi = float(daily['High'].tail(20).max()); sw20_lo = float(daily['Low'].tail(20).min())
        sw20_lo = max(sw20_lo, lo52); sw20_hi = min(sw20_hi, hi52)
        pivots = calc_all_pivots(ph, pl, pc)
        pvt = pivots['Standard']
        fib_levels, fib_ext = calc_fibonacci(sw20_hi, sw20_lo)
        raw = [
            ("52W HIGH", hi52, "R"), ("R3", pvt['R3'], "R"), ("R2", pvt['R2'], "R"),
            ("20D HIGH", sw20_hi, "R"), ("PREV HIGH", ph, "R"), ("5D HIGH", sw5_hi, "R"),
            ("R1", pvt['R1'], "R"), ("PIVOT", pvt['PP'], "P"), ("S1", pvt['S1'], "S"),
            ("5D LOW", sw5_lo, "S"), ("PREV LOW", pl, "S"), ("20D LOW", sw20_lo, "S"),
            ("S2", pvt['S2'], "S"), ("S3", pvt['S3'], "S"), ("52W LOW", lo52, "S"),
        ]
        if circuit and circuit.get("upper"):
            raw.append(("UPPER CIRCUIT", circuit["upper"], "R"))
        if circuit and circuit.get("lower"):
            raw.append(("LOWER CIRCUIT", circuit["lower"], "S"))
        levels = []
        for nm, lp, tp0 in raw:
            if lp is None or lp <= 0:
                continue
            if lp < lo52 and tp0 == "S" and ("52W" not in nm and "CIRCUIT" not in nm):
                continue
            tp = "P" if tp0 == "P" else ("R" if lp > price else "S")
            dist = round((lp - price) / price * 100, 2) if price > 0 else 0
            levels.append({'name': nm, 'price': round(float(lp), 2), 'type': tp, 'dist': dist})
        levels.sort(key=lambda x: x['price'], reverse=True)
        deduped = []
        for l in levels:
            if deduped and abs(deduped[-1]['price'] - l['price']) / price < 0.0025:
                deduped[-1]['name'] = deduped[-1]['name'] + " / " + l['name']
                continue
            deduped.append(l)
        levels = deduped
        above = [l for l in levels if l['price'] > price]
        below = [l for l in levels if l['price'] < price]
        nr = min(above, key=lambda x: x['price']) if above else None
        ns = max(below, key=lambda x: x['price']) if below else None
        return {
            'levels': levels, 'pvt': pvt, 'pivots': pivots,
            'prev_close': round(prev_close, 2), 'gap_pct': round(gap_pct, 2),
            'nr': nr, 'ns': ns,
            'ph': ph, 'pl': pl, 'pc': pc, 'sw5_hi': sw5_hi, 'sw5_lo': sw5_lo,
            'sw20_hi': sw20_hi, 'sw20_lo': sw20_lo, 'hi52': round(hi52, 2), 'lo52': round(lo52, 2),
            'hi_all': hi52, 'lo_all': lo52,
            'fib_levels': fib_levels, 'fib_ext': fib_ext, 'daily': daily,
        }
    except Exception:
        return None


# ============================================================
# TRADE PLAN GENERATOR
# ============================================================
def make_plan(price, atr, sr, sig, session='closed', circuit=None):
    prev_close = sr['prev_close'] if sr else price
    gap_pct = sr['gap_pct'] if sr else 0
    ns_price = sr['ns']['price'] if sr and sr['ns'] else round(price - atr * 1.5, 2)
    nr_price = sr['nr']['price'] if sr and sr['nr'] else round(price + atr * 2.0, 2)
    big_gap_up = gap_pct > 2.0
    big_gap_dn = gap_pct < -2.0
    near_resist = sr and sr['nr'] and abs(sr['nr']['dist']) < 0.8
    is_buy = 'BUY' in sig
    is_sell = 'SELL' in sig

    if big_gap_up and is_buy:
        sit = "GAP_UP"; act = "⚠️ GAP UP — WAIT FOR PULLBACK"
        buy_at = round(prev_close * 1.005, 2); sl = round(prev_close * 0.985, 2); ac = "#ea580c"
        msg = f"Gapped {gap_pct:+.1f}% from ₹{prev_close:.2f}. Don't chase! Wait for ₹{buy_at:.2f}"
        timing = "Watch till 10:30 AM. No pullback → SKIP today"
    elif big_gap_dn:
        sit = "GAP_DN"; act = "⛔ GAP DOWN — AVOID"
        buy_at = round(ns_price * 1.01, 2); sl = round(ns_price * 0.98, 2); ac = "#dc2626"
        msg = f"Fell {gap_pct:.1f}%. Risky. Support: ₹{ns_price:.2f}"
        timing = "Wait till 11 AM. If support holds → reconsider"
    elif near_resist and is_buy and 'STRONG' not in sig:
        sit = "NEAR_R"; act = "🚧 NEAR RESISTANCE — WAIT BREAKOUT"
        buy_at = round(nr_price * 1.002, 2); sl = round(nr_price * 0.985, 2); ac = "#d97706"
        msg = f"Resistance ₹{nr_price:.2f} is only {abs(sr['nr']['dist']):.1f}% away"
        timing = f"Buy ONLY if 15-min candle closes ABOVE ₹{nr_price:.2f} with volume"
    elif is_buy:
        sup_dist = (price - ns_price) / price * 100 if price > 0 else 0
        if sup_dist > 2.5:
            sit = "BUY_DIP"; act = "⏳ BUY ON PULLBACK TO SUPPORT"
            buy_at = round(ns_price * 1.003, 2)
            sl = round(ns_price * 0.992, 2)
            ac = "#d97706"
            msg = (f"Price ₹{price:.2f} is {sup_dist:.1f}% above support — buying here needs a wide stop. "
                   f"Place a BUY near support ₹{buy_at:.2f}; it fills only if price dips there. Stop ₹{sl:.2f}.")
            timing = "Set a buy-limit at support. If price never dips there, skip it — don't chase."
        else:
            sit = "BUY_NOW"; act = "✅ STRONG BUY NOW" if 'STRONG' in sig else "✅ BUY NOW"
            buy_at = round(price, 2)
            sl = round(max(ns_price * 0.992, price - atr * 1.5), 2); ac = "#16a34a"
            msg = "Price is near support — buy at market with the stop just below support."
            timing = "Enter 9:30 AM–2:30 PM | Best: 9:45–11:00 AM"
    elif is_sell:
        sit = "SELL"; act = "⛔ DO NOT BUY — SELL SIGNAL"
        buy_at = round(price, 2); sl = round(price - atr * 1.5, 2); ac = "#dc2626"
        msg = "Selling pressure. Wrong time to buy."
        timing = "Wait for reversal. Check tomorrow."
    else:
        sit = "WAIT"; act = "⏸ NEUTRAL — WAIT FOR SIGNAL"
        buy_at = round(price * 0.997, 2); sl = round(ns_price * 0.992, 2); ac = "#d97706"
        msg = "No clear direction yet."
        timing = "Check again in 1-2 hours."

    risk = max(buy_at - sl, buy_at * 0.003)
    t1 = round(buy_at + risk * 1.0, 2)
    t2 = round(buy_at + risk * 2.0, 2)
    t3 = round(buy_at + risk * 3.5, 2)
    if sr and sr.get('levels'):
        ra = sorted([l['price'] for l in sr['levels']
                     if l['type'] == 'R' and l['price'] > buy_at * 1.003])
        if len(ra) >= 1: t1 = round(ra[0], 2)
        if len(ra) >= 2: t2 = round(ra[1], 2)
        if len(ra) >= 3: t3 = round(ra[2], 2)
    t2 = max(t2, t1)
    t3 = max(t3, t2)
    if circuit and circuit.get("upper"):
        t1 = min(t1, circuit["upper"]); t2 = min(t2, circuit["upper"]); t3 = min(t3, circuit["upper"])
    if circuit and circuit.get("lower"):
        sl = max(sl, circuit["lower"])

    if session == 'open':
        now = now_ist()   # v14 FIX: cloud servers run on UTC — was datetime.now()
        mins_left = max(0, (15 * 60 + 30) - (now.hour * 60 + now.minute))
        hh = mins_left // 60; mm2 = mins_left % 60
        left_txt = f"{hh}h {mm2}m left today"
        t = now.time()
        when = f"TODAY (live · {left_txt})"
        head = f"📈 TODAY'S PLAN — {left_txt}"
        if t < dtime(9, 45):
            phase = "OPENING"
            timing = "First 30 min is volatile — wait for the 9:45 candle before entering."
        elif t < dtime(11, 30):
            phase = "MORNING"
            timing = f"Prime window. Full setup valid — T1→T2→T3 all in play ({left_txt})."
        elif t < dtime(13, 30):
            phase = "MIDDAY"
            timing = f"Midday lull — moves are slower. T1–T2 realistic today ({left_txt})."
        elif t < dtime(14, 45):
            phase = "LATE"
            timing = (f"Only ~{left_txt}. Take it ONLY on strong momentum — aim T1, maybe T2. "
                      f"T3 unlikely today. Tighten stop, square off by 3:15.")
            act = act + " · quick move only"
        else:
            phase = "CLOSING"
            timing = "Too late for a fresh intraday entry — square off open trades by 3:15. Plan this for tomorrow instead."
            if 'BUY' in sig:
                act = "🕒 TOO LATE TODAY — PLAN FOR TOMORROW"
                ac = "#fbbf24"
                msg = "Signal is fine, but not enough time left for a fresh intraday trade. Watch it at tomorrow's open."
    elif session == 'pre':
        when = "TODAY (pre-open)"
        head = "🌅 TODAY'S PLAN — market opens 9:15 AM"
        phase = "PREOPEN"
        timing = "Market opens at 9:15 AM today. Let the 9:15–9:30 first candle print, then act on the level below — don't buy at the very open."
    else:
        when = "TOMORROW"
        head = "🌙 TOMORROW'S PLAN — for the next session"
        phase = "NEXTDAY"
        if sit == 'BUY_NOW':
            timing = "Tomorrow: wait for the 9:30 first candle, then buy near the level below."

    sl_pct = round((buy_at - sl) / buy_at * 100, 2) if buy_at > 0 else 0
    t1p = round((t1 - buy_at) / buy_at * 100, 2) if buy_at > 0 else 0
    t2p = round((t2 - buy_at) / buy_at * 100, 2) if buy_at > 0 else 0
    t3p = round((t3 - buy_at) / buy_at * 100, 2) if buy_at > 0 else 0
    rr = round((t2 - buy_at) / max(buy_at - sl, 0.01), 1)
    return {
        'sit': sit, 'act': act, 'ac': ac, 'buy_at': buy_at, 'sl': sl,
        't1': t1, 't2': t2, 't3': t3, 'risk': round(risk, 2), 'msg': msg, 'timing': timing,
        'gap_pct': gap_pct, 'prev_close': prev_close, 'nr_price': nr_price, 'ns_price': ns_price,
        'sl_pct': sl_pct, 't1p': t1p, 't2p': t2p, 't3p': t3p, 'rr': rr,
        'when': when, 'head': head, 'phase': phase,
    }


# ============================================================
# CORE ANALYSIS ENGINE — 12 INDICATORS (pure function on a df)
# ============================================================
def compute_signals(df_in):
    """All indicator maths from a raw OHLCV dataframe. Used by BOTH the
    single-stock analysis and the 500-stock dashboard (bulk data)."""
    try:
        if df_in is None or df_in.empty or len(df_in) < 10:
            return None
        df = df_in.copy()
        df.columns = [str(c).title() for c in df.columns]
        if not {'Open', 'High', 'Low', 'Close'}.issubset(df.columns):
            return None
        if 'Volume' not in df.columns:
            df['Volume'] = 0
        df = df.dropna(subset=['Open', 'High', 'Low', 'Close'])
        if len(df) < 10:
            return None
    except Exception:
        return None
    n = len(df)
    try:
        for w, c in [(9, "E9"), (20, "E20"), (50, "E50"), (200, "E200")]:
            df[c] = ta.trend.ema_indicator(df['Close'], w) if n > w else np.nan
        for w, c in [(20, "S20"), (50, "S50")]:
            df[c] = ta.trend.sma_indicator(df['Close'], w) if n > w else np.nan
        df['RSI'] = ta.momentum.rsi(df['Close'], 14) if n >= 15 else np.nan
        if n >= 35:
            mc = ta.trend.MACD(df['Close'])
            df['MACD'] = mc.macd(); df['MS'] = mc.macd_signal(); df['MH'] = mc.macd_diff()
        else:
            df['MACD'] = df['MS'] = df['MH'] = np.nan
        if n >= 20:
            bb = ta.volatility.BollingerBands(df['Close'], 20, 2)
            df['BBU'] = bb.bollinger_hband(); df['BBL'] = bb.bollinger_lband()
            df['BBM'] = bb.bollinger_mavg(); df['BBW'] = bb.bollinger_wband(); df['BBP'] = bb.bollinger_pband()
        else:
            df['BBU'] = df['BBL'] = df['BBM'] = df['BBW'] = df['BBP'] = np.nan
        if n >= 14:
            sto = ta.momentum.StochasticOscillator(df['High'], df['Low'], df['Close'])
            df['SK'] = sto.stoch(); df['SD'] = sto.stoch_signal()
        else:
            df['SK'] = df['SD'] = np.nan
        if n >= 30:
            adx_i = ta.trend.ADXIndicator(df['High'], df['Low'], df['Close'], 14)
            df['ADX'] = adx_i.adx(); df['DMP'] = adx_i.adx_pos(); df['DMN'] = adx_i.adx_neg()
        else:
            df['ADX'] = df['DMP'] = df['DMN'] = np.nan
        df['ATR'] = (ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], 14)
                     if n >= 15 else df['High'] - df['Low'])
        df['MFI'] = (ta.volume.MFIIndicator(df['High'], df['Low'], df['Close'], df['Volume'], 14).money_flow_index()
                     if n >= 14 else np.nan)
        df['CCI'] = (ta.trend.CCIIndicator(df['High'], df['Low'], df['Close'], 20).cci() if n >= 20 else np.nan)
        df['WR'] = (ta.momentum.WilliamsRIndicator(df['High'], df['Low'], df['Close'], 14).williams_r()
                    if n >= 14 else np.nan)
        df['ROC'] = (ta.momentum.ROCIndicator(df['Close'], 12).roc() if n >= 12 else np.nan)
        try:
            # VWAP now resets EVERY MORNING (Gemini's one true catch, 23
            # Oct): cumsum is grouped by calendar date, so yesterday's
            # session never bleeds into today's level. Board scoring
            # only — no alert rule reads VWAP.
            _tp = df['Volume'] * (df['High'] + df['Low'] + df['Close']) / 3
            _day = df.index.date
            df['VWAP'] = (_tp.groupby(_day).cumsum()
                          / df['Volume'].groupby(_day).cumsum())
        except Exception:
            df['VWAP'] = np.nan
        df['STD20'] = df['Close'].rolling(20).std() if n >= 20 else np.nan
        if n >= 15:
            h2 = (df['High'] + df['Low']) / 2
            atr_ = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], 10)
            ub = (h2 + 3 * atr_).values; lb = (h2 - 3 * atr_).values
            cl_ = df['Close'].values.astype(float)
            # v14 FIX: proper Supertrend — final bands ratchet, and the
            # direction flips when the close crosses the FINAL band. (The old
            # loop compared against raw ±3·ATR bands of the previous bar, so it
            # almost never flipped: a stock down 54% still read "BUY".)
            sv = [np.nan] * n; sd = [0] * n
            fub = [np.nan] * n; flb = [np.nan] * n
            for i in range(10, n):
                if np.isnan(ub[i]) or np.isnan(lb[i]):
                    continue
                if i == 10 or np.isnan(fub[i-1]):
                    fub[i] = ub[i]; flb[i] = lb[i]
                    sd[i] = 1 if cl_[i] >= h2.iloc[i] else -1
                else:
                    fub[i] = ub[i] if (ub[i] < fub[i-1] or cl_[i-1] > fub[i-1]) else fub[i-1]
                    flb[i] = lb[i] if (lb[i] > flb[i-1] or cl_[i-1] < flb[i-1]) else flb[i-1]
                    if sd[i-1] == 1:
                        sd[i] = -1 if cl_[i] < flb[i] else 1
                    else:
                        sd[i] = 1 if cl_[i] > fub[i] else -1
                sv[i] = flb[i] if sd[i] == 1 else fub[i]
            df['ST'] = sv; df['STD'] = sd
        else:
            df['ST'] = np.nan; df['STD'] = 0
        df['OBV'] = ta.volume.OnBalanceVolumeIndicator(df['Close'], df['Volume']).on_balance_volume() if n >= 5 else np.nan
    except Exception:
        pass

    lat = df.iloc[-1]; prev = df.iloc[-2] if n >= 2 else lat
    price = float(lat['Close']); g = lambda c: safe(lat.get(c))
    bs = 0; ss = 0; sigs = []

    rsi = g('RSI')
    if not np.isnan(rsi):
        if rsi < 25: bs += 22; t = "Deep Oversold — Strong BUY"
        elif rsi < 35: bs += 15; t = "Oversold — BUY zone"
        elif rsi < 45: bs += 8; t = "Lean BUY"
        elif rsi < 55: bs += 4; ss += 4; t = "Neutral"
        elif rsi < 65: ss += 8; t = "Lean SELL"
        elif rsi < 75: ss += 15; t = "Overbought — SELL zone"
        else: ss += 22; t = "Extreme Overbought — Strong SELL"
        sigs.append({'n': 'RSI', 'v': f"{rsi:.1f}", 't': t, 'b': rsi < 50, 'cat': 'Momentum'})

    mv = g('MACD'); ms_ = g('MS'); mh = g('MH'); pmh = safe(prev.get('MH'))
    if not np.isnan(mv) and not np.isnan(ms_):
        cross_up = (mv > ms_ and not np.isnan(pmh) and not np.isnan(mh) and pmh < 0 < mh)
        cross_dn = (mv < ms_ and not np.isnan(pmh) and not np.isnan(mh) and pmh > 0 > mh)
        if cross_up: bs += 22; t = "🚀 Fresh Bullish Cross — Strong BUY!"
        elif mv > ms_: bs += 12; t = "MACD above Signal — BUY"
        elif cross_dn: ss += 22; t = "🔻 Fresh Bearish Cross — Strong SELL!"
        else: ss += 12; t = "MACD below Signal — SELL"
        sigs.append({'n': 'MACD', 'v': f"{mv:.3f}", 't': t, 'b': mv > ms_, 'cat': 'Trend'})

    ab = be = tot = 0
    for cn in ['E9', 'E20', 'E50', 'S20', 'S50']:
        v = g(cn)
        if not np.isnan(v):
            tot += 1; ab += 1 if price > v else 0; be += 1 if price <= v else 0
    if tot > 0:
        pct = ab / tot
        if pct >= 0.85: bs += 20; t = f"Above all {tot} MAs — Strong BUY"
        elif pct >= 0.60: bs += 13; t = f"Above {ab}/{tot} MAs — BUY"
        elif pct <= 0.15: ss += 20; t = f"Below all {tot} MAs — Strong SELL"
        elif pct <= 0.40: ss += 13; t = f"Below {be}/{tot} MAs — SELL"
        else: bs += 5; ss += 5; t = f"Mixed {ab}/{tot} MAs — Neutral"
        sigs.append({'n': 'Moving Avg', 'v': f"{ab}/{tot}", 't': t, 'b': ab > be, 'cat': 'Trend'})

    bu = g('BBU'); bl = g('BBL'); bw = g('BBW'); bp_val = g('BBP')
    if not np.isnan(bu) and not np.isnan(bl):
        rng = max(bu - bl, 0.01); pos = (price - bl) / rng
        sq = bw < 1.5 if not np.isnan(bw) else False
        if pos < 0.05: bs += 18; t = "At Lower Band — BUY zone"
        elif pos < 0.25: bs += 10; t = "Near Lower Band — Lean BUY"
        elif pos > 0.95: ss += 18; t = "At Upper Band — SELL zone"
        elif pos > 0.75: ss += 10; t = "Near Upper Band — Lean SELL"
        else: bs += 4; ss += 4; t = "Mid Band — Neutral"
        if sq: t += " ⚡ SQUEEZE!"
        sigs.append({'n': 'Bollinger Bands', 'v': f"{pos:.0%}", 't': t, 'b': pos < 0.5, 'cat': 'Volatility'})

    std_ = safe(lat.get('STD'), 0); stv = g('ST')
    if not np.isnan(stv) and std_ != 0:
        if std_ == 1: bs += 20; t = "✅ Supertrend BUY — Uptrend confirmed"
        else: ss += 20; t = "❌ Supertrend SELL — Downtrend confirmed"
        sigs.append({'n': 'Supertrend', 'v': f"₹{stv:.2f}", 't': t, 'b': std_ == 1, 'cat': 'Trend'})

    vw = g('VWAP')
    if not np.isnan(vw):
        pv = (price - vw) / vw * 100
        if pv > 1.0: bs += 12; t = f"Strong above VWAP +{pv:.1f}%"
        elif pv > 0: bs += 7; t = f"Above VWAP +{pv:.1f}%"
        elif pv < -1: ss += 12; t = f"Strong below VWAP {pv:.1f}%"
        else: ss += 7; t = f"Below VWAP {pv:.1f}%"
        sigs.append({'n': 'VWAP', 'v': f"₹{vw:.2f}", 't': t, 'b': price > vw, 'cat': 'Volume'})

    sk = g('SK')
    if not np.isnan(sk):
        if sk < 15: bs += 14; t = "Deep Oversold — Strong BUY"
        elif sk < 25: bs += 9; t = "Oversold — BUY"
        elif sk > 85: ss += 14; t = "Deep Overbought — Strong SELL"
        elif sk > 75: ss += 9; t = "Overbought — SELL"
        else: bs += 3; ss += 3; t = "Neutral zone"
        sigs.append({'n': 'Stochastic', 'v': f"{sk:.1f}", 't': t, 'b': sk < 50, 'cat': 'Momentum'})

    av = g('ADX'); ap = g('DMP'); an = g('DMN')
    if not np.isnan(av) and not np.isnan(ap) and not np.isnan(an):
        strength = "💪 Strong" if av > 30 else "📊 Moderate" if av > 20 else "💤 Weak"
        if ap > an: bs += 10; t = f"Bullish trend — {strength} ADX:{av:.0f}"
        else: ss += 10; t = f"Bearish trend — {strength} ADX:{av:.0f}"
        sigs.append({'n': 'ADX', 'v': f"{av:.1f}", 't': t, 'b': ap > an, 'cat': 'Trend'})

    cci = g('CCI')
    if not np.isnan(cci):
        if cci < -200: bs += 14; t = "Extreme Oversold — Strong BUY"
        elif cci < -100: bs += 8; t = "Oversold — BUY"
        elif cci > 200: ss += 14; t = "Extreme Overbought — Strong SELL"
        elif cci > 100: ss += 8; t = "Overbought — SELL"
        else: bs += 2; ss += 2; t = "Neutral"
        sigs.append({'n': 'CCI', 'v': f"{cci:.0f}", 't': t, 'b': cci < 0, 'cat': 'Momentum'})

    wr = g('WR')
    if not np.isnan(wr):
        if wr < -85: bs += 12; t = "Extremely Oversold — BUY"
        elif wr < -70: bs += 7; t = "Oversold — BUY"
        elif wr > -10: ss += 12; t = "Extremely Overbought — SELL"
        elif wr > -25: ss += 7; t = "Overbought — SELL"
        else: bs += 3; ss += 3; t = "Neutral"
        sigs.append({'n': 'Williams %R', 'v': f"{wr:.1f}", 't': t, 'b': wr < -50, 'cat': 'Momentum'})

    mf = g('MFI')
    if not np.isnan(mf):
        if mf < 20: bs += 12; t = "Strong money inflow — BUY"
        elif mf > 80: ss += 12; t = "Strong money outflow — SELL"
        else: bs += 3; ss += 3; t = "Neutral money flow"
        sigs.append({'n': 'MFI', 'v': f"{mf:.1f}", 't': t, 'b': mf < 50, 'cat': 'Volume'})

    roc = g('ROC')
    if not np.isnan(roc):
        if roc > 5: bs += 8; t = f"Strong positive momentum +{roc:.1f}%"
        elif roc > 0: bs += 4; t = f"Positive momentum +{roc:.1f}%"
        elif roc < -5: ss += 8; t = f"Strong negative momentum {roc:.1f}%"
        else: ss += 4; t = f"Negative momentum {roc:.1f}%"
        sigs.append({'n': 'ROC', 'v': f"{roc:.1f}%", 't': t, 'b': roc > 0, 'cat': 'Momentum'})

    tot2 = bs + ss
    bp = bs / tot2 * 100 if tot2 > 0 else 50
    sp = ss / tot2 * 100 if tot2 > 0 else 50
    conf = round(max(bp, sp), 1)
    if bp >= 80: sig = "STRONG BUY"; sc = "#4ade80"; bg = "sig-buy"
    elif bp >= 68: sig = "BUY"; sc = "#16a34a"; bg = "sig-buy"
    elif bp >= 56: sig = "LEAN BUY"; sc = "#2563eb"; bg = "sig-buy"
    elif sp >= 80: sig = "STRONG SELL"; sc = "#f87171"; bg = "sig-sell"
    elif sp >= 68: sig = "SELL"; sc = "#dc2626"; bg = "sig-sell"
    elif sp >= 56: sig = "LEAN SELL"; sc = "#ea580c"; bg = "sig-sell"
    else: sig = "NEUTRAL"; sc = "#fbbf24"; bg = "sig-wait"

    atr_v = safe(lat.get('ATR'), price * 0.015)
    if atr_v <= 0: atr_v = price * 0.015
    std20 = safe(lat.get('STD20'), price * 0.01)
    vol = float(lat['Volume'])
    avgv = float(df['Volume'].rolling(20).mean().iloc[-1]) if n >= 20 else vol
    vr = round(vol / avgv, 2) if avgv > 0 else 1.0
    hi52 = float(df['High'].max()); lo52 = float(df['Low'].min())
    rng52 = hi52 - lo52
    pos52 = round((price - lo52) / rng52 * 100, 1) if rng52 > 0 else 50

    trend = 'SIDEWAYS'
    if n >= 20:
        r2 = df.tail(20); H = r2['High'].values; L = r2['Low'].values
        sh = []; sl2 = []
        for i in range(2, len(H) - 2):
            if H[i] > max(H[i-1], H[i-2], H[i+1], H[i+2]): sh.append(float(H[i]))
            if L[i] < min(L[i-1], L[i-2], L[i+1], L[i+2]): sl2.append(float(L[i]))
        hh = len(sh) >= 2 and sh[-1] > sh[-2]; lh = len(sh) >= 2 and sh[-1] < sh[-2]
        hl = len(sl2) >= 2 and sl2[-1] > sl2[-2]; ll = len(sl2) >= 2 and sl2[-1] < sl2[-2]
        if hh and hl: trend = 'UPTREND'
        elif lh and ll: trend = 'DOWNTREND'
        elif hh and ll: trend = 'VOLATILE'

    return {
        'df': df, 'price': price, 'atr': atr_v, 'std20': std20,
        'sig': sig, 'sc': sc, 'bg': bg, 'bp': round(bp, 1), 'sp': round(sp, 1), 'conf': conf,
        'sigs': sigs, 'n_sigs': len(sigs), 'vr': vr, 'vol': vol, 'avgv': avgv,
        'trend': trend, 'pos52': pos52, 'hi52': hi52, 'lo52': lo52, 'lat': lat, 'prev': prev,
        'rsi': rsi, 'vw': vw, 'stv': stv, 'std_': std_,
        'bbu': bu, 'bbl': bl, 'bbw': bw, 'bbp': bp_val,
        'adx': av, 'cci': cci, 'wr': wr, 'mfi': mf,
    }


def run_analysis(sym, iv, per):
    try:
        df = yf.Ticker(sym).history(period=per, interval=iv)
        if df is None or df.empty:
            return None
        df = df.dropna()
    except Exception:
        return None
    return compute_signals(df)


# ============================================================
# PREMIUM CHART — 5 PANELS
# ============================================================
def make_chart(df, name, plan, sr):
    C = {'bg': '#ffffff', 'plot': '#fafbff', 'grid': '#1e293b', 'up': '#16a34a', 'dn': '#dc2626', 'text': '#e2e8f0'}
    fig = make_subplots(rows=5, cols=1, shared_xaxes=True, vertical_spacing=0.018,
                        row_heights=[0.42, 0.15, 0.15, 0.13, 0.15],
                        subplot_titles=[f"📈 {name}  |  Candles + EMAs + BB + Supertrend",
                                        "MACD", "RSI + Stochastic", "ADX + MFI", "Volume + OBV"])
    fig.update_layout(paper_bgcolor=C['bg'], plot_bgcolor=C['plot'], height=1000, showlegend=True,
                      xaxis_rangeslider_visible=False, margin=dict(l=60, r=180, t=55, b=30),
                      font=dict(size=11, color=C['text'], family='Inter'),
                      legend=dict(orientation='h', y=1.03, x=1, xanchor='right',
                                  bgcolor='rgba(255,255,255,0.95)', bordercolor='#1e293b', borderwidth=1))
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                                 name='Price', increasing=dict(line=dict(color=C['up'], width=1), fillcolor='rgba(22,163,74,0.8)'),
                                 decreasing=dict(line=dict(color=C['dn'], width=1), fillcolor='rgba(220,38,38,0.8)')), row=1, col=1)
    for c, clr, lbl, w in [('E9', '#f97316', 'EMA9', 1.4), ('E20', '#eab308', 'EMA20', 1.8), ('E50', '#6366f1', 'EMA50', 2.0)]:
        if c in df.columns:
            s = df[c].dropna()
            if len(s): fig.add_trace(go.Scatter(x=s.index, y=s, name=lbl, line=dict(color=clr, width=w)), row=1, col=1)
    if 'VWAP' in df.columns:
        s = df['VWAP'].dropna()
        if len(s): fig.add_trace(go.Scatter(x=s.index, y=s, name='VWAP', line=dict(color='#a855f7', width=1.8, dash='dot')), row=1, col=1)
    if 'BBU' in df.columns and 'BBL' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['BBU'], name='BB Upper', line=dict(color='rgba(220,38,38,0.4)', width=1, dash='dot')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['BBL'], name='BB Lower', line=dict(color='rgba(22,163,74,0.4)', width=1, dash='dot'),
                                 fill='tonexty', fillcolor='rgba(99,102,241,0.04)'), row=1, col=1)
    if plan:
        for y, clr, txt, dash, lw in [
            (plan['sl'], '#ef4444', f"🛑 SL ₹{plan['sl']:.2f}", 'dash', 2.0),
            (plan['t1'], '#22c55e', f"T1 ₹{plan['t1']:.2f}", 'dot', 1.5),
            (plan['t2'], '#16a34a', f"T2 ₹{plan['t2']:.2f}", 'dash', 2.0),
            (plan['t3'], '#a855f7', f"T3 ₹{plan['t3']:.2f}", 'dashdot', 1.5),
            (plan['buy_at'], '#3b82f6', f"📌 BUY ₹{plan['buy_at']:.2f}", 'solid', 2.2)]:
            fig.add_hline(y=y, line_dash=dash, line_color=clr, line_width=lw, annotation_text=txt,
                          annotation_position='right', annotation_font=dict(color=clr, size=10), row=1, col=1)
    if sr and sr.get('levels'):
        for lvl in sr['levels']:
            if abs(lvl['dist']) < 5:
                clr = 'rgba(220,38,38,0.2)' if lvl['type'] == 'R' else 'rgba(22,163,74,0.2)' if lvl['type'] == 'S' else 'rgba(245,158,11,0.2)'
                fig.add_hline(y=lvl['price'], line_dash='dot', line_color=clr, line_width=0.8, row=1, col=1)
    if 'ST' in df.columns:
        for dv, clr, sm in [(1, '#16a34a', 'triangle-up'), (-1, '#dc2626', 'triangle-down')]:
            pts = df[df['STD'] == dv]['ST'].dropna()
            if len(pts): fig.add_trace(go.Scatter(x=pts.index, y=pts, mode='markers', name=f"ST {'Buy' if dv==1 else 'Sell'}",
                                                  marker=dict(color=clr, size=6, symbol=sm)), row=1, col=1)
    if 'MACD' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], name='MACD', line=dict(color='#2563eb', width=1.6)), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MS'], name='Signal', line=dict(color='#f97316', width=1.6)), row=2, col=1)
        hc = ['#16a34a' if v >= 0 else '#dc2626' for v in df['MH'].fillna(0)]
        fig.add_trace(go.Bar(x=df.index, y=df['MH'], name='Histogram', marker_color=hc, opacity=0.75), row=2, col=1)
        fig.add_hline(y=0, line_dash='dash', line_color='#cbd5e1', row=2, col=1)
    if 'RSI' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'].fillna(50), name='RSI', line=dict(color='#8b5cf6', width=2.0)), row=3, col=1)
    if 'SK' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['SK'].fillna(50), name='Stoch %K', line=dict(color='#f97316', width=1.3, dash='dot')), row=3, col=1)
    for y, clr in [(70, 'rgba(220,38,38,0.4)'), (30, 'rgba(22,163,74,0.4)'), (50, 'rgba(0,0,0,0.1)')]:
        fig.add_hline(y=y, line_dash='dash', line_color=clr, line_width=0.8, row=3, col=1)
    if 'ADX' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['ADX'].fillna(0), name='ADX', line=dict(color='#0ea5e9', width=1.8)), row=4, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['DMP'].fillna(0), name='+DI', line=dict(color='#16a34a', width=1.2, dash='dot')), row=4, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['DMN'].fillna(0), name='-DI', line=dict(color='#dc2626', width=1.2, dash='dot')), row=4, col=1)
    if 'MFI' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['MFI'].fillna(50), name='MFI', line=dict(color='#a855f7', width=1.3, dash='dashdot')), row=4, col=1)
    vc = ['#16a34a' if c >= o else '#dc2626' for c, o in zip(df['Close'], df['Open'])]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='Volume', marker_color=vc, opacity=0.8), row=5, col=1)
    if 'OBV' in df.columns:
        obv = df['OBV'].dropna()
        if len(obv): fig.add_trace(go.Scatter(x=obv.index, y=obv, name='OBV', line=dict(color='#0ea5e9', width=1.5)), row=5, col=1)
    for i in range(1, 6):
        fig.update_xaxes(gridcolor=C['grid'], row=i, col=1, showgrid=True)
        fig.update_yaxes(gridcolor=C['grid'], row=i, col=1, showgrid=True)
    for i in range(1, 5):
        fig.update_xaxes(showticklabels=False, row=i, col=1)
    return fig


def pivot_table_html(levels_dict, price):
    rows = sorted(levels_dict.items(), key=lambda x: x[1], reverse=True)
    html = ""
    for lbl, lp in rows:
        dist = round((lp - price) / price * 100, 2) if price > 0 else 0
        is_cur = abs(dist) < 0.4
        if is_cur:
            css, clr, tag = "lv-cur", "#3b82f6", "📍 nearest to price"
        elif lbl.startswith('R'):
            css, clr, tag = "lv-r", "#ef4444", f"+{abs(dist):.1f}% above"
        elif lbl.startswith('S'):
            css, clr, tag = "lv-s", "#22c55e", f"{abs(dist):.1f}% below"
        else:
            css, clr, tag = "lv-p", "#f59e0b", f"{dist:+.1f}%"
        typ = "RESISTANCE" if lbl.startswith('R') else "SUPPORT" if lbl.startswith('S') else "PIVOT"
        html += (f"<div class='{css}'><div style='display:flex;justify-content:space-between;align-items:center;'>"
                 f"<div><span style='color:{clr};font-weight:700;font-size:13px;'>{lbl} — {typ}</span>"
                 f"<span style='color:#64748b;font-size:11px;margin-left:8px;'>{tag}</span></div>"
                 f"<div style='font-size:20px;font-weight:900;color:#e2e8f0;'>₹{lp:,.2f}</div></div></div>")
    return html


# ============================================================
# ADVANCED ANALYTICS — ML · regime · volume profile · patterns
#   · risk metrics · probability  (all fail-safe)
# ============================================================
@st.cache_data(ttl=1800, show_spinner=False)
def ml_predict(sym, price):
    try:
        from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
        from sklearn.linear_model import LinearRegression
    except Exception:
        return {"error": "scikit-learn not installed"}
    d = _daily_for_ml(sym)
    if d is None:
        return None
    try:
        d = d.copy()
        d['ret1'] = d['Close'].pct_change()
        d['ret5'] = d['Close'].pct_change(5)
        d['rsi'] = ta.momentum.rsi(d['Close'], 14)
        d['volat'] = d['ret1'].rolling(10).std()
        d['mom'] = d['Close'] / d['Close'].shift(10) - 1
        d['volr'] = d['Volume'] / d['Volume'].rolling(20).mean()
        d['ma20'] = d['Close'] / ta.trend.sma_indicator(d['Close'], 20) - 1
        d['ma50'] = d['Close'] / ta.trend.sma_indicator(d['Close'], 50) - 1
        d['macd'] = ta.trend.MACD(d['Close']).macd_diff()
        feats = ['ret1', 'ret5', 'rsi', 'volat', 'mom', 'volr', 'ma20', 'ma50', 'macd']
        horizons = [1, 3, 5, 10]
        out = {}
        for h in horizons:
            d['tgt'] = d['Close'].shift(-h) / d['Close'] - 1
            data = d.dropna(subset=feats + ['tgt'])
            if len(data) < 80:
                continue
            X = data[feats].values; y = data['tgt'].values
            sp = int(len(X) * 0.8)
            Xtr, Xte, ytr, yte = X[:sp], X[sp:], y[:sp], y[sp:]
            mdls = {"RF": RandomForestRegressor(n_estimators=60, max_depth=6, random_state=1, n_jobs=-1),
                    "GB": GradientBoostingRegressor(n_estimators=60, max_depth=3, random_state=1),
                    "LR": LinearRegression()}
            last = d[feats].iloc[[-1]].values
            preds, accs, te_preds = {}, {}, {}
            for nm, mdl in mdls.items():
                mdl.fit(Xtr, ytr)
                pt = mdl.predict(Xte)
                te_preds[nm] = pt
                accs[nm] = float(np.mean(np.sign(pt) == np.sign(yte))) if len(yte) else 0.5
                preds[nm] = float(mdl.predict(last)[0])
            wsum = sum(max(a, 0.01) for a in accs.values())
            ens = sum(preds[k] * max(accs[k], 0.01) for k in preds) / wsum
            ens_te = sum(te_preds[k] * max(accs[k], 0.01) for k in te_preds) / wsum
            resid = float(np.std(yte - ens_te)) if len(yte) else 0.02
            acc = float(np.mean(np.sign(ens_te) == np.sign(yte))) if len(yte) else 0.5
            pred_price = price * (1 + ens)
            lo = price * (1 + ens - 1.96 * resid); hi = price * (1 + ens + 1.96 * resid)
            out[h] = {"ret": ens * 100, "price": pred_price, "lo": lo, "hi": hi,
                      "acc": acc * 100, "dir": "UP" if ens > 0 else "DOWN",
                      "model_acc": {k: round(v * 100, 1) for k, v in accs.items()}}
        return out or None
    except Exception:
        return None


@st.cache_data(ttl=1800, show_spinner=False)
def ema200_filter(sym, price):
    d = _daily_for_ml(sym)
    if d is None or len(d) < 60:
        return None
    try:
        c = d['Close']
        e200 = ta.trend.ema_indicator(c, 200) if len(c) >= 200 else ta.trend.ema_indicator(c, min(len(c)-1, 150))
        e50 = ta.trend.ema_indicator(c, 50)
        n200 = float(e200.iloc[-1]); n50 = float(e50.iloc[-1])
        approx = len(c) < 200
        dist = (price - n200) / n200 * 100 if n200 else 0
        above = price > n200
        golden = n50 > n200
        near = abs(dist) < 1.2
        slope_up = float(e200.iloc[-1]) > float(e200.iloc[-6]) if len(e200) >= 6 else True
        if above and golden and slope_up:
            verdict, vc, ok = "BULL STRUCTURE — longs favoured", "#4ade80", True
        elif above and not golden:
            verdict, vc, ok = "Above 200 EMA but no golden cross — cautious longs", "#2563eb", True
        elif above:
            verdict, vc, ok = "Above 200 EMA — longs allowed", "#16a34a", True
        else:
            verdict, vc, ok = "BELOW 200 EMA — bear structure, AVOID longs", "#dc2626", False
        return {"ema200": round(n200, 2), "ema50": round(n50, 2), "dist": round(dist, 2),
                "above": above, "golden": golden, "near": near, "slope_up": slope_up,
                "verdict": verdict, "vc": vc, "ok": ok, "approx": approx}
    except Exception:
        return None


def entry_timing(res, df, sr, ema2=None):
    price = res['price']
    g = lambda k: res.get(k, np.nan)
    warns = []; goods = []; score = 0
    rsi = g('rsi')
    if not np.isnan(rsi):
        if rsi > 75: warns.append("RSI very overbought (>75)"); score -= 2
        elif rsi > 68: warns.append("RSI overbought"); score -= 1
        elif rsi < 40: goods.append("RSI has room to rise"); score += 1
    d = df.tail(30)
    hi = float(d['High'].max()); lo = float(d['Low'].min()); rng = max(hi - lo, 1e-9)
    pos = (price - lo) / rng
    if pos > 0.85: warns.append(f"Price at top of recent range ({pos:.0%}) — late"); score -= 2
    elif pos < 0.35: goods.append("Price in lower part of range"); score += 1
    vw = g('vw')
    if not np.isnan(vw) and vw > 0:
        vd = (price - vw) / vw * 100
        if vd > 2.5: warns.append(f"Stretched {vd:.1f}% above VWAP"); score -= 2
        elif vd > 1.2: warns.append(f"{vd:.1f}% above VWAP"); score -= 1
    bbp = g('bbp')
    if not np.isnan(bbp):
        if bbp > 0.95: warns.append("At/above upper Bollinger band"); score -= 2
        elif bbp < 0.15: goods.append("Near lower Bollinger band"); score += 1
    if sr and sr.get('nr') and abs(sr['nr']['dist']) < 1.0:
        warns.append(f"Resistance ₹{sr['nr']['price']:.2f} just above"); score -= 1
    if len(df) >= 15:
        rl = float(df['Low'].tail(15).min())
        run = (price - rl) / rl * 100 if rl > 0 else 0
        if run > 6: warns.append(f"Already ran +{run:.1f}% off recent low — move may be done"); score -= 2
        elif run > 3.5: warns.append(f"Up +{run:.1f}% recently"); score -= 1
    if 'MH' in df.columns:
        mh = df['MH'].dropna()
        if len(mh) >= 3 and mh.iloc[-1] > 0 and mh.iloc[-1] < mh.iloc[-2] < mh.iloc[-3]:
            warns.append("MACD momentum fading (histogram shrinking)"); score -= 1
    try:
        if 'RSI' in df.columns and len(df) >= 20:
            half = df.tail(20)
            a, b = half.iloc[:10], half.iloc[10:]
            if b['High'].max() > a['High'].max() and b['RSI'].max() < a['RSI'].max() - 2:
                warns.append("Bearish divergence (price up, RSI down)"); score -= 2
    except Exception:
        pass
    tr = res['trend']
    if ema2 and not ema2.get('above', True):
        warns.append("Below daily 200 EMA (bear structure)"); score -= 3
    elif ema2 and ema2.get('above') and ema2.get('golden'):
        goods.append("Above 200 EMA + golden cross"); score += 1
    if tr == 'UPTREND':
        if score <= -3:
            stage, q, tone, msg = ("EXTENDED / LATE", "POOR", "warn",
                "Uptrend — but price is overextended. You'd be buying near the top. WAIT for a pullback toward support before entering.")
        elif score <= -1:
            stage, q, tone, msg = ("MID — CAUTION", "CAUTION", "warn",
                "Uptrend is intact but this isn't a fresh entry. Prefer a dip toward support, or size smaller.")
        else:
            stage, q, tone, msg = ("EARLY / FRESH", "GOOD", "buy",
                "Uptrend with room to move — a reasonable entry, ideally near support.")
    elif tr == 'DOWNTREND':
        stage, q, tone, msg = ("DOWNTREND", "AVOID", "sell",
            "Downtrend — don't buy. Wait for a clear bottom and reversal.")
    else:
        if score >= 1:
            stage, q, tone, msg = ("BASING", "WATCH", "wait",
                "No clear trend, but not overextended — watch for a breakout.")
        else:
            stage, q, tone, msg = ("CHOPPY", "WAIT", "wait",
                "No clear trend and stretched — wait for a cleaner setup.")
    return {"stage": stage, "quality": q, "tone": tone, "msg": msg,
            "warns": warns, "goods": goods, "score": score}


# ============================================================
# NEWS + SENTIMENT
# ============================================================
_POS = ["surge", "jump", "gain", "rise", "profit", "beat", "record", "high", "wins",
        "win ", "order", "bag", "bags", "approval", "approved", "upgrade", "buy rating",
        "growth", "rally", "strong", "boost", "acquire", "acquisition", "expansion",
        "dividend", "bonus", "outperform", "target raised", "deal", "contract", "surges", "jumps"]
_NEG = ["fall", "drop", "slump", "loss", "miss", "cut", "fraud", "probe", "penalty",
        "warn", "downgrade", "sell rating", "crash", "decline", "weak", "debt", "default",
        "resign", "layoff", "raid", "ban", "scam", "lawsuit", "recall", "plunge", "slips",
        "falls", "drops", "tumble", "concern", "block", "stake sale", "selloff"]


@st.cache_data(ttl=900, show_spinner=False)
def get_stock_news(sym, limit=7):
    items = []
    try:
        items = yf.Ticker(sym).news or []
    except Exception:
        items = []
    out = []
    for it in items[: limit * 2]:
        try:
            c = it.get("content", it)
            title = c.get("title") or it.get("title")
            if not title:
                continue
            prov = c.get("provider") or {}
            pub = (prov.get("displayName") if isinstance(prov, dict) else None) or it.get("publisher") or "—"
            url = ""
            cu = c.get("canonicalUrl") or c.get("clickThroughUrl")
            if isinstance(cu, dict):
                url = cu.get("url", "")
            url = url or it.get("link", "")
            when = c.get("pubDate") or it.get("providerPublishTime", "")
            t = title.lower()
            pos = sum(1 for w in _POS if w in t)
            neg = sum(1 for w in _NEG if w in t)
            sent = "pos" if pos > neg else "neg" if neg > pos else "neu"
            out.append({"title": title, "pub": pub, "url": url, "when": str(when), "sent": sent})
            if len(out) >= limit:
                break
        except Exception:
            continue
    p = sum(1 for x in out if x["sent"] == "pos")
    n = sum(1 for x in out if x["sent"] == "neg")
    if not out:
        verdict, vc = "No recent news found", "#8fa3bd"
    elif p > n:
        verdict, vc = "NEWS LEANS POSITIVE", "#16a34a"
    elif n > p:
        verdict, vc = "NEWS LEANS NEGATIVE — be careful", "#dc2626"
    else:
        verdict, vc = "NEWS MIXED / NEUTRAL", "#fbbf24"
    return {"items": out, "pos": p, "neg": n, "verdict": verdict, "vc": vc}


@st.cache_data(ttl=600, show_spinner=False)
def fetch_news(sym, limit=8):
    """(from your v13 — kept as-is) Recent headlines, keyword-tagged."""
    out = []
    try:
        items = yf.Ticker(sym).news or []
    except Exception:
        items = []
    POS = ["surge", "jump", "gain", "rise", "profit", "beat", "high", "record", "wins",
           "win", "order", "bag", "bags", "approval", "approved", "upgrade", "buy", "rally",
           "soar", "growth", "strong", "acquire", "acquisition", "deal", "dividend", "bonus"]
    NEG = ["fall", "drop", "slump", "loss", "miss", "cut", "low", "fraud", "probe", "penalty",
           "warn", "downgrade", "sell", "crash", "decline", "weak", "block", "ban", "raid",
           "resign", "default", "debt", "lawsuit", "fine", "recall", "delay"]
    for it in items[:limit * 2]:
        try:
            c = it.get("content", it)
            title = c.get("title") or it.get("title")
            if not title:
                continue
            prov = c.get("provider") or {}
            pub = (prov.get("displayName") if isinstance(prov, dict) else None) or it.get("publisher") or "—"
            cu = c.get("canonicalUrl") or c.get("clickThroughUrl") or {}
            url = cu.get("url", "") if isinstance(cu, dict) else (it.get("link", "") or "")
            when = c.get("pubDate") or it.get("providerPublishTime", "")
            t = title.lower()
            pos = sum(w in t for w in POS); neg = sum(w in t for w in NEG)
            sent = "pos" if pos > neg else "neg" if neg > pos else "neu"
            out.append({"title": title, "pub": pub, "url": url, "when": str(when), "sent": sent})
            if len(out) >= limit:
                break
        except Exception:
            continue
    return out


def summarize_news_sentiment(news):
    """(from your v13 — kept as-is)"""
    if not news:
        return {"label": "No recent news found", "tone": "neu", "pos": 0, "neg": 0, "neu": 0}
    pos = sum(1 for n in news if n["sent"] == "pos")
    neg = sum(1 for n in news if n["sent"] == "neg")
    neu = len(news) - pos - neg
    if pos > neg and pos >= 2:
        label, tone = "📈 Mostly POSITIVE news", "pos"
    elif neg > pos and neg >= 2:
        label, tone = "📉 Mostly NEGATIVE news — be careful", "neg"
    elif pos > neg:
        label, tone = "Slightly positive", "pos"
    elif neg > pos:
        label, tone = "Slightly negative", "neg"
    else:
        label, tone = "Mixed / neutral headlines", "neu"
    return {"label": label, "tone": tone, "pos": pos, "neg": neg, "neu": neu}


# ============================================================
# TRADE JOURNAL — save today's plan, verify it next day
# ============================================================
import json as _json
import os as _os
import uuid as _uuid
# ── 🧑‍🤝‍🧑 MULTI-USER MEMORY ──────────────────────────────────────────────
#   Everyone who opens the app gets their OWN files, so memories never mix:
#   your key lives in the link (?u=yourname). Default key = "main".
#   Set / change it in the 🌙 EOD Review tab ("Your memory name").
def _ukey():
    return "cloud"   # ☁️ CLOUD BACKUP — its own state, fully separate from the VPS


def journal_file():
    return f"trade_journal_{_ukey()}.json"


def snap_file():
    return f"board_snapshots_{_ukey()}.json"


def eod_file():
    return f"eod_results_{_ukey()}.json"


# ── ♾️ RUNTIME PERSISTENCE — analysis keeps running across page refreshes.
#    The run state lives in a FILE (per person), so a browser refresh,
#    phone screen-lock or reconnect AUTO-RESUMES the analysis. Only the
#    ⏹ Stop / 🧹 Clear buttons end it.
def runtime_file():
    return f"runtime_{_ukey()}.json"


def _rt_sanitize(o):
    """Make everything JSON-safe (numpy floats, timestamps, etc.)."""
    if isinstance(o, dict):
        return {str(k): _rt_sanitize(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_rt_sanitize(v) for v in o]
    if isinstance(o, (bool, str)) or o is None:
        return o
    try:
        if isinstance(o, (int, float)):
            return o
        f = float(o)
        return int(f) if f.is_integer() and abs(f) < 1e15 else f
    except Exception:
        return str(o)


def rt_load():
    try:
        if _os.path.exists(runtime_file()):
            with open(runtime_file(), "r", encoding="utf-8") as f:
                d = _json.load(f)
            return d if isinstance(d, dict) else {}
    except Exception:
        pass
    return {}


def rt_save(engine, **kw):
    try:
        d = rt_load()
        d[engine] = {**d.get(engine, {}), **kw}
        with open(runtime_file(), "w", encoding="utf-8") as f:
            _json.dump(_rt_sanitize(d), f)
        return True
    except Exception:
        return False


# ── 🤖 AUTOPILOT — single-pilot lock: ONE session drives each engine ──
# The VPS runs a headless browser (autopilot.service) that keeps the app
# open 24/7 — IT scans, snapshots and sends Telegram RESULTS even when no
# human is watching. Any tab opened later becomes a LIVE READ-ONLY view
# (fresh data, zero duplicate scans/alerts).
def _sid(ss):
    try:
        if "_sid" not in ss:
            ss["_sid"] = _uuid.uuid4().hex[:10]
        return ss["_sid"]
    except Exception:
        return "s0"


def _pilot_ok(engine, ss, stale=240):
    """True if THIS session may drive `engine` (lock free, ours, or stale)."""
    try:
        lock = (rt_load().get(engine) or {}).get("_lock") or {}
        return lock.get("sid") == _sid(ss) or time.time() - (lock.get("ts") or 0) > stale
    except Exception:
        return True


def _pilot_beat(engine, ss):
    """Claim/refresh the pilot lock for this session (on every scan)."""
    try:
        rt_save(engine, _lock={"sid": _sid(ss), "ts": time.time()})
    except Exception:
        pass


def _mv_view_sync(ss):
    _rt = rt_load().get("mv") or {}
    if (_rt.get("last_scan") or 0) > ss.get("mv_last", 0):
        ss["mv_on"] = True
        ss["mv"] = _rt.get("movers") or ss.get("mv")
        ss["mv_last"] = _rt.get("last_scan") or 0
        ss["mv_ts_str"] = _rt.get("ts_str") or ss.get("mv_ts_str")
        if _rt.get("watch"):
            ss["mv_watch"] = _rt["watch"]
            ss["mv_names"] = _rt.get("names") or {}


def _bc_view_sync(ss):
    _rt = rt_load().get("bc") or {}
    if (_rt.get("last_scan") or 0) > ss.get("bc_last", 0):
        ss["bc_on"] = True
        ss["bc"] = _rt.get("bounces") or ss.get("bc")
        ss["bc_last"] = _rt.get("last_scan") or 0
        ss["bc_ts_str"] = _rt.get("ts_str") or ss.get("bc_ts_str")
        if _rt.get("watch"):
            ss["bc_watch"] = _rt["watch"]
            ss["bc_names"] = _rt.get("names") or {}


def _cb_view_sync(ss):
    _rt = rt_load().get("cb") or {}
    if (_rt.get("last_scan") or 0) > ss.get("cb_last", 0):
        ss["cb_on"] = True
        ss["cb"] = _rt.get("combos") or ss.get("cb")
        ss["cb_last"] = _rt.get("last_scan") or 0
        ss["cb_ts_str"] = _rt.get("ts_str") or ss.get("cb_ts_str")
        if _rt.get("watch"):
            ss["cb_watch"] = _rt["watch"]
            ss["cb_names"] = _rt.get("names") or {}
        if _rt.get("src"):
            ss["cb_src"] = _rt["src"]
        if _rt.get("n"):
            ss["cb_n"] = _rt["n"]


def _co_view_sync(ss):
    _rt = rt_load().get("co") or {}
    if (_rt.get("last_scan") or 0) > ss.get("co_last", 0):
        ss["co_on"] = True
        for _k, _rk in (("co_watch", "watch"), ("co_names", "names"), ("co_pos", "pos"),
                        ("co_feed", "feed"), ("co_log", "log")):
            if _rt.get(_rk) is not None:
                ss[_k] = _rt[_rk]
        ss["co_last"] = _rt.get("last_scan") or 0
        ss["co_ts"] = _rt.get("ts_str") or ss.get("co_ts")
        if _rt.get("cap"):
            ss["co_cap"] = _rt["cap"]


# ── 🔔 TELEGRAM ALERTS — free phone push for climb/bounce alerts ──
def tg_file():
    return f"tg_{_ukey()}.json"


def tg_load():
    try:
        if _os.path.exists(tg_file()):
            d = _json.load(open(tg_file(), encoding="utf-8"))
            if isinstance(d, dict) and d.get("token") and d.get("chat"):
                return d
    except Exception:
        pass
    return {"token": TG_DEFAULT_TOKEN, "chat": TG_DEFAULT_CHAT}


def tg_save(token, chat):
    try:
        _json.dump({"token": token, "chat": chat}, open(tg_file(), "w", encoding="utf-8"))
        return True
    except Exception:
        return False


def _esc(s):
    """HTML-escape dynamic text (M&M → M&amp;M) for Telegram HTML mode."""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _tg_post(token, cid, text, html, buttons=None):
    """One raw Telegram post → returns message_id (None if unknown).
    html=True adds parse_mode HTML; buttons = inline keyboard rows."""
    payload = {"chat_id": cid, "text": text[:1000], "disable_web_page_preview": True}
    if html:
        payload["parse_mode"] = "HTML"
    if buttons:
        payload["reply_markup"] = {"inline_keyboard": buttons}
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=_json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    r = _json.loads(urllib.request.urlopen(req, timeout=6).read().decode("utf-8"))
    return ((r.get("result") or {}).get("message_id"))


_TG_SENT = {"day": None, "items": []}     # sent messages (EOD cleaner + morning purge)
try:                                       # 🔄 restart-safe: tracked IDs live on disk,
    _t = _json.load(open(f"tg_sent_{_ukey()}.json", encoding="utf-8"))   # not in memory —
    if isinstance(_t, dict):               # a restart/deploy never orphans messages
        _TG_SENT.update(day=_t.get("day"), items=_t.get("items") or [])
except Exception:
    pass


def _tg_norm_items(d):
    """Normalize tracked items to [cid, mid, date, keep] (old files: [cid, mid])."""
    out = []
    for it in (d.get("items") or []):
        try:
            if len(it) >= 4:
                out.append([str(it[0]), int(it[1]), str(it[2]), 1 if it[3] else 0])
            else:
                out.append([str(it[0]), int(it[1]),
                            str(d.get("day") or now_ist().strftime("%Y-%m-%d")), 0])
        except Exception:
            continue
    return out


def _tg_track(cid, mid, keep=False):
    """Remember EVERY sent message (chat, id, DATE, keep-flag). The cleaners
    delete it later: same-day alerts after close · ALL previous-day messages
    at the next midnight rollover. Restart-safe — IDs live in the file."""
    try:
        if not mid:
            return
        _today = now_ist().strftime("%Y-%m-%d")
        _items = _tg_norm_items(_TG_SENT)   # normalize FIRST — old items keep their own date
        _TG_SENT["day"] = _today
        _TG_SENT["items"] = _items + [[str(cid), int(mid), _today, 1 if keep else 0]]
        _json.dump(_TG_SENT, open(f"tg_sent_{_ukey()}.json", "w", encoding="utf-8"))
    except Exception:
        pass


def _tg_delete(cfg, cid, mid):
    """Delete one Telegram message (quietly)."""
    try:
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{cfg['token']}/deleteMessage",
            data=_json.dumps({"chat_id": cid, "message_id": int(mid)}).encode("utf-8"),
            headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5).read()
        time.sleep(0.05)
        return True
    except Exception:
        return False      # already gone / too old — skip quietly


def tg_daily_cleanup():
    return 0   # 🩹 AUTO-DELETE OFF (user request 25 Sep) — Telegram history STAYS for later review
    """🧹 After close (15:35+): delete TODAY's alert messages (report cards
    and manual tests stay for the evening review). Telegram only allows
    deleting messages < 48h old."""
    try:
        n = now_ist()
        if n.weekday() >= 5:
            return 0
        if not (n.hour > 15 or (n.hour == 15 and n.minute >= 35)):
            return 0
        fn = f"tg_sent_{_ukey()}.json"
        try:
            d = _json.load(open(fn, encoding="utf-8"))
        except Exception:
            d = {}
        today = n.strftime("%Y-%m-%d")
        if d.get("cleanup_day") == today:
            return 0
        cfg = tg_load()
        if not cfg.get("token"):
            return 0
        items = _tg_norm_items(d)
        keep_items, deleted = [], 0
        for cid, mid, dstr, keep in items[:300]:
            if dstr == today and not keep:
                if _tg_delete(cfg, cid, mid):
                    deleted += 1
            else:
                keep_items.append([cid, mid, dstr, keep])
        _TG_SENT.update(day=today, items=list(keep_items))
        try:
            _json.dump({"cleanup_day": today, "purge_day": d.get("purge_day"),
                        "day": today, "items": keep_items},
                       open(fn, "w", encoding="utf-8"))
        except Exception:
            pass
        return deleted
    except Exception:
        return 0


def tg_morning_purge():
    return 0   # 🩹 AUTO-DELETE OFF (user request 25 Sep) — Telegram history STAYS for later review
    """🧹 NEW DAY, CLEAN CHAT: first run of each new day deletes ALL messages
    still tracked from PREVIOUS days (including report cards) — every trading
    morning starts with an empty Telegram chat."""
    try:
        fn = f"tg_sent_{_ukey()}.json"
        try:
            d = _json.load(open(fn, encoding="utf-8"))
        except Exception:
            d = {}
        today = now_ist().strftime("%Y-%m-%d")
        if d.get("purge_day") == today:
            return 0
        items = _tg_norm_items(d)
        if not any(it[2] < today for it in items):
            d["purge_day"] = today
            try:
                _json.dump(d, open(fn, "w", encoding="utf-8"))
            except Exception:
                pass
            return 0
        cfg = tg_load()
        if not cfg.get("token"):
            return 0
        keep_items, deleted = [], 0
        for cid, mid, dstr, keep in items[:300]:
            if dstr < today:
                if _tg_delete(cfg, cid, mid):
                    deleted += 1
            else:
                keep_items.append([cid, mid, dstr, keep])
        _TG_SENT.update(day=today, items=list(keep_items))
        try:
            _json.dump({"purge_day": today, "cleanup_day": d.get("cleanup_day"),
                        "day": today, "items": keep_items},
                       open(fn, "w", encoding="utf-8"))
        except Exception:
            pass
        return deleted
    except Exception:
        return 0


def stock_buttons(sym):
    """One-tap open buttons under a stock message — chart shortcuts."""
    s = str(sym).replace(".NS", "").strip()
    return [[
        {"text": "📈 Google", "url": f"https://www.google.com/finance/quote/{s}:NSE"},
        {"text": "📊 TradingView", "url": f"https://www.tradingview.com/symbols/NSE-{s}/"},
    ]]


def tg_send_one(cid, text, _retry=True, buttons=None, keep=False):
    """Send to ONE chat id in RICH format (bold · boxed prices · italics,
    optional one-tap buttons). keep=True survives the end-of-day cleanup
    (report cards, manual tests); everything else auto-deletes after close.
    If Telegram rejects the formatting, auto-resends plain — alerts never die."""
    cfg = tg_load()
    if not cfg.get("token"):
        return False, "no token configured"
    try:
        mid = _tg_post(cfg["token"], cid, text, html=_retry, buttons=buttons)
        _tg_track(cid, mid, keep)
        return True, ""
    except urllib.error.HTTPError as e:
        if e.code == 400 and _retry:      # bad formatting → strip tags, plain resend
            try:
                e.read()
            except Exception:
                pass
            try:
                mid = _tg_post(cfg["token"], cid, re.sub(r"<[^>]+>", "", text), html=False,
                               buttons=buttons)
                _tg_track(cid, mid, keep)
                return True, ""
            except Exception:
                pass
        try:
            desc = _json.loads(e.read().decode()).get("description", "")
        except Exception:
            desc = ""
        return False, desc or f"HTTP {e.code}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"[:110]


def tg_send(text, buttons=None, keep=False):
    """Send one message to EVERY configured chat — comma-separated IDs let you share
    alerts with your brother. Optional one-tap buttons; keep=True survives the
    end-of-day cleanup. Silently skips if not configured; never crashes a scan."""
    cfg = tg_load()
    if not cfg.get("token") or not cfg.get("chat"):
        return False
    # ☁️ source tag + 🕘 REAL TIME-STAMP (user request 11 Oct): every message
    #    carries its actual send date+time (IST) — Telegram history becomes a
    #    proper record, and catch-up pings show BOTH real event time and send time
    if "☁️ CLOUD" not in text:
        text = (text.rstrip()
                + f"\n<i>🕘 {now_ist().strftime('%a %d %b %Y · %H:%M IST')} · ☁️ CLOUD</i>")
    sent_any = False
    for cid in [c.strip() for c in str(cfg["chat"]).split(",") if c.strip()]:
        ok, _r = tg_send_one(cid, text, buttons=buttons, keep=keep)
        sent_any = sent_any or ok
    return sent_any


APP_VERSION = "v14.1 · PRECISION · 2-MIN LIVE"


def tg_online_ping():
    """🟢 ONE 'online' ping per trading morning (the day's first start,
    8 AM–12 PM only). Silent the rest of the day — restarts, refreshes
    and the autopilot's hourly reloads NEVER re-announce. A separate
    'PROGRAM UPDATED' notice fires ONLY when the running version really
    changed (evening deploy)."""
    try:
        fn = f"tg_boot_{_ukey()}.json"
        _fresh = not _os.path.exists(fn)          # first boot EVER of this app here
        d = {}
        if not _fresh:
            d = _json.load(open(fn, encoding="utf-8")) or {}
        today = now_ist().strftime("%Y-%m-%d")
        if d and d.get("ver") != APP_VERSION:
            tg_send(f"\u2705 <b>PROGRAM UPDATED</b>\n"
                    f"\U0001F680 Now running <b>{_esc(APP_VERSION)}</b>\n"
                    f"\U0001F552 {now_ist().strftime('%a %d %b %Y \u00b7 %H:%M')} IST\n"
                    f"<i>Same trading logic \u2014 engines and rules unchanged.</i>")
        elif _fresh:
            tg_send(f"\U0001F7E2 <b>AI Trader is ONLINE</b> \u00b7 <b>{_esc(APP_VERSION)}</b>\n"
                    f"\U0001F552 {now_ist().strftime('%a %d %b %Y \u00b7 %H:%M')} IST\n"
                    f"<i>Desk started \u2014 engines armed. Morning briefing arrives 8 AM\u201312 PM "
                    f"on trading days.</i>")
        d["ver"] = APP_VERSION
        _trading_day = now_ist().weekday() < 5 and today not in NSE_HOLIDAYS
        if (d.get("day") != today and _trading_day and 8 <= now_ist().hour < 12
                and tg_send(f"\U0001F7E2 <b>AI Trader is ONLINE</b>\n"
                            f"\U0001F552 {now_ist().strftime('%a %d %b %Y \u00b7 %H:%M')} IST\n"
                            f"<i>Morning auto-start \u2014 radars begin at 9:20.</i>\n"
                            f"\U0001F3C5 RESULT 1 09:40 \u00b7 RESULT 2 10:00 \u00b7 RESULT 3 10:15 \u00b7 FINAL 10:20 \u2014 right here on Telegram.")):
            d["day"] = today
        _json.dump(d, open(fn, "w", encoding="utf-8"))
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════
# 🎯 TRADE COACH — the morning shortlist gets a personal trainer.
#   9:20 → pick the FEW perfect stocks (₹100–₹1000, ranked board,
#   live-confirmed). Then the coach reads every 5-min candle and
#   tells the owner EXACTLY: when to BUY (breakout / VWAP hold),
#   when to SELL HALF (T1), when to SELL REST (T2), when to EXIT
#   (stoploss / lost-VWAP / time exit / square-off). Every order
#   instruction also goes to Telegram instantly.
# ══════════════════════════════════════════════════════════════════
COACH_N_DEFAULT = 8          # how many perfect stocks to coach
COACH_CAP_DEFAULT = 10000    # ₹ capital per trade (for qty suggestion)


def coach_ctx(sym, df, today=None):
    """Live candle snapshot for one stock (VWAP, session ranges, triggers)."""
    try:
        today = today or now_ist().date()
        dates = [_dist(ix) for ix in df.index]
        td = [i for i, d in enumerate(dates) if d == today]
        if not td:                      # pre-open / holiday → last session
            td = [i for i, d in enumerate(dates) if d == max(dates)]
        t = df.iloc[td[0]:td[-1] + 1]
        prev_close = float(df["Close"].iloc[td[0] - 1]) if td[0] > 0 else float(t["Open"].iloc[0])
        cl = t["Close"].values; op = t["Open"].values; v = t["Volume"].values
        h = t["High"].values; l = t["Low"].values
        n = len(cl)
        vwap = float((cl * v).sum() / v.sum()) if v.sum() > 0 else float(cl[-1])
        try:      # afternoon support = the stronger of VWAP and the morning low
            _mk = [ix.hour * 60 + ix.minute for ix in t.index]
            _ml = [float(l[i]) for i, k in enumerate(_mk) if k < 720] or [float(l.min())]
            lo_morn = min(_ml)
        except Exception:
            lo_morn = float(l.min())
        sup_aft = max(vwap, lo_morn)
        return {"sym": sym, "last": float(cl[-1]), "prev_close": prev_close,
                "lo_morn": round(float(lo_morn), 2), "sup_aft": round(float(sup_aft), 2),
                "vwap": vwap, "hi_ses": float(h.max()), "lo_ses": float(l.min()),
                "hi_prev": float(h[:-1].max()) if n > 1 else float(h[-1]),
                "lows3": [float(x) for x in l[-3:]], "cl_last": float(cl[-1]),
                "cl_prev": float(cl[-2]) if n > 1 else float(cl[-1]),
                "green_last": bool(cl[-1] > op[-1]), "red_last": bool(cl[-1] < op[-1]),
                "green_frac": float(sum(1 for i in range(n) if cl[i] > op[i]) / n) if n else 0.5,
                "vr_last": float(v[-1] / v.mean()) if (n and v.mean() > 0) else 1.0,
                "chg_day": (float(cl[-1]) / prev_close - 1) * 100 if prev_close else 0.0,
                "n": n}
    except Exception:
        return None


def coach_cycle(ctx, pos, cap=COACH_CAP_DEFAULT, mins=None):
    """One decision pass for ONE stock — mutates pos, returns events
    [(level, message)] · level: buy/t1/t2/sl/exit/time/eod."""
    ev = []
    if ctx is None:
        return ev
    last = ctx["last"]; vwap = ctx["vwap"]
    t = mins if mins is not None else (now_ist().hour * 60 + now_ist().minute)
    nm = pos.get("name") or ctx["sym"].replace(".NS", "")

    _brk = _coach_brake_state()
    if pos["stage"] == "WAIT":
        if ctx["n"] < 3 or t < 9 * 60 + 25:          # 9:15–9:25 warm-up
            return ev
        if _brk["braked"]:                           # 🛑 day brake active — manage only
            return ev
        if t >= 14 * 60 + 30:                         # no FRESH entries late
            return ev
        try:                                          # 🧠 regime-aware sizing
            _rg = market_regime() or {}
        except Exception:
            _rg = {}
        _rchg = float(_rg.get("chg") or 0)
        weak_day = _rchg <= -0.3
        mixed_day = -0.3 < _rchg <= 0.3
        cap = (cap // 2) if (weak_day or mixed_day) else cap   # 🟡🔴 half size
        if t >= 12 * 60 or _rchg <= -0.5:            # ☀️ afternoon OR 🔴 red day:
            sup = ctx.get("sup_aft") or vwap          # support bounces ONLY (Wed-9-Sep lesson:
                                                      # 6/6-snapshot stocks fell −3…−6.5% on a
                                                      # red NIFTY — morning strength means nothing
                                                      # when the market slides)
            if (ctx["green_last"] and ctx["chg_day"] > -3.0
                    and sup * 0.997 <= last <= sup * 1.004):
                entry = round(last, 2)
                sl = round(sup * 0.995, 2)
                if entry - sl < entry * 0.004:
                    sl = round(entry * 0.996, 2)
                R = entry - sl
                t1 = round(entry + 1.0 * R, 2)
                t2 = round(min(entry + 1.6 * R, entry * 1.025), 2)
                qty = max(1, int(cap // entry)) if cap else 1
                why = f"afternoon pullback HELD support ₹{sup:,.2f} and stabilized"
                pos.update(stage="HOLD", entry=entry, sl=sl, t1=t1, t2=t2, qty=qty,
                           half=False, res=None, sig=why, hw=entry, ent_mins=t, vr_streak=0)
                ev.append(("buy", f"\U0001F6E1\uFE0F <b>SUPPORT BOUNCE \u00b7 {_esc(nm)}</b>\n"
                                  f"\U0001F4B0 <b>BUY NOW</b> <code>\u20B9{entry:,.2f}</code> \u00b7 qty\u2248{qty} (\u20B9{cap:,})\n"
                                  f"\U0001F6D1 SL <code>\u20B9{sl:,.2f}</code> \u00b7 \U0001F3AF T1 <code>\u20B9{t1:,.2f}</code> sell HALF \u00b7 "
                                  f"\U0001F3AF T2 <code>\u20B9{t2:,.2f}</code> sell rest\n"
                                  f"<i>\U0001F4A1 {_esc(why)} \u2014 afternoon bounce, book quickly</i>"))
            return ev
        breakout = (ctx["green_last"] and last > ctx["hi_prev"]
                    and ctx["vr_last"] >= (2.0 if weak_day else 1.3)   # 🔴 weak day needs proof
                    and ctx["chg_day"] <= 4)
        vwap_hold = (ctx["green_last"] and abs(last / vwap - 1) <= 0.0025
                     and last >= vwap * 0.998 and ctx["cl_last"] > ctx["cl_prev"]
                     and 0 <= ctx["chg_day"] <= 4)
        too_extended = last > vwap * 1.012 and ctx["vr_last"] < 2.0   # 🚫 spike = instant pullback
        if (breakout or vwap_hold) and not too_extended:
            entry = round(last, 2)
            sl = round(min(vwap, min(ctx["lows3"])) * 0.998, 2)
            if entry - sl < entry * 0.005:      # wider net = fewer instant stop-outs
                sl = round(entry * 0.995, 2)
            R = entry - sl
            t1 = round(entry + 1.0 * R, 2)
            t2 = round(min(entry + (1.2 if (weak_day or mixed_day) else 1.8) * R,
                           entry * 1.035), 2)   # 🟡🔴 quicker target on soft days
            qty = max(1, int(cap // entry)) if cap else 1
            why = "session-high BREAKOUT with volume" if breakout else "pullback HELD VWAP and turned up"
            pos.update(stage="HOLD", entry=entry, sl=sl, t1=t1, t2=t2, qty=qty,
                       half=False, res=None, sig=why, hw=entry, ent_mins=t, vr_streak=0)
            ev.append(("buy", f"\U0001F7E2 <b>BUY NOW \u00b7 {_esc(nm)}</b>\n"
                              f"\U0001F4B0 Price <code>\u20B9{entry:,.2f}</code> \u00b7 qty\u2248{qty} (\u20B9{cap:,})\n"
                              f"\U0001F6D1 SL <code>\u20B9{sl:,.2f}</code>\n"
                              f"\U0001F3AF T1 <code>\u20B9{t1:,.2f}</code> (+{(t1/entry-1)*100:.1f}%) \u2014 sell HALF\n"
                              f"\U0001F3AF T2 <code>\u20B9{t2:,.2f}</code> (+{(t2/entry-1)*100:.1f}%) \u2014 sell rest\n"
                              f"<i>\U0001F4A1 {_esc(why)} \u2014 act fast, don't chase more than +0.3%</i>"))
        return ev

    if pos["stage"] == "HOLD":
        pos["hw"] = max(pos.get("hw") or pos["entry"], last)
        pnl = (last / pos["entry"] - 1) * 100
        grace = (t - pos.get("ent_mins", t)) < 15          # first 15 min: give the trade air
        if last <= pos["sl"]:
            pos.update(stage="DONE", res=round(pnl, 2), outcome="sl")
            _coach_pnl_add(pnl, cap)
            ev.append(("sl", f"\U0001F6D1 <b>STOPLOSS \u00b7 {_esc(nm)}</b>\n"
                             f"\u26A0\uFE0F <b>EXIT ALL NOW</b> below <code>\u20B9{pos['sl']:,.2f}</code>\n"
                             f"\U0001F4C9 Result <b>{pnl:+.1f}%</b> \u00b7 small loss = capital saved"
                             + (" \u00b7 T1 half already booked \u2714" if pos["half"] else "")))
        elif (not pos["half"]) and last >= pos["t1"]:
            pos["half"] = True; pos["sl"] = pos["entry"]
            ev.append(("t1", f"\U0001F4B0 <b>T1 HIT \u00b7 {_esc(nm)}</b>\n"
                             f"\U0001F3AF Sell <b>HALF</b> now at <code>\u20B9{pos['t1']:,.2f}</code>\n"
                             f"\U0001F6D1 SL moved to entry <code>\u20B9{pos['entry']:,.2f}</code> \u2014 <b>profit locked</b> \u2714"))
        elif pos["half"] and last >= pos["t2"]:
            pos.update(stage="DONE", res=round(pnl, 2), outcome="t2")
            _coach_pnl_add(pnl, cap)
            ev.append(("t2", f"\u2705 <b>T2 HIT \u00b7 {_esc(nm)}</b>\n"
                             f"\U0001F3AF Sell the <b>REST</b> at <code>\u20B9{pos['t2']:,.2f}</code>\n"
                             f"\U0001F3C6 Trade complete <b>{pnl:+.1f}%</b> \U0001F389"))
        elif t >= 15 * 60 + 5:
            pos.update(stage="DONE", res=round(pnl, 2), outcome="eod")
            _coach_pnl_add(pnl, cap)
            ev.append(("eod", f"\U0001F51A <b>SQUARE OFF \u00b7 {_esc(nm)}</b>\n"
                              f"Market closing \u2014 exit now \u00b7 <b>{pnl:+.1f}%</b>"))
        else:
            weak = (last < vwap * 0.9975 and ctx["red_last"])
            pos["vr_streak"] = (pos.get("vr_streak", 0) + 1) if weak else 0
            deep = last < vwap * 0.995
            if (not grace) and (deep or pos["vr_streak"] >= 2):
                pos.update(stage="DONE", res=round(pnl, 2), outcome="exit")
                _coach_pnl_add(pnl, cap)
                ev.append(("exit", f"\u26A0\uFE0F <b>EXIT ALL \u00b7 {_esc(nm)}</b>\n"
                                   f"\U0001F4C9 Fell below VWAP, momentum dead \u00b7 <b>{pnl:+.1f}%</b>"))
            elif (not grace) and t >= 11 * 60 + 30 and -0.3 < pnl < 0.4:
                pos.update(stage="DONE", res=round(pnl, 2), outcome="time")
                _coach_pnl_add(pnl, cap)
                ev.append(("time", f"\u23F0 <b>TIME EXIT \u00b7 {_esc(nm)}</b>\n"
                                   f"Going nowhere ({pnl:+.1f}%) \u2014 rotate to a live mover"))
    return ev


def coach_pick(n=COACH_N_DEFAULT):
    """9:20 shortlist — take the ranked board (₹100–₹1000), live-confirm the
    top 60 with 5-min candles, keep the n most perfect setups."""
    watch, names = rank_universe(500)
    cands = []
    got, _ = _sweep(watch[:60], "5m", "2d", with_daily=False, progress=False)
    for r, sym in enumerate(watch[:60]):
        ctx = coach_ctx(sym, got.get(sym)) if got.get(sym) is not None else None
        if not ctx or ctx["n"] < 2:
            continue
        if not (0 <= ctx["chg_day"] <= 2.5):
            continue
        if not (MIN_PRICE <= ctx["last"] <= MAX_PRICE):
            continue
        score = ((60 - r) / 60) * 40 + min(ctx["chg_day"], 2.0) / 2.0 * 25 \
                + ctx["green_frac"] * 20 + min(ctx["vr_last"], 2.0) / 2.0 * 15
        cands.append((round(score, 1), sym))
    cands.sort(reverse=True)
    top = [s for _, s in cands[:n]]
    return top, {s: names.get(s, s.replace(".NS", "")) for s in top}


def coach_collect_log(posd):
    """Pick up finished trades (once each) for the report card."""
    out = []
    for s, p in (posd or {}).items():
        try:
            if p.get("stage") == "DONE" and not p.get("logged") and p.get("outcome"):
                p["logged"] = True
                out.append({"sym": s, "name": p.get("name") or s.replace(".NS", ""),
                            "entry": p.get("entry"), "res": p.get("res"),
                            "outcome": p.get("outcome"), "sig": p.get("sig"),
                            "ts": now_ist().strftime("%H:%M")})
        except Exception:
            continue
    return out


def coach_eod_summary(log, cap):
    n = len(log)
    if not n:
        return (f"\U0001F4CA <b>COACH REPORT CARD \u00b7 {now_ist().strftime('%a %d %b')}</b>\n"
                "\U0001F9ED No completed trades today \u2014 no valid setups triggered.\n"
                "\U0001F4B0 Capital preserved \u2014 patience is a position too.")
    wins = [t for t in log if (t.get("res") or 0) > 0]
    avg = sum(t.get("res") or 0 for t in log) / n
    rupees = sum((t.get("res") or 0) * cap / 100 for t in log)
    best = max(log, key=lambda t: t.get("res") or 0)
    head = (f"\U0001F4CA <b>COACH REPORT CARD \u00b7 {now_ist().strftime('%a %d %b')}</b>\n"
            f"\U0001F4DD Trades <b>{n}</b> \u00b7 Wins <b>{len(wins)}</b> ({len(wins) * 100 // n}% win rate)\n"
            f"\U0001F4C8 Avg <b>{avg:+.2f}%</b> \u00b7 Est P&L <code>\u20B9{rupees:,.0f}</code> (on \u20B9{cap:,}/trade)\n"
            f"\U0001F3C6 Best: <b>{_esc(best['name'])} {best['res']:+.1f}%</b>")
    tail = " \u00b7 ".join(f"{_esc(t['name'])} {t['res']:+.1f}% ({t['outcome']})" for t in log[:6])
    return head + ("\n" + tail if tail else "")


@st.cache_data(ttl=300, show_spinner=False)
def nifty_regime():
    """🔴🟡🟢 NIFTY mood — when the index falls hard, uptrend calculations are
    unreliable. The app must SAY so on every result instead of staying silent."""
    try:
        d = yf.download("^NSEI", period="5d", interval="5m", progress=False, auto_adjust=True)
        if d is None or not len(d):
            return None
        if isinstance(d.columns, pd.MultiIndex):
            d.columns = [c[0] for c in d.columns]
        d = d.rename(columns=str.title)
        days = sorted(set(d.index.date))
        if len(days) < 2:
            return None
        prev = d[d.index.date == days[-2]]["Close"].dropna()
        today = d[d.index.date == days[-1]]["Close"].dropna()
        if not len(prev) or not len(today):
            return None
        chg = (float(today.iloc[-1]) / float(prev.iloc[-1]) - 1) * 100
        # NIFTY context (user 25 Oct A+B): mom = live 15-min momentum so
        # alerts can say "NIFTY rising/falling RIGHT NOW" (not just day %);
        # gap = today's open vs yesterday's close, for the 09:15 roadmap.
        try:
            _to_t = today.index[-1]              # last 5-min STAMP (not value)
            _to_v = float(today.iloc[-1])
            _m15 = today[today.index >= (_to_t - pd.Timedelta(minutes=15))]
            mom = round(_to_v - float(_m15.iloc[0]), 0) if len(_m15) else 0.0
        except Exception:
            mom = 0.0
        try:
            _tod_o = d[d.index.date == days[-1]]["Open"].dropna()
            gap = (float(_tod_o.iloc[0]) / float(prev.iloc[-1]) - 1) * 100 if len(_tod_o) else 0.0
        except Exception:
            gap = 0.0
        if chg <= -0.40:
            lab, ico, note = "RED", "\U0001F534", "market FALLING \u2014 calculations unreliable today \u2014 avoid longs"
        elif chg >= 0.25:
            lab, ico, note = "GREEN", "\U0001F7E2", "healthy day \u2014 normal reliability"
        else:
            lab, ico, note = "FLAT", "\U0001F7E1", "quiet day \u2014 normal reliability, expect smaller moves"
        return {"chg": round(chg, 2), "lab": lab, "ico": ico, "note": note,
                "mom": mom, "gap": round(gap, 2)}
    except Exception:
        return None


CONS_SLOTS = [("09:30", 9 * 60 + 30), ("09:45", 9 * 60 + 45),
              ("10:00", 10 * 60), ("10:15", 10 * 60 + 15)]   # legacy default
CONS_CFG_DEFAULT = {"wins": [{"start": "09:20", "end": "09:40", "every": 10},   # 🏅 RESULT 1 ~09:40
                             {"start": "09:40", "end": "10:00", "every": 10},   # 🏅 RESULT 2 ~10:00
                             {"start": "10:00", "end": "10:15", "every": 5},    # 🏅 RESULT 3 ~10:15
                             {"start": "10:15", "end": "10:20", "every": 5}]}   # 🏅 RESULT 4 ~10:20 · FINAL


def _hmm(s):
    """'9.30' / '09:30' / '930' → minutes past midnight (None if not a time)."""
    try:
        s = str(s).strip().replace(".", ":").replace(" ", "")
        if ":" in s:
            h, m = s.split(":", 1)
        elif len(s) > 2:
            h, m = s[:-2], s[-2:]
        else:
            h, m = s, "0"
        h, m = int(h), int(m)
        if 0 <= h <= 23 and 0 <= m <= 59:
            return h * 60 + m
    except Exception:
        pass
    return None


def cons_cfg_load():
    """⏱️ YOUR analysis windows: [{start, end, every}, …] — one result EACH."""
    try:
        c = rt_load().get("conscfg") or {}
        if c.get("v") != 2:                  # stale pre-v2 schedule -> ignore
            c = {}
        wins = c.get("wins")
        out = []
        if wins and isinstance(wins, list):
            for w in wins[:4]:
                w = w or {}
                a, b = _hmm(w.get("start")), _hmm(w.get("end"))
                try:
                    ev = int(w.get("every") or 15)
                except Exception:
                    ev = 15
                if a is not None and b is not None and b >= a and 2 <= ev <= 30:
                    out.append({"start": str(w["start"]), "end": str(w["end"]), "every": ev})
        if out:
            return {"wins": out}
    except Exception:
        pass
    return {"wins": [dict(w) for w in CONS_CFG_DEFAULT["wins"]]}


def cons_slots_win(w):
    """📸 One window's snapshot slots — start → end, every N minutes."""
    a, b = _hmm(w["start"]), _hmm(w["end"])
    step = max(2, int(w.get("every") or 15))
    out = []
    if a is None or b is None or b < a:
        return out
    t = a
    while t <= b and len(out) < 12:
        out.append((f"{t // 60:02d}:{t % 60:02d}", t))
        t += step
    return out


def cons_last_win():
    return max(len(cons_cfg_load()["wins"]) - 1, 0)


def cons_state():
    _today = now_ist().strftime("%Y-%m-%d")
    try:
        d = rt_load().get("cons") or {}
        if d.get("day") != _today:
            return {"day": _today, "wins": {}}
        if not isinstance(d.get("wins"), dict):
            # legacy single-window state (pre dual-window) → becomes window 1
            _w0 = ({"snaps": d.get("snaps") or {}, "ts": d.get("ts") or {},
                    "n": d.get("n") or 0, "date": d.get("date")} if d.get("n") else None)
            d = {**d, "wins": ({"0": _w0} if _w0 else {})}
        return d
    except Exception:
        return {"day": _today, "wins": {}}


def cons_capture(combos):
    """📸 Snapshot the TOP-20 into EVERY window whose next slot time has
    passed (one snapshot per window per scan cycle; piggybacks combo scan)."""
    try:
        n = now_ist()
        if n.weekday() >= 5 or n.strftime("%Y-%m-%d") in NSE_HOLIDAYS or not combos:
            return
        t = n.hour * 60 + n.minute
        d = cons_state()
        changed = False
        for wi, w in enumerate(cons_cfg_load()["wins"]):
            ws = d["wins"].setdefault(str(wi), {"snaps": {}, "ts": {}, "n": 0})
            for lbl, slot in cons_slots_win(w):
                if t >= slot and lbl not in (ws.get("snaps") or {}):
                    ws.setdefault("snaps", {})[lbl] = [c["sym"] for c in combos if not c.get("volc_only")][:25]
                    ws.setdefault("ts", {})[lbl] = n.strftime("%H:%M")
                    ws.setdefault("date", n.strftime("%a %d %b %Y"))
                    ws["n"] = len(ws["snaps"])
                    changed = True
                    break              # one snapshot per window per scan cycle
        if changed:
            rt_save("cons", **d)
    except Exception:
        pass


def cons_compute(win=0):
    """→ (tier1 [appeared need+ ×], tier2 [need−1 ×], meta) for ONE window."""
    d = cons_state()
    wins = cons_cfg_load()["wins"]
    if 0 <= win < len(wins):
        w = wins[win]
        ws = (d.get("wins") or {}).get(str(win)) or {}
    else:
        w = wins[0] if wins else dict(CONS_CFG_DEFAULT["wins"][0])
        ws = {}
    slots = cons_slots_win(w)
    total = len(slots)
    need = total if total <= 3 else max(3, round(total * 0.6))
    counts, best = {}, {}
    for lbl, syms in (ws.get("snaps") or {}).items():
        for i, s in enumerate(syms, 1):
            counts[s] = counts.get(s, 0) + 1
            best[s] = min(best.get(s, 999), i)
    n = ws.get("n") or 0
    tier1 = sorted([s for s, c in counts.items() if c >= need], key=lambda s: (-counts[s], best[s]))
    tier2 = sorted([s for s, c in counts.items() if c == need - 1 and need > 1], key=lambda s: best[s])
    return tier1, tier2, {"day": d.get("day"), "win": win, "nwins": len(wins), "n": n,
                          "counts": counts, "best": best, "total": total, "need": need,
                          "slots": slots, "ts": ws.get("ts") or {}, "date": ws.get("date"),
                          "result_ts": ws.get("result_ts"), "cfg": w}


def tg_pick_levels(syms):
    """🎯 LIVE BUY/TGT/SL for RESULT picks — ONE batched Upstox quote call
    at announce time (the 📡 quote endpoint). Any failure → {} — the RESULT
    always goes out; worst case it carries no levels."""
    try:
        syms = [s for s in (syms or []) if s]
        if not syms or not up_token_valid():
            return {}
        kmap = up_keys_map(syms[:40])
        if not kmap:
            return {}
        rev = {k: s for s, k in kmap.items()}
        tok = up_auth_token()
        out = {}
        vals = list(kmap.values())
        for i in range(0, len(vals), 500):
            req = urllib.request.Request(
                "https://api.upstox.com/v2/market-quote/ohlc?interval=1d&instrument_key="
                + ",".join(vals[i:i + 500]),
                headers={"Accept": "application/json", "User-Agent": UP_UA,
                         "Authorization": f"Bearer {tok}"})
            data = (_json.loads(urllib.request.urlopen(req, timeout=8)
                                .read().decode("utf-8")) or {}).get("data") or {}
            for k, v in data.items():
                s = rev.get(k)
                o = (v or {}).get("ohlc") or {}
                try:
                    px = float((v or {}).get("last_price") or o.get("close") or 0)
                except Exception:
                    px = 0.0
                if s and px > 0:
                    out[s] = {"px": round(px, 1), "tgt": round(px * 1.015, 1),
                              "sl": round(px * 0.99, 1),
                              "hi": round(float(o.get("high") or px), 1),
                              "lo": round(float(o.get("low") or px), 1)}
        return out
    except Exception:
        return {}


def cons_announce(names=None):
    """📲 GUARANTEED Telegram delivery — ONE result message PER window, the
    moment that window's scans are all in. Never silent, never lost."""
    try:
        d = cons_state()
        names = names or (rt_load().get("cb") or {}).get("names") or {}

        def _nm(s):
            return names.get(s, s.replace(".NS", ""))

        def _mins(hhmm):
            try:
                h, m = str(hhmm).split(":")
                return int(h) * 60 + int(m)
            except Exception:
                return 9999

        sent_any = False
        for wi, w in enumerate(cons_cfg_load()["wins"]):
            t1, t2, cm = cons_compute(wi)
            ws = d["wins"].setdefault(str(wi), {"snaps": {}, "ts": {}, "n": 0})
            _w_end = _mins(w.get("end", "23:59"))
            _t_now = now_ist().hour * 60 + now_ist().minute
            _n_cap, _tot_cap = (cm.get("n") or 0), (cm["total"] or 0)
            _partial = _n_cap < _tot_cap
            _late_ok = (not ws.get("announced")) and _partial and _w_end is not None \
                       and _t_now > _w_end + 10 and _n_cap >= 1
            # RESTART GUARD — if EVERY snapshot of this window was captured
            # minutes AFTER the window ended, the window was rebuilt from a
            # fresh scan after a restart/deploy (state was lost). Those are
            # NEVER re-sent to Telegram — the panel keeps them, marked.
            _rebuilt = False
            if _n_cap and not ws.get("announced"):
                try:
                    _tsm = [_mins(t) for t in (ws.get("ts") or {}).values() if t]
                    _rebuilt = bool(_tsm) and all(m != 9999 and m > _w_end + 3 for m in _tsm)
                except Exception:
                    _rebuilt = False
                if _rebuilt and not ws.get("rebuilt"):
                    ws["rebuilt"] = True
                    try:
                        rt_save("cons", **d)
                    except Exception:
                        pass
            if _rebuilt or ((not _tot_cap or _n_cap < _tot_cap or ws.get("announced"))
                            and not _late_ok):
                continue
            if _late_ok and not t1:          # partial window: picks in EVERY captured scan
                t1 = sorted([s for s, c in (cm.get("counts") or {}).items()
                             if c >= _n_cap], key=lambda s: (cm.get("best") or {}).get(s, 99))
            _cfg = cm.get("cfg") or {}
            _win_lbl = f"{_cfg.get('start', '09:20')}\u2013{_cfg.get('end', '09:40')}"
            _res_no = f"RESULT {wi + 1} of {cm['nwins']} \u00b7 " if cm["nwins"] > 1 else ""
            _tot, _nd = cm["total"], cm["need"]
            _date = cm.get("date") or now_ist().strftime("%a %d %b %Y")
            _part_tag = (f" \u26A0\uFE0F PARTIAL \u2014 {cm.get('n')}/{cm['total']} scans captured "
                         "(one missed) \u2014 slightly lower confidence"
                         if _partial and _n_cap else "")
            slots = " \u00b7 ".join(f"{lbl}\u2192{cm['ts'].get(lbl, '?')}" for lbl, _s in cm["slots"])
            late = any(_mins(cm["ts"].get(lbl, "?")) - _s > 10 for lbl, _s in cm["slots"])
            _rg = nifty_regime()
            _rg_line = (f"{_rg['ico']} NIFTY {_rg['chg']:+.2f}% \u2014 {_rg['note']}\n" if _rg else "")
            _lv = tg_pick_levels(list(t1 or [])[:35])
            if t1:
                _hi = [s for s in t1 if cm["counts"][s] == (cm.get("n") or _tot)
                    and (cm["best"].get(s) or 99) <= 5]
                _rest = [s for s in t1 if s not in _hi][:25]
                _lines = []
                if _hi:
                    _lines.append("\U0001F525 <b>99% CONFIDENT \u2014 every scan + top ranks:</b>")
                    for s in _hi[:10]:
                        _L = _lv.get(s) or {}
                        _lvs = (f" \u00b7 \U0001F3AF BUY {_L['px']:.1f} \u00b7 TGT {_L['tgt']:.1f} \u00b7 SL {_L['sl']:.1f}" if _L.get("px") else "")
                        _lines.append(f"\U0001F525 <b>{_esc(_nm(s))}</b> \u2014 {cm['counts'][s]}/{_tot} scans \u00b7 best rank #{cm['best'][s]}{_lvs}")
                if _rest:
                    _lines.append("\u2705 <b>ALSO STABLE:</b>")
                    for s in _rest:
                        _L = _lv.get(s) or {}
                        _lvs = (f" \u00b7 \U0001F3AF BUY {_L['px']:.1f} \u00b7 TGT {_L['tgt']:.1f} \u00b7 SL {_L['sl']:.1f}" if _L.get("px") else "")
                        _lines.append(f"\u2705 {_esc(_nm(s))} \u2014 {cm['counts'][s]}/{_tot} scans \u00b7 best rank #{cm['best'][s]}{_lvs}")
                try:
                    ws["levels"] = {s: _lv[s] for s in (t1 or []) if s in _lv}
                except Exception:
                    pass
                body = (f"\U0001F3C5 <b>STABLE PICKS \u00b7 {_res_no}{_win_lbl} window \u00b7 {cm.get('n') or _tot}/{_tot} scans</b>{_part_tag}\n"
                        f"\U0001F4C5 {_date}\n{_rg_line}" + "\n".join(_lines))
                if t2:
                    body += "\n\U0001F501 <i>Watchlist (" + str(_nd - 1) + "\u00d7): " + _esc(", ".join(_nm(s) for s in t2[:8])) + "</i>"
            else:
                body = (f"\U0001F3C5 <b>STABLE PICKS \u00b7 {_res_no}{_win_lbl} window \u00b7 {cm.get('n') or _tot}/{_tot} scans</b>{_part_tag}\n"
                        f"\U0001F4C5 {_date}\n{_rg_line}"
                        f"\u26A0\uFE0F <b>No stock appeared {_nd}\u00d7+</b> \u2014 no firm leaders in this window. "
                        "Do NOT force trades.")
            body += "\n\U0001F552 <i>Slots filled: " + slots + (" \u26A0\uFE0F late backfill" if late else "") + "</i>"
            body += "\n\U0001F3C1 <i>Result at " + now_ist().strftime("%H:%M") + " IST</i>"
            if cm["nwins"] > 1 and wi == cm["nwins"] - 1 and wi > 0:
                body += "\n\U0001F501 <i>FINAL window \u2014 coach now follows these picks.</i>"
            if _lv:
                body += ("\n\U0001F3AF <i>Levels: BUY = result-time price \u00b7 TGT +1.5% \u00b7 SL \u20141% "
                         "\u00b7 neither hit \u2192 exit by 15:15</i>")
            if tg_send(body):
                ws["announced"] = True
                ws["result_ts"] = now_ist().strftime("%H:%M")
                sent_any = True
                try:
                    rt_save("cons", **d)   # persist NOW — no second tab can re-send
                except Exception:
                    pass
                try:
                    blog(f"🏅 RESULT {wi + 1} delivered · {len(t1 or [])} picks")
                except Exception:
                    pass
        if sent_any:
            rt_save("cons", **d)
        return sent_any
    except Exception:
        return False


def cons_results_panel():
    """🏅 TODAY'S RESULTS — pinned to the page ALL DAY. Telegram is the
    delivery; THIS panel is the permanent record: sent, late, or never-sent,
    every completed window stays right here (nothing can be missed)."""
    try:
        d = cons_state()
        wins = cons_cfg_load()["wins"]
        names = (rt_load().get("cb") or {}).get("names") or {}
        n = now_ist()
        t_now = n.hour * 60 + n.minute

        def _nm(s):
            return names.get(s, s.replace(".NS", ""))
        blocks = []
        for wi, w in enumerate(wins):
            t1, t2, cm = cons_compute(wi)
            ws = (d.get("wins") or {}).get(str(wi)) or {}
            if not (cm.get("n") or 0):
                continue
            _end = _hmm(w.get("end", "10:20")) or 0
            _cfg = cm.get("cfg") or {}
            lbl = f"{_cfg.get('start', '09:20')}\u2013{_cfg.get('end', '09:40')}"
            if ws.get("announced"):
                tag, col = f"\U0001F4E2 SENT {ws.get('announced')}", "#16a34a"
            elif ws.get("rebuilt"):
                tag, col = ("\u26A0\uFE0F RECONSTRUCTED after restart \u2014 kept here, "
                            "NOT re-sent to Telegram"), "#f59e0b"
            elif t_now > _end + 10:
                tag, col = "\u26A0\uFE0F NOT SENT \u2014 Telegram missed it \u00b7 the result is HERE", "#f59e0b"
            else:
                tag, col = "\u23F3 in progress", "#60a5fa"
            best = cm.get("best") or {}
            club = [s for s in (t1 or []) if (best.get(s) or 99) <= 5
                    and (cm.get("counts") or {}).get(s) == (cm.get("n") or 1)]
            stable = [s for s in (t1 or []) if s not in club]
            chips = "".join(
                f"<span style='background:rgba(250,204,21,0.15);border:1px solid rgba(250,204,21,0.5);"
                f"border-radius:10px;padding:4px 10px;margin:3px;display:inline-block;color:#fde68a;"
                f"font-weight:700;font-size:12px;'>\U0001F525 {_esc(_nm(s))}</span>" for s in club[:10])
            chips += "".join(
                f"<span style='background:rgba(148,163,184,0.12);border:1px solid #334155;"
                f"border-radius:10px;padding:4px 10px;margin:3px;display:inline-block;color:#cbd5e1;"
                f"font-size:12px;'>\u2705 {_esc(_nm(s))}</span>" for s in stable[:15])
            if not chips:
                chips = "<span style='color:#8fa3bd;font-size:12px;'>No firm leaders in this window \u2014 no-trade window.</span>"
            _lvd = ws.get("levels") or {}
            _lvls = ""
            if _lvd:
                try:
                    _lvls = ("<div style='margin-top:6px;color:#93c5bd;font-size:11px;line-height:1.7;'>"
                             + " \u00b7 ".join(
                                 f"\U0001F3AF {_esc(_nm(s))} BUY {_v['px']:.0f} \u2192 TGT {_v['tgt']:.0f} / SL {_v['sl']:.0f}"
                                 for s, _v in list(_lvd.items())[:12]) + "</div>")
                except Exception:
                    _lvls = ""
            blocks.append(
                f"<div style='background:#0f1a2e;border:1px solid #1e293b;border-left:4px solid {col};"
                f"border-radius:12px;padding:10px 14px;margin:8px 0;'>"
                f"<b style='color:white;font-size:13px;'>\U0001F3C5 RESULT {wi + 1} \u00b7 {lbl}</b> "
                f"<span style='color:#8fa3bd;font-size:11px;'>{cm.get('n')}/{cm['total']} scans</span> "
                f"<span style='color:{col};font-size:11px;font-weight:700;'>{tag}</span>"
                f"<div style='margin-top:6px;'>{chips}</div>{_lvls}</div>")
        if blocks:
            st.markdown("<div style='font-size:15px;font-weight:800;color:#60a5fa;margin:14px 0 4px;'>"
                        "\U0001F3C5 TODAY'S RESULTS \u2014 always here, all day (Telegram is the bonus)</div>",
                        unsafe_allow_html=True)
            st.markdown("".join(blocks), unsafe_allow_html=True)
    except Exception:
        pass


def results_tab():
    """🏅 THE RESULTS TAB — the 🔥 99% club front and center. Everything the
    radar concluded today, in one place: the all-windows 99% summary first,
    then every window card (sent / not sent / in progress)."""
    st.markdown("<div style='font-size:19px;font-weight:900;color:white;margin:6px 0 2px;'>"
                "\U0001F3C5 99% RESULTS</div>"
                "<div style='color:#8fa3bd;font-size:12px;margin-bottom:12px;'>"
                "The day's most trusted picks \u2014 in EVERY scan AND top-ranked. "
                "Nothing here is a buy order \u2014 levels and SL discipline always apply.</div>",
                unsafe_allow_html=True)
    # ── 🔥 the all-windows 99% summary ──
    try:
        d = cons_state()
        wins = cons_cfg_load()["wins"]
        names = (rt_load().get("cb") or {}).get("names") or {}
        n = now_ist()
        t_now = n.hour * 60 + n.minute
        club_counts, best_overall, windows_live = {}, {}, 0
        for wi, w in enumerate(wins):
            t1, t2, cm = cons_compute(wi)
            if not (cm.get("n") or 0):
                continue
            windows_live += 1
            best = cm.get("best") or {}
            _cts = (cm.get("counts") or {})
            for s in (t1 or []):
                if (best.get(s) or 99) <= 5 and _cts.get(s) == (cm.get("n") or 1):
                    club_counts[s] = club_counts.get(s, 0) + 1
                    best_overall[s] = min(best_overall.get(s, 99), best.get(s) or 99)
        if club_counts:
            rows = sorted(club_counts.items(), key=lambda kv: (-kv[1], best_overall[kv[0]]))
            chips = "".join(
                f"<span style='background:rgba(250,204,21,0.15);border:1px solid rgba(250,204,21,0.5);"
                f"border-radius:10px;padding:6px 14px;margin:4px;display:inline-block;'>"
                f"<b style='color:#fde68a;font-size:14px;'>\U0001F525 {names.get(s, s.replace('.NS', ''))}</b> "
                f"<span style='color:#94a3b8;font-size:11px;'>{c}/{windows_live} windows</span></span>"
                for s, c in rows[:15])
            st.markdown(f"<div style='background:#2a2306;border:2px solid #facc15;border-radius:14px;"
                        f"padding:12px 16px;margin-bottom:14px;'>"
                        f"<b style='color:#facc15;font-size:13px;'>\U0001F525 THE 99% CLUB — trusted in "
                        f"every window it appeared</b><div style='margin-top:8px;'>{chips}</div>"
                        f"<div style='color:#a16207;font-size:11px;margin-top:6px;'>\U0001F525 = every scan "
                        f"+ top-5 rank in that window. Appearing in MORE windows = stronger.</div></div>",
                        unsafe_allow_html=True)
        else:
            st.info("\u23F3 No 99%-club picks yet today \u2014 they appear as the result windows "
                    "complete (09:40 / 10:00 / 10:15 / 10:20).")
    except Exception:
        pass
    # ── per-window cards ──
    cons_results_panel()


def cons_lock_coach(ss):
    """\U0001F3C5 After EACH window's last snapshot the coach follows that
    window's stable picks (held positions are preserved). Later windows
    re-lock the watchlist to the fresher consensus."""
    try:
        d = cons_state()
        for wi, w in enumerate(cons_cfg_load()["wins"]):
            t1, t2, cm = cons_compute(wi)
            if not t1 or not cm["total"] or (cm.get("n") or 0) < cm["total"]:
                continue
            _co_rt = rt_load().get("co") or {}
            _locks = _co_rt.get("cons_locks") or {}
            if _locks.get("day") == cm.get("day") and wi in (_locks.get("wins") or []):
                continue
            held = {s: p for s, p in (ss.get("co_pos") or {}).items()
                    if p.get("stage") in ("HOLD", "DONE")}
            want_n = int(ss.get("co_n") or COACH_N_DEFAULT)
            new_w = [s for s in t1 if s not in held][:want_n]
            for s in t2:
                if len(new_w) >= want_n:
                    break
                if s not in held and s not in new_w:
                    new_w.append(s)
            if not new_w:
                continue
            nm = ss.get("co_names") or {}
            pos = dict(held)
            for s in new_w:
                pos.setdefault(s, {"stage": "WAIT", "name": nm.get(s, s.replace(".NS", ""))})
            ss["co_watch"] = new_w + [s for s in held if s not in new_w]
            ss["co_pos"] = pos
            ss["co_ctx"] = {}
            txt = ", ".join(f"{nm.get(s, s.replace('.NS',''))} ({cm['counts'][s]}\u00d7)"
                            for s in new_w[:8])
            _res_no = f"RESULT {wi + 1} \u00b7 " if cm.get("nwins", 1) > 1 else ""
            tg_send(f"\U0001F3C5 <b>{_res_no}STABLE PICKS LOCKED \u00b7 coach follows ONLY these now</b>\n"
                    f"{_esc(txt)}\n"
                    f"<i>Appeared in {cm.get('need') or 3}+ of the {cm.get('total') or 4} scans "
                    f"({(cm.get('cfg') or {}).get('start', '09:30')}\u2013{(cm.get('cfg') or {}).get('end', '10:15')}) \u2014 "
                    f"the proven ones, no more confusion.</i>")
            rt_save("co", cons_day=f"{cm.get('day')}#W{wi}",
                    cons_locks={"day": cm.get("day"),
                                "wins": sorted(set((_locks.get("wins") or []) + [wi]))})
        return True
    except Exception:
        return False


def high52_map(syms):
    """🏔️ 52-week-high distance for the top combo stocks (1 batched 1y fetch)."""
    try:
        syms = [s for s in syms if s and not str(s).startswith("^")][:48]
        if not syms:
            return {}
        got = fetch_chunk(tuple(syms), "1d", "1y")
        out = {}
        for s in syms:
            df = got.get(s)
            if df is None or len(df) < 100:
                continue
            hi52 = float(df["High"].max())
            last = float(df["Close"].iloc[-1])
            if hi52 > 0:
                out[s] = {"hi52": round(hi52, 2), "dist": round((last / hi52 - 1) * 100, 2)}
        return out
    except Exception:
        return {}


_COACH_PNL = {"day": None, "pnl": 0.0, "braked": False}


def _coach_brake_state():
    _today = now_ist().strftime("%Y-%m-%d")
    if _COACH_PNL.get("day") != _today:
        _COACH_PNL.update(day=_today, pnl=0.0, braked=False)
    return _COACH_PNL


def _coach_pnl_add(res_pct, cap):
    """Track realized day P&L (₹ per trade-capital). At −1.5% of capital the
    coach stops taking new entries for the day — a bad day stays small."""
    try:
        st_ = _coach_brake_state()
        st_["pnl"] += (res_pct or 0) / 100.0 * (cap or COACH_CAP_DEFAULT)
        if (not st_["braked"] and st_["pnl"] <= -0.015 * (cap or COACH_CAP_DEFAULT)):
            st_["braked"] = True
            tg_send("\U0001F6D1 <b>DAY BRAKE \u00b7 coach stops new entries today</b>\n"
                    f"Realized {st_['pnl']:,.0f} \u20B9 today \u2014 past the \u22121.5% safety line.\n"
                    "<i>Existing holds are managed to their exits. Protect the capital, trade fresh tomorrow.</i>")
    except Exception:
        pass


def coach_phase(t=None):
    """The coach's day-plan: morning momentum → afternoon support → late manage."""
    t = t if t is not None else (now_ist().hour * 60 + now_ist().minute)
    if t < 12 * 60:
        return "morning", "🌅 MORNING MOMENTUM — fresh BUYs allowed · coach watching every candle"
    if t < 14 * 60 + 30:
        return "afternoon", ("☀️ AFTERNOON SUPPORT MODE — no new momentum buys (afternoon climbs fade) · "
                             "bounce plays at support only")
    return "late", "🌗 LATE DAY — no fresh entries · manage holds & square off 15:05"


def coach_action_text(sym, pos, ctx):
    """The one bold instruction line on each card."""
    if pos["stage"] == "DONE":
        r = pos.get("res")
        return (f"✅ TRADE CLOSED · {r:+.1f}%", "#22c55e" if (r or 0) >= 0 else "#f87171")
    if pos["stage"] == "HOLD":
        if pos.get("half"):
            return (f"💰 HALF SOLD ✔ — ride the rest · T2 ₹{pos['t2']:,.2f} · SL ₹{pos['sl']:,.2f} (entry)", "#fbbf24")
        return (f"💰 HOLDING — T1 ₹{pos['t1']:,.2f} (sell half) · SL ₹{pos['sl']:,.2f}", "#fbbf24")
    if ctx is None:
        return ("⏳ WAITING for candles…", "#64748b")
    if ctx["n"] < 3:
        return ("⏳ WAIT — first candles forming (act from 9:25)", "#64748b")
    ph, _p = coach_phase()
    if ph == "afternoon":
        sup = ctx.get("sup_aft") or ctx["vwap"]
        return (f"🛡️ SUPPORT MODE — buy zone ₹{sup*0.997:,.2f}–₹{sup*1.004:,.2f} once it stabilizes", "#fbbf24")
    if ph == "late":
        return ("🌗 window closed — managing holds only (square-off 15:05)", "#818cf8")
    return ("👀 WATCHING — coach will say BUY the moment the candle confirms", "#93c5fd")


def fresh_picks(movers):
    """Only the FRESH climbs with profit room: just started (day% small),
    still near VWAP (not stretched), slope up. The already-ran ones are
    exactly the ones that pull back — we skip them on purpose."""
    ranked = [m for m in movers if m.get("state") in ("CLIMBING", "FORMING")]
    fresh = [m for m in ranked if mv_room_ok(m) and m.get("slope1h", 0) > 0]
    return fresh, max(len(ranked) - len(fresh), 0)


def render_fresh_tab(ss, mst_s):
    st.markdown(_H("""<div style='background:linear-gradient(135deg,#14532d,#052e16);border-radius:18px;
    padding:18px 22px;margin-bottom:14px;'>
    <div style='color:white;font-size:20px;font-weight:900;'>🟢 FRESH BUYS — just starting, room left</div>
    <div style='color:#bbf7d0;font-size:12.5px;margin-top:6px;line-height:1.8;'>
    Only climbs that <b>JUST started</b>: day change small · price still near VWAP · slope turning up.
    The stocks that already ran keep looking tempting — but they are the ones that pull back and eat your money.
    This board hides them on purpose. Builds on the ⚡ radar (same scan, zero extra load).</div></div>"""),
        unsafe_allow_html=True)
    movers = ss.get("mv") or []
    if not movers:
        st.info("Start the ⚡ Live Movers radar first — this board fills from the same scan "
                "(no extra CPU). Then come back here.")
        return
    fresh, skipped = fresh_picks(movers)
    a1, a2, a3 = st.columns(3)
    with a1: st.metric("🟢 Fresh — buyable", len(fresh), "just started · room left")
    with a2: st.metric("🚫 Skipped — already ran", skipped, "these pull back — avoid")
    with a3: st.metric("🕒 Scan", ss.get("mv_ts_str") or "—")
    if not fresh:
        st.info("No FRESH climbs right now. The ones running have already stretched — buying them "
                "is how you become the exit liquidity. Wait; this board refills every radar scan. "
                f"({skipped} stretched climb(s) hidden)")
        return
    names = ss.get("mv_names") or {}
    for m in fresh[:40]:
        last, vw = m["last"], m.get("vwap") or m["last"]
        buy = round(min(last, vw * 1.001), 2)
        sl = round(min(vw * 0.995, buy * 0.995), 2)
        R = max(buy - sl, buy * 0.004)
        t1 = round(buy + 1.2 * R, 2)
        t2 = round(min(buy + 2.0 * R, buy * 1.035), 2)
        st.markdown(_H(
            f"<div style='background:#0f172a;border:1px solid #1e293b;border-left:3px solid #22c55e;"
            f"border-radius:12px;padding:10px 14px;margin:6px 0;'>"
            f"<div style='display:flex;justify-content:space-between;flex-wrap:wrap;gap:6px;'>"
            f"<b style='color:#f1f5f9;font-size:14px;'>{names.get(m['sym'], m['sym'].replace('.NS',''))}"
            f" <span style='color:#64748b;font-size:11px;'>{m['sym'].replace('.NS','')}</span></b>"
            f"<span style='color:#e2e8f0;font-family:monospace;font-weight:800;'>₹{last:,.2f} "
            f"<span style='color:#22c55e;font-size:11px;'>{m['chg_day']:+.2f}%</span></span></div>"
            f"<div style='color:#94a3b8;font-size:11px;margin-top:3px;'>"
            f"{'⚡ CLIMBING' if m['state']=='CLIMBING' else '🌱 FORMING'} · score {m['climb']:.0f} · "
            f"VWAP ₹{vw:,.2f} (<b style='color:#4ade80;'>{m.get('ext',0):+.2f}% above</b> = room left) · "
            f"1h {m['slope1h']:+.2f}%</div>"
            f"<div style='color:#e2e8f0;font-size:12px;font-family:monospace;margin-top:5px;'>"
            f"🎯 BUY dip ≤ <b style='color:#4ade80;'>₹{buy:,.2f}</b> · 🛑 SL <b style='color:#f87171;'>₹{sl:,.2f}</b> · "
            f"💰 T1 <b style='color:#fbbf24;'>₹{t1:,.2f}</b> · ✅ T2 <b style='color:#22c55e;'>₹{t2:,.2f}</b></div></div>"),
            unsafe_allow_html=True)
    st.caption("Plan maths: BUY at the dip near VWAP · SL 0.5% under VWAP · T1 +1.2R sell half · T2 +2R (max +3.5%). "
               "If price runs away without the dip — let it go, the next fresh one comes.")


def coach_volc_rows(got, watch, names):
    """🌋 VOLCANO rows from the coach's own live sweep — the eruption radar
    watches CONTINUOUSLY with the coach (every ~80 s), not just on combo scans."""
    out = []
    try:
        for s in watch or []:
            df = (got or {}).get(s)
            if df is None or len(df) < 14:
                continue
            out.append({"name": (names or {}).get(s, s.replace(".NS", "")), "sym": s,
                        "price": round(float(df["Close"].iloc[-1]), 2),
                        "chg_day": day_chg_from_intraday(df),
                        "volc": sleeper_detect(df, "live"),
                        "volc_day": sleeper_detect(df, "day")})
    except Exception:
        pass
    return out


def render_coach_tab(ss, mst_s):
    # ♾️ auto-resume
    if not ss.get("co_on"):
        _rt = rt_load().get("co") or {}
        if _rt.get("on") and _rt.get("watch"):
            if time.time() - (_rt.get("last_scan") or 0) > 2700:   # 🧹 stale (>45 min) — old data, start clean
                rt_clear("co")
                _rt = {}
        if _rt.get("on") and _rt.get("watch"):
            ss["co_on"] = True
            ss["co_watch"] = _rt["watch"]; ss["co_names"] = _rt.get("names") or {}
            ss["co_pos"] = _rt.get("pos") or {}
            ss["co_cap"] = _rt.get("cap") or COACH_CAP_DEFAULT
            ss["co_feed"] = _rt.get("feed") or []
            ss["co_log"] = _rt.get("log") or []
            ss["co_last"] = _rt.get("last_scan") or 0
            ss["co_ts"] = _rt.get("ts_str") or "—"
            ss["_co_resumed"] = True

    # 🚀 AUTO-START — the coach begins by itself after 9:20 on market days
    if (not ss.get("co_on") and mst_s == "open"
            and (now_ist().hour * 60 + now_ist().minute >= 9 * 60 + 20 or ss.get("up_kick"))
            and not up_wait_reason()          # ⏳ API-FIRST: hold for the Upstox login (till 9:35)
            and ss.get("co_stop_day") != now_ist().strftime("%Y-%m-%d")
            and ss.get("co_auto", False)     # 🚫 OFF by default
            and _pilot_ok("co", ss)):
        try:
            _top, _nm = coach_pick(int(ss.get("co_n") or COACH_N_DEFAULT))
        except Exception:
            _top, _nm = [], {}
        if _top:
            ss["co_on"] = True
            ss["co_watch"] = _top; ss["co_names"] = _nm
            ss["co_pos"] = {s: {"stage": "WAIT", "name": _nm[s]} for s in _top}
            ss["co_feed"] = []; ss["co_last"] = 0; ss["co_log"] = []
            rt_save("co", on=True, watch=_top, names=_nm, pos=ss["co_pos"],
                    cap=ss.get("co_cap") or COACH_CAP_DEFAULT, feed=[], last_scan=0,
                    ts_str="—", log=[])
            ss["_co_autostarted"] = True
            st.rerun()

    if not ss.get("co_on"):
        if mst_s == "open" and up_wait_reason():
            st.markdown("<div style='background:#3a2a06;border:1px solid #f59e0b;border-radius:12px;padding:12px 18px;"
                        "color:#fde68a;font-size:13px;line-height:1.8;'>⏳ <b>API-FIRST — coach is HOLDING for your "
                        "Upstox login.</b> Paste today's code in the 📡 panel below and press Activate — the coach "
                        "starts the same second. (No login today? Everything auto-starts on Yahoo at 9:35.)</div>",
                        unsafe_allow_html=True)
        st.markdown(_H("""<div style='background:linear-gradient(135deg,#0c4a6e,#164e63);border-radius:18px;
        padding:18px 22px;margin-bottom:14px;'>
        <div style='color:white;font-size:20px;font-weight:900;'>🎯 TRADE COACH — perfect stocks, perfect TIMING</div>
        <div style='color:#cffafe;font-size:12.5px;margin-top:6px;line-height:1.8;'>
        The coach picks the <b>few best stocks</b> from your ranked board (₹100–₹1000) at <b>9:20</b>,
        then watches every 5-minute candle and tells you <b>exactly when to BUY, SELL HALF, SELL REST or EXIT</b> —
        here and on Telegram. No thinking needed: follow the instructions instantly.<br>
        🟢 BUY when the candle confirms (breakout with volume / pullback holds VWAP) ·
        💰 T1 sell half · ✅ T2 sell rest · 🛑 stoploss · ⏰ time exit · 🔚 3:05 square-off</div></div>"""),
            unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            ss["co_cap"] = st.number_input("₹ Capital per trade (for qty suggestion)",
                                           min_value=1000, max_value=100000, step=500,
                                           value=int(ss.get("co_cap") or COACH_CAP_DEFAULT))
        with c2:
            ss["co_n"] = st.slider("How many perfect stocks to coach", 4, 10,
                                   int(ss.get("co_n") or COACH_N_DEFAULT))
            ss["co_auto"] = st.checkbox("🚀 Auto-start at 9:20 (coach begins by itself when the app is open)",
                                        value=bool(ss.get("co_auto", False)), key="co_auto_ck")
        if st.button("🎯 START COACH (run after the morning scan)", key="co_start", **STRETCH):
            if mst_s != "open":
                st.info("🔕 Market is CLOSED right now — the coach runs live only during market hours "
                        "(Mon–Fri 9:15–15:30 IST). After the next open: run the morning scan (⚡/🚀), "
                        "then come back and press START.")
                return
            with st.spinner("🎯 Picking today's perfect stocks from the ranked board…"):
                top, nm = coach_pick(int(ss.get("co_n") or COACH_N_DEFAULT))
            if not top:
                st.error("No perfect setups right now — press START again after the morning scan (⚡ or 🚀 tab).")
                return
            ss["co_on"] = True
            ss["co_watch"] = top; ss["co_names"] = nm
            ss["co_pos"] = {s: {"stage": "WAIT", "name": nm[s]} for s in top}
            ss["co_feed"] = []; ss["co_last"] = 0
            rt_save("co", on=True, watch=top, names=nm, pos=ss["co_pos"], cap=ss["co_cap"],
                    feed=[], last_scan=0, ts_str="—")
            st.rerun()
        st.caption("Best routine: ~9:05 run the morning scan (⚡/🚀) → 9:20 come here and START. "
                   "The coach does the watching — you do the clicking in your broker app.")
        st.markdown("<div style='background:#1c1206;border:1px solid #7c2d12;border-radius:12px;padding:10px 16px;"
                    "color:#fdba74;font-size:13px;line-height:1.8;'>🌋 <b>The VOLCANO eruption radar lives in this "
                    "tab.</b> It wakes up together with the coach (auto-start 9:20 on market days, or press START "
                    "above) — within ~1 minute of the first candle read you'll see the <b>🌋 VOLCANO — silent stock, "
                    "sudden BOOM</b> section right here: 💥 erupting now · 👀 magma building · 🕳️ sinkholes · "
                    "📜 today's eruption review.</div>", unsafe_allow_html=True)
        up_settings_ui("_co")
        return

    if ss.get("_co_resumed"):
        ss["_co_resumed"] = False
        st.info("♾️ Coach resumed automatically — a page refresh does NOT stop it. Press ⏹ Stop to end it.")
    if ss.get("_co_autostarted"):
        ss["_co_autostarted"] = False
        st.success("🚀 Coach AUTO-STARTED (market is open) — watching today's perfect stocks. "
                   "Instructions arrive here + on Telegram.")
    try:
        from streamlit_autorefresh import st_autorefresh
        if mst_s == "open":          # 🛌 after close: NO auto-refresh (free-CPU saver)
            st_autorefresh(interval=90 * 1000, key="co_tick")
    except Exception:
        pass

    if st.button("⏹ Stop coach", key="co_stop"):
        rt_clear("co")
        ss["co_on"] = False
        ss["co_stop_day"] = now_ist().strftime("%Y-%m-%d")
        st.rerun()

    _ph, _pht = coach_phase()
    _phc = {"morning": ("#052e16", "#22c55e"),
            "afternoon": ("#422006", "#f59e0b"),
            "late": ("#1e1b4b", "#818cf8")}[_ph]
    st.markdown(_H(f"<div style='background:{_phc[0]};border:1px solid {_phc[1]};border-radius:10px;"
                   f"padding:8px 14px;color:#e2e8f0;font-size:12.5px;font-weight:700;'>{_pht}</div>"),
                unsafe_allow_html=True)
    try:
        _rg = market_regime()
    except Exception:
        _rg = None
    if _rg:
        st.markdown(_H(f"<div style='background:#0b1220;border:1px solid {_rg['col']};border-radius:10px;"
                       f"padding:7px 14px;margin-top:4px;color:#e2e8f0;font-size:12px;'>"
                       f"{_rg['lab']} · NIFTY {_rg['chg']:+.2f}% — {_rg['tip']} "
                       f"<b>Position size auto-adjusted.</b></div>"), unsafe_allow_html=True)

    if not _pilot_ok("co", ss) and (rt_load().get("co") or {}).get("on"):
        st.caption("🤖 AUTOPILOT is driving the desk — live read-only view.")
    due = mst_s == "open" and time.time() - ss.get("co_last", 0) > 80
    _am_pilot = _pilot_ok("co", ss)
    if not _am_pilot:
        _co_view_sync(ss)                 # 🤖 autopilot drives — live view only
        if not ss.get("co_ctx") or time.time() - ss.get("co_ctx_ts", 0) > 300:
            try:
                with st.spinner("🎯 Reading live candles (view mode)…"):
                    _gotv, _ = _sweep(ss.get("co_watch") or [], "5m", "2d",
                                      with_daily=False, progress=False)
                ss["co_ctx"] = {s: coach_ctx(s, _gotv.get(s))
                                for s in (ss.get("co_watch") or [])}
                ss["co_ctx_ts"] = time.time()
                ss["co_volc"] = coach_volc_rows(_gotv, ss.get("co_watch") or [],
                                                ss.get("co_names"))   # 🌋 continuous watch
                ss["co_volc_ts"] = time.time()
            except Exception:
                pass
    if _am_pilot and (due or not ss.get("co_ctx")):
        _pilot_beat("co", ss)
        with st.spinner("🎯 Coach is reading the candles…"):
            got, _ = _sweep(ss["co_watch"], "5m", "2d", with_daily=False, progress=False)
        ctxs = {s: coach_ctx(s, got.get(s)) for s in ss["co_watch"]}
        ss["co_ctx"] = ctxs
        ss["co_volc"] = coach_volc_rows(got, ss["co_watch"], ss.get("co_names"))   # 🌋 continuous watch
        ss["co_volc_ts"] = time.time()
        feed = ss.get("co_feed") or []
        for s in ss["co_watch"]:
            try:
                events = coach_cycle(ctxs.get(s), ss["co_pos"][s], cap=int(ss.get("co_cap") or COACH_CAP_DEFAULT))
            except Exception:
                events = []
            for lvl, msg in events:
                if mst_s == "open":   # 🔕 trade instructions only while the market is LIVE
                    feed.insert(0, {"ts": now_ist().strftime("%H:%M:%S"), "lvl": lvl, "txt": msg})
                    tg_send(msg)
                    try:
                        st.toast(msg.split("·")[1][:60] if "·" in msg else msg[:60])
                    except Exception:
                        pass
        new_logs = coach_collect_log(ss.get("co_pos") or {})
        if new_logs:
            ss["co_log"] = (ss.get("co_log") or []) + new_logs
        _co_rt = rt_load().get("co") or {}
        _today = now_ist().strftime("%Y-%m-%d")
        _t_now = now_ist().hour * 60 + now_ist().minute
        if (mst_s == "open" and coach_phase(_t_now)[0] == "morning"
                and _co_rt.get("plan_day") != _today and ss.get("co_watch")):
            try:
                _rg = market_regime()
                _rgt = f"{_rg['lab']} ({_rg['chg']:+.2f}%)" if _rg else "regime n/a"
            except Exception:
                _rgt = "regime n/a"
            _nm = ", ".join((ss.get("co_names") or {}).get(s, s.replace(".NS", ""))
                            for s in ss["co_watch"][:8])
            if tg_send(f"\U0001F305 <b>MORNING PLAN \u00b7 {now_ist().strftime('%H:%M')}</b>\n"
                       f"\U0001F440 Watching: <b>{_esc(_nm)}</b>\n{_esc(_rgt)}\n"
                       f"\U0001F4B0 Capital <code>\u20B9{int(ss.get('co_cap') or COACH_CAP_DEFAULT):,}</code>/trade "
                       f"(auto-halved on soft days)\n"
                       f"<i>\u26A1 Momentum till 12:00 \u2192 \U0001F6E1\uFE0F support 12:00\u201314:30 \u2192 \U0001F51A square-off 15:05</i>"):
                rt_save("co", plan_day=_today)
        cons_lock_coach(ss)     # 🏅 after 10:15 snapshot: follow ONLY the stable picks
        ss["co_feed"] = feed[:60]
        ss["co_last"] = time.time()
        ss["co_ts"] = now_ist().strftime("%d %b %Y · %H:%M")
        rt_save("co", on=True, watch=ss["co_watch"], names=ss["co_names"], pos=ss["co_pos"],
                cap=ss.get("co_cap"), feed=ss["co_feed"], last_scan=ss["co_last"], ts_str=ss["co_ts"],
                log=ss.get("co_log") or [])

    # 📊 EVENING REPORT CARD — automatic, once/day after 15:10, survives cleanup
    try:
        _t_eod = now_ist().hour * 60 + now_ist().minute
        _eod_day = now_ist().strftime("%Y-%m-%d")
        if (ss.get("co_on") and _t_eod >= 15 * 60 + 10
                and (rt_load().get("co") or {}).get("eod_day") != _eod_day):
            if tg_send(coach_eod_summary(ss.get("co_log") or [],
                                         int(ss.get("co_cap") or COACH_CAP_DEFAULT)),
                       keep=True):
                rt_save("co", eod_day=_eod_day)
                try:
                    _cbrt = (rt_load().get("cb") or {}).get("combos") or []
                    _top = sorted([c for c in _cbrt if c.get("verdict") in ("🎯 PERFECT", "✅ MATCH")],
                                  key=lambda c: -(c.get("chg_day") or 0))[:5]
                    if _top:
                        _tl = "\n".join(f"{c['name']} {c['chg_day']:+.1f}% ({c['verdict']})" for c in _top)
                        tg_send("🏆 <b>COMBO BOARD · today's strongest agreements</b>\n" + _tl +
                                "\n<i>Live climb + calculation both agreed — the day's real leaders.</i>",
                                keep=True)
                except Exception:
                    pass
    except Exception:
        pass

    ctxs = ss.get("co_ctx") or {}
    posd = ss.get("co_pos") or {}
    holding = [s for s, p in posd.items() if p["stage"] == "HOLD"]
    done = [s for s, p in posd.items() if p["stage"] == "DONE"]
    a1, a2, a3, a4 = st.columns(4)
    with a1: st.metric("👀 Watching", len(ss["co_watch"]) - len(holding) - len(done))
    with a2: st.metric("💰 In trade", len(holding))
    with a3:
        wins = [p.get("res") for p in posd.values() if p["stage"] == "DONE" and (p.get("res") or 0) > 0]
        st.metric("✅ Closed", len(done), f"{len(wins)} green")
    with a4: st.metric("🕒 Last read", ss.get("co_ts") or "—")

    cards = list(ss["co_watch"])
    for i in range(0, len(cards), 2):
        cc = st.columns(2)
        for j, s in enumerate(cards[i:i + 2]):
            with cc[j]:
                p = posd.get(s) or {"stage": "WAIT"}
                ctx = ctxs.get(s)
                act, actc = coach_action_text(s, p, ctx)
                last = ctx["last"] if ctx else (p.get("entry") or 0)
                chg = ctx["chg_day"] if ctx else 0.0
                pnl = (last / p["entry"] - 1) * 100 if (p.get("entry") and p["stage"] == "HOLD") else None
                lv = ""
                if p["stage"] == "HOLD":
                    lv = (f"<div style='color:#94a3b8;font-size:10.5px;font-family:monospace;margin-top:4px;'>"
                          f"BUY ₹{p['entry']:,.2f} · SL ₹{p['sl']:,.2f} · T1 ₹{p['t1']:,.2f} · T2 ₹{p['t2']:,.2f}"
                          + (f" · <b style='color:{'#4ade80' if (pnl or 0) >= 0 else '#f87171'};'>LIVE {pnl:+.1f}%</b>"
                             if pnl is not None else "") + "</div>")
                st.markdown(_H(
                    f"<div style='background:#0f172a;border:1px solid #1e293b;border-left:3px solid "
                    f"{'#fbbf24' if p['stage']=='HOLD' else '#22c55e' if p['stage']=='DONE' else '#334155'};"
                    f"border-radius:12px;padding:10px 14px;margin:6px 0;'>"
                    f"<div style='display:flex;justify-content:space-between;flex-wrap:wrap;gap:6px;'>"
                    f"<b style='color:#f1f5f9;font-size:14px;'>{(ss.get('co_names') or {}).get(s, s.replace('.NS',''))}</b>"
                    f"<span style='color:#e2e8f0;font-family:monospace;font-weight:800;'>₹{last:,.2f} "
                    f"<span style='color:{'#22c55e' if chg >= 0 else '#ef4444'};font-size:11px;'>{chg:+.2f}%</span></span></div>"
                    f"<div style='color:{actc};font-weight:900;font-size:12.5px;margin-top:4px;'>{act}</div>{lv}</div>"),
                    unsafe_allow_html=True)

    feed = ss.get("co_feed") or []
    if feed:
        with st.expander(f"📣 COACH INSTRUCTIONS — today ({len(feed)})", expanded=True):
            for f in feed[:20]:
                col = {"buy": "#4ade80", "t1": "#fbbf24", "t2": "#22c55e",
                       "sl": "#f87171", "exit": "#f87171", "time": "#93c5fd", "eod": "#93c5fd"}.get(f["lvl"], "#94a3b8")
                st.markdown(f"<div style='border-left:3px solid {col};background:#0b1220;border-radius:8px;"
                            f"padding:6px 12px;margin:4px 0;color:#e2e8f0;font-size:12px;white-space:pre-line;'>"
                            f"<span style='color:#64748b;'>{f['ts']}</span> · {f['txt']}</div>",
                            unsafe_allow_html=True)
    _log = ss.get("co_log") or []
    if _log:
        with st.expander(f"📊 COACH REPORT CARD — today ({len(_log)} trades)", expanded=True):
            _n = len(_log); _wins = [t for t in _log if (t.get("res") or 0) > 0]
            _avg = sum(t.get("res") or 0 for t in _log) / _n
            _capu = int(ss.get("co_cap") or COACH_CAP_DEFAULT)
            _r1, _r2, _r3, _r4 = st.columns(4)
            with _r1: st.metric("Trades", _n)
            with _r2: st.metric("Win rate", f"{len(_wins) * 100 // _n}%")
            with _r3: st.metric("Avg result", f"{_avg:+.2f}%")
            with _r4: st.metric("Est P&L", f"₹{sum((t.get('res') or 0) * _capu / 100 for t in _log):,.0f}",
                                f"on ₹{_capu:,}/trade")
            try:
                st.dataframe(pd.DataFrame([{"Stock": t["name"], "Entry": t.get("entry"),
                                            "Result%": t.get("res"),
                                            "Outcome": {"sl": "🛑 SL", "t1": "💰 T1+SL", "t2": "✅ T2",
                                                        "exit": "⚠️ exit", "time": "⏰ time",
                                                        "eod": "🔚 EOD"}.get(t.get("outcome"), t.get("outcome")),
                                            "Setup": (t.get("sig") or "")[:44], "Closed": t.get("ts")}
                                           for t in _log]),
                             use_container_width=True, hide_index=True)
            except Exception:
                for t in _log:
                    st.markdown(f"- **{t['name']}** {t.get('res'):+.1f}% ({t.get('outcome')})")

    # ── 🌋 VOLCANO — lives HERE now: the coach watches continuously ──
    try:
        _vrows = list(ss.get("co_volc") or [])
        _cbr = ss.get("cb") or []
        if _cbr:
            _seen = {r["sym"] for r in _vrows}
            _vrows += [c for c in _cbr if c.get("sym") not in _seen
                       and (c.get("volc") or c.get("volc_day"))]
        if _vrows:
            _volc_ui(_vrows, mst_s)
    except Exception:
        pass

    with st.expander("📖 How the coach decides"):
        st.markdown("""<div style='color:#94a3b8;font-size:12.5px;line-height:1.9;'>
        🟢 <b style='color:#4ade80;'>BUY (morning, till 12:00)</b> — only when a 5-min candle CONFIRMS: session-high breakout
        with 1.3× volume, or a pullback that holds VWAP and turns up. Never chases spikes, never if already ran &gt; 4%.<br>
        ☀️ <b style='color:#fbbf24;'>AFTERNOON SUPPORT MODE (12:00–14:30)</b> — fresh climbs tend to fade after noon, so the
        coach takes no new momentum buys. It only takes <b>support bounces</b>: a pullback that holds its support
        (VWAP / morning low — the buy zone is on each card) and stabilizes with a green candle. Book fast, tight SL.<br>
        💰 <b style='color:#fbbf24;'>T1</b> = +1R → sell HALF, stoploss moves to entry (profit locked).<br>
        ✅ <b style='color:#22c55e;'>T2</b> = +1.8R (max +3.5%) → sell the rest.<br>
        🛑 <b style='color:#f87171;'>STOPLOSS</b> below VWAP/recent lows — exit all, small loss.<br>
        ⚠️ <b style='color:#f87171;'>MOMENTUM EXIT</b> — falls below VWAP on a red candle.<br>
        ⏰ <b style='color:#93c5fd;'>TIME EXIT</b> — after 11:30 the trade goes nowhere (−0.3%…+0.4%) → rotate.<br>
        🔚 <b style='color:#93c5fd;'>SQUARE OFF</b> — 15:05, intraday isn't carried overnight.<br>
        Refresh is ~90 s on free Yahoo data — good enough for 5-min candle timing.</div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# 📡 UPSTOX LIVE QUOTES — optional real-time layer over Yahoo
#   Yahoo stays the backbone (history + charts + scans). When an Upstox
#   token is active, every scan cycle ALSO pulls tick-fresh last-traded
#   prices (up to 500 per request) and splices them onto the newest
#   candle — states, alerts & coach instructions react in seconds.
#   Anything fails / no token → silent Yahoo fallback. Zero crash risk.
#   Credentials live ONLY inside this app instance — never in GitHub.
# ══════════════════════════════════════════════════════════════════
UP_REDIRECT_DEFAULT = "https://api.upstox.com"
UP_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
         "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
_UP_LTP = {}        # {sym: (price, ts)} in-memory live-price cache
_UP_TICKS = {}      # {sym: [(epoch, price, cum_volume), …]} live tick stream (fallback builder)
_UP_ID5 = {"ts": {}, "df": {}}   # 📡 5-min fallback candle cache (per symbol, 100 s)
_UP_CANDLE_CACHE = {"d": None, "df": {}, "saved": 0}   # last-good Yahoo candles, per day
_UP_KEYS = {"d": None, "m": {}}   # daily instrument-key map, in memory


def up_file():
    return f"upstox_{_ukey()}.json"   # ☁️ never used — backup runs on Yahoo only


def up_load():
    d = {"key": "", "secret": "", "redirect": UP_REDIRECT_DEFAULT, "token": "", "exp": 0,
         "atok": "", "aexp": ""}
    try:
        if _os.path.exists(up_file()):
            j = _json.load(open(up_file(), encoding="utf-8"))
            if isinstance(j, dict):
                for k in d:
                    if j.get(k) is not None:
                        d[k] = j[k]
    except Exception:
        pass
    # 🔐 CLOUD SECRETS — token pasted once in Streamlit Cloud → Settings → Secrets;
    #    survives every redeploy (files on the cloud are wiped on each rebuild)
    try:
        if not d.get("atok") and st.secrets and st.secrets.get("upstox"):
            _s = st.secrets["upstox"]
            d["atok"] = str(_s.get("atok") or "")
            d["aexp"] = str(_s.get("aexp") or "")
    except Exception:
        pass
    return d


def up_save(key, secret, redirect=None):
    d = up_load()
    d.update({"key": key.strip(), "secret": secret.strip(),
              "redirect": (redirect or d.get("redirect") or UP_REDIRECT_DEFAULT).strip()})
    if not (key.strip() and secret.strip()):
        d["token"], d["exp"] = "", 0
    try:
        _json.dump(d, open(up_file(), "w", encoding="utf-8"))
        return True
    except Exception:
        return False


def _atok_live(d):
    """Is the 1-year analytics token still valid?"""
    exp = str(d.get("aexp") or "")
    return bool(d.get("atok")) and (not exp or exp >= now_ist().strftime("%Y-%m-%d"))


def up_token_valid():
    try:
        return _atok_live(up_load())   # ☁️ Yahoo primary; Upstox auto-fallback ONLY
    except Exception:                  #    if a token exists (file or Secrets)
        return False


def up_auth_token():
    """A VALID token for the Bearer header — live analytics first, live OAuth
    second, "" last (never send an expired token)."""
    try:
        d = up_load()
        if _atok_live(d):
            return d["atok"]
        if d.get("token") and time.time() < float(d.get("exp") or 0) - 120:
            return d["token"]
        return ""
    except Exception:
        return ""


def up_save_atok(tok):
    d = up_load()
    tok = (tok or "").strip()
    d["atok"] = tok
    d["aexp"] = (now_ist() + _dtd(days=365)).strftime("%Y-%m-%d") if tok else ""
    try:
        _json.dump(d, open(up_file(), "w", encoding="utf-8"))
        return True
    except Exception:
        return False


def up_wait_reason():
    """⏳ API-FIRST — if Upstox keys are saved but today's token isn't activated
    yet, the 9:20 auto-starts HOLD (window 9:20–9:35 only) so you can paste the
    login code calmly. Activate → everything starts instantly (up_kick).
    Skip the login → engines start on Yahoo at 9:35 anyway."""
    try:
        d = up_load()
        if not (d.get("key") and d.get("secret")):
            return None                      # no keys configured → never wait
        if up_token_valid():
            return None
        n = now_ist()
        m = n.hour * 60 + n.minute
        if 9 * 60 + 20 <= m < 9 * 60 + 35:
            return "upstox_login"
    except Exception:
        return None
    return None


def up_login_url():
    import urllib.parse as _upp
    d = up_load()
    q = _upp.urlencode({"client_id": d["key"], "redirect_uri": d["redirect"],
                        "response_type": "code"})
    return f"https://api.upstox.com/v2/login/authorization/dialog?{q}"


def up_activate(code):
    """Exchange the one-time login code for an all-day access token
    (Upstox tokens expire at 3:30 AM IST — quick re-login each morning)."""
    d = up_load()
    code = (code or "").strip().split("code=")[-1].split("&")[0].strip()
    if not (d.get("key") and d.get("secret")):
        return False, "Save API Key + Secret first."
    if not code:
        return False, "Paste the code from the browser address bar first."
    try:
        import urllib.parse as _up
        req = urllib.request.Request(
            "https://api.upstox.com/v2/login/authorization/token",
            data=_up.urlencode({"code": code, "client_id": d["key"], "client_secret": d["secret"],
                                "redirect_uri": d["redirect"],
                                "grant_type": "authorization_code"}).encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded",
                     "Accept": "application/json", "User-Agent": UP_UA,
                     "Accept-Language": "en-US,en;q=0.9"})
        r = _json.loads(urllib.request.urlopen(req, timeout=15).read().decode("utf-8"))
        tok = r.get("access_token") or (r.get("data") or {}).get("access_token") or ""
        exp_in = float(r.get("expires_in") or (r.get("data") or {}).get("expires_in") or 86400)
        if not tok:
            return False, "Upstox did not return a token — check Key/Secret/Redirect URI."
        try:   # Upstox says "expires_in 86400" but REALLY dies at the next 3:30 AM IST —
            import calendar as _cal          # cap it so the box never shows a fake 🟢
            _n = now_ist().replace(hour=3, minute=30, second=0, microsecond=0)
            if _n <= now_ist():
                _n += _dtd(days=1)
            _cap = _cal.timegm(_n.timetuple()) - 19800   # next 3:30 AM IST → epoch
        except Exception:
            _cap = time.time() + 86400
        d["token"], d["exp"] = tok, min(time.time() + min(exp_in, 86400), _cap)
        _json.dump(d, open(up_file(), "w", encoding="utf-8"))
        return True, "LIVE"
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode()
            msg = ""
            if "cloudflare" in body.lower() or "error 1010" in body.lower():
                return False, "Upstox firewall blocked the request — press Activate again."
            try:
                msg = (_json.loads(body).get("errors") or [{}])[0].get("message", "")[:110]
            except Exception:
                pass
        except Exception:
            msg = ""
        if "client_id" in (msg or "").lower() or "client_secret" in (msg or "").lower():
            return False, ("Upstox says the API Key or SECRET is wrong. Go to "
                           "account.upstox.com/developer/apps → use the COPY button on both "
                           "(don't type by hand) → paste here → 💾 Save → fresh login code → Activate.")
        if "redirect" in (msg or "").lower():
            return False, ("Redirect URI mismatch — it must EXACTLY match the Redirect URI field "
                           "of your Upstox app (check for missing 's' in https, trailing '/').")
        if "segment" in (msg or "").lower():
            return False, ("Your Upstox account segments are not active — reactivate from the "
                           "Upstox app/web (Profile → Reactivate), then login again.")
        return False, (f"Upstox rejected it: {msg or 'check the code'}. "
                       f"Codes expire in minutes — login again & paste a fresh one.")
    except Exception as e:
        return False, f"Network issue — try again ({type(e).__name__})."


def up_keys_map(syms):
    """sym.NS → Upstox instrument_key via the instrument master (cached 1×/day)."""
    today = now_ist().strftime("%Y-%m-%d")
    fn = f"upstox_keys_{_ukey()}.json"
    if _UP_KEYS.get("d") != today:
        try:
            if _os.path.exists(fn):
                j = _json.load(open(fn, encoding="utf-8"))
                if j.get("d") == today:
                    _UP_KEYS.update({"d": today, "m": j.get("m") or {}})
        except Exception:
            pass
    # 🩹 load ONCE per day. (The old subset check re-downloaded the ENTIRE
    #    15 MB master on every call whenever a dead ticker was in the list —
    #    a hidden 10+ minute tax that made every big sweep die.)
    if _UP_KEYS.get("d") != today:
        try:
            import gzip as _gz
            rq = urllib.request.Request(
                "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz",
                headers={"User-Agent": UP_UA, "Accept": "*/*"})
            raw = _gz.decompress(urllib.request.urlopen(rq, timeout=45).read())
            mm = {}
            for r in _json.loads(raw):
                if r.get("segment") == "NSE_EQ" and r.get("trading_symbol"):
                    mm[r["trading_symbol"]] = r.get("instrument_key") or ""
            _UP_KEYS.update({"d": today, "m": mm})
            try:
                _json.dump({"d": today, "m": mm}, open(fn, "w", encoding="utf-8"))
            except Exception:
                pass
        except Exception:
            _UP_KEYS.update({"d": today, "m": _UP_KEYS.get("m") or {}})   # no retry storm
    want = {s.replace(".NS", ""): s for s in syms}
    return {v: _UP_KEYS["m"].get(k, "") for k, v in want.items() if _UP_KEYS["m"].get(k)}


def up_prefetch(syms):
    """1 batched call per ~500 symbols → tick-fresh prices + day cumulative
    volume into _UP_LTP/_UP_TICKS (the fallback candle builder's raw material).
    No token / any failure → returns False, scans stay on Yahoo untouched."""
    try:
        if not up_token_valid() or not syms:
            return False
        d = up_load()
        kmap = up_keys_map(list(syms))
        if not kmap:
            return False
        rev = {k: s for s, k in kmap.items()}
        vals = list(kmap.values())
        got_n, now = 0, time.time()
        for i in range(0, len(vals), 500):
            req = urllib.request.Request(
                "https://api.upstox.com/v2/market-quote/ohlc?interval=1d&instrument_key="
                + ",".join(vals[i:i + 500]),
                headers={"Accept": "application/json", "User-Agent": UP_UA,
                         "Authorization": f"Bearer {up_auth_token()}"})
            data = (_json.loads(urllib.request.urlopen(req, timeout=8)
                                .read().decode("utf-8")) or {}).get("data") or {}
            for k, v in data.items():
                s = rev.get(k)
                if not (s and isinstance(v, dict) and v.get("last_price")):
                    continue
                px = float(v["last_price"])
                try:
                    cv = float(v.get("volume") or 0)
                except Exception:
                    cv = 0.0
                _UP_LTP[s] = (px, now)
                _UP_TICKS.setdefault(s, []).append((now, px, cv))
                if len(_UP_TICKS[s]) > 300:
                    _UP_TICKS[s] = _UP_TICKS[s][-300:]
                got_n += 1
        return got_n > 0
    except Exception:
        return False


def up_patch_df(sym, df):
    """Splice the tick-fresh LTP onto the newest candle (Close; High/Low if broken)."""
    try:
        hit = _UP_LTP.get(sym)
        if not hit or time.time() - hit[1] > 300 or df is None or len(df) == 0:
            return df
        px = float(hit[0])
        i = len(df) - 1
        df.iloc[i, df.columns.get_loc("Close")] = px
        if px > float(df.iloc[i]["High"]):
            df.iloc[i, df.columns.get_loc("High")] = px
        if px < float(df.iloc[i]["Low"]):
            df.iloc[i, df.columns.get_loc("Low")] = px
    except Exception:
        pass
    return df


def up_cache_load():
    """📡 Last-good Yahoo candles for TODAY (pickle, one file per day)."""
    today = now_ist().strftime("%Y-%m-%d")
    if _UP_CANDLE_CACHE.get("d") == today:
        return _UP_CANDLE_CACHE["df"]
    df = {}
    try:
        import pickle as _pk
        fn = f"candle_cache_{_ukey()}_{today}.pkl"
        if _os.path.exists(fn):
            df = _pk.load(open(fn, "rb")) or {}
    except Exception:
        df = {}
    _UP_CANDLE_CACHE.update({"d": today, "df": df})
    return df


def up_cache_save(got):
    """📡 Healthy Yahoo sweep → remember the candles (disk writes throttled)."""
    try:
        if not got:
            return
        cache = up_cache_load()
        cache.update(got)
        _UP_CANDLE_CACHE["df"] = cache
        if time.time() - (_UP_CANDLE_CACHE.get("saved") or 0) > 120:
            _UP_CANDLE_CACHE["saved"] = time.time()
            import pickle as _pk
            today = now_ist().strftime("%Y-%m-%d")
            _pk.dump(cache, open(f"candle_cache_{_ukey()}_{today}.pkl", "wb"))
    except Exception:
        pass


def up_fallback_candles(syms):
    """📡 UNINTERRUPTED — 5-minute candles built from the last-good Yahoo
    cache + the live Upstox tick stream (same-day data only). Candle volume
    is approximated from cumulative-volume deltas between ticks. Used ONLY
    when Yahoo is blocked and a valid Upstox token exists."""
    out = {}
    try:
        cache = up_cache_load()
        for s in syms:
            try:
                parts, last_end = [], 0
                base = cache.get(s)
                if base is not None and len(base):
                    b = base[base.index.date == base.index[-1].date()]
                    if len(b):
                        parts.append(b[["Open", "High", "Low", "Close", "Volume"]])
                        last_end = int(b.index[-1].timestamp()) + 300
                ticks = [t for t in (_UP_TICKS.get(s) or []) if t[0] > last_end]
                if ticks:
                    buckets = {}
                    for ts, px, cv in ticks:
                        buckets.setdefault(int(ts) - int(ts) % 300, []).append((px, cv))
                    rows = []
                    for k in sorted(buckets):
                        pts = buckets[k]
                        pxs = [p for p, _ in pts]
                        cvs = [c for _, c in pts if c and c > 0]
                        vol = (max(cvs) - min(cvs)) if len(cvs) >= 2 else 0.0
                        rows.append((k, pxs[0], max(pxs), min(pxs), pxs[-1], max(vol, 0.0)))
                    if rows:
                        ts_idx = pd.to_datetime([r[0] for r in rows], unit="s", utc=True)
                        fb = pd.DataFrame([r[1:] for r in rows],
                                          columns=["Open", "High", "Low", "Close", "Volume"],
                                          index=pd.DatetimeIndex(ts_idx).tz_convert("Asia/Calcutta"))
                        parts.append(fb)
                if parts:
                    df = pd.concat(parts).sort_index()
                    df = df[~df.index.duplicated(keep="last")]
                    out[s] = df[["Open", "High", "Low", "Close", "Volume"]].astype(float)
            except Exception:
                continue
    except Exception:
        pass
    return out


def up_intraday_candles(syms):
    """📡 TRUE FALLBACK — today's REAL candles from Upstox (1-min intraday,
    resampled to 5-min), fetched by 6 PARALLEL workers so a 500-stock board
    rebuilds in ~30 s (the old sequential version was too slow for the page's
    auto-refresh — that caused the endless 'scanning' loop). Per-symbol cache
    keeps repeat cycles light."""
    out = {}
    try:
        if not up_token_valid() or not syms:
            return out
        now = time.time()
        todo = [s for s in syms
                if now - (_UP_ID5.get("ts") or {}).get(s, 0) > 100]
        for s in syms:
            if s not in todo and s in (_UP_ID5.get("df") or {}):
                out[s] = _UP_ID5["df"][s]
        if not todo:
            return out
        kmap = up_keys_map(todo)
        tok = up_auth_token()

        def _pull(item):
            s, k = item
            try:
                rq = urllib.request.Request(
                    f"https://api.upstox.com/v2/historical-candle/intraday/{k}/1minute",
                    headers={"Accept": "application/json", "User-Agent": UP_UA,
                             "Authorization": f"Bearer {tok}"})
                r = _json.loads(urllib.request.urlopen(rq, timeout=8).read().decode("utf-8"))
                candles = (r.get("data") or {}).get("candles") or []
                if not candles:
                    return s, None
                df = pd.DataFrame([c[:6] for c in candles],
                                  columns=["ts", "Open", "High", "Low", "Close", "Volume"])
                df.index = pd.to_datetime(df["ts"])
                try:
                    df.index = df.index.tz_convert("Asia/Calcutta")
                except Exception:
                    pass
                df = df[["Open", "High", "Low", "Close", "Volume"]].astype(float)
                agg = df.resample("5min").agg(
                    {"Open": "first", "High": "max", "Low": "min",
                     "Close": "last", "Volume": "sum"}).dropna()
                return s, (agg if len(agg) else None)
            except Exception:
                return s, None

        try:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=6) as ex:
                for s, df in ex.map(_pull, [it for it in kmap.items()]):
                    if df is not None:
                        out[s] = df
                        _UP_ID5.setdefault("ts", {})[s] = time.time()
                        _UP_ID5.setdefault("df", {})[s] = df
        except Exception:
            pass
    except Exception:
        pass
    return out


def up_daily_candles(syms):
    """📡 daily-history fallback (6mo OHLCV per symbol) — fetched ONCE per day,
    then disk-cached (pickle) — keeps trend/200EMA/signal verdicts real during
    a Yahoo outage."""
    out = {}
    try:
        if not up_token_valid() or not syms:
            return out
        today = now_ist().strftime("%Y-%m-%d")
        fn = f"upstox_daily_{_ukey()}_{today}.pkl"
        cache = {}
        try:
            import pickle as _pk
            if _os.path.exists(fn):
                cache = _pk.load(open(fn, "rb")) or {}
        except Exception:
            cache = {}
        todo = [s for s in syms if s not in cache]
        out.update({s: cache[s] for s in syms if s in cache})
        if not todo:
            return out
        kmap = up_keys_map(todo)
        tok = up_auth_token()
        _frm = (now_ist() - _dtd(days=400)).strftime("%Y-%m-%d")
        _to = now_ist().strftime("%Y-%m-%d")

        def _pull(item):
            s, k = item
            try:
                rq = urllib.request.Request(
                    f"https://api.upstox.com/v2/historical-candle/{k}/day/{_to}/{_frm}",
                    headers={"Accept": "application/json", "User-Agent": UP_UA,
                             "Authorization": f"Bearer {tok}"})
                r = _json.loads(urllib.request.urlopen(rq, timeout=8).read().decode("utf-8"))
                candles = (r.get("data") or {}).get("candles") or []
                if not candles:
                    return s, None
                df = pd.DataFrame([c[:6] for c in candles],
                                  columns=["ts", "Open", "High", "Low", "Close", "Volume"])
                df.index = pd.to_datetime(df["ts"])
                try:
                    df.index = df.index.tz_convert("Asia/Calcutta")
                except Exception:
                    pass
                df = df[["Open", "High", "Low", "Close", "Volume"]].astype(float)
                return s, (df if len(df) >= 30 else None)
            except Exception:
                return s, None

        try:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=6) as ex:
                for s, df in ex.map(_pull, [it for it in kmap.items()]):
                    if df is not None:
                        out[s] = df
                        cache[s] = df
        except Exception:
            pass
        try:
            import pickle as _pk
            _pk.dump(cache, open(fn, "wb"))
        except Exception:
            pass
    except Exception:
        pass
    return out


def feed_status():
    """('yahoo' | 'fallback', 'HH:MM') — is the Upstox fallback carrying the desk?"""
    try:
        fb, yok = _FEED.get("fb") or 0, _FEED.get("yahoo_ok") or 0
        if fb > yok and time.time() - fb < 900:
            m = int((fb + 19800) % 86400)
            return "fallback", f"{m // 3600:02d}:{(m % 3600) // 60:02d}"
    except Exception:
        pass
    return "yahoo", ""


def up_settings_ui(tag=""):
    st.caption("☁️ CLOUD DESK — Yahoo data, refreshes every 2 min. Optional armor: paste your "
               "Upstox token in Streamlit Cloud → Settings → Secrets → automatic fallback if "
               "Yahoo ever throttles this app too (one time, survives every update).")


def tg_settings_ui(tag=""):
    with st.expander("🔔 TELEGRAM ALERTS (optional — get alerts on your phone)"):
        cfg = tg_load()
        c1, c2 = st.columns(2)
        with c1:
            tok = st.text_input("Bot token (@BotFather)", value=cfg.get("token", ""),
                                type="password", key=f"tg_tok{tag}")
        with c2:
            chat = st.text_input("Chat ID(s) — comma-separate for brother/family",
                                 value=cfg.get("chat", ""), key=f"tg_chat{tag}")
        b1, b2 = st.columns(2)
        with b1:
            if st.button("💾 Save Telegram settings", key=f"tg_save{tag}", **STRETCH):
                if tok.strip() and chat.strip():
                    tg_save(tok.strip(), chat.strip())
                    st.success("Saved ✓ — alerts will now reach every chat ID above (keep this app running).")
                else:
                    st.error("Paste both the token and your chat ID first.")
        with b2:
            if st.button("📨 Send test message", key=f"tg_test{tag}", **STRETCH):
                if tg_send("\u2705 <b>AI Trader Pro \u2014 Telegram alerts are working!</b>\n"
                           "You will get \u26A1 climb and \U0001F680 support-bounce alerts here.",
                           keep=True):
                    st.success("Sent! Check your Telegram app. 🎉")
                else:
                    st.error("Couldn't send — press 💾 Save first, and double-check token & chat ID.")
        if st.button("📱 Send 4 EXAMPLE alerts — see the NEW message format",
                     key=f"tg_ex{tag}", **STRETCH):
            _ex_ok = 0
            if tg_send("🚀 <b>HOT ALERT · CHENNPETRO</b> · 🆕 <b>NEW</b>\n"
                       "<i>📱 FORMAT EXAMPLE — not a real signal</i>\n"
                       "🌅 opening mover · 2 candle-closes held — live now\n"
                       "₹1515.5 · +₹21.4 from open (+3.6% today)\n"
                       "🟢 5-min candle LIVE (~2 min left) · buy zone ₹1500.0–₹1515.5 — "
                       "buy INSIDE this candle, don't chase above it\n"
                       "⛔ this 5-min candle CLOSING below ₹1483.4 = spike, skip\n"
                       "📐 S2 ₹1442.1 · S1 ₹1463.8 · pivot ₹1489.2 · R1 ₹1514.6 · R2 ₹1536.3\n"
                       "📍 now ₹1515.5 — above R1 — breakout territory\n"
                       "⚠️ Fresh mover — NOT a combo pick · use your stop loss", keep=True):
                _ex_ok += 1
            if tg_send("✅ <b>HOT ALERT +2% · KOLTEPATIL</b> · 🔁 <b>GOING WELL</b> · "
                       "alert #2 today · since 🚀 12:05 @ ₹435.0: <b>+2.2%</b> — "
                       "keep an eye on this one\n"
                       "₹444.6 — target reached (alert was ₹435.0 at 12:05).\n"
                       "Book profit or trail your stop loss.\n"
                       "<i>📱 FORMAT EXAMPLE — not a real signal</i>", keep=True):
                _ex_ok += 1
            if tg_send("⚡ <b>RE-IGNITED · SSWL</b> · 🔁 <b>GOING WELL</b> · "
                       "alert #3 today · since 🚀 09:29 @ ₹398.0: <b>+12.6%</b> — "
                       "keep an eye on this one\n"
                       "faded at 09:44 — now back ABOVE the alert price ₹398.0\n"
                       "₹448.0 · +12.6% from the alert price\n"
                       "the move is running AGAIN — keep an eye on this one\n"
                       "⚠️ tracking notice — not a new pick · use your stop loss\n"
                       "<i>📱 FORMAT EXAMPLE — not a real signal</i>", keep=True):
                _ex_ok += 1
            if tg_send("\U0001F305 <b>NIFTY MORNING ROADMAP \u00b7 Mon 26 Oct</b>\n"
                       "gapped DOWN \u22120.42% \u2014 stocks bouncing off crashed opens (falling "
                       "knives) \u00b7 opening rockets carry extra risk today \u00b7 \U0001F504 "
                       "recovery alerts are the honest signal\n"
                       "\U0001F534 NIFTY now \u22120.45% vs prev close\n"
                       "One-time morning read \u2014 radars running.\n"
                       "<i>\U0001F4F1 FORMAT EXAMPLE \u2014 not a real signal</i>", keep=True):
                _ex_ok += 1
            if _ex_ok:
                st.success(f"{_ex_ok}/4 example alerts sent — check Telegram! "
                           "These show the NEW format (5-min candle line + levels + "
                           "badges + re-ignition). They are previews only, not signals.")
            else:
                st.error("Couldn't send — press 💾 Save first, and double-check token & chat ID.")
        b3, b4 = st.columns(2)
        with b3:
            if st.button("🔍 Diagnose connection", key=f"tg_diag{tag}", **STRETCH):
                cfg = tg_load()
                src_txt = ("built-in (you + brother)" if cfg.get("token") == TG_DEFAULT_TOKEN
                           and cfg.get("chat") == TG_DEFAULT_CHAT else "CUSTOM — saved in this app")
                try:
                    rq = urllib.request.Request(f"https://api.telegram.org/bot{cfg['token']}/getMe")
                    me = (_json.loads(urllib.request.urlopen(rq, timeout=8).read())
                          .get("result") or {})
                    st.info(f"🤖 Bot @{me.get('username', '?')} reachable · config: {src_txt}")
                except Exception as e:
                    st.error(f"Bot token problem: {e}")
                for cid in [c.strip() for c in str(cfg.get("chat", "")).split(",") if c.strip()]:
                    ok, why = tg_send_one(cid, "🔍 AI Trader Pro test — if you can read this, "
                                               "Telegram alerts to this chat work!\n"
                                               f"<i>🕘 {now_ist().strftime('%a %d %b %Y · %H:%M IST')} · ☁️ CLOUD</i>",
                                               keep=True)
                    if ok:
                        st.success(f"✅ {cid} — DELIVERED")
                    else:
                        st.error(f"❌ {cid} — {why}")
        with b4:
            if st.button("♻️ Reset to built-in (you + brother)", key=f"tg_rst{tag}", **STRETCH):
                tg_save(TG_DEFAULT_TOKEN, TG_DEFAULT_CHAT)
                st.success("Reset ✓ — alerts now go to you + brother again.")
        st.caption("Each person who wants alerts: open the bot link (t.me/…), press START, then get their Id "
                   "from @userinfobot. Paste IDs separated by commas — e.g. 123456789,987654321 — and everyone "
                   "gets every alert. Stored ONLY inside your app instance — never share publicly. "
                   "Daily alerts auto-delete after close (15:35) — only report cards stay.")


def rt_clear(engine):
    try:
        d = rt_load()
        d.pop(engine, None)
        with open(runtime_file(), "w", encoding="utf-8") as f:
            _json.dump(d, f)
    except Exception:
        pass

_JOURNAL = "trade_journal.json"


def journal_load():
    fn = journal_file()
    try:
        if _os.path.exists(fn):
            with open(fn, "r", encoding="utf-8") as f:
                return _json.load(f)
        if _ukey() == "main" and _os.path.exists(_JOURNAL):   # adopt old file
            with open(_JOURNAL, "r", encoding="utf-8") as f:
                return _json.load(f)
    except Exception:
        pass
    return []


def journal_save(entry):
    try:
        data = journal_load()
        entry["id"] = f"{entry['sym']}_{entry['saved']}"
        data = [d for d in data if d.get("id") != entry["id"]]
        data.append(entry)
        with open(journal_file(), "w", encoding="utf-8") as f:
            _json.dump(data, f, indent=2)
        return True
    except Exception:
        return False


def journal_delete(entry_id):
    try:
        data = [d for d in journal_load() if d.get("id") != entry_id]
        with open(journal_file(), "w", encoding="utf-8") as f:
            _json.dump(data, f, indent=2)
        return True
    except Exception:
        return False


def journal_verify(entry):
    try:
        saved_date = entry["saved"][:10]
        d = yf.Ticker(entry["sym"]).history(period="1mo", interval="1d").dropna()
        if d is None or len(d) == 0:
            return {"status": "NO DATA", "color": "#8fa3bd", "detail": "Couldn't fetch prices."}
        after = d[d.index.strftime("%Y-%m-%d") > saved_date]
        if len(after) == 0:
            return {"status": "TOO SOON", "color": "#8fa3bd",
                    "detail": "No trading day has completed since you saved this — check tomorrow."}
        hi = float(after["High"].max()); lo = float(after["Low"].min())
        last = float(after["Close"].iloc[-1])
        buy, sl = entry["buy_at"], entry["sl"]
        t1, t2, t3 = entry["t1"], entry["t2"], entry["t3"]
        moved = (last - entry["price"]) / entry["price"] * 100
        want_up = "UP" in entry.get("trend", "") or "BUY" in entry.get("signal", "")
        trend_right = (moved > 0) if want_up else (moved < 0)
        # v14 FIX — FIRST-TOUCH scoring, day by day. The old code checked the
        # targets BEFORE the stop over the whole month, so a trade that hit
        # its stop and later reached T1 counted as a WIN (random coin-flip
        # trades scored ~81% "wins"). Now: the trade starts on the fill day;
        # whichever of stop / T1 is touched FIRST decides it; if both are
        # touched on the same daily candle the order is unknown → LOSS
        # (conservative). After T1, the best target reached before the stop.
        _rows = after.sort_index()
        _filled = entry.get("sit") != "BUY_DIP"
        _res, _best, _day = None, 0, None
        for _ix, _r in _rows.iterrows():
            _h, _l = float(_r["High"]), float(_r["Low"])
            if not _filled:
                if _l <= buy:
                    _filled = True
                else:
                    continue
            if _res is None:
                _hs, _ht = _l <= sl, _h >= t1
                if _hs:
                    _res = "BOTH" if _ht else "SL"; _day = _ix; break
                if _ht:
                    _res = "WIN"; _best = 1; _day = _ix
            if _res == "WIN":
                if _l <= sl:
                    break
                _best = max(_best, 3 if _h >= t3 else 2 if _h >= t2 else 1)
        if not _filled:
            status, color = "NO-FILL (never dipped to buy)", "#8fa3bd"
            detail = f"Price never fell to ₹{buy:.2f}; low since was ₹{lo:.2f}. No trade taken — correct to wait."
        elif _res == "WIN" and _best >= 3:
            status, color = "WIN → T3 🎯", "#4ade80"; detail = f"Hit all targets before the stop (high ₹{hi:.2f})."
        elif _res == "WIN" and _best == 2:
            status, color = "WIN → T2 ✅", "#16a34a"; detail = f"Reached T2 ₹{t2:.2f} before the stop."
        elif _res == "WIN":
            status, color = "WIN → T1 ✅", "#16a34a"; detail = f"Reached T1 ₹{t1:.2f} before the stop."
        elif _res == "BOTH":
            status, color = "LOSS → stop & T1 same day ❌", "#dc2626"
            detail = (f"Stop ₹{sl:.2f} and T1 ₹{t1:.2f} both touched on "
                      f"{str(_day)[:10]} — order unknown, counted as a LOSS (honest scoring).")
        elif _res == "SL":
            status, color = "LOSS → hit stop ❌", "#dc2626"; detail = f"Fell to stop ₹{sl:.2f} first (low ₹{lo:.2f})."
        else:
            status, color = "OPEN — no target/stop hit yet", "#fbbf24"
            detail = f"Since save: high ₹{hi:.2f}, low ₹{lo:.2f}, now ₹{last:.2f}."
        return {"status": status, "color": color, "detail": detail,
                "moved": round(moved, 2), "trend_right": trend_right,
                "hi": hi, "lo": lo, "last": last}
    except Exception as e:
        return {"status": "ERROR", "color": "#8fa3bd", "detail": f"{type(e).__name__}"}


# ============================================================
# 🧠 BOARD MEMORY + 🌙 EOD (END-OF-DAY) VERIFICATION
#   The dashboard auto-saves WHAT IT SHOWED (snapshots). The EOD
#   tab later fetches what ACTUALLY happened and scores every
#   call — "how many stocks went as per our calculation?"
# ============================================================
SNAP_FILE = "board_snapshots.json"
EOD_FILE = "eod_results.json"
_SNAP_FIELDS = ("sym", "name", "price", "chg", "sig", "conf", "bp", "sp", "dtr",
                "above200", "score", "buy_at", "sl", "t1", "t2", "rr", "sit")


def snaps_load():
    fn = snap_file()
    try:
        if _os.path.exists(fn):
            with open(fn, "r", encoding="utf-8") as f:
                d = _json.load(f)
            return d if isinstance(d, list) else []
        if _ukey() == "main" and _os.path.exists(SNAP_FILE):   # adopt old file
            with open(SNAP_FILE, "r", encoding="utf-8") as f:
                d = _json.load(f)
            return d if isinstance(d, list) else []
    except Exception:
        pass
    return []


def snaps_save(rows):
    """ONE snapshot per day = that day's calculation (today's board). While the
    terminal runs, today's snapshot is refreshed — no intraday pile-up. The EOD
    tab verifies it the NEXT day. Keeps the last 40 days."""
    try:
        now = now_ist()
        snap = {"id": now.strftime("%Y-%m-%d"),
                "saved": now.strftime("%Y-%m-%d %H:%M"),
                "rows": [{k: r.get(k) for k in _SNAP_FIELDS} for r in rows.values()]}
        data = [s for s in snaps_load() if s.get("id") != snap["id"]]
        data.append(snap)
        data.sort(key=lambda s: s.get("saved", ""))
        data = data[-40:]
        with open(snap_file(), "w", encoding="utf-8") as f:
            _json.dump(data, f)
        return True
    except Exception:
        return False


def eod_load():
    fn = eod_file()
    try:
        if _os.path.exists(fn):
            with open(fn, "r", encoding="utf-8") as f:
                d = _json.load(f)
            return d if isinstance(d, list) else []
        if _ukey() == "main" and _os.path.exists(EOD_FILE):    # adopt old file
            with open(EOD_FILE, "r", encoding="utf-8") as f:
                d = _json.load(f)
            return d if isinstance(d, list) else []
    except Exception:
        pass
    return []


def eod_save(entry):
    try:
        data = [d for d in eod_load() if d.get("id") != entry.get("id")]
        data.append(entry)
        data.sort(key=lambda d: d.get("date", ""))
        data = data[-100:]
        with open(eod_file(), "w", encoding="utf-8") as f:
            _json.dump(data, f, indent=2)
        return True
    except Exception:
        return False


def verify_snapshot(snap):
    """AFTER: fetch what prices ACTUALLY did after a snapshot and score
    every call. Returns per-stock results + a summary."""
    syms = [r["sym"] for r in snap["rows"] if r.get("sym")]
    # market probe: latest candle Yahoo currently has (shows if data is available at all)
    last_candle = None
    try:
        _p = fetch_chunk(("RELIANCE.NS", "TCS.NS"), "1d", "6mo").get("RELIANCE.NS")
        if _p is not None and len(_p):
            last_candle = str(_p.index[-1].date())
    except Exception:
        pass
    # fetch with RETRIES — Yahoo throttles cloud servers; a single pass can fail completely
    got = {}
    for _attempt in range(3):
        todo = [s for s in syms if got.get(s) is None or len(got[s]) == 0]
        if not todo:
            break
        for i in range(0, len(todo), 50):
            try:
                got.update(fetch_chunk(tuple(todo[i:i + 50]), "1d", "6mo"))
            except Exception:
                pass
        if _attempt < 2:
            time.sleep(4)
    try:
        sdate = datetime.strptime(snap["saved"][:10], "%Y-%m-%d").date()
    except Exception:
        sdate = datetime.now().date()
    results = []
    for r in snap["rows"]:
        row = dict(r)
        row.update({"outcome": "NO DATA", "moved": 0.0, "correct": None,
                    "hi": None, "lo": None, "last": None})
        df = got.get(r.get("sym"))
        if df is not None and len(df):
            after = df[[ix.date() > sdate for ix in df.index]]
            same_day = False
            if len(after) == 0:   # snapshot is from today → use today's candle
                after = df[[ix.date() == sdate for ix in df.index]]
                same_day = True
            if len(after):
                hi = float(after["High"].max()); lo = float(after["Low"].min())
                last = float(after["Close"].iloc[-1])
                row["hi"], row["lo"], row["last"] = round(hi, 2), round(lo, 2), round(last, 2)
                row["moved"] = round((last - r["price"]) / r["price"] * 100, 2) if r["price"] else 0.0
                buy_call = ("BUY" in (r.get("sig") or "")) or r.get("dtr") == "UPTREND"
                hit_t1 = hi >= (r.get("t1") or 1e18)
                hit_t2 = hi >= (r.get("t2") or 1e18)
                hit_sl = lo <= (r.get("sl") or -1e18)
                if buy_call:
                    # v14 FIX: stop AND target touched → order unknown → it is
                    # NOT a win (old code checked T2 first and called it WIN).
                    if hit_sl and hit_t1:            row["outcome"] = "LOSS? T1&SL both ⚠️"
                    elif hit_t2:                     row["outcome"] = "WIN T2 ✅"
                    elif hit_t1:                     row["outcome"] = "WIN T1 ✅"
                    elif hit_sl:                     row["outcome"] = "LOSS SL ❌"
                    else:                            row["outcome"] = "NO MOVE ➖"
                    row["correct"] = (row["moved"] > 0) if row["moved"] != 0 else None
                elif r.get("dtr") == "DOWNTREND":
                    if row["moved"] < 0:
                        row["outcome"], row["correct"] = "FELL ✅", True
                    elif row["moved"] > 0:
                        row["outcome"], row["correct"] = "ROSE ❌", False
                    else:
                        row["outcome"], row["correct"] = "FLAT ➖", None
                else:
                    row["outcome"] = "—"
                if same_day:
                    row["outcome"] += " (same-day)"
        results.append(row)
    ups = [x for x in results if x.get("dtr") == "UPTREND"]
    dns = [x for x in results if x.get("dtr") == "DOWNTREND"]
    bu = [x for x in results if "BUY" in (x.get("sig") or "")]
    up_ok = [x for x in ups if x.get("correct") is True]
    t1w = [x for x in bu if str(x["outcome"]).startswith("WIN")]
    sls = [x for x in bu if str(x["outcome"]).startswith("LOSS")]

    def _avg(lst):
        v = [x["moved"] for x in lst if isinstance(x.get("moved"), (int, float))]
        return round(sum(v) / len(v), 2) if v else 0.0

    nodata = [x for x in results if str(x.get("outcome", "")).startswith("NO DATA")]
    scored_up = [x for x in ups if x.get("correct") is not None]
    summary = {"snap": snap["saved"], "checked": len(results),
               "n_up": len(ups), "up_ok": len(up_ok),
               "up_acc": round(len(up_ok) / len(ups) * 100, 1) if scored_up else None,
               "n_scored_up": len(scored_up),
               "avg_up": _avg(ups), "avg_dn": _avg(dns),
               "n_buy": len(bu), "n_t1": len(t1w), "n_sl": len(sls),
               "buy_wr": round(len(t1w) / (len(t1w) + len(sls)) * 100, 1) if (t1w or sls) else None,
               "n_valid": len(results) - len(nodata), "n_nodata": len(nodata),
               "last_candle": last_candle}
    return results, summary


def detect_regime(res):
    adx = res.get('adx', np.nan); bbw = res.get('bbw', np.nan)
    tr = res['trend']
    trending = (not np.isnan(adx)) and adx > 25
    ranging = (not np.isnan(adx)) and adx < 20
    if trending and tr == 'UPTREND':
        reg, rc = "STRONG UPTREND", "#4ade80"
    elif trending and tr == 'DOWNTREND':
        reg, rc = "STRONG DOWNTREND", "#f87171"
    elif ranging:
        reg, rc = "RANGING / SIDEWAYS", "#fbbf24"
    else:
        reg, rc = tr.title() if tr != 'SIDEWAYS' else "TRANSITIONING", "#2563eb"
    if not np.isnan(bbw):
        vol = "HIGH VOLATILITY" if bbw > 6 else "LOW VOLATILITY" if bbw < 2 else "MODERATE VOLATILITY"
    else:
        vol = "—"
    vc = "#dc2626" if "HIGH" in vol else "#16a34a" if "LOW" in vol else "#fbbf24"
    return {"regime": reg, "rc": rc, "vol": vol, "vc": vc, "adx": adx}


def volume_profile(df, bins=24):
    try:
        d = df.tail(120)
        lo, hi = float(d['Low'].min()), float(d['High'].max())
        if hi <= lo:
            return None
        edges = np.linspace(lo, hi, bins + 1)
        centers = (edges[:-1] + edges[1:]) / 2
        vol = np.zeros(bins)
        for _, r in d.iterrows():
            mid = (r['High'] + r['Low']) / 2
            idx = min(int((mid - lo) / (hi - lo) * bins), bins - 1)
            vol[idx] += r['Volume']
        poc = float(centers[int(np.argmax(vol))])
        order = np.argsort(vol)[::-1]
        total = vol.sum(); acc = 0; chosen = []
        for i in order:
            acc += vol[i]; chosen.append(i)
            if acc >= 0.70 * total:
                break
        va_lo = float(centers[min(chosen)]); va_hi = float(centers[max(chosen)])
        price = float(df['Close'].iloc[-1])
        if price > va_hi: pos = "ABOVE value area — extended up (mean-reversion risk)"
        elif price < va_lo: pos = "BELOW value area — extended down (bounce possible)"
        else: pos = "INSIDE value area — fairly priced"
        return {"poc": poc, "va_lo": va_lo, "va_hi": va_hi, "pos": pos, "price": price}
    except Exception:
        return None


def detect_patterns(df):
    try:
        d = df.tail(60)
        H = d['High'].values; L = d['Low'].values; C = d['Close'].values
        n = len(C)
        if n < 20:
            return []
        peaks, troughs = [], []
        for i in range(2, n - 2):
            if H[i] >= max(H[i-2:i]) and H[i] >= max(H[i+1:i+3]): peaks.append((i, H[i]))
            if L[i] <= min(L[i-2:i]) and L[i] <= min(L[i+1:i+3]): troughs.append((i, L[i]))
        out = []
        tol = np.mean(C) * 0.02
        if len(peaks) >= 2:
            (i1, h1), (i2, h2) = peaks[-2], peaks[-1]
            if abs(h1 - h2) < tol and i2 - i1 >= 3:
                out.append(("Double Top", "Bearish — watch for breakdown", "Medium"))
        if len(troughs) >= 2:
            (i1, l1), (i2, l2) = troughs[-2], troughs[-1]
            if abs(l1 - l2) < tol and i2 - i1 >= 3:
                out.append(("Double Bottom", "Bullish — watch for breakout", "Medium"))
        if len(peaks) >= 3:
            (_, a), (_, b), (_, c) = peaks[-3], peaks[-2], peaks[-1]
            if b > a and b > c and abs(a - c) < tol:
                out.append(("Head & Shoulders", "Bearish reversal", "High"))
        move = (C[-1] - C[-15]) / C[-15] * 100 if n >= 15 else 0
        rng = (np.max(H[-6:]) - np.min(L[-6:])) / C[-1] * 100
        if move > 6 and rng < 4:
            out.append(("Bull Flag", "Bullish continuation likely", "Medium"))
        elif move < -6 and rng < 4:
            out.append(("Bear Flag", "Bearish continuation likely", "Medium"))
        if len(peaks) >= 2 and len(troughs) >= 2:
            if peaks[-1][1] < peaks[-2][1] and troughs[-1][1] > troughs[-2][1]:
                out.append(("Triangle / Consolidation", "Breakout pending — trade the break", "Low"))
        return out
    except Exception:
        return []


@st.cache_data(ttl=1800, show_spinner=False)
def risk_metrics(sym):
    d = _daily_for_ml(sym)
    if d is None:
        return None
    try:
        ret = d['Close'].pct_change().dropna()
        if len(ret) < 60:
            return None
        ann = 252
        sharpe = float(ret.mean() / (ret.std() + 1e-9) * np.sqrt(ann))
        cum = (1 + ret).cumprod()
        dd = float(((cum - cum.cummax()) / cum.cummax()).min() * 100)
        ann_ret = float((cum.iloc[-1] ** (ann / len(ret)) - 1) * 100)
        calmar = float(ann_ret / abs(dd)) if dd != 0 else 0
        win = float((ret > 0).mean() * 100)
        var95 = float(np.percentile(ret, 5) * 100)
        avol = float(ret.std() * np.sqrt(ann) * 100)
        vrating = "HIGH" if avol > 40 else "LOW" if avol < 20 else "MODERATE"
        return {"sharpe": round(sharpe, 2), "maxdd": round(dd, 1), "calmar": round(calmar, 2),
                "win": round(win, 1), "var95": round(var95, 2), "avol": round(avol, 1),
                "vrating": vrating}
    except Exception:
        return None


def target_probability(price, plan, sym):
    d = _daily_for_ml(sym)
    try:
        from scipy.stats import norm
        have_scipy = True
    except Exception:
        have_scipy = False
    if d is None:
        return None
    try:
        ret = d['Close'].pct_change().dropna()
        sig = float(ret.std())
        if sig <= 0:
            return None
        H = 3
        sd = sig * np.sqrt(H)

        def prob_up(tp):
            move = (tp - price) / price
            z = move / (sd + 1e-9)
            if have_scipy:
                return float(1 - norm.cdf(z))
            return float(max(0.0, min(1.0, 0.5 - z * 0.2)))

        def rate(p):
            return ("High", "#16a34a") if p >= 0.55 else ("Moderate", "#fbbf24") if p >= 0.35 else ("Low", "#dc2626")

        res = {}
        for key, tp in [("T1", plan['t1']), ("T2", plan['t2']), ("T3", plan['t3'])]:
            p = prob_up(tp); r, c = rate(p)
            res[key] = {"p": round(p * 100, 1), "rating": r, "color": c, "price": tp}
        smove = (price - plan['sl']) / price
        zs = smove / (sd + 1e-9)
        psl = float(norm.cdf(-zs)) if have_scipy else float(max(0.0, min(1.0, 0.5 - zs * 0.2)))
        res["SL"] = {"p": round(psl * 100, 1)}
        res["scipy"] = have_scipy
        return res
    except Exception:
        return None


# ============================================================
# REPORTS
# ============================================================
def _report_text(sym, name, res, plan, sr, nse, htf):
    L = []
    L.append(f"{name} [{sym}] — AI Trader Pro analysis")
    L.append(datetime.now().strftime("Generated %d %b %Y, %H:%M"))
    L.append("=" * 52)
    L.append(f"Price: Rs {res['price']:.2f}")
    L.append(f"Trend: {res['trend']} | Signal: {res['sig']} ({res['conf']:.0f}%)")
    L.append(f"Buy%/Sell%: {res['bp']:.0f}/{res['sp']:.0f}")
    if htf and htf.get('trend'):
        L.append(f"Higher timeframe ({htf['label']}): {htf['trend']}")
    if nse and nse.get('upper'):
        L.append(f"Circuit: Upper Rs {nse['upper']:.2f} / Lower Rs {nse['lower']:.2f} ({nse.get('band','')})")
    elif nse and nse.get('no_band'):
        L.append("Circuit: No band (F&O)")
    if nse and nse.get('iep'):
        L.append(f"Pre-open (IEP): Rs {nse['iep']:.2f} ({nse.get('iep_pct',0):+.2f}%)")
    L.append("")
    L.append(f"PLAN ({plan['when']}): {plan['act']}")
    L.append(f"  Timing : {plan['timing']}")
    L.append(f"  Buy at : Rs {plan['buy_at']:.2f}")
    L.append(f"  Stop   : Rs {plan['sl']:.2f} ({plan['sl_pct']:.2f}%)")
    L.append(f"  T1     : Rs {plan['t1']:.2f} (+{plan['t1p']:.2f}%)")
    L.append(f"  T2     : Rs {plan['t2']:.2f} (+{plan['t2p']:.2f}%)")
    L.append(f"  T3     : Rs {plan['t3']:.2f} (+{plan['t3p']:.2f}%)")
    L.append(f"  R:R    : 1:{plan['rr']}")
    if sr and sr.get('pivots'):
        L.append("")
        L.append("PIVOTS")
        for sn, d in sr['pivots'].items():
            L.append(f"  {sn}: " + " ".join(f"{k}={v:.2f}" for k, v in d.items()))
    L.append("")
    L.append(f"INDICATORS ({res['n_sigs']})")
    for s in res['sigs']:
        L.append(f"  {s['n']:<16} {str(s['v']):<10} {'BUY' if s['b'] else 'SELL':<5} {s['t']}")
    L.append("")
    L.append("Educational only. Not financial advice. Always use a stop loss.")
    return "\n".join(L)


def build_report_html(sym, name, iv, per, res, plan, sr, nse, htf, mst_s):
    now = datetime.now().strftime("%d %b %Y, %H:%M")
    tr = res['trend']
    def row(k, v): return f"<tr><td class='k'>{k}</td><td class='v'>{v}</td></tr>"
    if nse and nse.get('upper'):
        circ = f"Upper ₹{nse['upper']:.2f} · Lower ₹{nse['lower']:.2f} · Band {nse.get('band','')} · Prev ₹{nse.get('prev',0):.2f}"
    elif nse and nse.get('no_band'):
        circ = "No price band (F&O stock)"
    else:
        circ = "unavailable"
    preopen = (f"₹{nse['iep']:.2f} ({nse.get('iep_chg',0):+.2f} / {nse.get('iep_pct',0):+.2f}%)"
               if nse and nse.get('iep') else "—")
    htf_txt = f"{htf['label']} trend: {htf['trend']}" if htf and htf.get('trend') else "—"
    sr_rows = ""
    if sr and sr.get('levels'):
        for l in sr['levels']:
            sr_rows += f"<tr><td>{l['name']}</td><td>{l['type']}</td><td>₹{l['price']:.2f}</td><td>{l['dist']:+.2f}%</td></tr>"
    piv_html = ""
    if sr and sr.get('pivots'):
        for sysname, d in sr['pivots'].items():
            cells = " · ".join(f"{k} ₹{v:.2f}" for k, v in d.items())
            piv_html += f"<p><b>{sysname}:</b> {cells}</p>"
    fib_html = ""
    if sr and sr.get('fib_levels'):
        fib_html = " · ".join(f"{k} ₹{v:.2f}" for k, v in sr['fib_levels'].items())
    ind_rows = ""
    for s in res['sigs']:
        ind_rows += f"<tr><td>{s['n']}</td><td>{s['v']}</td><td>{'BUY' if s['b'] else 'SELL'}</td><td>{s['t']}</td></tr>"
    return f"""<!doctype html><html><head><meta charset='utf-8'><title>{name} Analysis</title>
<style>
body{{font-family:Arial,Helvetica,sans-serif;color:#1a1f36;max-width:900px;margin:20px auto;padding:0 20px;}}
h1{{color:#1d4ed8;margin:0;}} h2{{color:#1d4ed8;border-bottom:2px solid #e0e7ff;padding-bottom:4px;margin-top:26px;}}
.sub{{color:#6b7280;font-size:13px;margin:4px 0 16px;}}
.big{{font-size:28px;font-weight:800;}}
table{{border-collapse:collapse;width:100%;font-size:13px;margin:6px 0;}}
td,th{{border:1px solid #e0e7ff;padding:6px 10px;text-align:left;}} th{{background:#eff6ff;}}
.k{{color:#6b7280;width:34%;}} .v{{font-weight:600;}}
.verdict{{padding:14px 18px;border-radius:10px;font-size:20px;font-weight:800;margin:10px 0;}}
.up{{background:#f0fdf4;color:#15803d;border:2px solid #16a34a;}}
.dn{{background:#fff1f2;color:#b91c1c;border:2px solid #dc2626;}}
.wt{{background:#fffbeb;color:#b45309;border:2px solid #d97706;}}
.disc{{color:#9ca3af;font-size:11px;border-top:1px solid #e0e7ff;margin-top:24px;padding-top:10px;}}
@media print{{h2{{page-break-after:avoid;}}}}
</style></head><body>
<h1>💹 {name} <span style='font-size:16px;color:#6b7280;'>[{sym}]</span></h1>
<div class='sub'>Generated {now} · Timeframe {iv} · Period {per} · Market {mst_s.upper()}</div>
<div class='big'>₹{res['price']:,.2f}</div>
<div class='verdict {"up" if tr=="UPTREND" else "dn" if tr=="DOWNTREND" else "wt"}'>
Trend: {tr}  |  Signal: {res['sig']} ({res['conf']:.0f}% confidence)</div>
<h2>Summary</h2><table>
{row("Signal", res['sig'] + f" · Buy {res['bp']:.0f}% / Sell {res['sp']:.0f}%")}
{row("Trend", tr)}
{row("Higher timeframe", htf_txt)}
{row("Plan", plan['head'])}
{row("Timing", plan['timing'])}
{row("Circuit limits", circ)}
{row("Pre-open (IEP)", preopen)}
{row("52-week range", f"₹{res['lo52']:.2f} – ₹{res['hi52']:.2f} (pos {res['pos52']:.0f}%)")}
{row("ATR / Volume", f"₹{res['atr']:.2f} · {res['vr']:.1f}x avg")}
</table>
<h2>Trade Levels ({plan['when']})</h2><table>
{row("Action", plan['act'])}
{row("Buy at", f"₹{plan['buy_at']:.2f}")}
{row("Stop loss", f"₹{plan['sl']:.2f} ({plan['sl_pct']:.2f}% below)")}
{row("Target 1", f"₹{plan['t1']:.2f} (+{plan['t1p']:.2f}%)")}
{row("Target 2", f"₹{plan['t2']:.2f} (+{plan['t2p']:.2f}%)")}
{row("Target 3", f"₹{plan['t3']:.2f} (+{plan['t3p']:.2f}%)")}
{row("Risk : Reward", f"1 : {plan['rr']}")}
</table>
<h2>Support &amp; Resistance</h2>
<table><tr><th>Level</th><th>Type</th><th>Price</th><th>Distance</th></tr>{sr_rows}</table>
<h3>Pivots (Standard / Camarilla / Woodie)</h3>{piv_html}
<h3>Fibonacci</h3><p>{fib_html}</p>
<h2>All {res['n_sigs']} Indicators</h2>
<table><tr><th>Indicator</th><th>Value</th><th>Bias</th><th>Reading</th></tr>{ind_rows}</table>
<div class='disc'>⚠️ EDUCATIONAL PURPOSE ONLY · NOT FINANCIAL ADVICE · ALWAYS USE A STOP LOSS ·
Trade at your own risk · Generated by AI Trader Pro v13.6. To save as PDF: open this file and press Ctrl+P → "Save as PDF".</div>
</body></html>"""


def build_report_docx(sym, name, iv, per, res, plan, sr, nse, htf, mst_s):
    try:
        from docx import Document
        from docx.shared import Pt
        import io as _io
    except Exception:
        return None
    try:
        doc = Document()
        doc.add_heading(f"{name} [{sym}] — Analysis", level=0)
        doc.add_paragraph(f"Generated {datetime.now().strftime('%d %b %Y, %H:%M')} · "
                          f"{iv} / {per} · Market {mst_s.upper()}")
        doc.add_paragraph(f"Price ₹{res['price']:.2f}").runs[0].bold = True
        p = doc.add_paragraph()
        r = p.add_run(f"Trend: {res['trend']} | Signal: {res['sig']} ({res['conf']:.0f}%)")
        r.bold = True; r.font.size = Pt(14)

        def tbl(title, rows):
            doc.add_heading(title, level=1)
            t = doc.add_table(rows=0, cols=2); t.style = 'Light Grid Accent 1'
            for k, v in rows:
                c = t.add_row().cells; c[0].text = str(k); c[1].text = str(v)

        htf_txt = f"{htf['label']}: {htf['trend']}" if htf and htf.get('trend') else "—"
        circ = (f"Upper ₹{nse['upper']:.2f} · Lower ₹{nse['lower']:.2f} · {nse.get('band','')}"
                if nse and nse.get('upper') else ("No band" if nse and nse.get('no_band') else "unavailable"))
        preopen = (f"₹{nse['iep']:.2f} ({nse.get('iep_pct',0):+.2f}%)" if nse and nse.get('iep') else "—")
        tbl("Summary", [("Signal", f"{res['sig']} · Buy {res['bp']:.0f}%/Sell {res['sp']:.0f}%"),
                        ("Trend", res['trend']), ("Higher timeframe", htf_txt),
                        ("Timing", plan['timing']), ("Circuit", circ), ("Pre-open", preopen),
                        ("52W range", f"₹{res['lo52']:.2f}-₹{res['hi52']:.2f}")])
        tbl(f"Trade Levels ({plan['when']})",
            [("Action", plan['act']), ("Buy at", f"₹{plan['buy_at']:.2f}"),
             ("Stop loss", f"₹{plan['sl']:.2f} ({plan['sl_pct']:.2f}%)"),
             ("Target 1", f"₹{plan['t1']:.2f} (+{plan['t1p']:.2f}%)"),
             ("Target 2", f"₹{plan['t2']:.2f} (+{plan['t2p']:.2f}%)"),
             ("Target 3", f"₹{plan['t3']:.2f} (+{plan['t3p']:.2f}%)"),
             ("Risk:Reward", f"1:{plan['rr']}")])
        if sr and sr.get('pivots'):
            doc.add_heading("Pivots", level=1)
            for sn, d in sr['pivots'].items():
                doc.add_paragraph(f"{sn}: " + " · ".join(f"{k} ₹{v:.2f}" for k, v in d.items()))
        doc.add_heading(f"All {res['n_sigs']} Indicators", level=1)
        it = doc.add_table(rows=1, cols=4); it.style = 'Light Grid Accent 1'
        hdr = it.rows[0].cells
        hdr[0].text, hdr[1].text, hdr[2].text, hdr[3].text = "Indicator", "Value", "Bias", "Reading"
        for s in res['sigs']:
            c = it.add_row().cells
            c[0].text = s['n']; c[1].text = str(s['v'])
            c[2].text = "BUY" if s['b'] else "SELL"; c[3].text = s['t']
        doc.add_paragraph("⚠️ Educational only · Not financial advice · Always use a stop loss.")
        buf = _io.BytesIO(); doc.save(buf); return buf.getvalue()
    except Exception:
        return None


def live_candle_view(df, res):
    try:
        d = df.tail(14)
        if len(d) < 4:
            return None
        price = float(d['Close'].iloc[-1])
        closes = d['Close'].values
        greens = int((d['Close'] >= d['Open']).sum()); reds = len(d) - greens
        slope = closes[-1] - closes[-6] if len(closes) >= 6 else closes[-1] - closes[0]
        vw = res.get('vw', np.nan)
        above_vwap = (not np.isnan(vw)) and price > vw
        last_up = float(d['Close'].iloc[-1]) >= float(d['Open'].iloc[-1])
        streak = 1
        arr = (d['Close'] >= d['Open']).values
        for i in range(len(arr) - 2, -1, -1):
            if arr[i] == arr[-1]:
                streak += 1
            else:
                break
        up = slope > 0 and greens >= reds and (above_vwap or np.isnan(vw))
        dn = slope < 0 and reds > greens and (not above_vwap or np.isnan(vw))
        rng_hi = float(df['High'].tail(30).max()); rng_lo = float(df['Low'].tail(30).min())
        rpos = (price - rng_lo) / max(rng_hi - rng_lo, 1e-9)
        vd = ((price - vw) / vw * 100) if (not np.isnan(vw) and vw > 0) else 0
        extended = rpos > 0.85 or vd > 2.5
        if up and extended:
            verdict, vc, vico = "UP — BUT EXTENDED (pullback risk, don't chase)", "#ea580c", "🛑"
        elif up:
            verdict, vc, vico = "UPTREND FORMING", "#16a34a", "📈"
        elif dn:
            verdict, vc, vico = "DOWNTREND FORMING", "#dc2626", "📉"
        else:
            verdict, vc, vico = "CHOPPY — NO CLEAR DIRECTION", "#fbbf24", "➡️"
        blocks = ""
        for i, (_, r) in enumerate(d.iterrows()):
            g = r['Close'] >= r['Open']
            clr = "#16a34a" if g else "#dc2626"
            body = max(abs(r['Close'] - r['Open']), 0.01)
            hgt = 14 + min(int(body / max(price * 0.004, 0.01) * 6), 34)
            border = "border:2px solid #e2e8f0;" if i == len(d) - 1 else ""
            blocks += f"<div title='O{r['Open']:.2f} H{r['High']:.2f} L{r['Low']:.2f} C{r['Close']:.2f}' style='width:16px;height:{hgt}px;background:{clr};border-radius:3px;{border}'></div>"
        last = d.iloc[-1]
        chg = (float(last['Close']) - float(last['Open']))
        chgp = chg / float(last['Open']) * 100 if last['Open'] else 0
        vwtxt = (f"{'above' if above_vwap else 'below'} VWAP" if not np.isnan(vw) else "")
        return {
            "verdict": verdict, "vc": vc, "vico": vico, "blocks": blocks,
            "streak": streak, "last_up": last_up, "greens": greens, "reds": reds,
            "chg": chg, "chgp": chgp, "vwtxt": vwtxt, "price": price,
            "oc": f"O ₹{last['Open']:.2f} · H ₹{last['High']:.2f} · L ₹{last['Low']:.2f} · C ₹{last['Close']:.2f}",
        }
    except Exception:
        return None


# ============================================================
# FULL ANALYSIS PAGE (single stock)
# ============================================================
def show_analysis(sym, name, iv, per):
    with st.spinner(f"⏳ Loading {name}..."):
        res = run_analysis(sym, iv, per)
    if res is None:
        st.markdown(_H(f"""<div style='background:#2a0e0e;border:2px solid #dc2626;border-radius:16px;padding:24px;'>
        <div style='font-size:18px;font-weight:800;color:#dc2626;'>❌ Cannot Load {sym}</div>
        <div style='color:#cbd5e1;font-size:13px;margin-top:8px;'>Try exact NSE symbol · check internet ·
        best combo: 15m timeframe + 1mo period</div></div>"""), unsafe_allow_html=True)
        return
    mst_s, ml, mm = mkt_status()
    with st.spinner("🧠 Computing SR, Fibonacci, Pivots, Plan, Circuit, HTF..."):
        nse = get_nse_quote(sym)
        ck = f"nse_good_{sym}"
        if nse and (nse.get('upper') or nse.get('no_band')):
            st.session_state[ck] = nse
        elif st.session_state.get(ck):
            nse = st.session_state[ck]
        yahoo_price = res['price']
        price_src = "Yahoo (may be ~15 min delayed)"
        if nse and nse.get('ltp') and nse['ltp'] > 0 and abs(nse['ltp'] - yahoo_price) / yahoo_price < 0.25:
            res['price'] = round(nse['ltp'], 2)
            price_src = "NSE live"
        sr = get_sr_fib(sym, res['price'], res['atr'], nse)
        wk_hi = nse.get('wk_hi') if nse else None
        wk_lo = nse.get('wk_lo') if nse else None
        if not (wk_hi and wk_lo) and sr and sr.get('hi52'):
            wk_hi, wk_lo = sr['hi52'], sr['lo52']
        if wk_hi and wk_lo:
            res['hi52'] = round(wk_hi, 2); res['lo52'] = round(wk_lo, 2)
            rng = wk_hi - wk_lo
            res['pos52'] = round((res['price'] - wk_lo) / rng * 100, 1) if rng > 0 else 50
        htf = htf_trend(sym, iv)
        ema2 = ema200_filter(sym, res['price'])
        news = get_stock_news(sym)
        session = mst_s
        plan = make_plan(res['price'], res['atr'], sr, res['sig'], session, nse)
    price = res['price']; sc = res['sc']

    gap_text = ""
    if sr:
        gg = sr['gap_pct']; gclr = "#16a34a" if gg > 0 else "#dc2626" if gg < 0 else "#8fa3bd"
        gap_text = f"<span style='color:{gclr};font-weight:700;font-size:13px;'> {gg:+.1f}% gap</span>"
    mclr = "#16a34a" if mst_s == "open" else "#f59e0b" if mst_s == "pre" else "#dc2626"
    st.markdown(_H(f"""<div style='background:#0f1a2e;border:1px solid #1e293b;border-radius:18px;padding:18px 24px;
    margin-bottom:18px;box-shadow:0 4px 20px rgba(0,0,0,0.06);display:flex;justify-content:space-between;
    align-items:center;flex-wrap:wrap;gap:10px;'><div>
    <div style='display:flex;align-items:center;gap:10px;flex-wrap:wrap;'>
    <span style='font-size:26px;font-weight:900;color:#e2e8f0;'>{name}</span>
    <span style='background:#1e293b;color:#3730a3;font-size:12px;font-weight:700;padding:4px 12px;border-radius:20px;'>{sym}</span>
    <span style='background:{mclr}22;color:{mclr};font-size:12px;font-weight:700;padding:4px 12px;border-radius:20px;border:1px solid {mclr}44;'>{ml}</span>
    {gap_text}</div>
    <div style='color:#8fa3bd;font-size:12px;margin-top:6px;'>⏱️ {iv} · {per} · {datetime.now().strftime("%d %b %Y %H:%M")}
     ·  Trend: <b style='color:{sc};'>{res["trend"]}</b>  ·  52W pos: <b>{res["pos52"]:.1f}%</b>
     ·  Vol: <b>{res["vr"]:.1f}x</b></div></div>
    <div style='text-align:right;'><div style='font-size:40px;font-weight:900;color:#60a5fa;'>₹{price:,.2f}</div>
    <div style='font-size:10px;font-weight:700;color:{"#16a34a" if price_src=="NSE live" else "#fbbf24"};'>{"🟢 NSE LIVE" if price_src=="NSE live" else "⚠️ "+price_src.upper()+" · CHECK BROKER FOR EXACT LTP"}</div>
    <div style='color:#8fa3bd;font-size:12px;'>52W H: ₹{res["hi52"]:.2f} | L: ₹{res["lo52"]:.2f}</div></div></div>"""),
                unsafe_allow_html=True)

    st.markdown("<div style='background:#3a2a06;border:1px solid #fde68a;border-radius:10px;"
                "padding:8px 16px;margin-bottom:10px;color:#fbbf24;font-size:12px;'>"
                "<b>Reality check:</b> the levels (price, circuit, support/resistance) are exact — but the "
                "<b>direction call is a probability, not a prediction</b>. Even good setups fail ~40–50% of "
                "the time. The stop-loss is your protection; size small enough that a loss doesn't hurt. "
                "Track results in the 📓 Journal — trust your measured hit-rate, not any confidence number.</div>",
                unsafe_allow_html=True)

    if mst_s == 'open':
        stc = session_time_context()
        pcol = {"early": "#16a34a", "mid": "#2563eb", "late": "#ea580c",
                "closing": "#dc2626", "done": "#dc2626"}[stc['phase']]
        pemoji = {"early": "🟢", "mid": "🔵", "late": "🟠", "closing": "🔴", "done": "🔴"}[stc['phase']]
        st.markdown(_H(f"""<div style='background:{pcol}12;border:2px solid {pcol};border-radius:14px;
        padding:14px 20px;margin-bottom:14px;display:flex;align-items:center;gap:14px;flex-wrap:wrap;'>
        <div style='font-size:28px;'>{pemoji}</div>
        <div style='flex:1;min-width:220px;'>
        <div style='font-size:13px;font-weight:900;color:{pcol};'>⏰ {stc['left_txt'].upper()} · {stc['phase'].upper()} SESSION</div>
        <div style='color:#cbd5e1;font-size:13px;margin-top:2px;'>{stc['note']}</div></div></div>"""),
                    unsafe_allow_html=True)

    buy_c = sum(1 for s in res['sigs'] if s['b']); sell_c = len(res['sigs']) - buy_c
    lc = live_candle_view(res['df'], res)
    if lc:
        live_on = st.session_state.get('live_on', False)
        if mst_s == 'open':
            title = "🔴 LIVE CANDLE ANALYSIS"
            live_tag = ("<span style='background:#dc2626;color:white;border-radius:6px;padding:2px 8px;"
                        "font-size:11px;font-weight:700;'>● LIVE</span>" if live_on else
                        "<span style='background:#64748b;color:white;border-radius:6px;padding:2px 8px;"
                        "font-size:11px;font-weight:700;'>turn on 🔴 LIVE auto-refresh below to update live</span>")
        else:
            title = "📊 CANDLE ANALYSIS (last session)"
            live_tag = ("<span style='background:#8fa3bd;color:white;border-radius:6px;padding:2px 8px;"
                        "font-size:11px;font-weight:700;'>market closed — updates live once it opens</span>")
        st.markdown(_H(f"""<div style='background:#0f1a2e;border:2px solid {lc['vc']};border-radius:16px;
        padding:16px 20px;margin-bottom:14px;'>
        <div style='display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;'>
        <div style='font-size:14px;font-weight:900;color:{lc['vc']};'>{lc['vico']} {title} · {lc['verdict']}</div>
        {live_tag}</div>
        <div style='display:flex;align-items:flex-end;gap:4px;height:52px;margin:12px 0 8px;'>{lc['blocks']}</div>
        <div style='color:#cbd5e1;font-size:12px;'>Latest candle: <b style='color:{"#16a34a" if lc['last_up'] else "#dc2626"};'>{'UP' if lc['last_up'] else 'DOWN'} {lc['chgp']:+.2f}%</b>
        · {lc['streak']} in a row · last 14: {lc['greens']}🟢 / {lc['reds']}🔴 · {lc['vwtxt']}</div>
        <div style='color:#64748b;font-size:11px;margin-top:2px;'>{lc['oc']}</div></div>"""),
                    unsafe_allow_html=True)
    st.markdown(_H(f"""<div class='{res["bg"]}'><div style='display:flex;justify-content:space-between;
    align-items:flex-start;flex-wrap:wrap;gap:16px;'><div style='flex:1;min-width:260px;'>
    <div style='font-size:11px;color:#8fa3bd;font-weight:700;letter-spacing:2px;text-transform:uppercase;'>AI Signal · {res["n_sigs"]} Indicators</div>
    <div style='font-size:46px;font-weight:900;color:{sc};line-height:1.1;margin-top:8px;'>{res["sig"]}</div>
    <div style='margin-top:14px;'><span style='background:{plan["ac"]};color:white;font-size:15px;font-weight:800;
    padding:10px 24px;border-radius:24px;'>{plan["act"]}</span></div>
    <div style='color:#cbd5e1;font-size:14px;margin-top:14px;background:rgba(255,255,255,0.5);border-radius:10px;padding:10px 14px;'>{plan["msg"]}</div></div>
    <div><div style='text-align:center;background:rgba(255,255,255,0.6);border-radius:16px;padding:16px 24px;'>
    <div style='font-size:60px;font-weight:900;color:{sc};line-height:1;'>{res["conf"]:.0f}<span style='font-size:24px;'>%</span></div>
    <div style='color:#8fa3bd;font-size:13px;font-weight:700;margin-top:4px;'>INDICATOR AGREEMENT</div>
    <div style='color:#fbbf24;font-size:10px;font-weight:700;margin-top:4px;max-width:170px;'>⚠️ NOT win probability.
Indicators agreeing ≠ price will move that way.</div>
    <div style='color:#8fa3bd;font-size:12px;margin-top:8px;'>🟢 {buy_c} buy · 🔴 {sell_c} sell</div></div></div></div>
    <div style='display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:18px;'>
    <div style='background:rgba(22,163,74,0.1);border:1px solid rgba(22,163,74,0.3);border-radius:12px;padding:12px;'>
    <div style='display:flex;justify-content:space-between;'><span style='color:#cbd5e1;font-size:13px;font-weight:600;'>BUY STRENGTH</span>
    <span style='color:#16a34a;font-weight:900;font-size:22px;'>{res["bp"]:.0f}%</span></div>
    <div class='pbar-container' style='margin-top:8px;'><div class='pbar-buy' style='width:{res["bp"]}%;'></div></div></div>
    <div style='background:rgba(220,38,38,0.08);border:1px solid rgba(220,38,38,0.2);border-radius:12px;padding:12px;'>
    <div style='display:flex;justify-content:space-between;'><span style='color:#cbd5e1;font-size:13px;font-weight:600;'>SELL STRENGTH</span>
    <span style='color:#dc2626;font-weight:900;font-size:22px;'>{res["sp"]:.0f}%</span></div>
    <div class='pbar-container' style='margin-top:8px;'><div class='pbar-sell' style='width:{res["sp"]}%;'></div></div></div></div></div>"""),
                unsafe_allow_html=True)

    tr = res['trend']; is_buy = 'BUY' in res['sig']; is_sell = 'SELL' in res['sig']
    tim = entry_timing(res, res['df'], sr, ema2)
    if tr == 'UPTREND' and not is_sell:
        if tim['quality'] == 'GOOD':
            tv_txt, tv_sub, tv_clr, tv_bg, tv_ico = ("UPTREND — FRESH ENTRY",
                "Trend is up and price is NOT overextended — a reasonable entry, ideally near support.",
                "#4ade80", "linear-gradient(135deg,#052e16,#0b3a1f)", "📈")
        elif tim['quality'] == 'CAUTION':
            tv_txt, tv_sub, tv_clr, tv_bg, tv_ico = ("UPTREND — BUT NOT FRESH (wait for dip)",
                "Trend is up, but this isn't an early entry. Prefer a pullback toward support, or size smaller.",
                "#fbbf24", "linear-gradient(135deg,#3a2a06,#3a2a06)", "⚠️")
        else:
            tv_txt, tv_sub, tv_clr, tv_bg, tv_ico = ("UPTREND — LATE / EXTENDED · DON'T CHASE",
                "The up-move likely already happened — buying here risks catching the top. WAIT for a pullback to support.",
                "#ea580c", "linear-gradient(135deg,#2b1c0c,#33200a)", "🛑")
    elif tr == 'DOWNTREND' or is_sell:
        tv_txt, tv_sub, tv_clr, tv_bg, tv_ico = ("DOWNTREND — AVOID BUYING",
            "Lower highs & lower lows. Wrong side for longs — wait for a reversal.",
            "#f87171", "linear-gradient(135deg,#2a0e0e,#3d1420)", "📉")
    elif tr == 'VOLATILE':
        tv_txt, tv_sub, tv_clr, tv_bg, tv_ico = ("VOLATILE — RISKY",
            "Wide swings both ways. Trade small or wait for it to settle.",
            "#fbbf24", "linear-gradient(135deg,#3a2a06,#3a2a06)", "⚡")
    else:
        tv_txt, tv_sub, tv_clr, tv_bg, tv_ico = ("SIDEWAYS — WAIT",
            "No clear trend yet. Let a direction form before entering.",
            "#fbbf24", "linear-gradient(135deg,#3a2a06,#3a2a06)", "➡️")
    adx_txt = (f" · ADX {res['adx']:.0f} "
               + ("(strong)" if not np.isnan(res.get('adx', np.nan)) and res['adx'] > 25 else "(weak)")) \
              if not np.isnan(res.get('adx', np.nan)) else ""
    htf_chip = ""
    if htf and htf.get("trend"):
        ht = htf["trend"]
        agree = (ht == "UP" and tr == "UPTREND") or (ht == "DOWN" and tr == "DOWNTREND")
        hclr = "#16a34a" if ht == "UP" else "#dc2626" if ht == "DOWN" else "#fbbf24"
        mark = "✓ confirms" if agree else "✗ differs" if ht in ("UP", "DOWN") else "flat"
        htf_chip = (f"<span style='background:{hclr}18;color:{hclr};border:1px solid {hclr}44;"
                    f"font-size:12px;font-weight:700;padding:4px 12px;border-radius:20px;margin-left:8px;'>"
                    f"{htf['label']} trend: {ht.title()} · {mark}</span>")
    st.markdown(_H(f"""<div style='background:{tv_bg};border:3px solid {tv_clr};border-radius:18px;
    padding:20px 26px;margin:16px 0;display:flex;align-items:center;gap:18px;flex-wrap:wrap;'>
    <div style='font-size:46px;'>{tv_ico}</div><div style='flex:1;min-width:220px;'>
    <div style='font-size:12px;color:#8fa3bd;font-weight:700;letter-spacing:1px;'>TREND VERDICT{adx_txt}</div>
    <div style='font-size:30px;font-weight:900;color:{tv_clr};line-height:1.1;'>{tv_txt}</div>
    <div style='color:#cbd5e1;font-size:13px;margin-top:6px;'>{tv_sub} {htf_chip}</div></div></div>"""),
                unsafe_allow_html=True)

    stage_clr = {"GOOD": "#16a34a", "CAUTION": "#fbbf24", "POOR": "#ea580c",
                 "AVOID": "#dc2626", "WATCH": "#2563eb", "WAIT": "#fbbf24"}.get(tim['quality'], "#8fa3bd")
    reasons = ""
    if tim['warns']:
        reasons += "<div style='margin-top:6px;'><b style='color:#fbbf24;'>⚠️ Late/risk signals:</b> " + \
                   " · ".join(tim['warns']) + "</div>"
    if tim['goods']:
        reasons += "<div style='margin-top:4px;'><b style='color:#16a34a;'>✓ In favour:</b> " + \
                   " · ".join(tim['goods']) + "</div>"
    st.markdown(_H(f"""<div style='background:#0f1a2e;border:1px solid #1e293b;border-left:5px solid {stage_clr};
    border-radius:0 12px 12px 0;padding:12px 18px;margin:-6px 0 14px;'>
    <span style='background:{stage_clr}18;color:{stage_clr};font-weight:800;font-size:12px;
    padding:3px 12px;border-radius:20px;'>ENTRY TIMING: {tim['stage']} · {tim['quality']}</span>
    <span style='color:#cbd5e1;font-size:13px;margin-left:8px;'>{tim['msg']}</span>{reasons}</div>"""),
                unsafe_allow_html=True)

    if ema2:
        ico = "✅" if ema2['ok'] else "⛔"
        gc = "Golden cross (50>200)" if ema2['golden'] else "Death cross (50<200)"
        gclr = "#16a34a" if ema2['golden'] else "#dc2626"
        approx = " (approx — <200 daily bars)" if ema2.get('approx') else ""
        near_txt = (" · <b>price is AT the 200 EMA — major support/resistance, watch for bounce or rejection</b>"
                    if ema2['near'] else "")
        st.markdown(_H(f"""<div style='background:{ema2['vc']}10;border:2px solid {ema2['vc']};
        border-radius:14px;padding:14px 20px;margin-bottom:14px;'>
        <div style='display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;'>
        <div><span style='font-size:13px;font-weight:900;color:{ema2['vc']};'>{ico} 200 EMA METHOD · {ema2['verdict']}</span>
        <div style='color:#cbd5e1;font-size:12px;margin-top:3px;'>Daily 200 EMA ₹{ema2['ema200']:.2f}{approx} ·
        price is <b>{abs(ema2['dist']):.1f}% {'above' if ema2['above'] else 'below'}</b> it ·
        <span style='color:{gclr};font-weight:700;'>{gc}</span>{near_txt}</div></div></div>
        <div style='color:#8fa3bd;font-size:11px;margin-top:6px;'>Rule of the 200 EMA method: only take longs when price is
        <b>above</b> the daily 200 EMA. Below it = bear structure, where 'uptrend' bounces usually fail.</div></div>"""),
                    unsafe_allow_html=True)

    if news:
        head = (f"<div style='font-size:13px;font-weight:900;color:{news['vc']};'>📰 NEWS CHECK · {news['verdict']}"
                f" <span style='color:#64748b;font-weight:600;'>({news['pos']}👍 / {news['neg']}👎)</span></div>")
        rows = ""
        for it in news['items']:
            sc_ = {"pos": "#16a34a", "neg": "#dc2626", "neu": "#8fa3bd"}[it['sent']]
            tag = {"pos": "👍 good", "neg": "👎 bad", "neu": "• neutral"}[it['sent']]
            link = f"<a href='{it['url']}' target='_blank' style='color:#e2e8f0;text-decoration:none;'>{it['title']}</a>" if it['url'] else it['title']
            rows += (f"<div style='padding:7px 0;border-top:1px solid #f1f5f9;'>"
                     f"<span style='background:{sc_}18;color:{sc_};font-size:10px;font-weight:700;padding:1px 7px;border-radius:5px;'>{tag}</span> "
                     f"<span style='font-size:13px;color:#e2e8f0;'>{link}</span> "
                     f"<span style='color:#64748b;font-size:11px;'>· {it['pub']}</span></div>")
        st.markdown(_H(f"""<div style='background:#0f1a2e;border:2px solid {news['vc']};border-radius:14px;
        padding:14px 20px;margin-bottom:14px;'>{head}{rows}
        <div style='color:#64748b;font-size:11px;margin-top:8px;'>Headlines are a rough keyword read — open a link to verify.
        News can override the chart, so if something big broke, trust the news over the levels.</div></div>"""),
                    unsafe_allow_html=True)

    if nse:
        cc = st.columns(3)
        with cc[0]:
            st.markdown(f"<div class='mc-white'><div style='color:#8fa3bd;font-size:11px;font-weight:700;'>PREV CLOSE</div><div style='font-size:26px;font-weight:900;color:#e2e8f0;'>{'₹%.2f'%nse['prev'] if nse.get('prev') else '—'}</div><div style='color:#64748b;font-size:10px;'>NSE</div></div>", unsafe_allow_html=True)
        with cc[1]:
            if nse.get("upper"):
                st.markdown(f"<div class='mc-red'><div style='color:#8fa3bd;font-size:11px;font-weight:700;'>🔴 UPPER CIRCUIT</div><div style='font-size:26px;font-weight:900;color:#dc2626;'>₹{nse['upper']:.2f}</div><div style='color:#64748b;font-size:10px;'>max today · {nse.get('band','')}</div></div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='mc-white'><div style='color:#8fa3bd;font-size:11px;font-weight:700;'>UPPER CIRCUIT</div><div style='font-size:18px;font-weight:800;color:#8fa3bd;'>No band</div><div style='color:#64748b;font-size:10px;'>F&amp;O stock</div></div>", unsafe_allow_html=True)
        with cc[2]:
            if nse.get("lower"):
                st.markdown(f"<div class='mc-green'><div style='color:#8fa3bd;font-size:11px;font-weight:700;'>🟢 LOWER CIRCUIT</div><div style='font-size:26px;font-weight:900;color:#16a34a;'>₹{nse['lower']:.2f}</div><div style='color:#64748b;font-size:10px;'>min today · {nse.get('band','')}</div></div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='mc-white'><div style='color:#8fa3bd;font-size:11px;font-weight:700;'>LOWER CIRCUIT</div><div style='font-size:18px;font-weight:800;color:#8fa3bd;'>No band</div><div style='color:#64748b;font-size:10px;'>F&amp;O stock</div></div>", unsafe_allow_html=True)
        if nse.get("iep") and mst_s in ("pre", "closed"):
            ic = "#16a34a" if (nse.get("iep_chg") or 0) > 0 else "#dc2626" if (nse.get("iep_chg") or 0) < 0 else "#8fa3bd"
            st.markdown(f"<div style='background:#16233d;border:2px solid #3b82f6;border-radius:12px;padding:12px 18px;margin-top:8px;'><span style='color:#60a5fa;font-weight:800;'>🌅 Pre-open (IEP): ₹{nse['iep']:.2f}</span> <span style='color:{ic};font-weight:700;'>({nse.get('iep_chg',0):+.2f} / {nse.get('iep_pct',0):+.2f}%)</span> <span style='color:#8fa3bd;font-size:12px;'>— NSE's likely opening price, set in the 9:00–9:15 auction.</span></div>", unsafe_allow_html=True)
    elif not sym.startswith("^"):
        st.markdown("<div style='background:#16233d;border:1px solid #334155;border-radius:10px;padding:8px 14px;margin-top:6px;color:#64748b;font-size:12px;'>Circuit limits & pre-open unavailable (NSE not reachable right now).</div>", unsafe_allow_html=True)

    st.markdown('<div class="sh">💾 SAVE THIS ANALYSIS</div>', unsafe_allow_html=True)
    try:
        stamp = datetime.now().strftime("%Y%m%d_%H%M")
        fnbase = f"{name.replace(' ', '_')[:20]}_{stamp}"
        html_report = build_report_html(sym, name, iv, per, res, plan, sr, nse, htf, mst_s)
        docx_bytes = build_report_docx(sym, name, iv, per, res, plan, sr, nse, htf, mst_s)
        dcols = st.columns(3 if docx_bytes else 2)
        with dcols[0]:
            st.download_button("📄 Download report (HTML)", data=html_report,
                               file_name=f"{fnbase}.html", mime="text/html",
                               **STRETCH)
        with dcols[1]:
            st.download_button("📝 Download as text", data=_report_text(sym, name, res, plan, sr, nse, htf),
                               file_name=f"{fnbase}.txt", mime="text/plain",
                               **STRETCH)
        if docx_bytes:
            with dcols[2]:
                st.download_button("📘 Download Word (.docx)", data=docx_bytes,
                                   file_name=f"{fnbase}.docx",
                                   mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                   **STRETCH)
        st.markdown("<div style='color:#8fa3bd;font-size:12px;margin-top:4px;'>"
                    "Saves every detail — trend, signal, circuit, levels, all pivots, Fibonacci &amp; "
                    "all indicators. <b>For a PDF:</b> open the HTML file and press <b>Ctrl+P → Save as PDF</b>."
                    + ("" if docx_bytes else " (Install <code>python-docx</code> to also get a Word file.)")
                    + "</div>", unsafe_allow_html=True)
    except Exception as e:
        st.caption(f"Report export unavailable: {type(e).__name__}")

    jc1, jc2 = st.columns([1, 2])
    with jc1:
        if st.button("📓 Save to Journal (verify tomorrow)", **STRETCH, key="jrn_save"):
            entry = {"saved": now_ist().strftime("%Y-%m-%d %H:%M"),
                     "sym": sym, "name": name, "price": res['price'],
                     "trend": res['trend'], "signal": res['sig'], "conf": res['conf'],
                     "stage": tim['stage'], "quality": tim['quality'],
                     "sit": plan['sit'], "buy_at": plan['buy_at'], "sl": plan['sl'],
                     "t1": plan['t1'], "t2": plan['t2'], "t3": plan['t3'], "rr": plan['rr'],
                     "news": news['verdict'] if news else "—",
                     "ema200_ok": bool(ema2 and ema2.get('ok'))}
            if journal_save(entry):
                st.success("✅ Saved. Open the 📓 Journal tab tomorrow to see if it was right.")
            else:
                st.error("Couldn't write journal file.")
    with jc2:
        st.markdown("<div style='color:#8fa3bd;font-size:12px;margin-top:6px;'>Saves today's plan to "
                    "<code>trade_journal_NAME.json</code> (NAME = your memory name). Next day the <b>📓 Journal</b> tab checks whether "
                    "price hit your targets or stop — building your real accuracy record.</div>",
                    unsafe_allow_html=True)

    st.markdown('<div class="sh">📊 KEY METRICS</div>', unsafe_allow_html=True)
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    rv = res.get('rsi', np.nan); adxv = res.get('adx', np.nan); cciv = res.get('cci', np.nan)
    mfiv = res.get('mfi', np.nan); bbwv = res.get('bbw', np.nan)
    with m1: st.metric("RSI (14)", f"{rv:.1f}" if not np.isnan(rv) else "N/A",
                       "Oversold" if not np.isnan(rv) and rv < 30 else "Overbought" if not np.isnan(rv) and rv > 70 else "Neutral")
    with m2: st.metric("ADX", f"{adxv:.1f}" if not np.isnan(adxv) else "N/A",
                       "Strong" if not np.isnan(adxv) and adxv > 25 else "Weak trend")
    with m3: st.metric("CCI", f"{cciv:.0f}" if not np.isnan(cciv) else "N/A",
                       "Buy" if not np.isnan(cciv) and cciv < -100 else "Sell" if not np.isnan(cciv) and cciv > 100 else "Neutral")
    with m4: st.metric("MFI", f"{mfiv:.1f}" if not np.isnan(mfiv) else "N/A",
                       "Inflow" if not np.isnan(mfiv) and mfiv < 40 else "Outflow" if not np.isnan(mfiv) and mfiv > 60 else "Balanced")
    with m5: st.metric("BB Width", f"{bbwv:.2f}%" if not np.isnan(bbwv) else "N/A",
                       "⚡ SQUEEZE!" if not np.isnan(bbwv) and bbwv < 1.5 else "Normal")
    with m6: st.metric("ATR", f"₹{res['atr']:.2f}", f"σ ₹{res['std20']:.2f}" if res['std20'] else "")

    st.markdown(f'<div class="sh">{plan["head"]} · ENTRY · STOP · TARGETS</div>', unsafe_allow_html=True)
    ep1, ep2, ep3 = st.columns(3)
    with ep1:
        el = "💰 BUY NOW AT" if plan['sit'] == 'BUY_NOW' else "⏳ BUY WHEN PRICE IS"
        st.markdown(f"<div style='background:{'#052e16' if plan['sit']=='BUY_NOW' else '#2b1c0c'};border:2px solid {plan['ac']};border-radius:16px;padding:22px;text-align:center;'><div style='color:#8fa3bd;font-size:11px;font-weight:700;'>{el}</div><div style='font-size:40px;font-weight:900;color:{plan['ac']};margin:10px 0;'>₹{plan['buy_at']:,.2f}</div><div style='color:{plan['ac']};font-size:12px;font-weight:600;'>{plan['timing']}</div></div>", unsafe_allow_html=True)
    with ep2:
        st.markdown(f"<div style='background:#2a0e0e;border:2px solid #dc2626;border-radius:16px;padding:22px;text-align:center;'><div style='color:#8fa3bd;font-size:11px;font-weight:700;'>🛑 STOP LOSS</div><div style='font-size:40px;font-weight:900;color:#dc2626;margin:10px 0;'>₹{plan['sl']:,.2f}</div><div style='color:#dc2626;font-size:13px;font-weight:700;'>{plan['sl_pct']:.1f}% below entry</div></div>", unsafe_allow_html=True)
    with ep3:
        st.markdown(f"<div style='background:#16233d;border:2px solid #3b82f6;border-radius:16px;padding:22px;text-align:center;'><div style='color:#8fa3bd;font-size:11px;font-weight:700;'>⚖️ RISK : REWARD</div><div style='font-size:40px;font-weight:900;color:#60a5fa;margin:10px 0;'>1 : {plan['rr']}</div><div style='color:#3b82f6;font-size:13px;font-weight:700;'>at Target 2</div></div>", unsafe_allow_html=True)

    tp1, tp2, tp3 = st.columns(3)
    for col, tprice, tpct, lbl, css, clr in [
        (tp1, plan['t1'], plan['t1p'], "🥉 TARGET 1 · book part", "mc-green", "#16a34a"),
        (tp2, plan['t2'], plan['t2p'], "🥈 TARGET 2 ⭐ main", "mc-green", "#16a34a"),
        (tp3, plan['t3'], plan['t3p'], "🥇 TARGET 3 · runner", "mc-purple", "#9333ea")]:
        with col:
            st.markdown(f"<div class='{css}'><div style='font-size:12px;font-weight:700;color:#8fa3bd;'>{lbl}</div><div style='font-size:34px;font-weight:900;color:{clr};margin:8px 0;line-height:1;'>₹{tprice:,.2f}</div><div style='font-size:13px;color:#8fa3bd;font-weight:600;'>+{tpct:.2f}% from entry</div></div>", unsafe_allow_html=True)
    st.markdown(f"<div style='background:#16233d;border:2px solid #3b82f6;border-radius:14px;padding:14px 20px;margin:14px 0;'><span style='color:#60a5fa;font-weight:800;font-size:14px;'>📋 Plan:</span> <span style='color:#cbd5e1;font-size:14px;'>Buy near <b>₹{plan['buy_at']:.2f}</b> · stop <b>₹{plan['sl']:.2f}</b> · book at T1 <b>₹{plan['t1']:.2f}</b>, main exit T2 <b>₹{plan['t2']:.2f}</b>. You decide the quantity based on your own money.</span></div>", unsafe_allow_html=True)

    st.markdown('<div class="sh">📐 SUPPORT · RESISTANCE · FIBONACCI · CAMARILLA · WOODIE</div>', unsafe_allow_html=True)
    if sr:
        s1, s2 = st.columns(2)
        with s1:
            ns = sr.get('ns')
            if ns:
                st.markdown(f"<div style='background:#052e16;border:2px solid #16a34a;border-radius:16px;padding:18px;'><div style='color:#16a34a;font-weight:800;font-size:14px;'>🟢 NEAREST SUPPORT — BUY ZONE</div><div style='font-size:34px;font-weight:900;color:#16a34a;margin:8px 0;'>₹{ns['price']:.2f}</div><div style='color:#cbd5e1;font-size:12px;'>{abs(ns['dist']):.1f}% below · SL ₹{round(ns['price']*0.993,2):.2f}</div></div>", unsafe_allow_html=True)
        with s2:
            nr = sr.get('nr')
            if nr:
                st.markdown(f"<div style='background:#2a0e0e;border:2px solid #dc2626;border-radius:16px;padding:18px;'><div style='color:#dc2626;font-weight:800;font-size:14px;'>🔴 NEAREST RESISTANCE — BOOK PROFIT</div><div style='font-size:34px;font-weight:900;color:#dc2626;margin:8px 0;'>₹{nr['price']:.2f}</div><div style='color:#cbd5e1;font-size:12px;'>{abs(nr['dist']):.1f}% above · book profit here</div></div>", unsafe_allow_html=True)

        tab_std, tab_fib, tab_cam, tab_wood = st.tabs(
            ["📐 Standard Pivots", "🌀 Fibonacci", "🎯 Camarilla", "🔷 Woodie"])
        with tab_std:
            st.markdown("<div style='background:#16233d;border:1px solid #bfdbfe;border-radius:12px;padding:12px 16px;margin-bottom:12px;'><b style='color:#60a5fa;'>📐 Full level ladder</b> — pivots + swings + 52-week + circuits, typed by position vs current price (a broken support becomes resistance).</div>", unsafe_allow_html=True)
            for lvl in sr['levels']:
                lp = lvl['price']; dist = lvl['dist']; tp = lvl['type']
                is_cur = abs(dist) < 0.5
                if is_cur: css, lbl, clr, dt = "lv-cur", "📍 CURRENT PRICE", "#3b82f6", ""
                elif tp == 'R': css, lbl, clr, dt = "lv-r", f"🔴 {lvl['name']} — RESISTANCE", "#ef4444", f"+{abs(dist):.1f}%"
                elif tp == 'P': css, lbl, clr, dt = "lv-p", f"🟡 {lvl['name']} — PIVOT", "#f59e0b", f"{abs(dist):.1f}%"
                else: css, lbl, clr, dt = "lv-s", f"🟢 {lvl['name']} — SUPPORT", "#22c55e", f"{abs(dist):.1f}%"
                st.markdown(f"<div class='{css}'><div style='display:flex;justify-content:space-between;align-items:center;'><div><span style='color:{clr};font-weight:700;font-size:13px;'>{lbl}</span><span style='color:#64748b;font-size:11px;margin-left:8px;'>{dt}</span></div><div style='font-size:20px;font-weight:900;color:#e2e8f0;'>₹{lp:,.2f}</div></div></div>", unsafe_allow_html=True)
        with tab_fib:
            st.markdown(f"<div style='background:#1e1b3a;border:1px solid #d8b4fe;border-radius:12px;padding:12px 16px;margin-bottom:12px;'><b style='color:#7e22ce;'>🌀 Fibonacci Retracement</b> — 20-day swing (High ₹{sr['sw20_hi']:.2f} → Low ₹{sr['sw20_lo']:.2f})</div>", unsafe_allow_html=True)
            for ln, lp in sr['fib_levels'].items():
                dist = round((lp - price) / price * 100, 2) if price > 0 else 0
                is_cur = abs(dist) < 0.5; is_key = ln in ['38.2%', '50%', '61.8%']
                css = "lv-cur" if is_cur else "lv-fib"; clr = "#3b82f6" if is_cur else "#a855f7"
                st.markdown(f"<div class='{css}'><div style='display:flex;justify-content:space-between;align-items:center;'><div><span style='color:{clr};font-weight:{'800' if is_key else '700'};font-size:13px;'>🌀 Fib {ln}{' ⭐ KEY' if is_key else ''}</span><span style='color:#64748b;font-size:11px;margin-left:8px;'>{'← HERE' if is_cur else f'{dist:+.1f}%'}</span></div><div style='font-size:20px;font-weight:900;color:#e2e8f0;'>₹{lp:,.2f}</div></div></div>", unsafe_allow_html=True)
            st.markdown("<div style='background:#16233d;border:1px solid #bfdbfe;border-radius:12px;padding:12px 16px;margin:12px 0 8px;'><b style='color:#60a5fa;'>📈 Fibonacci Extensions</b> — profit targets</div>", unsafe_allow_html=True)
            for en, ep_ in sr['fib_ext'].items():
                dist = round((ep_ - price) / price * 100, 2) if price > 0 else 0
                st.markdown(f"<div class='lv-r'><div style='display:flex;justify-content:space-between;align-items:center;'><span style='color:#2563eb;font-weight:700;'>📈 Extension {en}</span><div><span style='font-size:18px;font-weight:900;color:#e2e8f0;'>₹{ep_:,.2f}</span><span style='color:#8fa3bd;font-size:12px;margin-left:8px;'>{dist:+.1f}%</span></div></div></div>", unsafe_allow_html=True)
        with tab_cam:
            st.markdown("<div style='background:#16233d;border:1px solid #bfdbfe;border-radius:12px;padding:12px 16px;margin-bottom:12px;'><b style='color:#60a5fa;'>🎯 Camarilla Pivots</b> — tight intraday levels. R3/S3 are strong reversal zones; a close beyond R4/S4 signals a breakout.</div>", unsafe_allow_html=True)
            st.markdown(pivot_table_html(sr['pivots']['Camarilla'], price), unsafe_allow_html=True)
        with tab_wood:
            st.markdown("<div style='background:#3a2a06;border:1px solid #fde68a;border-radius:12px;padding:12px 16px;margin-bottom:12px;'><b style='color:#fbbf24;'>🔷 Woodie Pivots</b> — weights yesterday's close more heavily, so it reacts faster to momentum than Standard pivots.</div>", unsafe_allow_html=True)
            st.markdown(pivot_table_html(sr['pivots']['Woodie'], price), unsafe_allow_html=True)

    # ── ADVANCED ANALYTICS ──
    daily_df = sr['daily'] if sr and sr.get('daily') is not None else res['df']

    reg = detect_regime(res)
    st.markdown('<div class="sh">📊 MARKET REGIME</div>', unsafe_allow_html=True)
    rg1, rg2 = st.columns(2)
    with rg1:
        st.markdown(f"<div style='background:{reg['rc']}12;border:2px solid {reg['rc']};border-radius:14px;padding:18px;text-align:center;'><div style='color:#8fa3bd;font-size:11px;font-weight:700;'>CURRENT REGIME</div><div style='font-size:24px;font-weight:900;color:{reg['rc']};margin:6px 0;'>{reg['regime']}</div><div style='color:#8fa3bd;font-size:12px;'>ADX {reg['adx']:.0f}</div></div>" if not np.isnan(reg['adx']) else f"<div style='background:{reg['rc']}12;border:2px solid {reg['rc']};border-radius:14px;padding:18px;text-align:center;'><div style='font-size:24px;font-weight:900;color:{reg['rc']};'>{reg['regime']}</div></div>", unsafe_allow_html=True)
    with rg2:
        st.markdown(f"<div style='background:{reg['vc']}12;border:2px solid {reg['vc']};border-radius:14px;padding:18px;text-align:center;'><div style='color:#8fa3bd;font-size:11px;font-weight:700;'>VOLATILITY</div><div style='font-size:24px;font-weight:900;color:{reg['vc']};margin:6px 0;'>{reg['vol']}</div><div style='color:#8fa3bd;font-size:12px;'>strategy: {'trend-follow' if 'STRONG' in reg['regime'] else 'range/mean-revert' if 'RANG' in reg['regime'] else 'wait'}</div></div>", unsafe_allow_html=True)

    st.markdown('<div class="sh">🤖 MACHINE LEARNING FORECAST</div>', unsafe_allow_html=True)
    with st.spinner("Training ML models (RF · GB · Linear)…"):
        ml = ml_predict(sym, price)
    if ml and "error" in ml:
        st.info("Install scikit-learn for ML forecasts:  `pip install scikit-learn scipy`")
    elif not ml:
        st.caption("Not enough daily history for ML on this stock.")
    else:
        st.markdown("<div style='background:#3a2a06;border:1px solid #fde68a;border-radius:10px;padding:10px 16px;margin-bottom:10px;color:#fbbf24;font-size:12px;'>⚠️ ML forecasts are statistical estimates from past patterns — markets are not truly predictable. Use the <b>backtested accuracy %</b> as a reality check: near 50% means little better than a coin flip. Never trade on this alone.</div>", unsafe_allow_html=True)
        mlc = st.columns(len(ml))
        for col, (h, v) in zip(mlc, sorted(ml.items())):
            dclr = "#16a34a" if v['dir'] == "UP" else "#dc2626"
            acc = v['acc']; aclr = "#16a34a" if acc >= 55 else "#fbbf24" if acc >= 50 else "#dc2626"
            with col:
                st.markdown(f"<div class='mc-white'><div style='color:#8fa3bd;font-size:11px;font-weight:700;'>{h}-DAY</div><div style='font-size:22px;font-weight:900;color:{dclr};margin:4px 0;'>₹{v['price']:.2f}</div><div style='color:{dclr};font-size:12px;font-weight:700;'>{v['ret']:+.2f}% {v['dir']}</div><div style='color:#64748b;font-size:10px;margin-top:4px;'>95% CI ₹{v['lo']:.0f}–{v['hi']:.0f}</div><div style='background:{aclr}18;color:{aclr};border-radius:6px;padding:2px 8px;font-size:11px;font-weight:700;margin-top:6px;display:inline-block;'>{acc:.0f}% accuracy</div></div>", unsafe_allow_html=True)

    prob = target_probability(price, plan, sym)
    if prob:
        st.markdown('<div class="sh">📈 TARGET PROBABILITY</div>', unsafe_allow_html=True)
        pcols = st.columns(4)
        for col, key in zip(pcols[:3], ["T1", "T2", "T3"]):
            pv = prob[key]
            with col:
                st.markdown(f"<div class='mc-white'><div style='color:#8fa3bd;font-size:11px;font-weight:700;'>{key} · ₹{pv['price']:.2f}</div><div style='font-size:28px;font-weight:900;color:{pv['color']};margin:4px 0;'>{pv['p']:.0f}%</div><div style='color:{pv['color']};font-size:12px;font-weight:700;'>{pv['rating']} chance</div></div>", unsafe_allow_html=True)
        with pcols[3]:
            st.markdown(f"<div class='mc-red'><div style='color:#8fa3bd;font-size:11px;font-weight:700;'>STOP HIT</div><div style='font-size:28px;font-weight:900;color:#dc2626;margin:4px 0;'>{prob['SL']['p']:.0f}%</div><div style='color:#dc2626;font-size:12px;font-weight:700;'>risk of SL</div></div>", unsafe_allow_html=True)
        st.caption("Rough estimate from ~3-day return volatility (normal model). Real markets have fat tails — treat as a guide, not a promise.")

    vp = volume_profile(daily_df)
    if vp:
        st.markdown('<div class="sh">📊 VOLUME PROFILE</div>', unsafe_allow_html=True)
        v1, v2, v3 = st.columns(3)
        with v1: st.markdown(f"<div class='mc-purple'><div style='color:#8fa3bd;font-size:11px;font-weight:700;'>POINT OF CONTROL</div><div style='font-size:24px;font-weight:900;color:#9333ea;'>₹{vp['poc']:.2f}</div><div style='color:#8fa3bd;font-size:11px;'>highest-volume price</div></div>", unsafe_allow_html=True)
        with v2: st.markdown(f"<div class='mc-blue'><div style='color:#8fa3bd;font-size:11px;font-weight:700;'>VALUE AREA (70%)</div><div style='font-size:20px;font-weight:900;color:#60a5fa;'>₹{vp['va_lo']:.0f}–₹{vp['va_hi']:.0f}</div><div style='color:#8fa3bd;font-size:11px;'>fair-value zone</div></div>", unsafe_allow_html=True)
        with v3: st.markdown(f"<div class='mc-white'><div style='color:#8fa3bd;font-size:11px;font-weight:700;'>POSITION</div><div style='font-size:13px;font-weight:700;color:#e2e8f0;margin-top:8px;'>{vp['pos']}</div></div>", unsafe_allow_html=True)

    pats = detect_patterns(daily_df)
    if pats:
        st.markdown('<div class="sh">🔍 CHART PATTERNS</div>', unsafe_allow_html=True)
        for nm, action, rel in pats:
            rc = {"High": "#16a34a", "Medium": "#fbbf24", "Low": "#8fa3bd"}[rel]
            st.markdown(f"<div style='background:#0f1a2e;border:1px solid #1e293b;border-left:5px solid {rc};border-radius:0 12px 12px 0;padding:12px 18px;margin:5px 0;'><b style='color:#e2e8f0;'>{nm}</b> <span style='background:{rc}18;color:{rc};border-radius:6px;padding:2px 8px;font-size:11px;font-weight:700;margin-left:8px;'>{rel} reliability</span><div style='color:#8fa3bd;font-size:12px;margin-top:3px;'>{action}</div></div>", unsafe_allow_html=True)
        st.caption("Pattern detection is heuristic — confirm visually on the chart before acting.")

    rm = risk_metrics(sym)
    if rm:
        st.markdown('<div class="sh">⚖️ RISK METRICS (from ~2y daily history)</div>', unsafe_allow_html=True)
        k1, k2, k3, k4, k5, k6 = st.columns(6)
        with k1: st.metric("Sharpe", f"{rm['sharpe']}", "risk-adj return")
        with k2: st.metric("Max Drawdown", f"{rm['maxdd']}%", "worst drop")
        with k3: st.metric("Calmar", f"{rm['calmar']}", "ret/drawdown")
        with k4: st.metric("Win Rate", f"{rm['win']}%", "up days")
        with k5: st.metric("VaR 95%", f"{rm['var95']}%", "1-day worst")
        with k6: st.metric("Volatility", rm['vrating'], f"{rm['avol']}% ann.")

    if sr and sr.get('daily') is not None and len(sr['daily']) >= 2:
        try:
            dd = sr['daily']
            dm = demark_pivot(float(dd['High'].iloc[-1]), float(dd['Low'].iloc[-1]),
                              float(dd['Close'].iloc[-1]), float(dd['Open'].iloc[-1]))
            if dm:
                st.markdown(f"<div style='background:#1e1b3a;border:1px solid #d8b4fe;border-radius:10px;padding:10px 16px;margin-top:8px;'><b style='color:#7e22ce;'>🎯 DeMark Pivots:</b> <span style='color:#cbd5e1;'>PP ₹{dm['PP']:.2f} · R1 ₹{dm['R1']:.2f} · S1 ₹{dm['S1']:.2f}</span></div>", unsafe_allow_html=True)
        except Exception:
            pass

    st.markdown('<div class="sh">📈 ADVANCED PRICE CHART — 5 Panels</div>', unsafe_allow_html=True)
    try:
        st.plotly_chart(make_chart(res['df'], name, plan, sr), **STRETCH)
    except Exception:
        st.info("Chart couldn't render for this data — the numbers above are still valid.")

    st.markdown('<div class="sh">🔬 ALL 12 INDICATOR SIGNALS</div>', unsafe_allow_html=True)
    cats = {}
    for s in res['sigs']:
        cats.setdefault(s.get('cat', 'Other'), []).append(s)
    for cat_name, cat_sigs in cats.items():
        st.markdown(f"**{cat_name} Indicators**")
        cols = st.columns(min(len(cat_sigs), 4))
        for col, s in zip(cols, cat_sigs):
            css = "ind-buy" if s['b'] else "ind-sell"; icon = "🟢" if s['b'] else "🔴"
            with col:
                st.markdown(f"<div class='{css}'><span style='color:{'#16a34a' if s['b'] else '#dc2626'};font-weight:700;'>{icon} {s['n']}</span> <code style='background:{'#0b3a1f' if s['b'] else '#fee2e2'};color:{'#166534' if s['b'] else '#991b1b'};font-size:11px;padding:2px 8px;border-radius:4px;'>{s['v']}</code><div style='color:#94a3b8;font-size:11px;margin-top:4px;'>{s['t']}</div></div>", unsafe_allow_html=True)

    with st.expander("📊 Raw OHLCV Data (Last 50 candles)"):
        st.dataframe(res['df'].tail(50), **STRETCH)
    st.markdown("<div style='text-align:center;color:#64748b;font-size:10px;padding:14px;border-top:1px solid #1e293b;margin-top:20px;'>⚠️ EDUCATIONAL PURPOSE ONLY · NOT FINANCIAL ADVICE · ALWAYS USE STOP LOSS · TRADE AT YOUR OWN RISK</div>", unsafe_allow_html=True)


# ============================================================
# ============================================================
# 🔴🔴🔴  LIVE 500-STOCK DASHBOARD ENGINE  🔴🔴🔴
#   bulk batched downloads · rotating refresh · flip alerts
#   · breadth · per-stock tabs · sortable table · CSV export
# ============================================================
# ============================================================
DASH_SRC = {
    "⭐ Famous 68 (most liquid)": FAMOUS,
    "🏅 Nifty 50": NIFTY50,
    "📈 Next 50": NEXT50,
    "💎 Midcap picks": MIDCAP,
    "🧩 Curated ~200 (all lists)": ALL_STOCKS,
    "🌐 Full NSE (auto-fill to your count)": None,
    "✍️ My custom list (paste symbols)": "custom",
}

DASH_PER = {"5m": "5d", "15m": "1mo", "30m": "3mo", "1h": "3mo"}
SECTORS_FOR_BREADTH = {"💻 IT": IT_S, "🏦 Bank": BANK_S, "⚡ Power": POWER_S,
                        "🛡️ Defence": DEF_S, "🚗 Auto": AUTO_S, "💊 Pharma": PHARMA_S}


@st.cache_resource
def _rank_bg_store():
    """🧵 ONE ranker worker for the whole process — survives page reruns (a
    plain module dict re-inits on every rerun and spawned DUPLICATE
    2000-stock ranking threads — the server drowning in its own work)."""
    return {"t": None, "day": None, "fin": 0.0}


_RANK_BG = _rank_bg_store()


def rank_universe(n):
    """🌐 FIRST SCAN OF THE DAY — TOP n of the whole NSE, cached to disk for
    the day. The heavy sweep runs in a BACKGROUND thread (the old inline
    version was killed mid-flight by the page's 2-minute refresh → the
    endless 'scanning symbols, no result' loop). While it works, callers
    get (None, None) and use the curated board — the radar never waits."""
    key = f"universe_rank_{_ukey()}_{now_ist().strftime('%Y-%m-%d')}.json"
    try:
        if _os.path.exists(key):
            d = _json.load(open(key, encoding="utf-8"))
            if isinstance(d, dict) and d.get("watch") and d.get("n") == n:
                return d["watch"], d.get("names") or {}
    except Exception:
        pass
    try:
        import threading
        today = now_ist().strftime("%Y-%m-%d")
        _alive = bool(_RANK_BG.get("t") and _RANK_BG["t"].is_alive())
        if _RANK_BG.get("day") == today and (_alive or time.time() - _RANK_BG.get("fin", 0) < 600):
            return None, None                     # running / recently failed — don't storm
        def _work():
            blog(f"🌐 ranker started · {n} of the whole NSE (background)")
            _t0 = time.time()
            try:
                _rank_work(n)
                blog(f"🌐 ranker DONE in {time.time()-_t0:.0f}s")
            except Exception as _e:
                blog(f"🌐 ranker FAILED after {time.time()-_t0:.0f}s · {type(_e).__name__}")
            finally:
                _RANK_BG["fin"] = time.time()
        _RANK_BG.update(day=today, fin=0.0)
        _RANK_BG["t"] = threading.Thread(target=_work, daemon=True)
        _RANK_BG["t"].start()
    except Exception:
        pass
    return None, None


def _rank_work(n):
    """🌐 (background) rank the ENTIRE NSE (2,000+ stocks) by uptrend
    strength and keep the TOP n — cached to disk for the day, then every
    engine (dashboard · movers · bounces · combo) uses the best board."""
    key = f"universe_rank_{_ukey()}_{now_ist().strftime('%Y-%m-%d')}.json"
    try:
        if _os.path.exists(key):
            d = _json.load(open(key, encoding="utf-8"))
            if isinstance(d, dict) and d.get("watch") and d.get("n") == n:
                return d["watch"], d.get("names") or {}
    except Exception:
        pass
    uni = fetch_universe()["sym_map"]
    items = sorted(uni.items())
    all_syms = [y for _, y in items]
    got = {}
    prog = None
    try:
        prog = st.progress(0.0, text=f"🌐 Full-market scan — ranking ALL {len(all_syms):,} NSE stocks…")
    except Exception:
        pass
    for i in range(0, len(all_syms), 50):
        got.update(fetch_chunk(tuple(all_syms[i:i + 50]), "1d", "6mo"))
        if prog:
            try:
                prog.progress(min((i + 50) / len(all_syms), 1.0),
                              text=f"🌐 Ranking ALL NSE · {min(i + 50, len(all_syms)):,}/{len(all_syms):,}")
            except Exception:
                pass
        time.sleep(0.08)
    if prog:
        try:
            prog.empty()
        except Exception:
            pass

    def _c01(x):
        return max(-1.0, min(1.0, x))

    scored = []
    for s, y in items:
        df = got.get(y)
        try:
            if df is None or len(df) < 60:
                continue
            cl = df["Close"].values
            price = float(cl[-1])
            if price < MIN_PRICE or price > MAX_PRICE:   # keep ₹100–₹1000 only
                continue
            try:      # 💧 liquidity floor for the ranked board too
                if float(df["Volume"].astype(float).tail(20).mean()) < 100_000:
                    continue
            except Exception:
                pass
            chg5 = (price / float(cl[-6]) - 1) * 100 if len(cl) >= 6 else 0.0
            chg20 = (price / float(cl[-21]) - 1) * 100 if len(cl) >= 21 else 0.0
            base = float(cl[-200:].mean()) if len(cl) >= 200 else float(cl.mean())
            score = (45 * _c01(chg5 / 6.0) + 35 * _c01(chg20 / 12.0)
                     + (20.0 if price > base else 0.0))
            scored.append((round(score, 2), y, s))
        except Exception:
            continue
    scored.sort(key=lambda x: -x[0])
    watch = [y for _, y, _ in scored[:n]]
    names = {y: s for _, y, s in scored[:n]}
    try:
        _json.dump({"n": n, "watch": watch, "names": names}, open(key, "w", encoding="utf-8"))
    except Exception:
        pass
    return watch, names


def build_watchlist(src_key, n, custom_txt=""):
    """Watchlist of yahoo symbols (+ pretty names) for the dashboard."""
    d = DASH_SRC.get(src_key)
    out = []; nm = {}; seen = set()

    def add(sym, name):
        if sym and sym not in seen:
            seen.add(sym); out.append(sym); nm[sym] = name

    if d == "custom":
        for tok in re.split(r"[,\s]+", (custom_txt or "").upper()):
            t = tok.strip()
            if not t:
                continue
            if "." not in t and not t.startswith("^"):
                t += ".NS"
            add(t, t.replace(".NS", ""))
        return out[:500], nm
    if d is None:  # full NSE: RANK the whole market once per morning, keep TOP n
        try:
            uni = fetch_universe()["sym_map"]
        except Exception:
            uni = {}
        if uni and n < len(uni):
            try:
                _rw, _rn = rank_universe(n)
                if _rw:
                    return _rw, _rn
                # 🧵 ranking still running in background → curated board for now,
                # swapped to the ranked board automatically once it lands
            except Exception:
                pass
        for k, v in ALL_STOCKS.items():
            add(v, k)
        try:
            for s, yh in sorted(uni.items()):
                if len(out) >= n:
                    break
                add(yh, s)
        except Exception:
            pass
        return out[:n], nm
    items = list(d.items())[:n]
    for k, v in items:
        add(v, k)
    return out, nm


_FEED = {"req": 0, "got": 0, "ts": 0.0, "fb": 0.0, "yahoo_ok": 0.0}   # 🩺 feed health + fallback state


_YF_THROTTLE = {"ts": 0.0, "hits": 0}   # ⚡ Yahoo health probe state
_YF_CHUNK_TIMEOUT = 40                   # ⏱ max seconds per 50-symbol Yahoo chunk


def _yf_dl(syms, per, iv):
    """⏱ WATCHDOG download — yf.download has no timeout and hangs forever
    when Yahoo throttles big batches. Run it in a daemon thread and give up
    after _YF_CHUNK_TIMEOUT seconds → return None (caller falls back to
    Upstox). 'Loading forever' becomes structurally impossible."""
    import threading
    box, done = {}, threading.Event()
    def _w():
        try:
            try:
                box["d"] = yf.download(list(syms), period=per, interval=iv, group_by='ticker',
                                       threads=True, progress=False, auto_adjust=True)
            except RuntimeError:        # 🧵 free-host thread limit → single-thread retry
                box["d"] = yf.download(list(syms), period=per, interval=iv, group_by='ticker',
                                       threads=False, progress=False, auto_adjust=True)
        except Exception:
            box["d"] = None
        finally:
            done.set()
    threading.Thread(target=_w, daemon=True).start()
    if not done.wait(_YF_CHUNK_TIMEOUT):
        return None          # hung — abandon it (thread dies quietly as daemon)
    return box.get("d")


def _yf_ok():
    """⚡ THROTTLE SKIP — one tiny 8-second probe BEFORE any big download.
    Yahoo throttling? → skip straight to the Upstox fallback for 5 minutes
    (yfinance hangs for MINUTES per request when throttled — that endless
    'loading' is exactly this). Probe passes again automatically once
    Yahoo recovers."""
    try:
        if time.time() - _YF_THROTTLE["ts"] < 300:
            return False
        req = urllib.request.Request(
            "https://query1.finance.yahoo.com/v8/finance/chart/TATASTEEL.NS?range=1d&interval=5m",
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
        urllib.request.urlopen(req, timeout=8).read()
        return True
    except Exception:
        _was_ok = _YF_THROTTLE.get("ts") == 0
        _YF_THROTTLE["ts"] = time.time()
        _YF_THROTTLE["hits"] += 1
        if _was_ok:
            blog("⚡ Yahoo throttled — switching to Upstox (auto, 5-min recheck)")
        return False


@st.cache_data(ttl=90, max_entries=120, show_spinner=False)
def fetch_chunk(syms, iv, per):
    """ONE batched Yahoo download for ~50 symbols (normal data source).
    Upstox = automatic fallback when Yahoo is slow/blocked — watchdog-
    bounded, so it can never hang. 500-stock scanning stays possible."""
    try:
        _FEED["req"] += len(syms)
    except Exception:
        pass
    if iv in ("1m", "5m", "15m"):
        up_prefetch(tuple(syms))   # 📡 tick-fresh LTPs into cache (no-op without token)
    try:
        if not _yf_ok():
            data = None           # ⚡ throttled — skip straight to the fallback
        else:
            data = _yf_dl(syms, per, iv)     # ⏱ watchdog-bounded (never hangs)
            if data is None:
                _YF_THROTTLE["ts"] = time.time()   # ⏱ it hung → cooldown + fallback
    except Exception:
        data = None               # 📡 flow on — the UNINTERRUPTED hook below may rescue
    out = {}
    try:
        if data is None or data.empty:
            data = None
        single = not isinstance(data.columns, pd.MultiIndex)   # flat cols only (1-symbol yf
        #  downloads can ALSO be MultiIndex — data[s] handles both, so never assume flat)
        for s in syms:
            try:
                df = data if single else data[s]
                if df is None or len(df) == 0:
                    continue
                df = df.rename(columns=str.title)
                need = {'Open', 'High', 'Low', 'Close', 'Volume'}
                if not need.issubset(set(df.columns)):
                    continue
                df = df[list(need)].dropna()
                if len(df) >= 30:
                    out[s] = df
            except Exception:
                continue
    except Exception:
        pass
    try:
        _FEED["got"] += len(out); _FEED["ts"] = time.time()
    except Exception:
        pass
    # ── 📡 UNINTERRUPTED — Yahoo blocked/thin? → Upstox live fallback ──
    try:
        _miss = [s for s in syms if s not in out]
        _fb = {}
        if _miss and up_token_valid():
            if iv == "1d":
                _fb = up_daily_candles(_miss) or {}          # 📡 6-month daily history (cached/day)
            else:
                _fb = up_intraday_candles(_miss) or {}       # 📡 real candles from market open
                if not _fb:
                    _fb = up_fallback_candles(_miss) or {}   # 📡 tick-stitch backup
            if not _fb:
                _FEED["fb_fail"] = time.time()               # 🩺 honest diagnostic signal
            if _fb:
                out.update(_fb)
                _FEED["fb"] = time.time()
        if len(out) - len(_fb) >= max(2, int(len(syms) * 0.8)):
            up_cache_save({s: d for s, d in out.items() if s not in _fb})   # yf-sourced only
            _FEED["yahoo_ok"] = time.time()
    except Exception:
        pass
    return {s: up_patch_df(s, d) for s, d in out.items()}   # 📡 splice live LTP


def day_chg_from_intraday(df):
    """% change vs PREVIOUS day's close, from an intraday series."""
    try:
        dates = sorted(set(df.index.date))
        if len(dates) >= 2:
            prev_day = df[df.index.date == dates[-2]]
            prev_close = float(prev_day['Close'].iloc[-1])
            last = float(df['Close'].iloc[-1])
            if prev_close > 0:
                return round((last / prev_close - 1) * 100, 2)
    except Exception:
        pass
    return 0.0


def daily_context(daily):
    """Daily-chart trend + 200EMA position for one stock (fast, no fetch)."""
    out = {"dtr": "—", "ema200": None, "above200": None}
    try:
        if daily is None or len(daily) < 30:
            return out
        c = daily['Close']; n = len(c)
        e200 = ta.trend.ema_indicator(c, 200) if n >= 200 else ta.trend.ema_indicator(c, min(n - 1, 150))
        e200v = safe(e200.iloc[-1])
        d = daily.tail(60); H = d['High'].values; L = d['Low'].values
        sh = []; slo = []
        for i in range(2, len(H) - 2):
            if H[i] > max(H[i-1], H[i-2], H[i+1], H[i+2]): sh.append(H[i])
            if L[i] < min(L[i-1], L[i-2], L[i+1], L[i+2]): slo.append(L[i])
        hh = len(sh) >= 2 and sh[-1] > sh[-2]; hl = len(slo) >= 2 and slo[-1] > slo[-2]
        lh = len(sh) >= 2 and sh[-1] < sh[-2]; ll = len(slo) >= 2 and slo[-1] < slo[-2]
        if hh and hl:   tr = "UPTREND"
        elif lh and ll: tr = "DOWNTREND"
        elif hh and ll: tr = "VOLATILE"
        else:           tr = "SIDEWAYS"
        out["dtr"] = tr
        if not np.isnan(e200v) and e200v > 0:
            out["ema200"] = round(e200v, 2)
            out["above200"] = bool(float(c.iloc[-1]) > e200v)
        return out
    except Exception:
        return out


def dash_row(name, sym, intra, daily):
    """One dashboard row: intraday signal + daily trend + quick plan + score."""
    try:
        res = compute_signals(intra.tail(400))
        if not res:
            return None
        dc = daily_context(daily)
        plan = make_plan(res['price'], res['atr'], None, res['sig'])
        chg = day_chg_from_intraday(intra)
        score = (res['bp'] * 0.4 + res['conf'] * 0.2
                 + (20 if dc['dtr'] == 'UPTREND' else 0)
                 + (10 if dc['above200'] else 0)
                 + (5 if res['trend'] == 'UPTREND' else 0)
                 + min(max(res['vr'], 0), 2.5) * 2
                 + max(min(chg, 5), -5))
        spark = [round(float(x), 2) for x in intra['Close'].tail(80).tolist()]
        return {"name": name, "sym": sym, "price": res['price'], "chg": chg,
                "sig": res['sig'], "sc": res['sc'], "conf": res['conf'],
                "bp": res['bp'], "sp": res['sp'], "dtr": dc['dtr'],
                "above200": dc['above200'], "ema200": dc['ema200'],
                "rsi": res['rsi'], "adx": res['adx'], "vr": res['vr'], "atr": res['atr'],
                "itrend": res['trend'], "score": round(score, 1),
                "buy_at": plan['buy_at'], "sl": plan['sl'], "t1": plan['t1'],
                "t2": plan['t2'], "rr": plan['rr'], "act": plan['act'], "sit": plan['sit'],
                "spark": spark, "ts": time.time()}
    except Exception:
        return None


def _ingest(syms, got, got_d, names, rows, prev, alerts):
    """Build dashboard rows from fetched frames + track flips & uptrend-since."""
    for sym in syms:
        intra = got.get(sym)
        if intra is None:
            continue
        r = dash_row(names.get(sym, sym.replace(".NS", "")), sym, intra, got_d.get(sym))
        if not r or not (MIN_PRICE <= (r.get("price") or 0) <= MAX_PRICE):
            continue
        old = prev.get(sym)
        if old and (old.get("sig") != r["sig"] or old.get("dtr") != r["dtr"]):
            alerts.insert(0, {"ts": now_ist().strftime("%H:%M:%S"),
                              "name": r["name"], "sym": sym,
                              "txt": f"{old.get('sig', '—')} → {r['sig']} · trend {old.get('dtr', '—')} → {r['dtr']}"})
        prev[sym] = {"sig": r["sig"], "dtr": r["dtr"]}
        old_row = rows.get(sym)
        if r["dtr"] == "UPTREND":
            r["up_since"] = (old_row.get("up_since")
                             if (old_row and old_row.get("dtr") == "UPTREND" and old_row.get("up_since"))
                             else time.time())
        else:
            r["up_since"] = None
        rows[sym] = r


def _sweep(syms, iv, per, with_daily=True, progress=False, label=""):
    """Batched download of a symbol list (chunks of 50)."""
    got, got_d = {}, {}
    CH = 50
    prog = (st.progress(0.0) if progress and not _CB_BG.get("busy") else None)
    for i in range(0, len(syms), CH):
        chunk = tuple(syms[i:i + CH])
        got.update(fetch_chunk(chunk, iv, per))
        if with_daily:
            got_d.update(fetch_chunk(chunk, '1d', '6mo'))
        if prog:
            try:
                prog.progress(min((i + CH) / max(len(syms), 1), 1.0),
                              text=f"🔴 {label} {min(i + CH, len(syms))}/{len(syms)} symbols…")
            except Exception:
                prog.progress(min((i + CH) / max(len(syms), 1), 1.0))
        try:
            time.sleep(0.12)
        except Exception:
            pass
    if prog:
        prog.empty()
    return got, got_d


def dash_refresh(ss, watch, iv, per, batch, progress=False, with_daily=True, ensure_min=0):
    """Refresh the stalest/missing batch — and GUARANTEE a minimum number of
    live rows by retrying missing symbols in extra passes."""
    state = ss.get("dash") or {}
    rows = state.get("rows", {}); prev = state.get("prev", {}); alerts = state.get("alerts", [])
    names = ss.get("dash_names") or {}
    missing = [s for s in watch if s not in rows]
    if missing:
        target = missing[:batch]
    else:
        target = sorted(watch, key=lambda s: rows.get(s, {}).get("ts", 0))[:batch]
    got, got_d = _sweep(target, iv, per, with_daily, progress, "Live sweep")
    _ingest(target, got, got_d, names, rows, prev, alerts)
    # ── minimum-count guarantee: retry whatever is still missing (max 2 passes)
    pass_n = 0
    while ensure_min and len(rows) < min(ensure_min, len(watch)) and pass_n < 2:
        pass_n += 1
        miss2 = [s for s in watch if s not in rows]
        if not miss2:
            break
        if progress:
            try:
                st.info(f"🔁 Guarantee pass {pass_n} — filling {len(miss2)} missing symbols (target: ≥{ensure_min} live)…")
            except Exception:
                pass
        g2, gd2 = _sweep(miss2, iv, per, with_daily, False)
        _ingest(miss2, g2, gd2, names, rows, prev, alerts)
    rows = {s: r for s, r in rows.items() if s in watch}
    alerts[:] = alerts[:40]
    ss["dash"] = {"rows": rows, "prev": prev, "alerts": alerts}
    return ss["dash"]


@st.cache_data(ttl=90, show_spinner=False)
def fetch_indices():
    """NIFTY 50 + BANK NIFTY pulse for the terminal header."""
    out = {"NIFTY 50": None, "BANK NIFTY": None}
    try:
        got = fetch_chunk(tuple(["^NSEI", "^NSEBANK"]), "15m", "5d")
        for lbl, s in out.items():
            sym = "^NSEI" if lbl == "NIFTY 50" else "^NSEBANK"
            df = got.get(sym)
            if df is not None and len(df):
                out[lbl] = {"price": float(df['Close'].iloc[-1]),
                            "chg": day_chg_from_intraday(df)}
    except Exception:
        pass
    return out


def svg_spark(vals, w=120, h=30):
    """Tiny inline SVG sparkline — crisp on any screen, no JS needed."""
    try:
        v = [x for x in (vals or []) if x == x]
        if len(v) < 2:
            return ""
        lo, hi = min(v), max(v); rng = (hi - lo) or 1e-9
        pts = [f"{i/(len(v)-1)*w:.1f},{h-2-(x-lo)/rng*(h-4):.1f}" for i, x in enumerate(v)]
        up = v[-1] >= v[0]
        stroke = "#22c55e" if up else "#ef4444"
        fill = "rgba(34,197,94,0.12)" if up else "rgba(239,68,68,0.12)"
        return (f"<svg width='{w}' height='{h}' viewBox='0 0 {w} {h}' style='display:block;'>"
                f"<polygon points='0,{h} {' '.join(pts)} {w},{h}' fill='{fill}'/>"
                f"<polyline points='{' '.join(pts)}' fill='none' stroke='{stroke}' stroke-width='1.8'/></svg>")
    except Exception:
        return ""


def _pill(txt, fg, bg):
    return f"<span style='background:{bg};color:{fg};border-radius:7px;padding:1px 8px;font-size:10px;font-weight:800;margin-right:4px;'>{txt}</span>"


def _kpi(label, value, sub, color):
    return (f"<div style='flex:1;min-width:128px;background:#0f172a;border:1px solid #1e293b;border-radius:14px;padding:13px 15px;'>"
            f"<div style='color:#64748b;font-size:10px;font-weight:800;letter-spacing:1px;'>{label}</div>"
            f"<div style='color:{color};font-size:29px;font-weight:900;font-family:ui-monospace,Menlo,Consolas,monospace;line-height:1.2;'>{value}</div>"
            f"<div style='color:#64748b;font-size:11px;margin-top:1px;'>{sub}</div></div>")


def _lb_row(i, r, now):
    chg = r.get("chg", 0); cc = "#22c55e" if chg >= 0 else "#ef4444"
    badges = ""
    if r.get("up_since") and now - r["up_since"] < 3600:
        badges += _pill("🆕 NEW UPTREND", "#4ade80", "rgba(34,197,94,0.16)")
    if r.get("above200"):
        badges += _pill("⬆ 200EMA", "#93c5fd", "rgba(59,130,246,0.16)")
    if (r.get("vr") or 0) >= 2:
        badges += _pill(f"🔊 VOL {r['vr']:.1f}x", "#fbbf24", "rgba(245,158,11,0.16)")
    spark = svg_spark(r.get("spark"))
    return (f"<div style='display:flex;align-items:center;gap:12px;background:#0f172a;border:1px solid #1e293b;"
            f"border-left:3px solid #22c55e;border-radius:12px;padding:8px 14px;margin:5px 0;flex-wrap:wrap;'>"
            f"<div style='color:#475569;font-weight:900;font-size:15px;width:32px;font-family:monospace;'>{i}</div>"
            f"<div style='min-width:148px;'><div style='color:#f1f5f9;font-weight:800;font-size:14px;'>{r['name'][:19]}</div>"
            f"<div style='color:#64748b;font-size:10px;'>{r['sym'].replace('.NS','')} · {r['sig'].title()}</div></div>"
            f"<div style='min-width:96px;color:#e2e8f0;font-weight:800;font-size:14px;font-family:monospace;'>₹{r['price']:,.2f}</div>"
            f"<div style='min-width:72px;'><span style='color:{cc};font-weight:900;font-size:13px;font-family:monospace;'>{chg:+.2f}%</span></div>"
            f"<div style='min-width:126px;'><div style='display:flex;align-items:center;gap:6px;'>"
            f"<div style='background:#1e293b;width:70px;height:6px;border-radius:3px;'><div style='background:#22c55e;width:{min(r['conf'],100):.0f}%;height:6px;border-radius:3px;'></div></div>"
            f"<span style='color:#94a3b8;font-size:10px;font-family:monospace;'>{r['conf']:.0f}%</span></div>"
            f"<div style='display:flex;align-items:center;gap:6px;margin-top:3px;'>"
            f"<div style='background:#1e293b;width:70px;height:6px;border-radius:3px;'><div style='background:#3b82f6;width:{min(r['score'],100):.0f}%;height:6px;border-radius:3px;'></div></div>"
            f"<span style='color:#94a3b8;font-size:10px;font-family:monospace;'>score {r['score']:.0f}</span></div></div>"
            f"<div style='min-width:126px;'>{spark}<div style='margin-top:2px;'>{badges}</div></div></div>")


def spark_fig(r):
    y = r.get("spark") or []
    up = (y[-1] >= y[0]) if len(y) >= 2 else True
    clr = "#16a34a" if up else "#dc2626"
    fig = go.Figure(go.Scatter(y=y, mode="lines", line=dict(color=clr, width=2.2),
                               fill="tozeroy",
                               fillcolor="rgba(22,163,74,0.08)" if up else "rgba(220,38,38,0.08)"))
    fig.update_layout(height=230, margin=dict(l=8, r=8, t=6, b=6), showlegend=False,
                      paper_bgcolor="white", plot_bgcolor="white",
                      xaxis=dict(showticklabels=False, showgrid=False),
                      yaxis=dict(showticklabels=True, showgrid=True, gridcolor="#1e293b", tickfont=dict(size=9)))
    return fig


def _fmt_age(sec):
    sec = int(max(sec, 0))
    return f"{sec//60}m {sec%60}s" if sec >= 60 else f"{sec}s"


# ============================================================
# ⚡ LIVE MOVERS — follow the MONEY, not the math.
#   Pure price action: who is REALLY going up right now?
#   (steady green candles · last-hour slope · near day-high ·
#    volume confirming). No indicator predictions here.
# ============================================================
def compute_movers(got):
    """Score every stock's LIVE climb from today's 5-minute candles."""
    out = []
    today = now_ist().date()
    # effective session: today if candles exist, else the latest traded day
    # (post-midnight / pre-open → full review of the LAST session)
    all_dates = set()
    for _s, _df in got.items():
        try:
            if _df is not None and len(_df):
                for _ix in _df.index:
                    all_dates.add(_dist(_ix))
        except Exception:
            pass
    sess = max((d for d in all_dates if d <= today), default=today)
    for sym, df in got.items():
        try:
            if df is None or len(df) < 12:
                continue
            dates = [_dist(ix) for ix in df.index]
            td = [i for i, d in enumerate(dates) if d == sess]
            if len(td) < 3:      # 9:30 AM IST = 3 candles — already scorable
                continue
            d0 = td[0]
            prev_close = float(df["Close"].iloc[d0 - 1]) if d0 > 0 else float(df["Open"].iloc[d0])
            t = df.iloc[d0:td[-1] + 1]
            o = float(t["Open"].iloc[0]); last = float(t["Close"].iloc[-1])
            hi = float(t["High"].max()); lo = float(t["Low"].min())
            if last < MIN_PRICE or last > MAX_PRICE:   # keep ₹100–₹1000 only
                continue
            cl = t["Close"].values; op = t["Open"].values; vol = t["Volume"].values
            n = len(cl)
            chg_day = (last - prev_close) / prev_close * 100 if prev_close else 0.0
            g, oo = cl[-24:], op[-24:]
            green = (sum(1 for i in range(len(g)) if g[i] > oo[i]) / len(g)) if len(g) else 0.5
            base = cl[-13] if n >= 13 else cl[0]
            slope1h = (last - base) / base * 100 if base else 0.0
            pos = (last - lo) / (hi - lo) if hi > lo else 0.5
            vrec = vol[-6:]
            vold = vol[:-6] if len(vol) > 6 else vol
            vr = (vrec.mean() / vold.mean()) if (len(vold) and vold.mean() > 0) else 1.0

            def _c(x):
                return max(-1.0, min(1.0, x))
            s = (35 * _c(chg_day / 3.0) + 25 * _c((green - 0.5) / 0.35) + 20 * _c(slope1h / 1.0)
                 + 10 * _c((pos - 0.5) / 0.5) + 10 * _c((vr - 1.0) / 1.5))
            climb = round(50 + s / 2, 1)
            steady = (0.2 <= chg_day <= 4.5) and green >= 0.55
            state = ("CLIMBING" if (climb >= 68 and chg_day > 0 and slope1h > 0)
                     else "FORMING" if (climb >= 57 and chg_day > 0 and slope1h > -0.05)
                     else "WATCH" if climb >= 58 else "—")
            _vw = float((cl * vol).sum() / vol.sum()) if vol.sum() > 0 else last
            out.append({"sym": sym, "last": round(last, 2), "chg_day": round(chg_day, 2),
                        "green": int(round(green * 100)), "slope1h": round(float(slope1h), 2),
                        "pos": int(round(pos * 100)), "vr": round(float(vr), 2),
                        "climb": climb, "steady": steady, "state": state,
                        "hi": round(hi, 2), "lo": round(lo, 2),
                        "vwap": round(_vw, 2), "ext": round((last / _vw - 1) * 100, 2)})
        except Exception:
            continue
    out.sort(key=lambda m: -m["climb"])
    return out


def mv_room_ok(m):
    """True if the climb still has PROFIT ROOM: not stretched above VWAP and
    not already up too much today — the buyable kind, not the topped-out kind
    (those keep 'climbing' but pull back and eat your money)."""
    return (m.get("ext", 9.9) <= 1.2 and 0 < m.get("chg_day", 9) <= 3.0)


def _mv_row(i, m, name, delta=0):
    climbing = m["state"] == "CLIMBING"
    forming = m["state"] == "FORMING"
    border = ("#22c55e" if climbing else "#a3e635" if forming
              else "#3b82f6" if m["state"] == "WATCH" else "#334155")
    cc = "#22c55e" if m["chg_day"] >= 0 else "#ef4444"
    badge = ("<span style='background:rgba(34,197,94,.16);color:#4ade80;font-size:9.5px;"
             "font-weight:900;padding:2px 8px;border-radius:8px;'>⚡ CLIMBING</span>" if climbing else
             ("<span style='background:rgba(163,230,53,.14);color:#bef264;font-size:9.5px;"
               "font-weight:900;padding:2px 8px;border-radius:8px;'>🌱 FORMING</span>" if forming else
             ("<span style='background:rgba(59,130,246,.16);color:#93c5fd;font-size:9.5px;"
               "font-weight:900;padding:2px 8px;border-radius:8px;'>👀 WATCH</span>" if m["state"] == "WATCH" else "")))
    if m["steady"]:
        badge += (" <span style='background:rgba(245,158,11,.16);color:#fbbf24;font-size:9.5px;"
                  "font-weight:900;padding:2px 8px;border-radius:8px;'>🐢 SLOW-STEADY</span>")
    sc = m["climb"]; scw = max(0, min(100, sc)); scc = "#22c55e" if sc >= 68 else ("#3b82f6" if sc >= 58 else "#64748b")
    return (f"<div style='display:flex;align-items:center;gap:12px;background:#0f172a;border:1px solid #1e293b;"
            f"border-left:3px solid {border};border-radius:12px;padding:8px 14px;margin:5px 0;flex-wrap:wrap;'>"
            f"<div style='width:34px;'><div style='color:#475569;font-weight:900;font-size:15px;font-family:monospace;'>{i}</div>"
            f"<div style='font-size:9px;font-weight:900;font-family:monospace;color:"
            f"{'#4ade80;' if delta > 0 else '#f87171;' if delta < 0 else '#334155;'}'>"
            f"{('▲' + str(delta)) if delta > 0 else (('▼' + str(-delta)) if delta < 0 else '·')}</div></div>"
            f"<div style='min-width:150px;'><div style='color:#f1f5f9;font-weight:800;font-size:14px;'>{name[:20]}</div>"
            f"<div style='color:#64748b;font-size:10px;'>{m['sym'].replace('.NS','')} · hi ₹{m['hi']:,.2f} · lo ₹{m['lo']:,.2f}</div></div>"
            f"<div style='min-width:92px;color:#e2e8f0;font-weight:800;font-size:14px;font-family:monospace;'>₹{m['last']:,.2f}</div>"
            f"<div style='min-width:70px;color:{cc};font-weight:900;font-size:13px;font-family:monospace;'>{m['chg_day']:+.2f}%</div>"
            f"<div style='min-width:104px;'><div style='color:#64748b;font-size:9px;'>GREEN CANDLES</div>"
            f"<div style='background:#1e293b;width:70px;height:6px;border-radius:3px;'><div style='background:#22c55e;width:{m['green']}%;height:6px;border-radius:3px;'></div></div>"
            f"<div style='color:#94a3b8;font-size:9.5px;font-family:monospace;'>{m['green']}% · 1h {m['slope1h']:+.2f}%</div></div>"
            f"<div style='min-width:88px;'><div style='color:#64748b;font-size:9px;'>VOLUME · DAY POS</div>"
            f"<div style='color:{'#fbbf24' if m['vr'] >= 1.3 else '#94a3b8'};font-size:11px;font-family:monospace;font-weight:800;'>{m['vr']:.2f}×</div>"
            f"<div style='color:#94a3b8;font-size:9.5px;font-family:monospace;'>{m['pos']}% of range</div></div>"
            f"<div style='min-width:104px;'><div style='color:#64748b;font-size:9px;'>CLIMB SCORE</div>"
            f"<div style='background:#1e293b;width:74px;height:6px;border-radius:3px;'><div style='background:{scc};width:{scw}%;height:6px;border-radius:3px;'></div></div>"
            f"<div style='color:{scc};font-size:10px;font-family:monospace;font-weight:800;'>{sc:.0f}/100</div></div>"
            f"<div style='min-width:130px;'>{badge}</div></div>")


def live_movers_tab(ss, mst_s):
    # ♾️ AUTO-RESUME — the radar keeps running across page refreshes
    if not ss.get("mv_on"):
        _rt = rt_load().get("mv") or {}
        if _rt.get("on") and _rt.get("watch"):
            ss["mv_on"] = True
            ss["mv_watch"] = _rt["watch"]; ss["mv_names"] = _rt.get("names") or {}
            ss["mv"] = _rt.get("movers") or None
            ss["mv_last"] = _rt.get("last_scan", 0)
            ss["mv_ts_str"] = _rt.get("ts_str") or "—"
            ss["mv_prev"] = _rt.get("prev") or []
            ss["mv_prevform"] = _rt.get("prevform") or []
            ss["mv_alerts"] = _rt.get("alerts") or []
            if _rt.get("src"):
                ss["mv_src"] = _rt["src"]
            if _rt.get("n"):
                ss["mv_n"] = _rt["n"]
            ss["_mv_resumed"] = True

    st.markdown(_H("""<div style='background:linear-gradient(135deg,#052e16,#14532d);border-radius:18px;
    padding:18px 22px;margin-bottom:14px;'>
    <div style='color:white;font-size:20px;font-weight:900;'>⚡ LIVE MOVERS — follow the money, not the math</div>
    <div style='color:#bbf7d0;font-size:12.5px;margin-top:6px;line-height:1.7;'>This tab makes <b>NO predictions</b>.
    It watches live 5-minute candles of the whole board and shows who is <b>actually going up NOW</b>: steady green
    candles · rising in the last hour · holding near the day's high · volume confirming. When a stock starts
    climbing you get a 🔔 alert below. 🐢 SLOW-STEADY = the "slowly going up" ones you asked for (up 0.2–4.5%
    without spiking) — usually the safest to ride.</div></div>"""), unsafe_allow_html=True)

    # ── settings ──
    with st.expander("⚙️ UNIVERSE · REFRESH", expanded=not ss.get("mv_watch")):
        k1, k2 = st.columns(2)
        with k1:
            _keys = list(DASH_SRC.keys())
            _def = _keys.index(ss["dash_src"]) if ss.get("dash_src") in _keys else (
                _keys.index("🌐 Full NSE (auto-fill to your count)")
                if "🌐 Full NSE (auto-fill to your count)" in _keys else 0)
            mv_src = st.selectbox("Universe", _keys, index=_def, key="mv_src")
            mv_n = st.slider("How many stocks", 100, 500, ss.get("dash_n", 500), 50, key="mv_n")
        with k2:
            st.selectbox("Auto-refresh every", ["1 min", "2 min", "3 min", "5 min"], index=1, key="mv_int")
            st.caption("Each scan = one live sweep of the whole board (5-minute candles).")
        s1, s2, s3 = st.columns(3)
        with s1:
            start_mv = st.button("⚡ START LIVE MOVERS", type="primary", **STRETCH, key="mv_start")
        with s2:
            rescan = st.button("🔄 Scan now", **STRETCH, key="mv_rescan")
        with s3:
            stop_mv = st.button("⏹ Stop", **STRETCH, key="mv_stop")

    if stop_mv:
        ss["mv_on"] = False
        rt_clear("mv")
    if start_mv:
        watch, names = build_watchlist(mv_src, mv_n)
        ss["mv_watch"] = watch; ss["mv_names"] = names
        ss["mv_on"] = True; ss["mv"] = None; ss["mv_last"] = 0
        rt_save("mv", on=True, src=mv_src, n=mv_n, watch=watch, names=names)

    tg_settings_ui("_mv")
    up_settings_ui("_mv")

    if not ss.get("mv_on"):
        st.markdown("<div style='background:#0b1220;border-radius:20px;padding:48px;text-align:center;'>"
                    "<div style='font-size:48px;'>⚡</div>"
                    "<div style='font-size:21px;font-weight:900;color:#f1f5f9;margin-top:10px;'>LIVE MOVERS RADAR</div>"
                    "<div style='color:#64748b;font-size:13px;margin-top:8px;'>Up to 500 stocks watched live · "
                    "who is climbing right now · slow-steady riders · 🔔 alerts when a climb starts</div>"
                    "<div style='color:#94a3b8;font-size:12px;margin-top:12px;'>↑ Press "
                    "<b style='color:#22c55e;'>⚡ START LIVE MOVERS</b></div></div>", unsafe_allow_html=True)
        return

    if ss.get("_mv_resumed"):
        ss["_mv_resumed"] = False
        st.info("♾️ Live Movers resumed automatically — a page refresh does NOT stop it. "
                "Press ⏹ Stop to end the session.")

    # auto-refresh
    try:
        from streamlit_autorefresh import st_autorefresh
        _sec = int(ss.get("mv_int", "2 min").split()[0]) * 60
        if mst_s == "open":          # 🛌 after close: NO auto-refresh (free-CPU saver)
            st_autorefresh(interval=_sec * 1000, key="mv_tick")
    except Exception:
        pass

    watch = ss.get("mv_watch") or []
    names = ss.get("mv_names") or {}
    _sec = int(ss.get("mv_int", "2 min").split()[0]) * 60
    due = mst_s == "open" and time.time() - ss.get("mv_last", 0) > (_sec - 10)
    if due and not _pilot_ok("mv", ss):
        due = False
        _mv_view_sync(ss)                 # 🤖 autopilot drives — live view only
    if rescan or due or not ss.get("mv"):
        _pilot_beat("mv", ss)
        with st.spinner("⚡ Scanning the board live (5-minute candles)…"):
            got, _ = _sweep(watch, "5m", "2d", with_daily=False, progress=True)
        movers = compute_movers(got)
        ss["mv_health"] = {"ts": now_ist().strftime("%H:%M:%S"), "req": len(watch or []),
                           "got": len(got), "rows": len(movers)}
        ss["mv"] = movers
        ss["mv_last"] = time.time()
        ss["mv_ts_str"] = now_ist().strftime("%d %b %Y · %H:%M")
        # 🔔 alerts: JUST entered CLIMBING / 🌱 FORMING (early warning)
        prev_climb = set(ss.get("mv_prev") or [])
        now_climb = {m["sym"] for m in movers if m["state"] == "CLIMBING"}
        prev_form = set(ss.get("mv_prevform") or [])
        now_form = {m["sym"] for m in movers if m["state"] == "FORMING"}
        ss["mv_ranks_prev"] = ss.get("mv_ranks") or {}
        ss["mv_ranks"] = {mm["sym"]: r for r, mm in enumerate(movers, 1)}
        alerts = ss.get("mv_alerts") or []
        if mst_s == "open":   # 🔕 after close: silent review — never re-announce old climbs
            for m in [x for x in movers if x["sym"] in (now_form - prev_form - now_climb)
                      and mv_room_ok(x)][:6]:
                alerts.insert(0, {"ts": now_ist().strftime("%H:%M:%S"), "sym": m["sym"],
                                  "name": names.get(m["sym"], m["sym"].replace(".NS", "")),
                                  "txt": (f"🌱 FORMING a climb (early) · {m['chg_day']:+.2f}% today · "
                                          f"{m['green']}% green · 1h {m['slope1h']:+.2f}% · ₹{m['last']:,.2f} · "
                                          f"🎯 buy the DIP ~₹{m['last'] * 0.99:,.2f}, don't chase up")})
            for m in [x for x in movers if x["sym"] in (now_climb - prev_climb)
                      and mv_room_ok(x)]:
                alerts.insert(0, {"ts": now_ist().strftime("%H:%M:%S"), "sym": m["sym"],
                                  "name": names.get(m["sym"], m["sym"].replace(".NS", "")),
                                  "txt": (f"started climbing · {m['chg_day']:+.2f}% today · {m['green']}% green candles · "
                                          f"1h {m['slope1h']:+.2f}% · vol {m['vr']:.1f}× · ₹{m['last']:,.2f}"
                                          + (" · 🐢 slow-steady" if m["steady"] else ""))})
        ss["mv_alerts"] = alerts[:40]
        ss["mv_prev"] = sorted(now_climb)
        ss["mv_prevform"] = sorted(now_form | now_climb)
        if mst_s == "open":   # 🔕 Telegram/toasts only while the market is LIVE
            for _m in [x for x in movers if x["sym"] in (now_form - prev_form - now_climb)
                       and mv_room_ok(x)][:3]:
                _nmm = _esc(names.get(_m['sym'], _m['sym'].replace('.NS', '')))
                tg_send(f"\U0001F331 <b>{_nmm} \u00b7 FORMING A CLIMB (early)</b>\n"
                        f"\U0001F4C8 {_m['chg_day']:+.2f}% today \u00b7 {_m['green']}% green \u00b7 1h {_m['slope1h']:+.2f}% \u00b7 "
                        f"vol {_m['vr']:.1f}x\n"
                        f"\U0001F4B0 Now <code>\u20B9{_m['last']:,.2f}</code>\n"
                        f"\U0001F3AF WAIT for the dip ~<code>\u20B9{_m['last'] * 0.99:,.2f}</code> (\u22121%) to buy \u2014 don't chase up\n"
                        f"<i>\u26A0\uFE0F Already jumped away? Let it go \u2014 the next one will come</i>")
            for _m in [x for x in movers if x["sym"] in (now_climb - prev_climb)
                       and mv_room_ok(x)][:5]:
                _nmm = _esc(names.get(_m['sym'], _m['sym'].replace('.NS', '')))
                tg_send(f"\u26A1 <b>{_nmm} \u00b7 STARTED CLIMBING</b>\n"
                        f"\U0001F4C8 {_m['chg_day']:+.2f}% today \u00b7 {_m['green']}% green candles \u00b7 "
                        f"1h {_m['slope1h']:+.2f}% \u00b7 vol {_m['vr']:.1f}x\n"
                        f"\U0001F4B0 Price <code>\u20B9{_m['last']:,.2f}</code>"
                        + (" \u00b7 \U0001F422 slow-steady" if _m["steady"] else "")
                        + f"\n\U0001F3AF Safer entry on a dip ~<code>\u20B9{_m['last'] * 0.99:,.2f}</code> (\u22121%)\n"
                        f"<i>Already ran &gt; 3% today? Skip \u2014 wait for the next one</i>")
            for a in ss["mv_alerts"][:3]:
                try:
                    st.toast(f"🔔 {a['name']} — {a['txt'][:70]}")
                except Exception:
                    pass
        rt_save("mv", on=True, watch=watch, names=names, movers=movers,
                last_scan=ss["mv_last"], ts_str=ss.get("mv_ts_str"), prev=ss.get("mv_prev") or [],
                prevform=ss.get("mv_prevform") or [],
                alerts=ss.get("mv_alerts") or [], src=ss.get("mv_src"), n=ss.get("mv_n"))

    movers = ss.get("mv") or []
    _mvh = ss.get("mv_health") or {}
    if not movers:
        _hr, _hg = int(_mvh.get("req") or 0), int(_mvh.get("got") or 0)
        _pct = int(_hg * 100 / _hr) if _hr else 0
        if _hr:
            _fsx = (f" · 📡 LIVE FALLBACK on Upstox since {feed_status()[1]} IST"
                    if feed_status()[0] == "fallback" else "")
            st.caption(f"🩺 SCAN DIAGNOSIS · data feed {_hg}/{_hr} stocks ({_pct}%) · "
                       f"last scan {_mvh.get('ts', '—')}{_fsx}")
        if mst_s == "open" and _hr and _hg == 0:
            st.markdown("<div style='background:#2a0e0e;border:1px solid #ef4444;border-radius:12px;padding:14px 18px;"
                        "color:#fecaca;font-size:13px;line-height:1.8;'>❌ <b>DATA FEED FAILED — downloaded 0 of "
                        f"{_hr} stocks.</b><br>The connection between this server and the price source (Yahoo) is "
                        "failing — host overload or a temporary block. <b>The program is fine; the connection is not."
                        "</b><br>✔️ The radar retries automatically every cycle.<br>"
                        "🔁 If this red box stays for <b>15+ minutes</b>: reboot the app <b>ONCE</b>, then wait "
                        "5 minutes without touching anything.</div>", unsafe_allow_html=True)
        elif mst_s == "open" and _hr and _pct < 60:
            st.markdown(f"<div style='background:#3a2a06;border:1px solid #f59e0b;border-radius:12px;padding:14px 18px;"
                        f"color:#fde68a;font-size:13px;line-height:1.8;'>⚠️ <b>PARTIAL DATA — only {_hg}/{_hr} stocks "
                        f"({_pct}%) downloaded.</b><br>The server connection is struggling right now; the board below "
                        "may be incomplete. Auto-retry on the next scan — no action needed.</div>", unsafe_allow_html=True)
        elif mst_s == "open":
            st.markdown("<div style='background:#0b2447;border:1px solid #3b82f6;border-radius:12px;padding:14px 18px;"
                        "color:#bfdbfe;font-size:13px;line-height:1.8;'>🕘 <b>Market is open but the session just "
                        "started.</b> Five-minute candles are still building (first ones arrive after 9:15).<br>"
                        "✔️ Press <b>🔄 Scan now</b> again — from <b>~9:30 AM</b> you'll get early scores, and they "
                        "become reliable from <b>~9:45 AM</b> (6+ candles).<br>"
                        "⏰ Keep auto-refresh ON — the radar fills up by itself."
                        + (f"<br>✅ <b>Data connection is HEALTHY</b> ({_hg}/{_hr} · {_pct}%) — the filters just "
                           "haven't found movers yet." if _hr else "") + "</div>", unsafe_allow_html=True)
        elif mst_s == "pre":
            st.info("🌅 Market opens at 9:15 AM IST. Press ⚡ START before the open — the radar will begin scoring "
                    "as soon as the first candles form (~9:20–9:30).")
        else:
            st.info("🔴 Market is closed — no candles for today. On the next trading day: START before 9:15, "
                    "first scores from ~9:30, reliable from ~9:45 AM IST.")
        return
    if mst_s == "open" and now_ist().time() < dtime(9, 45):
        st.markdown("<div style='background:#3f2d04;border:1px solid #f59e0b;border-radius:10px;padding:8px 14px;"
                    "color:#fde68a;font-size:12px;margin-bottom:10px;'>⚠️ Early session (before 9:45) — scores are "
                    "based on few candles. Opening spikes can fake a climb; wait for 9:45–10:00 for confirmations."
                    "</div>", unsafe_allow_html=True)

    _mv_age = int((time.time() - ss.get("mv_last", 0)) / 60)
    _mv_ts = ss.get("mv_ts_str") or "—"
    _mvc = "#4ade80" if _mv_age <= 5 else ("#fbbf24" if _mv_age <= 12 else "#f87171")
    st.markdown(f"<div style='background:#0b1220;border:1px solid #1e293b;border-radius:10px;padding:8px 14px;"
                f"color:#94a3b8;font-size:12px;margin-bottom:10px;'>🕒 Last scan: <b style='color:#e2e8f0;'>{_mv_ts} IST</b>"
                f" · <b style='color:{_mvc};'>{_mv_age} min ago</b>"
                + (f" · 🩺 feed <b style='color:{'#4ade80' if _mvh.get('got', 0) >= _mvh.get('req', 1) * 0.6 else '#f87171'};'>"
                   f"{_mvh.get('got', '?')}/{_mvh.get('req', '?')}</b>" if _mvh.get("req") else "")
                + (" — <b style='color:#f87171;'>data is old, climbs may have ended. Press 🔄 Scan now.</b>"
                   if _mv_age > 12 and mst_s == "open" else "") + "</div>", unsafe_allow_html=True)

    climbing = [m for m in movers if m["state"] == "CLIMBING"]
    steady = [m for m in movers if m["steady"] and m["chg_day"] > 0]
    forming = [m for m in movers if m["state"] == "FORMING"]
    if mst_s == "closed":
        st.markdown("<div style='background:#3f2d04;border:1px solid #f59e0b;border-radius:10px;padding:8px 14px;"
                    "color:#fde68a;font-size:12px;margin-bottom:10px;'>🔴 Market closed — this is TODAY'S full-session "
                    "climb review: what live money actually did today. Alerts resume next trading day.</div>",
                    unsafe_allow_html=True)
    a1, a2, a3, a4 = st.columns(4)
    with a1: st.metric("⚡ Climbing now", len(climbing))
    with a2: st.metric("🐢 Slow-steady riders", len(steady))
    with a3: st.metric("🌱 Forming (early)", len(forming), "buy the dip, don't chase")
    with a4: st.metric("Scanned", len(movers),
                       f"avg move {sum(m['chg_day'] for m in movers)/max(len(movers),1):+.2f}%")

    alerts = ss.get("mv_alerts") or []
    if alerts:
        with st.expander(f"🔔 CLIMB ALERTS — this session ({len(alerts)})", expanded=True):
            for a in alerts[:12]:
                st.markdown(f"<div style='background:rgba(34,197,94,.08);border:1px solid rgba(34,197,94,.35);"
                            f"border-radius:10px;padding:8px 14px;margin:4px 0;color:#d1fae5;font-size:12px;'>"
                            f"<b style='color:#4ade80;'>🔔 {a['name']}</b> · <span style='color:#64748b;'>{a['ts']}</span>"
                            f" · {a['txt']}</div>", unsafe_allow_html=True)

    st.markdown("<div style='color:#94a3b8;font-size:12px;font-weight:900;margin:10px 0 4px;'>"
                f"⚡ TOP 100 CLIMBERS — all {len(movers)} scanned live in the background · "
                "▲▼ = rank movement since last scan</div>", unsafe_allow_html=True)
    _prk = ss.get("mv_ranks_prev") or {}
    rows_html = "".join(_mv_row(i + 1, m, names.get(m["sym"], m["sym"].replace(".NS", "")),
                                delta=(_prk[m["sym"]] - (i + 1)) if _prk.get(m["sym"]) else 0)
                        for i, m in enumerate(movers[:100]))
    st.markdown(rows_html, unsafe_allow_html=True)

    with st.expander("📋 Full board — all scanned stocks (sortable)"):
        disp = pd.DataFrame([{"Stock": names.get(m["sym"], m["sym"].replace(".NS", "")),
                              "Symbol": m["sym"], "Price": m["last"], "Day%": m["chg_day"],
                              "GreenCandles%": m["green"], "Slope1h%": m["slope1h"],
                              "DayPosition%": m["pos"], "Vol×": m["vr"], "ClimbScore": m["climb"],
                              "State": m["state"], "SlowSteady": "🐢" if m["steady"] else "",
                              "ScanTime": _mv_ts}
                             for m in movers])
        try:
            st.dataframe(disp, **STRETCH, height=420, hide_index=True)
        except Exception:
            st.dataframe(disp, **STRETCH)
        try:
            st.download_button("⬇️ Download movers (CSV)", data=disp.to_csv(index=False).encode(),
                               file_name=f"live_movers_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                               mime="text/csv", **STRETCH, key="mv_csv")
        except Exception:
            pass


# ============================================================
# 🎯 COMBO — the accuracy booster: LIVE climb ∩ CALCULATION.
#   A stock qualifies only if REAL money is moving it up now
#   (⚡ climb score) AND the calculation agrees (uptrend / BUY /
#   above 200EMA / confidence). Both green = highest-probability.
# ============================================================
# 🌋 VOLCANO — the sleeper-eruption detector (the 'Tata Chemicals
#   pattern'): a tight box of tiny candles → ONE big candle + volume
#   burst. Piggybacks the combo scan's candles — ZERO extra Yahoo calls.
# ============================================================
def sleeper_detect(df, mode="live"):
    """🌋 VOLCANO detector — the 'Tata Chemicals pattern': a stock drifting in a
    tight box of tiny candles suddenly prints ONE BIG candle.
      mode='live' → check the last 2 candles vs the 10 before → dict | None
      mode='day'  → every eruption in today's session (+ aftermath) → list
    A candle is an ERUPTION when: 10 quiet candles before it (avg body ≤0.30%,
    box ≤1.8% wide) → then one candle ≥ max(0.75%, 3× quiet) that CLOSES
    outside the box. BOOM = green breakout · TRAP = red breakdown.
    LOADING = still inside a tight box but volume building (pre-eruption)."""
    def _one(d, e, hold_now):
        if e < 10:
            return None
        q = d.iloc[e-10:e]                                  # the silence box
        qo, qc = q["Open"].astype(float), q["Close"].astype(float)
        if (qo <= 0).any():
            return None
        bodies = (qc - qo).abs() / qo * 100
        qavg = float(bodies.mean())
        box_hi, box_lo = float(q["High"].max()), float(q["Low"].min())
        if box_hi <= 0:
            return None
        tight = (box_hi - box_lo) / box_hi * 100
        if qavg > 0.30 or tight > 1.8:                      # not silent enough
            return None
        eo, ec = float(d["Open"].iloc[e]), float(d["Close"].iloc[e])
        eh, el = float(d["High"].iloc[e]), float(d["Low"].iloc[e])
        if eo <= 0:
            return None
        body = (ec - eo) / eo * 100
        thr = max(0.75, 3 * max(qavg, 0.12))
        if hold_now and not (float(d["Close"].iloc[-1]) > box_hi if body > 0
                             else float(d["Close"].iloc[-1]) < box_lo):
            return None                                      # live: must still hold
        vol_mult = None
        try:
            qv = float(d["Volume"].astype(float).iloc[e-10:e].mean())
            if qv > 0:
                vol_mult = round(float(d["Volume"].iloc[e]) / qv, 1)
        except Exception:
            pass
        ev = "BOOM" if (body >= thr and ec > box_hi) else ("TRAP" if (body <= -thr and ec < box_lo) else None)
        if not ev:
            return None
        risk = eh - box_lo
        return {"state": ev, "ts": d.index[e].strftime("%H:%M"),
                "body": round(body, 2), "quiet_avg": round(qavg, 2),
                "box_hi": round(box_hi, 2), "box_lo": round(box_lo, 2),
                "tight": round(tight, 2), "vol_mult": vol_mult,
                "buy": round(eh, 2), "sl": round(box_lo, 2),
                "t1": round(eh + 1.5 * risk, 2) if risk > 0 else None,
                "fading": bool(eh - el > 0 and (eh - max(eo, ec)) / (eh - el) >= 0.45),
                "strong": bool(body >= 1.5 or (vol_mult or 99) >= 5),
                "age": len(d) - 1 - e}

    def _after(d, e, box_hi):
        """What happened AFTER the eruption — did it run or fade? (day review)"""
        try:
            nxt = d.iloc[e+1:e+7]
            if not len(nxt):
                return None, None
            ran = round((float(nxt["High"].max()) / float(d["Close"].iloc[e]) - 1) * 100, 1) + 0.0
            faded = len(nxt) >= 2 and float(nxt["Close"].iloc[1]) < float(d["Close"].iloc[e])
            return ran, bool(faded)
        except Exception:
            return None, None

    try:
        if df is None or len(df) < 14:
            return None if mode == "live" else []
        d = df[df.index.date == df.index[-1].date()]         # today's candles only
        if len(d) < 14:
            return None if mode == "live" else []
        if mode == "day":
            out, last_min = [], -99
            for e in range(10, len(d)):
                r = _one(d, e, hold_now=False)
                if not r:
                    continue
                m = d.index[e].hour * 60 + d.index[e].minute
                if m - last_min < 15:                        # same burst — keep first
                    continue
                last_min = m
                r["ran"], r["faded_after"] = _after(d, e, r["box_hi"])
                out.append(r)
            return out
        for e in (len(d) - 1, len(d) - 2):                   # live: last 2 candles
            r = _one(d, e, hold_now=True)
            if r:
                return r
        q = d.iloc[-11:-1]                                   # still quiet → magma check
        qo, qc = q["Open"].astype(float), q["Close"].astype(float)
        if (qo <= 0).any():
            return None
        qavg = float(((qc - qo).abs() / qo * 100).mean())
        box_hi, box_lo = float(q["High"].max()), float(q["Low"].min())
        lc = float(d["Close"].iloc[-1])
        if qavg <= 0.22 and box_hi > box_lo and lc >= box_lo + 0.6 * (box_hi - box_lo):
            try:
                v = d["Volume"].astype(float)
                early, rec = float(v.iloc[-14:-4].mean()), float(v.iloc[-4:].mean())
                if early > 0 and rec / early >= 2.0:
                    return {"state": "LOADING", "vol_build": round(rec / early, 1),
                            "box_hi": round(box_hi, 2), "box_lo": round(box_lo, 2),
                            "tight": round((box_hi - box_lo) / box_hi * 100, 2)}
            except Exception:
                pass
        return None
    except Exception:
        return None if mode == "live" else []


# ============================================================
# 🎯 COMBO — the accuracy booster: LIVE climb ∩ CALCULATION.
#   A stock qualifies only if REAL money is moving it up now
#   (⚡ climb score) AND the calculation agrees (uptrend / BUY /
#   above 200EMA / confidence). Both green = highest-probability.
# ============================================================
def combo_scan(watch, names):
    """One sweep → both engines: live movers + dashboard calculation."""
    got, gotd = _sweep(watch, "5m", "2d", with_daily=True, progress=True)
    movers = {m["sym"]: m for m in compute_movers(got)}
    rows = {}
    _thin_ct = 0
    for sym in watch:
        intra = got.get(sym)
        if intra is None:
            continue
        # 💧 LIQUIDITY FLOOR — thin stocks are operator country. A stock must
        #    trade ≥ 100k shares/day (20-day avg) to be scorable at all.
        try:
            _dv = gotd.get(sym)
            _av = (float(_dv["Volume"].astype(float).tail(20).mean())
                   if _dv is not None and len(_dv) >= 5 and "Volume" in _dv else 0.0)
            if _av < 100_000:
                _thin_ct += 1
                continue
        except Exception:
            pass
        try:
            r = dash_row(names.get(sym, sym.replace(".NS", "")), sym, intra, gotd.get(sym))
        except Exception:
            r = None
        if r:
            rows[sym] = r
    out = []
    for sym, r in rows.items():
        mv = movers.get(sym)
        if not mv:
            continue
        sup = res = sup_dist = res_dist = None
        try:
            d = gotd.get(sym)
            if d is not None and len(d) >= 30:
                lo10 = float(d["Low"].tail(10).min()); lo20 = float(d["Low"].tail(20).min())
                support = max(lo20 * 0.995, lo10)
                hi20 = float(d["High"].tail(20).max())
                sup, res = round(support, 2), round(hi20, 2)
                sup_dist = round((mv["last"] - support) / support * 100, 2)
                res_dist = round((hi20 - mv["last"]) / mv["last"] * 100, 2)
        except Exception:
            pass
        sig = (r.get("sig") or "").upper()
        live_pts = (2 if mv["climb"] >= 68 else 1 if mv["climb"] >= 58 else 0) \
                   + (0.5 if mv["steady"] else 0) + (0.5 if mv["vr"] >= 1.3 else 0)
        calc_pts = (1 if "BUY" in sig else 0) + (1 if r.get("dtr") == "UPTREND" else 0) \
                   + (0.5 if r.get("above200") else 0) + (0.5 if (r.get("conf") or 0) >= 65 else 0)
        combo = round(min(live_pts, 3.0) / 3.0 * 60 + min(calc_pts, 3.0) / 3.0 * 40, 1)
        if mv["climb"] >= 68 and "BUY" in sig and r.get("dtr") == "UPTREND":
            verdict = "🎯 PERFECT"
        elif mv["climb"] >= 58 and calc_pts >= 1:
            verdict = "✅ MATCH"
        elif mv["climb"] >= 58:
            verdict = "⚠️ LIVE ONLY"
        elif calc_pts >= 2:
            verdict = "🧮 CALC ONLY"
        else:
            verdict = "—"
        out.append({"name": r.get("name", sym.replace(".NS", "")), "sym": sym,
                    "price": mv["last"], "chg_day": mv["chg_day"], "climb": mv["climb"],
                    "green": mv["green"], "slope1h": mv["slope1h"], "vr": mv["vr"],
                    "steady": mv["steady"], "sig": r.get("sig"), "dtr": r.get("dtr"),
                    "conf": r.get("conf"), "above200": bool(r.get("above200")),
                    "score": r.get("score"), "combo": combo, "verdict": verdict,
                    "buy_at": r.get("buy_at"), "sl": r.get("sl"), "t1": r.get("t1"), "t2": r.get("t2"),
                    "support": sup, "resistance": res, "sup_dist": sup_dist, "res_dist": res_dist,
                    "from_support": sup_dist is not None and sup_dist <= 1.5,
                    "at_resistance": res_dist is not None and res_dist <= 1.0})
    order = {"🎯 PERFECT": 0, "✅ MATCH": 1, "⚠️ LIVE ONLY": 2, "🧮 CALC ONLY": 3, "—": 4}
    out.sort(key=lambda x: (order.get(x["verdict"], 9), -x["combo"]))
    return out


def _trade_html(c):
    """💰 BUY / SL / SELL levels + resistance warning on combo cards."""
    b, sl = c.get("buy_at"), c.get("sl")
    t1, t2 = c.get("t1"), c.get("t2")
    res, rd = c.get("resistance"), c.get("res_dist")
    if not b or not sl:
        return ""
    res_line = ""
    if res:
        wr = (" · ⚠️ AT RESISTANCE — may reverse!" if (rd or 99) <= 1.0 else "")
        res_line = (f"<div style='color:#94a3b8;font-size:9px;margin-top:2px;'>RES ₹{res:,.0f}"
                    f" (+{rd:.1f}% above){wr}</div>")
    return (f"<div style='min-width:150px;'><div style='color:#64748b;font-size:9px;'>💰 TRADE · BUY & SELL</div>"
            f"<div style='font-size:10.5px;font-family:monospace;line-height:1.5;'>"
            f"<span style='color:#4ade80;font-weight:900;'>BUY ₹{b:,.2f}</span> · "
            f"<span style='color:#f87171;'>SL ₹{sl:,.2f}</span><br>"
            f"<span style='color:#22c55e;font-weight:900;'>SELL T1 ₹{(t1 or b):,.2f}</span> · "
            f"<span style='color:#16a34a;font-weight:900;'>T2 ₹{(t2 or b):,.2f}</span></div>{res_line}</div>")


def _alive_html(c, now_map):
    """🕒 NOW vs SCAN — is the climb still alive, fading, or already ENDED?"""
    nowp = (now_map or {}).get(c["sym"])
    if not nowp or not c.get("price"):
        return ""
    d = (nowp - c["price"]) / c["price"] * 100
    if d >= -0.12:
        b, col = "✅ STILL ON", "#22c55e"
    elif d >= -0.35:
        b, col = "⚠️ FADING", "#fbbf24"
    else:
        b, col = "❌ ENDED", "#ef4444"
    return (f"<div style='min-width:108px;'><div style='color:#64748b;font-size:9px;'>🕒 NOW vs SCAN</div>"
            f"<div style='color:{col};font-size:11px;font-family:monospace;font-weight:800;'>₹{nowp:,.2f}</div>"
            f"<div style='color:{col};font-size:9.5px;font-weight:900;'>{d:+.2f}% · {b}</div></div>")


def _combo_row(i, c, scan_ts="", now_map=None):
    now_map = now_map or {}
    vc = {"🎯 PERFECT": "#22c55e", "✅ MATCH": "#4ade80",
          "⚠️ LIVE ONLY": "#fbbf24", "🧮 CALC ONLY": "#93c5fd"}.get(c["verdict"], "#64748b")
    cc = "#22c55e" if c["chg_day"] >= 0 else "#ef4444"
    cb = max(0, min(100, c["combo"]))
    ema = "200EMA ✓" if c["above200"] else "below 200EMA"
    return (f"<div style='display:flex;align-items:center;gap:12px;background:#0f172a;border:1px solid #1e293b;"
            f"border-left:3px solid {vc};border-radius:12px;padding:8px 14px;margin:5px 0;flex-wrap:wrap;'>"
            f"<div style='color:#475569;font-weight:900;font-size:15px;width:26px;font-family:monospace;'>{i}</div>"
            f"<div style='min-width:148px;'><div style='color:#f1f5f9;font-weight:800;font-size:14px;'>{c['name'][:19]}{' 🏔️' if c.get('near52') else ''}</div>"
            f"<div style='color:#64748b;font-size:10px;'>{c['sym'].replace('.NS','')} · {c['sig'].title()} · {ema}"
            f"{' · 🕒 ' + scan_ts if scan_ts else ''}</div></div>"
            f"<div style='min-width:92px;color:#e2e8f0;font-weight:800;font-size:14px;font-family:monospace;'>₹{c['price']:,.2f}</div>"
            f"<div style='min-width:68px;color:{cc};font-weight:900;font-size:13px;font-family:monospace;'>{c['chg_day']:+.2f}%</div>"
            f"<div style='min-width:98px;'><div style='color:#64748b;font-size:9px;'>⚡ LIVE CLIMB</div>"
            f"<div style='background:#1e293b;width:66px;height:6px;border-radius:3px;'><div style='background:#16a34a;width:{c['climb']:.0f}%;height:6px;border-radius:3px;'></div></div>"
            f"<div style='color:#94a3b8;font-size:9.5px;font-family:monospace;'>{c['climb']:.0f}/100 · {c['green']}% green</div></div>"
            f"<div style='min-width:98px;'><div style='color:#64748b;font-size:9px;'>🧮 CALCULATION</div>"
            f"<div style='background:#1e293b;width:66px;height:6px;border-radius:3px;'><div style='background:#3b82f6;width:{min(c['conf'] or 0,100):.0f}%;height:6px;border-radius:3px;'></div></div>"
            f"<div style='color:#94a3b8;font-size:9.5px;font-family:monospace;'>conf {c['conf']:.0f}% · {str(c.get('dtr') or '—')[:8].title()}</div></div>"
            f"{_alive_html(c, now_map)}"
            f"{_trade_html(c)}"
            f"<div style='min-width:98px;'><div style='color:#64748b;font-size:9px;'>🎯 COMBO SCORE</div>"
            f"<div style='background:#1e293b;width:66px;height:6px;border-radius:3px;'><div style='background:{vc};width:{cb}%;height:6px;border-radius:3px;'></div></div>"
            f"<div style='color:{vc};font-size:10px;font-family:monospace;font-weight:800;'>{c['combo']:.0f}/100</div></div>"
            f"<div style='min-width:120px;'><span style='background:{'rgba(34,197,94,.16)' if 'PERFECT' in c['verdict'] or 'MATCH' in c['verdict'] else 'rgba(59,130,246,.16)'};"
            f"color:{vc};font-size:10.5px;font-weight:900;padding:3px 10px;border-radius:8px;'>{c['verdict']}</span>"
            + (" <span style='background:rgba(245,158,11,.16);color:#fbbf24;font-size:9.5px;font-weight:900;padding:2px 7px;border-radius:8px;'>🐢</span>" if c["steady"] else "")
            + (" <span style='background:rgba(59,130,246,.16);color:#93c5fd;font-size:9.5px;font-weight:900;padding:2px 7px;border-radius:8px;'>🛡️ FROM SUPPORT</span>" if c.get("from_support") else "")
            + (" <span style='background:rgba(239,68,68,.14);color:#f87171;font-size:9.5px;font-weight:900;padding:2px 7px;border-radius:8px;'>⚠️ AT RESISTANCE</span>" if c.get("at_resistance") else "")
            + "</div></div>")


@st.cache_data(ttl=300, show_spinner=False)
def market_regime():
    """🟢🟡🔴 Today's NIFTY regime — bounce/combo odds change with it.
    Friday proved it: on a weak afternoon only 22% of 'starting' calls held."""
    try:
        df = fetch_chunk(("^NSEI", "RELIANCE.NS"), "1d", "6mo").get("^NSEI")
        if df is None or len(df) < 2:
            return None
        cl = df["Close"].values
        chg = (float(cl[-1]) / float(cl[-2]) - 1) * 100
        if chg > 0.3:
            return {"chg": round(chg, 2), "lab": "🟢 TREND DAY UP", "col": "#16a34a",
                    "tip": "Bounces & breakouts favoured — trade the picks normally."}
        if chg >= -0.3:
            return {"chg": round(chg, 2), "lab": "🟡 MIXED DAY", "col": "#f59e0b",
                    "tip": "Choppy — be selective: half size, book T1, don't wait for T2."}
        return {"chg": round(chg, 2), "lab": "🔴 WEAK DAY", "col": "#ef4444",
                "tip": "Bounce failures common — watch 🛡️ AT SUPPORT only, skip chasing 🚀 STARTING."}
    except Exception:
        return None


def _regime_banner():
    rg = market_regime()
    if not rg:
        return
    st.markdown(f"<div style='background:#0f172a;border:1px solid {rg['col']};border-radius:10px;padding:8px 14px;"
                f"color:#cbd5e1;font-size:12px;margin-bottom:10px;'>MARKET TODAY: <b style='color:{rg['col']};'>"
                f"{rg['lab']}</b> · NIFTY {rg['chg']:+.2f}% · {rg['tip']}</div>", unsafe_allow_html=True)


# ============================================================
# 🚀 UPTREND STARTING — the support-bounce radar.
#   As per our calculation: which stock has REACHED its support
#   point and is now slowly turning up? Buy at the bounce,
#   sell into strength — levels shown on every card.
# ============================================================
def compute_bounces(got, gotd):
    out = []
    all_dates = set()
    for _s, _df in got.items():
        try:
            if _df is not None and len(_df):
                for _ix in _df.index:
                    all_dates.add(_dist(_ix))
        except Exception:
            pass
    today = now_ist().date()
    sess = max((d for d in all_dates if d <= today), default=today)
    for sym, df in got.items():
        try:
            if df is None or len(df) < 12:
                continue
            dates = [_dist(ix) for ix in df.index]
            td = [i for i, d in enumerate(dates) if d == sess]
            if len(td) < 3:
                continue
            d0 = td[0]
            prev_close = float(df["Close"].iloc[d0 - 1]) if d0 > 0 else float(df["Open"].iloc[d0])
            t = df.iloc[d0:td[-1] + 1]
            last = float(t["Close"].iloc[-1]); hi = float(t["High"].max()); lo = float(t["Low"].min())
            if last < MIN_PRICE or last > MAX_PRICE:   # keep ₹100–₹1000 only
                continue
            cl = t["Close"].values; op = t["Open"].values; vol = t["Volume"].values
            chg_day = (last - prev_close) / prev_close * 100 if prev_close else 0.0
            g, oo = cl[-24:], op[-24:]
            green = (sum(1 for i in range(len(g)) if g[i] > oo[i]) / len(g)) if len(g) else 0.5
            base = cl[-13] if len(cl) >= 13 else cl[0]
            slope1h = (last - base) / base * 100 if base else 0.0
            rec = (last - lo) / lo * 100 if lo else 0.0
            vrec = vol[-6:]; vold = vol[:-6] if len(vol) > 6 else vol
            vr = (vrec.mean() / vold.mean()) if (len(vold) and vold.mean() > 0) else 1.0
            d = gotd.get(sym)
            if d is None or len(d) < 30:
                continue
            lo10 = float(d["Low"].tail(10).min()); lo20 = float(d["Low"].tail(20).min())
            support = max(lo20 * 0.995, lo10)
            hi20 = float(d["High"].tail(20).max())
            sup_dist = (last - support) / support * 100
            res_dist = (hi20 - last) / last * 100
            if not (-0.5 <= sup_dist <= 1.5):     # only stocks AT/ON support
                continue
            # ── 🔁 support-test counter: FIRST bounce is the best bounce.
            #    Bounced once and fell back to test again = weakening support;
            #    sliced below support and crawled back = broken level. Neither
            #    is a fresh buy — they are exactly how "it bounced again!"
            #    trades lose money.
            _lows = [float(x) for x in t["Low"].values]
            _tz, _bz = support * 1.004, support * 0.994
            _touches, _broke, _in_t, _away = 0, False, False, 0
            for _lv in _lows:
                if _lv <= _bz:
                    _broke = True
                if _lv <= _tz:
                    if not _in_t:
                        _touches += 1
                        _in_t = True
                    _away = 0
                else:
                    _away += 1
                    if _away >= 3:
                        _in_t = False
            # strict turn confirmation (loose version won only 22% on a soft day):
            # real bounce = clearly off the low + rising last hour + green candles + volume interest
            turning = (((rec >= 0.40 and slope1h > 0.0 and green >= 0.55) or
                        (slope1h >= 0.20 and green >= 0.60))
                       and (vr >= 1.05 or rec >= 0.60))
            # first test ONLY: retests (2nd+ touch) and broken supports never flag STARTING
            starting = (turning and chg_day <= 4.0 and _touches == 1 and not _broke)
            score = (40 * max(0.0, (1.5 - sup_dist)) / 1.5 + 30 * min(rec, 1.5) / 1.5
                     + 15.0 * green + 15.0 * min(vr, 2.0) / 2.0)
            # ── realistic bounce targets: tight stop just below support,
            #    modest T1, and T2 CAPPED AT RESISTANCE (that's where a
            #    bounce normally stalls — old wide targets were unreachable)
            sl = round(support * 0.99, 2)
            buy = round(min(last, support * 1.005), 2)
            r_ = max(buy - sl, buy * 0.004)
            t1 = round(buy + 1.2 * r_, 2)
            t2 = round(buy + 2.0 * r_, 2)
            if hi20 and hi20 > buy:
                t2 = round(min(t2, hi20), 2)
                t1 = round(min(t1, round(hi20 - max((hi20 - buy) * 0.25, buy * 0.001), 2)), 2)
                if t2 <= t1:
                    t2 = t1
            out.append({"sym": sym, "last": round(last, 2), "chg_day": round(chg_day, 2),
                        "support": round(support, 2), "resistance": round(hi20, 2),
                        "sup_dist": round(sup_dist, 2), "res_dist": round(res_dist, 2),
                        "rec": round(rec, 2), "green": int(round(green * 100)),
                        "slope1h": round(float(slope1h), 2), "vr": round(float(vr), 2),
                        "score": round(score, 1),
                        "state": ("🚀 UPTREND STARTING" if starting else
                                  "⚠️ SUPPORT BROKEN" if _broke else
                                  "🔁 RETESTED — weaker" if _touches >= 2 else "🛡️ AT SUPPORT"),
                        "starting": starting, "buy": buy, "sl": sl,
                        "t1": t1, "t2": t2, "touches": _touches, "broke": _broke})
        except Exception:
            continue
    out.sort(key=lambda b: (not b["starting"], -b["score"]))
    return out


def _bc_row(i, b, name):
    st_ = "#22c55e" if b["starting"] else "#3b82f6"
    cc = "#22c55e" if b["chg_day"] >= 0 else "#ef4444"
    badge = (f"<span style='background:rgba(34,197,94,.16);color:#4ade80;font-size:10px;font-weight:900;"
             f"padding:3px 10px;border-radius:8px;'>🚀 UPTREND STARTING</span>" if b["starting"] else
             (f"<span style='background:rgba(239,68,68,.16);color:#f87171;font-size:10px;font-weight:900;"
              f"padding:3px 10px;border-radius:8px;'>⚠️ SUPPORT BROKEN — skip</span>" if b.get("broke") else
              f"<span style='background:rgba(245,158,11,.16);color:#fbbf24;font-size:10px;font-weight:900;"
              f"padding:3px 10px;border-radius:8px;'>🔁 TEST #{b.get('touches', 1)} — weaker, skip</span>"
              if (b.get("touches") or 1) >= 2 else
              f"<span style='background:rgba(59,130,246,.16);color:#93c5fd;font-size:10px;font-weight:900;"
              f"padding:3px 10px;border-radius:8px;'>🛡️ AT SUPPORT · waiting for turn</span>"))
    return (f"<div style='display:flex;align-items:center;gap:12px;background:#0f172a;border:1px solid #1e293b;"
            f"border-left:3px solid {st_};border-radius:12px;padding:8px 14px;margin:5px 0;flex-wrap:wrap;'>"
            f"<div style='color:#475569;font-weight:900;font-size:15px;width:26px;font-family:monospace;'>{i}</div>"
            f"<div style='min-width:140px;'><div style='color:#f1f5f9;font-weight:800;font-size:14px;'>{name[:19]}</div>"
            f"<div style='color:#64748b;font-size:10px;'>{b['sym'].replace('.NS','')} · +{b['rec']:.2f}% off day's low</div></div>"
            f"<div style='min-width:88px;color:#e2e8f0;font-weight:800;font-size:14px;font-family:monospace;'>₹{b['last']:,.2f}</div>"
            f"<div style='min-width:64px;color:{cc};font-weight:900;font-size:13px;font-family:monospace;'>{b['chg_day']:+.2f}%</div>"
            f"<div style='min-width:118px;'><div style='color:#64748b;font-size:9px;'>🛡️ SUPPORT (BUY ZONE)</div>"
            f"<div style='color:#4ade80;font-size:11.5px;font-family:monospace;font-weight:800;'>₹{b['support']:,.2f}</div>"
            f"<div style='color:#94a3b8;font-size:9.5px;font-family:monospace;'>{b['sup_dist']:+.2f}% away</div></div>"
            f"<div style='min-width:118px;'><div style='color:#64748b;font-size:9px;'>💰 TRADE LEVELS</div>"
            f"<div style='font-size:10.5px;font-family:monospace;line-height:1.5;'>"
            f"<span style='color:#4ade80;font-weight:900;'>BUY ₹{b['buy']:,.2f}</span> · "
            f"<span style='color:#f87171;'>SL ₹{b['sl']:,.2f}</span><br>"
            f"<span style='color:#22c55e;font-weight:900;'>SELL T1 ₹{b['t1']:,.2f}</span> · "
            f"<span style='color:#16a34a;font-weight:900;'>T2 ₹{b['t2']:,.2f}</span></div></div>"
            f"<div style='min-width:104px;'><div style='color:#64748b;font-size:9px;'>🎯 RESISTANCE (SELL ZONE)</div>"
            f"<div style='color:#fbbf24;font-size:11.5px;font-family:monospace;font-weight:800;'>₹{b['resistance']:,.2f}</div>"
            f"<div style='color:#94a3b8;font-size:9.5px;font-family:monospace;'>+{b['res_dist']:.2f}% above"
            + (" · ⚠️ NEAR" if b["res_dist"] <= 1.0 else "") + "</div></div>"
            f"<div style='min-width:98px;'><div style='color:#64748b;font-size:9px;'>BOUNCE SCORE</div>"
            f"<div style='background:#1e293b;width:70px;height:6px;border-radius:3px;'><div style='background:{st_};width:{min(b['score'],100):.0f}%;height:6px;border-radius:3px;'></div></div>"
            f"<div style='color:#94a3b8;font-size:9.5px;font-family:monospace;'>{b['score']:.0f}/100 · {b['green']}% green</div></div>"
            f"<div style='min-width:150px;'>{badge}</div></div>")


def bounce_tab(ss, mst_s):
    # ♾️ AUTO-RESUME
    if not ss.get("bc_on"):
        _rt = rt_load().get("bc") or {}
        if _rt.get("on") and _rt.get("watch"):
            ss["bc_on"] = True
            ss["bc_watch"] = _rt["watch"]; ss["bc_names"] = _rt.get("names") or {}
            ss["bc"] = _rt.get("bounces") or None
            ss["bc_last"] = _rt.get("last_scan", 0)
            ss["bc_ts_str"] = _rt.get("ts_str") or "—"
            ss["bc_prev"] = _rt.get("prev") or []
            ss["bc_alerts"] = _rt.get("alerts") or []
            ss["_bc_resumed"] = True

    st.markdown(_H("""<div style='background:linear-gradient(135deg,#0f2b1e,#1e3a8a);border-radius:18px;
    padding:18px 22px;margin-bottom:12px;'>
    <div style='color:white;font-size:20px;font-weight:900;'>🚀 UPTREND STARTING — support-bounce radar</div>
    <div style='color:#bbf7d0;font-size:12.5px;margin-top:6px;line-height:1.7;'>As per our calculation: which stocks
    have <b>REACHED their SUPPORT point</b> and are <b>slowly starting to turn up</b>? 🚀 UPTREND STARTING = at
    support + bouncing now — the safest buy zone (buy at support, stop just below, sell into T1/T2).
    🛡️ AT SUPPORT = sitting on support, turn not confirmed yet — watchlist it. Every card shows the exact
    <b>BUY, STOP-LOSS and SELL</b> values, plus the resistance where the rally may stall.</div></div>"""),
                unsafe_allow_html=True)

    _regime_banner()
    with st.expander("⚙️ UNIVERSE · REFRESH", expanded=not ss.get("bc_watch")):
        k1, k2 = st.columns(2)
        with k1:
            _keys = list(DASH_SRC.keys())
            _def = _keys.index("🌐 Full NSE (auto-fill to your count)") if "🌐 Full NSE (auto-fill to your count)" in _keys else 0
            st.selectbox("Universe", _keys, index=_def, key="bc_src")
            st.slider("How many stocks", 100, 500, 500, 50, key="bc_n")
        with k2:
            st.selectbox("Auto-refresh every", ["1 min", "2 min", "3 min", "5 min"], index=2, key="bc_int")
            st.caption("One scan = live 5-min candles + daily history (support/resistance) for the whole board.")
        s1, s2, s3 = st.columns(3)
        with s1:
            start_bc = st.button("🚀 START BOUNCE RADAR", type="primary", use_container_width=True, key="bc_start")
        with s2:
            rescan_bc = st.button("🔄 Scan now", use_container_width=True, key="bc_rescan")
        with s3:
            stop_bc = st.button("⏹ Stop", use_container_width=True, key="bc_stop")

    if stop_bc:
        ss["bc_on"] = False
        rt_clear("bc")
    if start_bc:
        watch, names = build_watchlist(ss.get("bc_src"), ss.get("bc_n", 500))
        ss["bc_watch"] = watch; ss["bc_names"] = names
        ss["bc_on"] = True; ss["bc"] = None; ss["bc_last"] = 0; ss["bc_alerts"] = []; ss["bc_prev"] = []
        rt_save("bc", on=True, src=ss.get("bc_src"), n=ss.get("bc_n", 500), watch=watch, names=names)

    tg_settings_ui("_bc")
    up_settings_ui("_bc")

    if not ss.get("bc_on"):
        st.markdown("<div style='background:#0b1220;border-radius:20px;padding:44px;text-align:center;'>"
                    "<div style='font-size:44px;'>🚀</div>"
                    "<div style='font-size:20px;font-weight:900;color:#f1f5f9;margin-top:10px;'>SUPPORT-BOUNCE RADAR</div>"
                    "<div style='color:#64748b;font-size:13px;margin-top:8px;'>All-India board · who just reached support "
                    "and started turning up · exact BUY / SL / SELL levels · 🔔 alerts</div>"
                    "<div style='color:#94a3b8;font-size:12px;margin-top:12px;'>↑ Press "
                    "<b style='color:#22c55e;'>🚀 START BOUNCE RADAR</b></div></div>", unsafe_allow_html=True)
        return

    if ss.get("_bc_resumed"):
        ss["_bc_resumed"] = False
        st.info("♾️ Bounce radar resumed automatically — a page refresh does NOT stop it. Press ⏹ Stop to end it.")

    try:
        from streamlit_autorefresh import st_autorefresh
        _sec = int(ss.get("bc_int", "3 min").split()[0]) * 60
        if mst_s == "open":          # 🛌 after close: NO auto-refresh (free-CPU saver)
            st_autorefresh(interval=_sec * 1000, key="bc_tick")
    except Exception:
        pass

    watch = ss.get("bc_watch") or []
    names = ss.get("bc_names") or {}
    _sec = int(ss.get("bc_int", "3 min").split()[0]) * 60
    due = mst_s == "open" and time.time() - ss.get("bc_last", 0) > (_sec - 10)
    if due and not _pilot_ok("bc", ss):
        due = False
        _bc_view_sync(ss)                 # 🤖 autopilot drives — live view only
    if rescan_bc or due or not ss.get("bc"):
        _pilot_beat("bc", ss)
        with st.spinner("🚀 Scanning for support bounces (live candles + support levels)…"):
            got, gotd = _sweep(watch, "5m", "2d", with_daily=True, progress=True)
            bounces = compute_bounces(got, gotd)
            ss["bc"] = bounces
            ss["bc_last"] = time.time()
            ss["bc_ts_str"] = now_ist().strftime("%d %b %Y · %H:%M")
            prev_start = set(ss.get("bc_prev") or [])
            now_start = {b["sym"] for b in bounces if b["starting"]}
            alerts = ss.get("bc_alerts") or []
            _td = now_ist().strftime("%Y-%m-%d")
            if ss.get("bc_alerted_day") != _td:      # fresh day → fresh alert budget
                ss["bc_alerted_day"] = _td
                ss["bc_alerted"] = set()
            _alerted = set(ss.get("bc_alerted") or [])
            if mst_s == "open":   # 🔕 after close: silent review + ONE alert/stock/day
                for b in [x for x in bounces if x["sym"] in (now_start - prev_start)
                          and x["sym"] not in _alerted]:
                    _alerted.add(b["sym"])
                    alerts.insert(0, {"ts": now_ist().strftime("%H:%M:%S"), "sym": b["sym"],
                                      "name": names.get(b["sym"], b["sym"].replace(".NS", "")),
                                      "txt": (f"reached support ₹{b['support']:,.2f} and TURNING UP · now ₹{b['last']:,.2f} "
                                              f"(+{b['rec']:.2f}% off low) · BUY ₹{b['buy']:,.2f} · SL ₹{b['sl']:,.2f} "
                                              f"· SELL T1 ₹{b['t1']:,.2f}")})
            ss["bc_alerts"] = alerts[:40]
            ss["bc_alerted"] = _alerted
            ss["bc_prev"] = sorted(now_start)
            if mst_s == "open":
                for _b in [x for x in bounces if x["sym"] in (now_start - prev_start)][:5]:
                    _nmb = _esc(names.get(_b['sym'], _b['sym'].replace('.NS', '')))
                    tg_send(f"\U0001F680 <b>{_nmb} \u00b7 UPTREND STARTING</b>\n"
                            f"\U0001F4CD Reached support <code>\u20B9{_b['support']:,.2f}</code> and turning up\n"
                            f"\U0001F4B0 Now <code>\u20B9{_b['last']:,.2f}</code>\n"
                            f"\U0001F7E2 BUY <code>\u20B9{_b['buy']:,.2f}</code> \u00b7 \U0001F6D1 SL <code>\u20B9{_b['sl']:,.2f}</code>\n"
                            f"\U0001F3AF T1 <code>\u20B9{_b['t1']:,.2f}</code> \u00b7 T2 <code>\u20B9{_b['t2']:,.2f}</code> \u00b7 resistance <code>\u20B9{_b['resistance']:,.2f}</code>")
                for a in ss["bc_alerts"][:3]:
                    try:
                        st.toast(f"🚀 {a['name']} — {a['txt'][:70]}")
                    except Exception:
                        pass
            rt_save("bc", on=True, watch=watch, names=names, bounces=bounces,
                    last_scan=ss["bc_last"], ts_str=ss["bc_ts_str"],
                    prev=ss["bc_prev"], alerts=ss["bc_alerts"],
                    src=ss.get("bc_src"), n=ss.get("bc_n"))

    bounces = ss.get("bc") or []
    if not bounces:
        st.info("No stocks are sitting at support right now — that's fine (cash is a position). "
                "Re-scan later; 🔔 alerts fire the moment one turns up.")
        return

    _age = int((time.time() - ss.get("bc_last", 0)) / 60)
    _ts = ss.get("bc_ts_str") or "—"
    _agc = "#4ade80" if _age <= 7 else ("#fbbf24" if _age <= 15 else "#f87171")
    st.markdown(f"<div style='background:#0b1220;border:1px solid #1e293b;border-radius:10px;padding:8px 14px;"
                f"color:#94a3b8;font-size:12px;margin-bottom:10px;'>🕒 Last scan: <b style='color:#e2e8f0;'>{_ts} IST</b>"
                f" · <b style='color:{_agc};'>{_age} min ago</b>"
                + (" — <b style='color:#f87171;'>old scan. Press 🔄 Scan now.</b>" if _age > 15 and mst_s == "open" else "")
                + "</div>", unsafe_allow_html=True)

    starting = [b for b in bounces if b["starting"]]
    waiting = [b for b in bounces if not b["starting"]]
    a1, a2, a3 = st.columns(3)
    with a1: st.metric("🚀 Uptrend starting", len(starting), "at support + turning up")
    with a2: st.metric("🛡️ At support", len(waiting), "waiting for confirmation")
    with a3: st.metric("Scanned", ss.get("bc_n", 500))

    alerts = ss.get("bc_alerts") or []
    if alerts:
        with st.expander(f"🔔 BOUNCE ALERTS — this session ({len(alerts)})", expanded=True):
            for a in alerts[:12]:
                st.markdown(f"<div style='background:rgba(34,197,94,.08);border:1px solid rgba(34,197,94,.35);"
                            f"border-radius:10px;padding:8px 14px;margin:4px 0;color:#d1fae5;font-size:12px;'>"
                            f"<b style='color:#4ade80;'>🚀 {a['name']}</b> · <span style='color:#64748b;'>{a['ts']}</span>"
                            f" · {a['txt']}</div>", unsafe_allow_html=True)

    if starting:
        st.markdown(f"<div style='color:#94a3b8;font-size:12px;font-weight:900;margin:10px 0 4px;'>"
                    f"🚀 UPTREND STARTING — reached support & turning up ({len(starting)})</div>", unsafe_allow_html=True)
        st.markdown("".join(_bc_row(i + 1, b, names.get(b["sym"], b["sym"].replace(".NS", "")))
                            for i, b in enumerate(starting[:100])), unsafe_allow_html=True)
    if waiting:
        with st.expander(f"🛡️ AT SUPPORT — waiting for the turn ({len(waiting)})"):
            st.markdown("".join(_bc_row(i + 1, b, names.get(b["sym"], b["sym"].replace(".NS", "")))
                                for i, b in enumerate(waiting[:100])), unsafe_allow_html=True)
    with st.expander("📋 Full bounce board + download"):
        disp = pd.DataFrame([{"Stock": names.get(b["sym"], b["sym"].replace(".NS", "")), "Symbol": b["sym"],
                              "Price": b["last"], "Day%": b["chg_day"], "Support": b["support"],
                              "SupDist%": b["sup_dist"], "BUY@": b["buy"], "SL": b["sl"],
                              "SellT1": b["t1"], "SellT2": b["t2"], "Resistance": b["resistance"],
                              "ResDist%": b["res_dist"], "OffLow%": b["rec"], "GreenCandles%": b["green"],
                              "Slope1h%": b["slope1h"], "Vol×": b["vr"], "BounceScore": b["score"],
                              "State": b["state"], "ScanTime": _ts} for b in bounces])
        try:
            st.dataframe(disp, use_container_width=True, height=420, hide_index=True)
        except Exception:
            st.dataframe(disp, use_container_width=True)
        try:
            st.download_button("⬇️ Download bounce board (CSV)", data=disp.to_csv(index=False).encode(),
                               file_name=f"support_bounces_{now_ist().strftime('%Y%m%d_%H%M')}.csv",
                               mime="text/csv", use_container_width=True, key="bc_csv")
        except Exception:
            pass


@st.cache_resource
def _cb_bg_store():
    """🧵 ONE shared combo-sweep worker for the whole process — st.cache_resource
    is created once and NEVER re-created, so the background thread and its
    result survive every page refresh/rerun (a plain module-level dict is
    re-created on each rerun and would lose the thread)."""
    return {"t": None, "done": 0.0, "res": None, "key": None, "busy": False}


_CB_BG = _cb_bg_store()


def cb_bg_alive():
    try:
        return bool(_CB_BG["t"] and _CB_BG["t"].is_alive())
    except Exception:
        return False


def cb_bg_start(watch, names):
    """🧵 REFRESH-PROOF combo scan — the 500-stock sweep (2–3 min) runs in a
    background thread that the page's auto-refresh CANNOT kill. The old
    inline sweep died mid-flight every 2 minutes → the endless 'scanning
    symbols, no result' loop. The page just polls; the board lands itself."""
    import threading
    key = f"{len(watch)}|{'|'.join(watch[:3])}"
    if cb_bg_alive():
        return False
    if _CB_BG.get("key") == key and _CB_BG.get("done") and time.time() - _CB_BG["done"] < 60:
        return False
    def _work():
        _CB_BG["busy"] = True          # suppresses st.progress inside the thread
        _t0 = time.time()
        try:
            _CB_BG["res"] = combo_scan(list(watch), dict(names or {}))
            blog(f"🎯 combo sweep DONE · {len(_CB_BG['res'])} rows in {time.time()-_t0:.0f}s "
                 f"· feed={'Upstox' if _FEED.get('fb', 0) > _FEED.get('yahoo_ok', 0) else 'Yahoo'}")
        except Exception as _e:
            _CB_BG["res"] = []
            blog(f"🎯 combo sweep FAILED · {type(_e).__name__}: {_e}")
        finally:
            _CB_BG["busy"] = False
            _CB_BG["done"] = time.time()
    _CB_BG.update(done=0.0, res=None, key=key)
    _CB_BG["t"] = threading.Thread(target=_work, daemon=True)
    _CB_BG["t"].start()
    blog(f"🎯 combo sweep started · {len(watch)} stocks")
    return True


def _volc_ui(combos, mst_s, now_map=None):
    """🌋 VOLCANO section — renders the sleeper-eruption radar inside the
    Combo tab. Green = erupting now · amber = loading (magma) · red = trap."""
    now_map = now_map or {}
    boom, load, trap = [], [], []
    for c in combos:
        v = c.get("volc") or {}
        if v.get("state") == "BOOM" and v.get("body", 0) >= 1.0 and (v.get("vol_mult") or 99) >= 2.0:
            boom.append((c, v))
        elif v.get("state") == "LOADING":
            load.append((c, v))
        elif v.get("state") == "TRAP" and abs(v.get("body", 0)) >= 1.0:
            trap.append((c, v))
    st.markdown(_H("<div style='color:#fdba74;font-size:15px;font-weight:900;margin:16px 0 2px;'>"
                   "🌋 VOLCANO — silent stock, sudden BOOM</div>"), unsafe_allow_html=True)
    st.caption("The Tata-Chemicals pattern (17 Sep: quiet ±0.1% all day → +5.5% in ONE 5-min candle, "
               "52× volume): a stock drifts inside a tiny box, then erupts. Every combo scan re-checks "
               "the whole board automatically — zero extra data calls — at ANY price (the picks board keeps "
               "your ₹100–₹1000 trading band; the volcano watches everything above ₹100, so a ₹736 Tata "
               "Chemicals or a ₹2,190 TCS can never slip past again).")
    if not (boom or load or trap):
        st.info("🌋 No eruptions on the board right now. Quiet boxes with volume starting to build "
                "(👀 MAGMA) appear here BEFORE the big candle fires — keep the radar running.")
    for c, v in boom:
        age = v.get("age", 0)
        np_now = now_map.get(c["sym"])
        badges = (["💪 STRONG"] if v.get("strong") else []) + \
                 (["⚡ LIVE CANDLE" if age == 0 else "🔁 2nd candle"]) + \
                 (["⚠️ FADING WICK"] if v.get("fading") else []) + \
                 (["🔇 THIN VOLUME"] if (v.get("vol_mult") or 99) < 2.5 else []) + \
                 (["🐢 LATE — day already ran"] if (c.get("chg_day") or 0) > 3 else [])
        st.markdown(_H(
            f"<div style='display:flex;align-items:center;gap:12px;background:#1c1206;border:1px solid #7c2d12;"
            f"border-left:3px solid #f97316;border-radius:12px;padding:8px 14px;margin:5px 0;flex-wrap:wrap;'>"
            f"<div style='min-width:150px;'><div style='color:#fdba74;font-weight:800;font-size:14px;'>💥 {c['name'][:19]}</div>"
            f"<div style='color:#64748b;font-size:10px;'>{c['sym'].replace('.NS','')} · erupted <b>{v['ts']}</b> IST</div></div>"
            f"<div style='min-width:88px;'><div style='color:#64748b;font-size:9px;'>PRICE</div>"
            f"<div style='color:#e2e8f0;font-weight:800;font-size:14px;font-family:monospace;'>₹{(np_now or c['price']):,.2f}</div></div>"
            f"<div style='min-width:118px;'><div style='color:#64748b;font-size:9px;'>💥 BIG CANDLE</div>"
            f"<div style='color:#f97316;font-size:13px;font-family:monospace;font-weight:900;'>+{v['body']:.2f}% in 5 min</div>"
            f"<div style='color:#94a3b8;font-size:9.5px;'>after ±{v['quiet_avg']:.2f}% drift</div></div>"
            f"<div style='min-width:112px;'><div style='color:#64748b;font-size:9px;'>📦 THE BOX</div>"
            f"<div style='color:#e2e8f0;font-size:10.5px;font-family:monospace;'>₹{v['box_lo']:,.1f}–{v['box_hi']:,.1f}</div>"
            f"<div style='color:#94a3b8;font-size:9.5px;'>only {v['tight']:.1f}% wide</div></div>"
            + (f"<div style='min-width:76px;'><div style='color:#64748b;font-size:9px;'>📊 VOLUME</div>"
               f"<div style='color:#22c55e;font-size:13px;font-family:monospace;font-weight:900;'>×{v['vol_mult']}</div>"
               f"<div style='color:#94a3b8;font-size:9.5px;'>vs quiet avg</div></div>" if v.get("vol_mult") else "")
            + (f"<div style='min-width:150px;'><div style='color:#64748b;font-size:9px;'>💰 TRADE (breakout style)</div>"
               f"<div style='font-size:10.5px;font-family:monospace;line-height:1.5;'>"
               f"<span style='color:#4ade80;font-weight:900;'>BUY ₹{v['buy']:,.2f}</span> · "
               f"<span style='color:#f87171;'>SL ₹{v['sl']:,.2f}</span><br>"
               f"<span style='color:#22c55e;font-weight:900;'>T1 ₹{v['t1']:,.2f}</span></div></div>" if v.get("t1") else "")
            + "<div style='min-width:160px;'>" + "".join(
                f"<span style='background:rgba(249,115,22,.15);color:#fdba74;font-size:9px;font-weight:900;"
                f"padding:2px 7px;border-radius:8px;margin:1px 2px;display:inline-block;'>{b}</span>" for b in badges)
            + "</div></div>"), unsafe_allow_html=True)
    if boom:
        st.caption("⚠️ BE CAREFUL — the exact thing you noticed: an eruption can FADE in the very next "
                   "candle (Tata Chemicals fired a FAKE eruption 11:45 that died instantly; the real one "
                   "came at 14:35). Rules: wait for the candle to CLOSE above the box · volume must be "
                   "≥2× · if price already ran more than 2× the box height, NEVER chase — wait for a "
                   "pullback to the box top.")
    if load:
        items = "".join(
            f"<span style='background:#1c1206;border:1px solid #7c2d12;color:#fdba74;font-size:10.5px;"
            f"padding:3px 9px;border-radius:8px;margin:2px;display:inline-block;'>👀 {c['name'][:16]} · "
            f"₹{c['price']:,.1f} · box ₹{v['box_lo']:,.0f}–{v['box_hi']:,.0f} · vol building ×{v.get('vol_build')}</span>"
            for c, v in load[:12])
        st.markdown(_H(f"<div style='color:#fdba74;font-size:11px;font-weight:800;margin:8px 0 3px;'>"
                       f"👀 MAGMA — quiet boxes with volume building ({len(load)}) · pre-eruption watch</div>"
                       f"<div>{items}</div>"), unsafe_allow_html=True)
    for c, v in trap:
        st.markdown(_H(
            f"<div style='display:flex;align-items:center;gap:12px;background:#1a0d0d;border:1px solid #7f1d1d;"
            f"border-left:3px solid #ef4444;border-radius:12px;padding:7px 14px;margin:5px 0;flex-wrap:wrap;'>"
            f"<div style='color:#fca5a5;font-weight:800;font-size:13px;min-width:150px;'>🕳️ {c['name'][:19]}</div>"
            f"<div style='color:#ef4444;font-weight:900;font-family:monospace;font-size:13px;'>{v['body']:.2f}% in 5 min</div>"
            f"<div style='color:#94a3b8;font-size:11px;'>fell out of a quiet box (₹{v['box_lo']:,.1f}–₹{v['box_hi']:,.1f}) at {v['ts']}</div>"
            f"<div style='color:#f87171;font-size:11px;font-weight:900;'>❌ DO NOT BUY today · holding? tighten SL</div></div>"),
            unsafe_allow_html=True)
    evs = sorted(((c, e) for c in combos for e in (c.get("volc_day") or [])),
                 key=lambda x: -abs(x[1].get("body") or 0))
    if evs:
        with st.expander(f"📜 Today's eruptions — full review ({len(evs)})"):
            rows = "".join(
                f"<div style='display:flex;gap:10px;background:#0b1220;border:1px solid #1e293b;border-radius:8px;"
                f"padding:5px 10px;margin:3px 0;font-size:11px;flex-wrap:wrap;align-items:center;'>"
                f"<b style='color:#e2e8f0;min-width:110px;'>{c['name'][:14]}</b>"
                f"<span style='color:#64748b;min-width:44px;'>{e['ts']}</span>"
                f"<span style='color:{'#22c55e' if e['body'] > 0 else '#ef4444'};font-weight:900;min-width:64px;"
                f"font-family:monospace;'>{e['body']:+.2f}%</span>"
                + (f"<span style='color:#94a3b8;min-width:56px;'>vol ×{e['vol_mult']}</span>" if e.get("vol_mult") else "")
                + (f"<span style='color:#94a3b8;min-width:96px;'>ran +{e['ran']}% after</span>" if e.get("ran") is not None else "")
                + ("<span style='color:#f87171;font-weight:900;'>❌ FADED — trap</span>" if e.get("faded_after")
                   else "<span style='color:#4ade80;font-weight:900;'>✅ HELD</span>")
                + "</div>" for c, e in evs[:25])
            st.markdown(_H(rows), unsafe_allow_html=True)
            st.caption("HELD = the move extended after the eruption candle · FADED = the next candles gave "
                       "it straight back — that is the 'be careful' side of this pattern.")


# ═══ 🚀 HOT MOVERS — whole-market spike radar (separate tab, watch-only) ═══
# The combo board finds CONFIRMED uptrends; a sudden +10% runner from a flat
# stock (RAYMONDREL +14%, ELECON +11% — the stocks you asked about) can never
# rank on day one. This tab sweeps EVERY NSE equity (~2500, incl. brand-new
# listings the NSE list misses) in seconds and answers: what spiked, and WHY
# it is not on our board (price band / thin volume / not curated / new listing).

_HOT_ETF_PAT = re.compile(
    r"ETF|Exchange Traded|BEES$|^NIFTY|^SENSEX|^LIQUID|^MOM|^MONQ|^MON100|^MIDCAP"
    r"|^LOWVOL|^QUAL|^EQUAL|^ALPHA|^HDFCNIF|^HDFCSML|^INDIGO|^SETF|^SGB", re.I)


def hot_universe():
    """Every NSE equity instrument (ETFs/junk filtered) — one master
    download per day, cached to its own day-file."""
    try:
        today = now_ist().strftime("%Y-%m-%d")
        fn = f"hot_univ_{_ukey()}.json"
        try:
            if _os.path.exists(fn):
                j = _json.load(open(fn, encoding="utf-8"))
                if j.get("d") == today and j.get("m"):
                    return j["m"]
        except Exception:
            pass
        import gzip as _gz
        rq = urllib.request.Request(
            "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz",
            headers={"User-Agent": UP_UA, "Accept": "*/*"})
        raw = _gz.decompress(urllib.request.urlopen(rq, timeout=45).read())
        m = {}
        for r in _json.loads(raw):
            if (r.get("segment") == "NSE_EQ" and r.get("instrument_type") == "EQ"
                    and r.get("trading_symbol") and r.get("instrument_key")):
                sym, nm = r["trading_symbol"], (r.get("name") or "")
                if _HOT_ETF_PAT.search(sym) or _HOT_ETF_PAT.search(nm):
                    continue
                m[sym + ".NS"] = r["instrument_key"]
        if m:
            try:
                _json.dump({"d": today, "m": m}, open(fn, "w", encoding="utf-8"))
            except Exception:
                pass
        return m
    except Exception:
        return {}


def _warmup_tick(chunk=70):
    """🔥 PRE-OPEN WARM-UP (user 21 Oct evening: "starting hot mover 09:15 but
    results coming almost 09:18 and the website tab takes a lot of time").
    09:00–09:14, while the user waits pre-open: progressively pre-cache the
    daily history (prev close · 20-day avg volume · week trend) for the
    band's biggest YESTERDAY-movers — the exact per-stock data the first
    09:15 sweep would otherwise fetch ONE-BY-ONE inside itself (~150 calls
    ≈ the 2–3 minute opening delay). Warm entries carry d=<today> so
    hot_scan's own cache check skips them: the first sweep drops to seconds
    and the first 🚀 can land 09:16–09:17 instead of ~09:18+."""
    try:
        _n = now_ist()
        today = _n.strftime("%Y-%m-%d")
        rt = rt_load()
        w = rt.get("warmup") or {}
        if w.get("day") == today and w.get("done", 0) >= (w.get("total") or 0):
            return {"done": w.get("done"), "total": w.get("total"), "fin": True}
        tok = up_auth_token()
        if not tok:
            return {"err": "token"}
        uni = hot_universe()
        if not uni:
            return {"err": "universe"}
        items = sorted(uni.items())
        Q = {}
        for i in range(0, len(items), 500):
            try:
                req = urllib.request.Request(
                    "https://api.upstox.com/v3/market-quote/ohlc?interval=1d&instrument_key="
                    + ",".join(k for _s, k in items[i:i + 500]),
                    headers={"Accept": "application/json", "User-Agent": UP_UA,
                             "Authorization": f"Bearer {tok}"})
                data = (_json.loads(urllib.request.urlopen(req, timeout=20)
                                    .read().decode("utf-8")) or {}).get("data") or {}
                for k, v in data.items():
                    try:
                        Q[(k.split(":")[-1] or "") + ".NS"] = v
                    except Exception:
                        pass
            except Exception:
                pass
        cand = []
        for s, v in Q.items():
            try:
                last = float(v.get("last_price") or 0)
                po = float(((v.get("prev_ohlc") or {}).get("close")) or 0)
                if 90.0 <= last <= 3100.0 and last > 0:
                    ym = abs(last / po - 1) if po > 0 else 0.0
                    cand.append((round(ym, 4), s))
            except Exception:
                continue
        cand.sort(reverse=True)
        syms = [s for _ym, s in cand][:600]
        if not syms:
            return {"err": "quotes"}
        hist = ((rt_load().get("hot_hist") or {}).get("m")) or {}
        start = w.get("done", 0) if w.get("day") == today else 0
        n = 0
        for s in syms[start:start + chunk]:
            if (hist.get(s) or {}).get("d") == today:
                n += 1
                continue
            k = uni.get(s) or ""
            if not k:
                n += 1
                continue
            try:
                req = urllib.request.Request(
                    f"https://api.upstox.com/v2/historical-candle/{k}/day/{today}/"
                    f"{(now_ist() - _dtd(days=45)).strftime('%Y-%m-%d')}",
                    headers={"Accept": "application/json", "User-Agent": UP_UA,
                             "Authorization": f"Bearer {tok}"})
                cd = ((_json.loads(urllib.request.urlopen(req, timeout=12)
                                   .read().decode("utf-8")) or {}).get("data") or {}).get("candles") or []
                if cd:
                    _tod = cd[0][0][:10] == today      # pre-open: today's row absent
                    pc = float(cd[1][4]) if _tod else float(cd[0][4])
                    vs = cd[1:21] if _tod else cd[0:20]
                    _p5 = None
                    try:
                        _i5 = 6 if _tod else 5
                        if len(cd) > _i5:
                            _p5 = round((pc / float(cd[_i5][4]) - 1) * 100, 1)
                    except Exception:
                        _p5 = None
                    hist[s] = {"d": today, "pc": pc, "p5": _p5,
                               "avg": (sum(float(x[5]) for x in vs) / 20) if len(vs) == 20 else None}
            except Exception:
                pass
            n += 1
            time.sleep(0.06)
        try:
            rt_save("hot_hist", m=hist)
        except Exception:
            pass
        done = min(start + n, len(syms))
        try:
            rt_save("warmup", day=today, done=done, total=len(syms))
        except Exception:
            pass
        return {"done": done, "total": len(syms), "fin": done >= len(syms)}
    except Exception:
        return {"err": "x"}


def _hot_badge(_ha, _s, now_px=0.0):
    """🆕/🔁 first-line badge for every HOT-MOVERS Telegram alert (user 21 Oct:
    "if any stock is repeating, it is GOING WELL — keep an eye on that").
    🆕 NEW = this stock's FIRST hot alert today · 🔁 GOING WELL = the stock
    already alerted today AND is above its first alert price — shows alert
    count, the first alert (type/time/price) and the gain since, so a runner
    is instantly visible as "this one keeps going — watch it". Warning
    follow-ups (⚠️/FAILED) pass no price → neutral 🔁 REPEAT with first-alert
    context only (never claims "going well" on a failing move). Message
    FORMATTING only — no rule, gate, cap, timing or ping-logic change."""
    try:
        _cands = []
        _n = 0                                    # alerts already sent today
        _r = (_ha.get("syms") or {}).get(_s)
        if isinstance(_r, dict) and _r.get("t"):
            _cands.append((str(_r["t"]),
                           ("💎" if _r.get("prem") else
                            ("🔥" if _r.get("big") else "🚀")),
                           float(_r.get("px") or 0)))
            _n += 1 + (1 if _r.get("done") else 0)
        _r = (_ha.get("d2u") or {}).get(_s)
        if isinstance(_r, dict) and _r.get("t"):
            _cands.append((str(_r["t"]), "🔄", float(_r.get("bp") or 0)))
            _n += 1 + (1 if _r.get("done") else 0)
        _r = (_ha.get("micro") or {}).get(_s)
        if isinstance(_r, dict) and _r.get("t"):
            _cands.append((str(_r["t"]), "💰", float(_r.get("px") or 0)))
            _n += 1 + (1 if _r.get("done") else 0)
        if not _cands:
            return "🆕 <b>NEW</b>"
        _t, _ic, _fpx = min(_cands, key=lambda c: c[0])
        if _fpx > 0 and now_px >= _fpx * 1.005:   # genuinely above the start
            return (f"🔁 <b>GOING WELL</b> · alert #{_n + 1} today · since {_ic} {_t} "
                    f"@ ₹{_fpx:.1f}: <b>+{(now_px / _fpx - 1) * 100:.1f}%</b> — keep an eye on this one")
        return (f"🔁 <b>REPEAT</b> — first alert {_ic} {_t}"
                + (f" @ ₹{_fpx:.1f}" if _fpx > 0 else ""))
    except Exception:
        return ""


def _stair_fresh(cd):
    """🕐 REAL-TIME freshness of a staircase (cd = 1-min candles, oldest
    first). fresh = price still ≤4% above the day open AND the 6-candle
    stair itself climbed ≤3%. The 26-30 Oct study: LATE stairs (SPARC
    +7.8% · J&KBANK +5.2% · URBANCO +4.5% above open) gave just +0.8%
    after the alert; FRESH ones (KARAMTARA +2.1% · FABTECH +2.9% ·
    BATAINDIA +3.9%) gave +3.2% to +6.5%. Returns (fresh, climb%, above%).
    Bad data → (True, 0, 0): never block on the unknown."""
    try:
        _op = float(cd[0][1])
        _last = float(cd[-1][4])
        _stair_open = float(cd[-6][1])
        _above = (_last / _op - 1) * 100
        _climb = (_last / _stair_open - 1) * 100
        return (_above <= 4.0 and _climb <= 3.0, _climb, _above)
    except Exception:
        return (True, 0.0, 0.0)


def _stair_confirm(rank, _ha, uni, tok, hist, _rg, _fr_ok):
    """🟢 GREEN STAIRCASE CONFIRMATION (user 21 Oct night: "already hot-
    alerted stock also moving with next-next green candles → inform → more
    confident meaning will buy"). For every stock that received a hot alert
    today (🚀/💎/🔥 in _ha['syms']) and is not yet resolved, watch for the
    SAME green-6 staircase the 🔥 rule uses (6 straight green 1-min candles
    + volume pace ≥1.5× + wicks ≥5/6 + above open). When it prints → ONE
    confidence message per stock per day, badge showing the going-well
    story. Standing 🔥 family gates apply: nothing before 09:30 (opening
    window owns it) and the red-market gate (no confidence pushes when
    NIFTY ≤ −0.50%). Message add-on only — entry rules, one-ping and caps
    of the base alerts are untouched."""
    try:
        _n = now_ist()
        _nowm = _n.hour * 60 + _n.minute
        if _nowm < 9 * 60 + 30:
            return                       # 🔥 family owns 09:30+ only
        _sent = 0
        _cand = []
        for r in rank:
            try:
                _rec = (_ha.get("syms") or {}).get(r["s"])
                if (isinstance(_rec, dict) and _rec.get("px")
                        and not _rec.get("done") and not _rec.get("stair")
                        and ((hist.get(r["s"]) or {}).get("avg") or 0) >= 100000):
                    _cand.append(r)
            except Exception:
                continue
        _cand.sort(key=lambda r: -r["fo"])
        for r in _cand[:10]:
            if _sent >= 6:
                break
            _k = uni.get(r["s"]) or ""
            if not _k:
                continue
            try:
                rq = urllib.request.Request(
                    f"https://api.upstox.com/v2/historical-candle/intraday/{_k}/1minute",
                    headers={"Accept": "application/json", "User-Agent": UP_UA,
                             "Authorization": f"Bearer {tok}"})
                cd = _up_closed(((_json.loads(urllib.request.urlopen(rq, timeout=10)
                                   .read().decode("utf-8")) or {}).get("data") or {}).get("candles") or [])
                if len(cd) >= 6:
                    cd = cd[::-1]                    # oldest first
                    _op = float(cd[0][1])
                    _g6 = all(float(c[4]) > float(c[1]) for c in cd[-6:])
                    _q6, _pr6 = cd[-6:], cd[:-6]
                    _volok, _vr = True, 0.0
                    if len(_pr6) >= 5:
                        try:
                            _pv = sum(float(c[5]) for c in _pr6) / len(_pr6)
                            _v6 = sum(float(c[5]) for c in _q6) / 6.0
                            _volok = (not _pv) or _v6 >= 1.5 * _pv
                            _vr = (_v6 / _pv) if _pv else 0.0
                        except Exception:
                            _volok = True
                    _wk = 0
                    for c in _q6:
                        try:
                            _hh, _ll, _cc = float(c[2]), float(c[3]), float(c[4])
                            _wk += 1 if (_hh <= _ll) or ((_cc - _ll) / (_hh - _ll)) >= 0.5 else 0
                        except Exception:
                            _wk += 1
                    if (_g6 and _volok and _wk >= 5
                            and r["last"] >= _op + max(1.5, 0.005 * _op)):
                        _fr, _clmb, _abv = _stair_fresh(cd)
                        if not _fr:
                            continue   # 🕐 LATE stair: >4% above open or >3% inside the stair = the top (26-30 Oct study)
                        if not _fr_ok:
                            continue                 # standing red gate
                        _nm = _esc(r["s"].replace(".NS", ""))
                        _msg = (f"🟢 <b>GREEN STAIRCASE · {_nm}</b> · {_hot_badge(_ha, r['s'], r['last'])}\n"
                                "already alerted today — and now climbing with 6 green candles in a row\n"
                                f"₹{r['last']:.1f} · +{100 * (r['last'] / r['op'] - 1):.1f}% "
                                f"above today's open ₹{r['op']:.1f}\n"
                                + (f"💧 staircase volume {_vr:.1f}× normal pace\n" if _vr else "")
                                + f"🟢 fresh stair — only +{_abv:.1f}% off today's open\n"
                                + "🟢🟢 the alerted move is STRENGTHENING — stronger confirmation now\n"
                                + (((f"{_rg['ico']} NIFTY {_rg['chg']:+.2f}% today"
                                     + ((f" \u00b7 last 15 min: "
                                        + ("rising \U0001F4C8" if (_rg.get("mom") or 0) > 5
                                           else ("falling \U0001F4C9" if (_rg.get("mom") or 0) < -5 else "flat"))
                                        + "\n") if _rg.get("mom") else "\n"))) if _rg else "")
                                + "🎯 don't chase the 6th candle — a small dip is the safer add\n"
                                + "⚠️ confidence signal, not a new pick · use your stop loss")
                        try:
                            if tg_send(_msg):
                                _rec = (_ha.get("syms") or {}).get(r["s"]) or {}
                                _rec["stair"] = _n.strftime("%H:%M")
                                _ha["syms"][r["s"]] = _rec
                                rt_save("hotalerts", **_ha)
                                _sent += 1
                        except Exception:
                            pass
                time.sleep(0.06)
            except Exception:
                continue
        # ── 🆕 FRESH-CLIMBER STAIRCASE (26-30 Oct deep study · user GO 31 Oct):
        #    the week's monsters printed steady 6×5-minute green staircases
        #    while NOT yet alerted (SUNTV 13 greens +4.7% left · INDOSTAR
        #    +7.7% · TINNARUBR +5.3% · BOROLTD +3.5%) — the old rule could
        #    only confirm already-alerted stocks. Now ANY liquid ₹100-3000
        #    mover in the sweep ranking printing 6 straight green 5-min
        #    candles + ≥1.3× volume gets ONE 🟢 per day. A fresh climber
        #    AGAINST a red NIFTY is real strength (23 Oct: all 6 red-launch
        #    winners paid) → the red gate does NOT block fresh climbers.
        #    Too-late stairs (>4% above open, or >3% inside the stair
        #    itself) stay suppressed in BOTH passes. 1-min candles are
        #    resampled to 5-min bars here. ──
        try:
            _extra = _ha.get("stairs_extra") or {}
            _cand2 = []
            for r in rank:
                try:
                    if (r["s"] not in (_ha.get("syms") or {})
                            and r["s"] not in _extra
                            and 100.0 <= float(r.get("last") or 0) <= 3000.0
                            and ((hist.get(r["s"]) or {}).get("avg") or 0) >= 100000):
                        _cand2.append(r)
                except Exception:
                    continue
            _cand2.sort(key=lambda r: -r.get("fo", 0))
            _fresh_sent = 0
            for r in _cand2[:10]:
                if _fresh_sent >= 3 or _sent >= 9:
                    break
                _k = uni.get(r["s"]) or ""
                if not _k:
                    continue
                try:
                    rq = urllib.request.Request(
                        f"https://api.upstox.com/v2/historical-candle/intraday/{_k}/1minute",
                        headers={"Accept": "application/json", "User-Agent": UP_UA,
                                 "Authorization": f"Bearer {tok}"})
                    cd = _up_closed(((_json.loads(urllib.request.urlopen(rq, timeout=10)
                                       .read().decode("utf-8")) or {}).get("data") or {}).get("candles") or [])
                    if len(cd) >= 35:
                        cd = cd[::-1]                       # oldest first
                        bars = {}                           # ── resample 1-min → 5-min ──
                        for c in cd:
                            try:
                                _ts = str(c[0])
                                _mm = int(_ts[14:16])
                                _b5 = _ts[:14] + f"{5 * (_mm // 5):02d}"
                                if _b5 not in bars:
                                    bars[_b5] = [float(c[1]), float(c[2]), float(c[3]),
                                                 float(c[4]), float(c[5])]
                                else:
                                    b = bars[_b5]
                                    b[1] = max(b[1], float(c[2]))
                                    b[2] = min(b[2], float(c[3]))
                                    b[3] = float(c[4])
                                    b[4] += float(c[5])
                            except Exception:
                                continue
                        bl = [bars[k] for k in sorted(bars)]
                        if len(bl) >= 7:
                            _op5 = bl[0][0]
                            _g6 = all(b[3] > b[0] for b in bl[-6:])
                            _volok, _vr = True, 0.0
                            _pr = bl[:-6]
                            if len(_pr) >= 3:
                                _pv = sum(b[4] for b in _pr) / len(_pr)
                                _v6 = sum(b[4] for b in bl[-6:]) / 6.0
                                _volok = (not _pv) or _v6 >= 1.3 * _pv
                                _vr = (_v6 / _pv) if _pv else 0.0
                            _last5 = float(bl[-1][3])
                            _abv5 = (_last5 / _op5 - 1) * 100
                            _clmb5 = (_last5 / float(bl[-6][0]) - 1) * 100
                            _fresh5 = (_abv5 <= 4.0 and _clmb5 <= 3.0)
                            if (_g6 and _volok and _fresh5
                                    and _last5 >= _op5 + max(1.5, 0.005 * _op5)):
                                _nm = _esc(r["s"].replace(".NS", ""))
                                _red_note = ""
                                if _rg and float(_rg.get("chg") or 0) <= -0.30:
                                    _red_note = (f"{_rg['ico']} NIFTY {_rg['chg']:+.2f}% — "
                                                 "climbing against a red tape = REAL strength\n")
                                _msg = (f"🟢 <b>GREEN STAIRCASE · {_nm}</b> · 🆕 <b>FRESH CLIMBER</b>\n"
                                        "not alerted before — a steady 6-candle climb just formed\n"
                                        f"₹{r['last']:.1f} · +{100 * (r['last'] / r['op'] - 1):.1f}% "
                                        f"above today's open ₹{r['op']:.1f}\n"
                                        + (f"💧 climb volume {_vr:.1f}× normal pace\n" if _vr else "")
                                        + _red_note
                                        + f"🟢 fresh stair — only +{_abv5:.1f}% off today's open\n"
                                        + "🎯 don't chase the 6th candle — a small dip is the safer entry\n"
                                        + "⚠️ confidence signal, not a pick · use your stop loss")
                                try:
                                    if tg_send(_msg):
                                        _extra[r["s"]] = _n.strftime("%H:%M")
                                        _ha["stairs_extra"] = _extra
                                        rt_save("hotalerts", **_ha)
                                        _fresh_sent += 1
                                        _sent += 1
                                except Exception:
                                    pass
                    time.sleep(0.06)
                except Exception:
                    continue
        except Exception:
            pass
    except Exception:
        pass


def _reignition_check(Q, _ha):
    """⚡ RE-IGNITION (user GO 23 Oct evening — born from SSWL 23 Oct: rocket
    09:29 → real fade → re-ignited 11:30 → closed +20.2% at the day high
    with ZERO further pings: one-ping had fired, the d2u bounce crossed its
    line between sweeps, fire-net skips pinged stocks). Fix: a FADED alert
    that crosses back ABOVE its original alert price and HOLDS it across
    two sweeps (>=3 min apart — the CALM-FADES pattern mirrored) gets ONE
    re-ignited tracking ping with the going-well badge. One per stock per
    day · quote-based (no extra API calls) · NOT red-gated — a tracking
    notice about a stock the user already holds an alert for, not a new
    pick (SSWL re-ignited while NIFTY was -1.2%)."""
    try:
        _n = now_ist()
        _nowm = _n.hour * 60 + _n.minute
        for _s, _rec in list((_ha.get("syms") or {}).items()):
            try:
                if (not (isinstance(_rec, dict) and _rec.get("px"))
                        or _rec.get("done") != "fade"       # only faded alerts
                        or _rec.get("reig")):               # one per stock/day
                    continue
                _q = Q.get(_s) or {}
                _last = float(_q.get("last_price")
                              or ((_q.get("ohlc") or {}).get("close")) or 0)
                if _last <= 0:
                    continue
                _ap = float(_rec["px"])
                if _last > _ap:
                    _pend = int(_rec.get("reig_pend") or 0)
                    if not _pend:
                        _rec["reig_pend"] = _nowm           # first sight — hold
                    elif _nowm - _pend >= 3:                # held across sweeps
                        _nm = _esc(_s.replace(".NS", ""))
                        if tg_send(f"⚡ <b>RE-IGNITED · {_nm}</b> · {_hot_badge(_ha, _s, _last)}\n"
                                   f"faded at {_rec.get('done_t', '?')} — now back ABOVE the alert price ₹{_ap:.1f}\n"
                                   f"₹{_last:.1f} · +{100 * (_last / _ap - 1):.1f}% from the alert price\n"
                                   "the move is running AGAIN — keep an eye on this one\n"
                                   "⚠️ tracking notice — not a new pick · use your stop loss"):
                            _rec["reig"] = _n.strftime("%H:%M")
                            rt_save("hotalerts", **_ha)
                else:
                    if _rec.get("reig_pend"):
                        _rec["reig_pend"] = 0               # fell back — reset
            except Exception:
                continue
    except Exception:
        pass


def _o5_now(cd):
    """Open of the CURRENT 5-minute candle, from 1-min candles (user 25 Oct:
    "alert comes, next candle dips — I want to buy the SAME 5-min candle").
    Orientation-independent (compares timestamp strings). None if the
    current bucket has no candle yet."""
    try:
        _n = now_ist()
        _b = (_n.hour * 60 + _n.minute) // 5
        _best = None
        for c in cd:
            try:
                t = str(c[0])
                if (int(t[11:13]) * 60 + int(t[14:16])) // 5 == _b:
                    if _best is None or t < _best[0]:      # earliest in bucket
                        _best = (t, float(c[1]))
            except Exception:
                continue
        return _best[1] if _best else None
    except Exception:
        return None


def _c5_block(x):
    """5-min candle CONTEXT line for entry alerts (user 25 Oct). Says: this
    5-min candle is LIVE with ~N min left, the buy zone (bucket open ->
    current price = INSIDE the candle, not above it), and the skip line:
    this 5-min candle CLOSING below the alert level = spike, skip. Context
    only — trigger logic untouched."""
    try:
        _n = now_ist()
        _m = _n.hour * 60 + _n.minute
        _left = 5 - (_m % 5) or 5
        _px = float(x.get("px") or 0)
        if _px <= 0:
            return ""
        _lvl = float(x.get("cross_px") or _px)
        _o5 = x.get("o5")
        try:
            _o5f = float(_o5)
        except Exception:
            _o5f = 0.0
        _lo = _lvl
        if 0 < _o5f < _px:
            _lo = max(_o5f, _lvl)          # candle open, never below the skip line
        if _lo >= _px - 0.05:
            _zone = f"around \u20B9{_px:.1f}"
        else:
            _zone = f"\u20B9{_lo:.1f}\u2013\u20B9{_px:.1f}"
        return (f"\U0001F7E2 5-min candle LIVE (~{_left} min left) \u00b7 buy zone {_zone} \u2014 buy INSIDE this candle, don\u2019t chase above it\n"
                f"\u26D4 this 5-min candle CLOSING below \u20B9{_lvl:.1f} = spike, skip\n")
    except Exception:
        return ""


def _sr_levels(s, uni, tok, hist, px):
    """Support/resistance levels on every entry alert (user 25 Oct: "it
    will help \u2014 we know when it will bounce"). Classic floor pivots from
    YESTERDAY's H/L/C: P=(H+L+C)/3, S1=2P-H, R1=2P+L, S2=P-(H-L), R2=P+(H-L).
    Cached in the hot_hist entry (one ~0.15s fetch per stock per day).
    Analysis layer on the message only \u2014 triggers stay zero-analysis."""
    try:
        h = hist.get(s) or {}
        piv = (h.get("piv") or {}) if isinstance(h, dict) else {}
        if not piv:
            k = uni.get(s) or ""
            if not k:
                return ""
            _ed = now_ist().strftime("%Y-%m-%d")
            _st = (now_ist() - _dtd(days=12)).strftime("%Y-%m-%d")
            rq = urllib.request.Request(
                f"https://api.upstox.com/v2/historical-candle/{k}/day/{_ed}/{_st}",
                headers={"Accept": "application/json", "User-Agent": UP_UA,
                         "Authorization": f"Bearer {tok}"})
            cds = ((_json.loads(urllib.request.urlopen(rq, timeout=10)
                                .read().decode("utf-8")) or {}).get("data") or {}).get("candles") or []
            y = None
            for c in cds:                     # v2 newest-first: first non-today = yesterday
                if str(c[0])[:10] < _ed:
                    y = c
                    break
            if not y:
                return ""
            _H, _L, _C = float(y[2]), float(y[3]), float(y[4])
            _P = (_H + _L + _C) / 3.0
            piv = {"p": _P, "s1": 2 * _P - _H, "r1": 2 * _P - _L,
                   "s2": _P - (_H - _L), "r2": _P + (_H - _L)}
            try:
                hist[s] = {**h, "piv": piv}
                rt_save("hot_hist", m=hist)
            except Exception:
                pass
        _px = float(px or 0)
        if _px <= 0:
            return ""
        if _px >= piv["r1"]:
            _hint = "above R1 \u2014 breakout territory"
        elif _px >= piv["p"]:
            _hint = "above pivot \u2014 strength"
        elif _px >= piv["s1"]:
            _hint = "S1\u2192pivot = bounce zone"
        else:
            _hint = "below S1 \u2014 next support S2"
        return (f"\U0001F4D0 S2 \u20B9{piv['s2']:.1f} \u00b7 S1 \u20B9{piv['s1']:.1f} \u00b7 pivot \u20B9{piv['p']:.1f} \u00b7 R1 \u20B9{piv['r1']:.1f} \u00b7 R2 \u20B9{piv['r2']:.1f}\n"
                f"\U0001F4CD now \u20B9{_px:.1f} \u2014 {_hint}\n")
    except Exception:
        return ""


def _nifty_roadmap(_rg):
    """NIFTY MORNING ROADMAP (user 25 Oct, option B): ONE Telegram message
    in the 09:15-09:45 window telling how NIFTY OPENED - gap down (crashed
    opens = falling-knife bounces, Thu 22 Oct), gap up (if it slides from
    the day high, opening rockets die, Fri 23 Oct: 1 of 27), or flat (the
    09:15-09:29 window at full power). Information only - no engine, gate
    or rule reads this. One per morning, persisted via rt 'niftyroad'."""
    try:
        if not _rg:
            return
        _n = now_ist()
        _nowm = _n.hour * 60 + _n.minute
        if _nowm < 9 * 60 + 15 or _nowm >= 9 * 60 + 45:
            return                      # opening window only
        _td = _n.strftime("%Y-%m-%d")
        try:
            if (rt_load().get("niftyroad") or {}).get("day") == _td:
                return                  # already sent this morning
        except Exception:
            pass
        gap = float(_rg.get("gap") or 0)
        chg = float(_rg.get("chg") or 0)
        if gap <= -0.25:
            _g = (f"gapped DOWN {gap:+.2f}% \u2014 stocks bouncing off crashed opens "
                  "(falling knives) \u00b7 opening rockets carry extra risk today \u00b7 "
                  "\U0001F504 recovery alerts are the honest signal")
        elif gap >= 0.25:
            _g = (f"gapped UP {gap:+.2f}% \u2014 watch whether it HOLDS: an open at the day high "
                  "that slides kills opening rockets (measured Fri: 1 of 27 worked)")
        else:
            _g = (f"opened FLAT {gap:+.2f}% \u2014 normal morning, the 09:15\u201309:29 window "
                  "is at full power")
        if tg_send(f"\U0001F305 <b>NIFTY MORNING ROADMAP \u00b7 {_n.strftime('%a %d %b')}</b>\n"
                   f"{_g}\n"
                   f"{_rg['ico']} NIFTY now {chg:+.2f}% vs prev close\n"
                   "One-time morning read \u2014 radars running."):
            try:
                rt_save("niftyroad", day=_td)
            except Exception:
                pass
    except Exception:
        pass


# ============================================================
# 🏅 v14 PRECISION LAYER — HOT ALERTS
#   1. _up_closed      : never judge a still-forming 1-min candle
#   2. hot_quality     : A+/A/B/C grade from LIVE Upstox data the old rules
#                        never used — exchange VWAP, bid/ask spread, order
#                        book, upper-circuit room, strength vs NIFTY, time
#   3. _graded_send    : every NEW-entry hot alert gets its grade line; an
#                        optional minimum grade suppresses weaker pings
#   4. alert log + eval: records the REAL price at send time, then scores
#                        every alert (sent AND suppressed) by FIRST TOUCH of
#                        +T% vs −S% on 1-min candles → measured win-rate per
#                        grade and per alert type. Trust this, not opinions.
#   Fail-open: missing/odd data → that check is "unknown", never blocks.
# ============================================================
HQ_NIFTY_KEY = "NSE_INDEX|Nifty 50"
HQ_TGT = 1.5      # % target for honest scoring (first touch)
HQ_STOP = 1.0     # % stop for honest scoring (first touch)
HQ_COST = 0.10    # % round-trip costs (brokerage + STT + slippage, intraday approx)
HQ_GRADES = ["ALL", "A", "A+"]
_HOT_ENTRY_RE = re.compile(
    r"^(🚀|💎|🔥|🔄|🎯) <b>(?:PREMIUM HOT ALERT|HOT ALERT|BIG MOVER|DOWN-TO-UP|SNIPER ₹3–4) · (.+?)</b>")
_HQ_KIND = {"🚀": "HOT", "💎": "PREMIUM", "🔥": "BIG", "🔄": "D2U", "🎯": "SNIPER"}


def _up_closed(cd):
    """Upstox intraday candles come newest-first and include the minute that
    is STILL FORMING. Drop it, so '2 closes held' / '6 green candles' are
    judged on finished candles only (a forming green candle can still close red)."""
    try:
        if cd and str(cd[0][0])[:16] >= now_ist().strftime("%Y-%m-%dT%H:%M"):
            return cd[1:]
    except Exception:
        pass
    return cd


def _hq_f(x):
    try:
        v = float(x)
        return v if v == v else 0.0
    except Exception:
        return 0.0


def _up_quotes(keys, tok):
    """Full market quotes (depth, VWAP, circuits, buy/sell qty) — one call."""
    out = {}
    try:
        import urllib.parse as _uparse
        q = ",".join(_uparse.quote(k, safe="") for k in keys if k)
        rq = urllib.request.Request(
            "https://api.upstox.com/v2/market-quote/quotes?instrument_key=" + q,
            headers={"Accept": "application/json", "User-Agent": UP_UA,
                     "Authorization": f"Bearer {tok}"})
        data = (_json.loads(urllib.request.urlopen(rq, timeout=10)
                            .read().decode("utf-8")) or {}).get("data") or {}
        for kk, v in data.items():
            if not isinstance(v, dict):
                continue
            out[str(kk)] = v
            if v.get("instrument_token"):
                out[str(v["instrument_token"])] = v
    except Exception:
        pass
    return out


def hot_quality(sym, kind=""):
    """🏅 Grade one alert candidate RIGHT NOW from the live Upstox quote."""
    res = {"grade": "?", "checks": [], "last": 0.0, "line": ""}
    try:
        k = (hot_universe() or {}).get(sym) or ""
        tok = up_auth_token()
        if not k or not tok:
            return res
        qs = _up_quotes([k, HQ_NIFTY_KEY], tok)
        q = qs.get(k) or qs.get("NSE_EQ:" + sym.replace(".NS", "")) or {}
        nq = qs.get(HQ_NIFTY_KEY) or qs.get("NSE_INDEX:Nifty 50") or {}
        last = _hq_f(q.get("last_price"))
        res["last"] = last
        ck = []
        if last > 0:
            vw = _hq_f(q.get("average_price"))
            if vw > 0:
                ext = (last / vw - 1) * 100
                if kind == "D2U":   # a recovery only needs to be back above VWAP-ish
                    ck.append(("VWAP", ext >= -0.3, f"{ext:+.1f}% vs VWAP"))
                else:               # above VWAP, but not stretched (chasing)
                    ck.append(("VWAP", 0.0 <= ext <= 2.0, f"{ext:+.1f}% vs VWAP"))
            uc = _hq_f(q.get("upper_circuit_limit"))
            if uc > 0:
                room = (uc / last - 1) * 100
                ck.append(("room", room >= 2.0, f"{room:.1f}% to upper circuit"))
            try:
                _d = q.get("depth") or {}
                bid = _hq_f(((_d.get("buy") or [{}])[0] or {}).get("price"))
                ask = _hq_f(((_d.get("sell") or [{}])[0] or {}).get("price"))
                if bid > 0 and ask > 0:
                    spr = (ask - bid) / last * 100
                    ck.append(("spread", spr <= 0.15, f"spread {spr:.2f}%"))
            except Exception:
                pass
            tb, tsq = _hq_f(q.get("total_buy_quantity")), _hq_f(q.get("total_sell_quantity"))
            if tb > 0 and tsq > 0:
                ck.append(("book", tb / tsq >= 1.0, f"buyers {tb / tsq:.1f}× sellers"))
            nc = _hq_f(q.get("net_change"))
            chg = (nc / (last - nc) * 100) if (last - nc) > 0 else None
            nl, nnc = _hq_f(nq.get("last_price")), _hq_f(nq.get("net_change"))
            nchg = (nnc / (nl - nnc) * 100) if (nl - nnc) > 0 else None
            if chg is not None and nchg is not None and nc != 0:
                ck.append(("RS", chg - nchg >= 1.0, f"{chg - nchg:+.1f}% vs NIFTY"))
            if nchg is not None and nl > 0:
                ck.append(("NIFTY", nchg > -0.50, f"NIFTY {nchg:+.2f}%"))
        _n = now_ist()
        _m = _n.hour * 60 + _n.minute
        ck.append(("time", 9 * 60 + 16 <= _m <= 14 * 60 + 30, _n.strftime("%H:%M")))
        res["checks"] = ck
        known = len(ck)
        fails = sum(1 for c in ck if not c[1])
        if known >= 4:
            res["grade"] = "A+" if fails == 0 else "A" if fails == 1 else "B" if fails == 2 else "C"
        ico = {"A+": "🏅", "A": "🥈", "B": "🟡", "C": "🔻"}.get(res["grade"], "❔")
        res["line"] = (f"{ico} <b>QUALITY {res['grade']}</b> ({known - fails}/{known}) · "
                       + " ".join(("✅" if c[1] else "❌") + c[0] for c in ck)
                       + ("\n   ↳ " + " · ".join(c[2] for c in ck if not c[1]) if fails else ""))
    except Exception:
        pass
    return res


def hot_cfg():
    try:
        return rt_load().get("hotcfg") or {}
    except Exception:
        return {}


def _grade_ok(g, mode):
    if g == "?" or mode not in ("A", "A+"):
        return True                      # unknown data never blocks (fail-open)
    return g == "A+" if mode == "A+" else g in ("A+", "A")


def _alert_log(sym, kind, qd, sent):
    """Persist every entry alert (sent or suppressed) with the REAL price at
    send time — the honest entry for later scoring. First sighting wins;
    a later actual send upgrades a suppressed record."""
    try:
        day = now_ist().strftime("%Y-%m-%d")
        lg = rt_load().get("alertlog") or {}
        days = lg.get("days") or {}
        rows = days.get(day) or {}
        key = f"{kind}|{sym}"
        old = rows.get(key)
        if old and (old.get("sent") or not sent):
            return
        rows[key] = {"sym": sym, "kind": kind, "t": now_ist().strftime("%H:%M"),
                     "ps": round(float(qd.get("last") or 0), 2), "g": qd.get("grade", "?"),
                     "fails": [c[0] for c in qd.get("checks", []) if not c[1]],
                     "sent": bool(sent)}
        days[day] = rows
        for d in sorted(days)[:-12]:      # keep the last 12 trading days
            days.pop(d, None)
        rt_save("alertlog", days=days)
    except Exception:
        pass


def _graded_send(text, buttons=None, keep=False):
    """Drop-in tg_send for hot_scan: grades NEW-entry alerts, logs them, and
    applies the minimum-grade filter. Follow-ups pass straight through."""
    m = _HOT_ENTRY_RE.match(text or "")
    if not m:
        return tg_send(text, buttons=buttons, keep=keep)
    try:
        import html as _html
        kind = _HQ_KIND.get(m.group(1), "HOT")
        sym = _html.unescape(m.group(2)).strip() + ".NS"
        qd = hot_quality(sym, kind)
        if not qd.get("last"):           # no live quote → price printed in the alert
            _pm = re.search(r"₹\s?([0-9][0-9,]*\.?[0-9]*)", b_ if (b_ := text.partition("\n")[2]) else "")
            if _pm:
                qd["last"] = _hq_f(_pm.group(1).replace(",", ""))
        ok = _grade_ok(qd["grade"], hot_cfg().get("min_grade", "ALL"))
        if not ok:
            _alert_log(sym, kind, qd, sent=False)
            return False
        if qd.get("line"):
            a, _, b = text.partition("\n")
            text = a + "\n" + qd["line"] + ("\n" + b if b else "")
        sent = tg_send(text, buttons=buttons, keep=keep)
        if sent:
            _alert_log(sym, kind, qd, sent=True)
        return sent
    except Exception:
        return tg_send(text, buttons=buttons, keep=keep)


def _hq_candles(key, day, tok):
    """1-min candles of one session, oldest first, closed candles only."""
    try:
        if day == now_ist().strftime("%Y-%m-%d"):
            url = f"https://api.upstox.com/v2/historical-candle/intraday/{key}/1minute"
        else:
            url = f"https://api.upstox.com/v3/historical-candle/{key}/minutes/1/{day}/{day}"
        rq = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": UP_UA,
                                                  "Authorization": f"Bearer {tok}"})
        cd = ((_json.loads(urllib.request.urlopen(rq, timeout=12).read().decode("utf-8"))
               or {}).get("data") or {}).get("candles") or []
        cd = _up_closed([c for c in cd if str(c[0])[:10] == day])
        return cd[::-1]
    except Exception:
        return []


def hq_first_touch(cd, t_hhmm, ps, tgt=HQ_TGT, stop=HQ_STOP, exit_hhmm="15:20"):
    """Score one entry: candles strictly AFTER the send minute; stop and
    target in the same candle → LOSS (order unknown = conservative)."""
    up, dn = ps * (1 + tgt / 100), ps * (1 - stop / 100)
    mfe = mae = 0.0
    last = ps
    for c in cd:
        hm = str(c[0])[11:16]
        if hm <= t_hhmm:
            continue
        if hm > exit_hhmm:
            break
        h, l, cl = float(c[2]), float(c[3]), float(c[4])
        mfe = max(mfe, (h / ps - 1) * 100)
        mae = min(mae, (l / ps - 1) * 100)
        last = cl
        if l <= dn:
            return {"res": "LOSS", "pnl": -stop, "mfe": mfe, "mae": mae, "at": hm}
        if h >= up:
            return {"res": "WIN", "pnl": tgt, "mfe": mfe, "mae": mae, "at": hm}
    return {"res": "OPEN", "pnl": (last / ps - 1) * 100, "mfe": mfe, "mae": mae, "at": exit_hhmm}


def hot_eval_pending(force_today=False):
    """Score every logged alert day not yet scored (today only after 15:30)."""
    try:
        tok = up_auth_token()
        if not tok:
            return 0
        rt = rt_load()
        days = (rt.get("alertlog") or {}).get("days") or {}
        stats = (rt.get("alertstats") or {}).get("days") or {}
        today = now_ist().strftime("%Y-%m-%d")
        _m = now_ist().hour * 60 + now_ist().minute
        uni = hot_universe() or {}
        n = 0
        for day in sorted(days):
            if day in stats and day != today:
                continue
            if day == today and not (force_today or _m >= 15 * 60 + 30):
                continue
            out = []
            for key, r in (days.get(day) or {}).items():
                k = uni.get(r.get("sym")) or ""
                if not k or not r.get("ps"):
                    continue
                cd = _hq_candles(k, day, tok)
                if not cd:
                    continue
                ft = hq_first_touch(cd, r.get("t", "09:15"), float(r["ps"]))
                out.append({**r, **{kk: (round(v, 2) if isinstance(v, float) else v)
                                    for kk, v in ft.items()}})
                n += 1
                time.sleep(0.05)
            if out:
                stats[day] = out
        for d in sorted(stats)[:-30]:
            stats.pop(d, None)
        rt_save("alertstats", days=stats)
        return n
    except Exception:
        return 0


def hot_stats_table(last_days=30):
    """Aggregate measured results → rows per (group, value)."""
    try:
        stats = ((rt_load().get("alertstats") or {}).get("days")) or {}
        rows = [r for d in sorted(stats)[-last_days:] for r in stats[d]]
    except Exception:
        rows = []
    if not rows:
        return [], 0

    def _agg(lbl, rs):
        w = sum(1 for r in rs if r.get("res") == "WIN")
        l = sum(1 for r in rs if r.get("res") == "LOSS")
        o = len(rs) - w - l
        net = sum(float(r.get("pnl") or 0) for r in rs) / len(rs) - HQ_COST
        return {"group": lbl, "alerts": len(rs), "win": w, "loss": l, "open@15:20": o,
                "win%": round(100 * w / (w + l), 1) if (w + l) else None,
                "avg net % / trade": round(net, 2)}
    out = [_agg("ALL (sent + suppressed)", rows),
           _agg("sent only", [r for r in rows if r.get("sent")])]
    for g in ["A+", "A", "B", "C", "?"]:
        rs = [r for r in rows if r.get("g") == g]
        if rs:
            out.append(_agg(f"grade {g}", rs))
    for kd in ["HOT", "PREMIUM", "BIG", "D2U", "SNIPER"]:
        rs = [r for r in rows if r.get("kind") == kd]
        if rs:
            out.append(_agg(f"type {kd}", rs))
    for chk in ["VWAP", "room", "spread", "book", "RS", "NIFTY", "time"]:
        rs = [r for r in rows if chk in (r.get("fails") or [])]
        if rs:
            out.append(_agg(f"failed {chk}", rs))
    return out, len(rows)


def hot_stats_lines(day):
    """Short Telegram block for the daily scorecard."""
    try:
        stats = ((rt_load().get("alertstats") or {}).get("days")) or {}
        rs = stats.get(day) or []
        if not rs:
            return []
        L = ["", f"🏅 HONEST SCORE (first touch +{HQ_TGT}% vs −{HQ_STOP}%, from the real send price)"]
        for g in ["A+", "A", "B", "C", "?"]:
            x = [r for r in rs if r.get("g") == g]
            if not x:
                continue
            w = sum(1 for r in x if r.get("res") == "WIN")
            l = sum(1 for r in x if r.get("res") == "LOSS")
            L.append(f"   grade {g}: {len(x)} alerts · ✅{w} ❌{l} ⏳{len(x) - w - l}"
                     + (f" · win {100 * w // (w + l)}%" if (w + l) else ""))
        tab, n = hot_stats_table()
        if n:
            a = next((t for t in tab if t["group"].startswith("ALL")), None)
            if a and a.get("win%") is not None:
                L.append(f"   📚 last 30 days: {n} alerts · win {a['win%']}% · "
                         f"avg {a['avg net % / trade']:+.2f}%/trade after costs")
        return L
    except Exception:
        return []


def hot_scan(progress=None, tg=True):
    """🚀 Whole-market sweep: ~2500 equities in seconds (batched 📡 quotes),
    then exact prev-close + 20-day avg volume for the top movers. Works live
    during market hours AND after close (shows the full day)."""
    tg_send = _graded_send   # 🏅 v14: entry alerts are graded + logged (follow-ups pass through)
    try:
        if not up_token_valid():
            return {"err": "no_token"}
        uni = hot_universe()
        if not uni:
            return {"err": "universe"}
        tok = up_auth_token()
        items = sorted(uni.items())
        Q = {}
        for i in range(0, len(items), 500):
            try:
                req = urllib.request.Request(
                    "https://api.upstox.com/v2/market-quote/ohlc?interval=1d&instrument_key="
                    + ",".join(k for _s, k in items[i:i + 500]),
                    headers={"Accept": "application/json", "User-Agent": UP_UA,
                             "Authorization": f"Bearer {tok}"})
                data = (_json.loads(urllib.request.urlopen(req, timeout=20)
                                    .read().decode("utf-8")) or {}).get("data") or {}
                for k, v in data.items():
                    try:
                        Q[(k.split(":")[-1] or "") + ".NS"] = v
                    except Exception:
                        pass
            except Exception:
                pass
            try:
                if progress:
                    progress(min(1.0, (i + 500) / max(1, len(items))))
            except Exception:
                pass
        rank = []
        for s, v in Q.items():
            o = (v or {}).get("ohlc") or {}
            try:
                last = float((v or {}).get("last_price") or o.get("close") or 0)
                op = float(o.get("open") or 0)
                lo = float(o.get("low") or 0)
            except Exception:
                continue
            if last > 1 and op > 0:
                rank.append({"s": s, "last": last, "op": op, "lo": lo,
                             "fo": last / op - 1})
        # 🌙 OVERNIGHT-SESSION DETECT: after midnight (and on weekends/holidays)
        #    the quotes still describe the LAST completed session — every
        #    stock's last_price equals its session close. Then "today" must
        #    mean THAT session, not the calendar date — otherwise chg = 0%
        #    for every stock and the tab goes blind until the next open.
        try:
            _eq = sum(1 for v in Q.values()
                      if abs(float((v or {}).get("last_price") or 0)
                             - float(((v or {}).get("ohlc") or {}).get("close") or -1)) < 0.01)
            _SESS_DONE = len(Q) > 0 and _eq >= 0.9 * len(Q)
        except Exception:
            _SESS_DONE = False
        _sess_d = ""    # session date the data describes (set from daily candles)
        disp = sorted(rank, key=lambda r: -r["fo"])[:60]      # tab list (by %)
        # 🚀 ₹-MOVER shortlist — biggest RUPEE moves in the band. (The old
        #    +2.5% rule = ₹2.5 on a ₹100 stock but ₹12 on ₹500 — now the
        #    trigger is RUPEE-based: ₹10/day movers caught early at +₹3.)
        candpool = sorted([r for r in rank if MIN_PRICE <= r["last"] <= MAX_PRICE],
                          key=lambda r: -(r["last"] - r["op"]))[:150]
        # 🔄 DOWN-TO-UP shortlist — dipped ≥₹2 below open, bounced ≥₹5 off low
        d2upool = []
        for r in rank:
            if (MIN_PRICE <= r["last"] <= MAX_PRICE
                    and (r["op"] - r["lo"]) >= max(2.0, 0.005 * r["op"])
                    and (r["last"] - r["lo"]) >= max(5.0, 0.01 * r["last"])):
                d2upool.append(r)
        d2upool = sorted(d2upool, key=lambda r: -(r["last"] - r["lo"]))[:20]
        # 💎 PREMIUM ₹-mover shortlist — ₹1000–3000 band, its OWN pipeline so
        #    the main list/alerts stay exactly as before (user request 12 Oct)
        prempool = sorted([r for r in rank if PREM_MIN < r["last"] <= PREM_MAX],
                          key=lambda r: -(r["last"] - r["op"]))[:25]
        short = list(dict.fromkeys([r["s"] for r in disp]
                                   + [r["s"] for r in candpool]
                                   + [r["s"] for r in d2upool]
                                   + [r["s"] for r in prempool]))
        # exact prev-close + 20d avg volume for the shortlist (cached 1×/day)
        today = now_ist().strftime("%Y-%m-%d")
        hist = ((rt_load().get("hot_hist") or {}).get("m")) or {}
        fromd = (now_ist() - _dtd(days=45)).strftime("%Y-%m-%d")
        for s in short:
            if (hist.get(s) or {}).get("d") == today:
                continue
            k = uni.get(s) or ""
            if not k:
                continue
            try:
                rq = urllib.request.Request(
                    f"https://api.upstox.com/v2/historical-candle/{k}/day/{today}/{fromd}",
                    headers={"Accept": "application/json", "User-Agent": UP_UA,
                             "Authorization": f"Bearer {tok}"})
                cd = ((_json.loads(urllib.request.urlopen(rq, timeout=12)
                                   .read().decode("utf-8")) or {}).get("data") or {}).get("candles") or []
                if len(cd) >= 2:
                    _tod = (cd[0][0][:10] == today) or _SESS_DONE   # 🌙 overnight too
                    pc = float(cd[1][4]) if _tod else float(cd[0][4])
                    if not _sess_d:
                        _sess_d = cd[0][0][:10] if _SESS_DONE else today
                    vs = cd[1:21] if _tod else cd[0:20]
                    _p5 = None                                   # week trend (context)
                    try:
                        _i5 = 6 if _tod else 5                   # close 5 sessions back
                        if len(cd) > _i5:
                            _p5 = round((pc / float(cd[_i5][4]) - 1) * 100, 1)
                    except Exception:
                        _p5 = None
                    hist[s] = {"d": (_sess_d or today), "pc": pc, "p5": _p5,
                               "avg": (sum(float(x[5]) for x in vs) / 20) if len(vs) == 20 else None}
                time.sleep(0.08)
            except Exception:
                continue
        try:
            rt_save("hot_hist", m=hist)
        except Exception:
            pass
        try:
            cur = set(ALL_STOCKS.values()) if ALL_STOCKS else set()
        except Exception:
            cur = set()
        try:
            _u = fetch_universe()
            usearch = set(_u["sym_map"].values()) if _u.get("live") else None
        except Exception:
            usearch = None
        rows = []
        for r in disp:
            s = r["s"]
            c = hist.get(s) or {}
            try:
                chg = (r["last"] / c["pc"] - 1) * 100 if c.get("pc") else r["fo"] * 100
            except Exception:
                chg = r["fo"] * 100
            rows.append({"s": s, "px": round(r["last"], 1), "chg": round(chg, 2),
                         "avg20": (c.get("avg") or 0), "p5": c.get("p5"), "curated": s in cur,
                         "listed": True if usearch is None else s in usearch})
        # 🧹 CLEAN LIST (user request 29 Sep): the tab shows only real,
        # tradeable movers — price ≥ ₹60 AND ≥1L shares/day. Penny stocks
        # and thin counters never appear (alerts already need ₹100 + 1L).
        rows = [x for x in rows if x["chg"] >= 2.0
                and 60.0 <= x["px"] <= MAX_PRICE      # 💎 >₹1000 now lives in its OWN section
                and (x["avg20"] or 0) >= 100000][:60]
        # ── 🚀 STAGE 3a — WHEN did each ₹-mover start? A fresh mover = first
        #    SUSTAINED close ≥ open + max(₹3, 1%) — two consecutive candles
        #    ("crossed CONTINUOUSLY", not a one-tick spike). That cross is
        #    the early catch-point for ₹10/day movers. ──
        _intra_ok = {}   # 🚫 intraday-verified? (only stocks actually fetched)
        cand = []
        for r in candpool:
            c = hist.get(r["s"]) or {}
            if ((c.get("avg") or 0) >= 100000 and (r["last"] - r["op"]) >= 3.0):
                cand.append({"s": r["s"], "px": round(r["last"], 1),
                             "op": round(r["op"], 1), "avg20": c.get("avg") or 0,
                             "p5": c.get("p5"), "pc": c.get("pc")})
        cand = cand[:25]
        for x in cand:
            k = uni.get(x["s"]) or ""
            if not k:
                continue
            try:
                rq = urllib.request.Request(
                    f"https://api.upstox.com/v2/historical-candle/intraday/{k}/1minute",
                    headers={"Accept": "application/json", "User-Agent": UP_UA,
                             "Authorization": f"Bearer {tok}"})
                cd = _up_closed(((_json.loads(urllib.request.urlopen(rq, timeout=10)
                                   .read().decode("utf-8")) or {}).get("data") or {}).get("candles") or [])
                if not cd and _sess_d:        # 🌙 v2 EMPTY (overnight/holiday/lag): pull
                    #    the last session via v3. Young 1–14-candle stocks
                    #    during the live opening are NOT overwritten —
                    #    they stay visible (fallback was wiping them).
                    try:                       #    NEW day (empty) — pull the last
                        _sd = _sess_d          #    session's candles via v3
                        _pv = (datetime.strptime(_sd, "%Y-%m-%d") - _dtd(days=1)).strftime("%Y-%m-%d")
                        for _f in (_sd, _pv):
                            try:
                                rq3 = urllib.request.Request(
                                    f"https://api.upstox.com/v3/historical-candle/{k}/minutes/1/{_sd}/{_f}",
                                    headers={"Accept": "application/json", "User-Agent": UP_UA,
                                             "Authorization": f"Bearer {tok}"})
                                _c3 = ((_json.loads(urllib.request.urlopen(rq3, timeout=10)
                                                   .read().decode("utf-8")) or {}).get("data") or {}).get("candles") or []
                                cd = [c for c in _c3 if str(c[0])[:10] == _sd]
                                if len(cd) >= 15:
                                    break
                            except Exception:
                                cd = []
                    except Exception:
                        cd = []
                _intra_ok[x["s"]] = len(cd) >= 1        # 🚫 intraday data present? (≥1 candle =
                    #    trading — 15 candles are needed only for cross math,
                    #    so young stocks STAY visible during the opening)
                x["o5"] = _o5_now(cd)              # 5-min candle open (user 25 Oct)
                if len(cd) >= 2:                     # 🌅 opening confirm (FIX ALL 13 Oct):
                    try:                             # TWO consecutive completed closes
                        _op2 = float(cd[-1][1])      # ≥ open + max(₹3, 1%) — the user's
                        _t2 = max(3.0, 0.01 * _op2)  # own 2-min wait, automated. Kills
                        x["c2"] = (float(cd[0][4]) >= _op2 + _t2   # the 2-minute tick-spikes
                                  and float(cd[1][4]) >= _op2 + _t2)   # (measured: −70% fakes)
                    except Exception:
                        pass
                if len(cd) >= 15:                       # ⏱ 15 candles = live from ~09:30
                    cd = cd[::-1]                       # oldest first
                    op = float(cd[0][1])
                    if x.get("pc"):
                        x["gap"] = round((op / x["pc"] - 1) * 100, 2)
                        x["chg"] = round((x["px"] / x["pc"] - 1) * 100, 2)
                    _thr = max(3.0, 0.01 * op)          # ₹3 — or 1% if costlier
                    for i in range(len(cd) - 1):        # sustained ₹-cross
                        if (float(cd[i][4]) >= op + _thr
                                and float(cd[i + 1][4]) >= op + _thr):
                            x["cross"] = cd[i][0][11:16]
                            x["cross_px"] = round(float(cd[i][4]), 1)
                            x["rmove"] = round(float(cd[i][4]) - op, 1)
                            break
                    if x.get("cross") and x["avg20"]:
                        try:
                            _mins = max(int(x["cross"][:2]) * 60 + int(x["cross"][3:])
                                        - (9 * 60 + 15), 1)
                            _vby = sum(float(c[5]) for c in cd
                                       if c[0][11:16] <= x["cross"])
                            x["pace"] = round((_vby / x["avg20"]) / (_mins / 375.0), 1)
                        except Exception:
                            pass
                time.sleep(0.06)
            except Exception:
                continue
        # ── 💎 PREMIUM STAGE — ₹1000–3000 movers: same sustained-cross rule
        #    (≥ open + max(₹3, 1%), 2 candles held) but its OWN candidate list;
        #    pings are labeled 💎 PREMIUM so the bands never mix in your head.
        candp = []
        for r in prempool:
            c = hist.get(r["s"]) or {}
            if ((c.get("avg") or 0) >= 100000 and (r["last"] - r["op"]) >= 3.0):
                candp.append({"s": r["s"], "px": round(r["last"], 1),
                              "op": round(r["op"], 1), "avg20": c.get("avg") or 0,
                              "p5": c.get("p5"), "pc": c.get("pc")})
        candp = candp[:10]
        for x in candp:
            k = uni.get(x["s"]) or ""
            if not k:
                continue
            try:
                rq = urllib.request.Request(
                    f"https://api.upstox.com/v2/historical-candle/intraday/{k}/1minute",
                    headers={"Accept": "application/json", "User-Agent": UP_UA,
                             "Authorization": f"Bearer {tok}"})
                cd = _up_closed(((_json.loads(urllib.request.urlopen(rq, timeout=10)
                                   .read().decode("utf-8")) or {}).get("data") or {}).get("candles") or [])
                if not cd and _sess_d:        # 🌙 v2 EMPTY only — never wipe young
                    try:                      #    live-opening candles
                        _sd = _sess_d
                        _pv = (datetime.strptime(_sd, "%Y-%m-%d") - _dtd(days=1)).strftime("%Y-%m-%d")
                        for _f in (_sd, _pv):
                            try:
                                rq3 = urllib.request.Request(
                                    f"https://api.upstox.com/v3/historical-candle/{k}/minutes/1/{_sd}/{_f}",
                                    headers={"Accept": "application/json", "User-Agent": UP_UA,
                                             "Authorization": f"Bearer {tok}"})
                                _c3 = ((_json.loads(urllib.request.urlopen(rq3, timeout=10)
                                                   .read().decode("utf-8")) or {}).get("data") or {}).get("candles") or []
                                cd = [c for c in _c3 if str(c[0])[:10] == _sd]
                                if cd:
                                    break
                            except Exception:
                                cd = []
                    except Exception:
                        cd = []
                x["o5"] = _o5_now(cd)              # 5-min candle open (user 25 Oct)
                if len(cd) >= 2:                     # 🌅 opening confirm (FIX ALL 13 Oct):
                    try:                             # TWO consecutive completed closes
                        _op2 = float(cd[-1][1])      # ≥ open + max(₹3, 1%) — the user's
                        _t2 = max(3.0, 0.01 * _op2)  # own 2-min wait, automated. Kills
                        x["c2"] = (float(cd[0][4]) >= _op2 + _t2   # the 2-minute tick-spikes
                                  and float(cd[1][4]) >= _op2 + _t2)   # (measured: −70% fakes)
                    except Exception:
                        pass
                if len(cd) >= 15:
                    cd = cd[::-1]
                    op = float(cd[0][1])
                    if x.get("pc"):
                        x["gap"] = round((op / x["pc"] - 1) * 100, 2)
                        x["chg"] = round((x["px"] / x["pc"] - 1) * 100, 2)
                    _thr = max(3.0, 0.01 * op)          # ₹3 — or 1% (₹1500 → ₹15)
                    for i in range(len(cd) - 1):        # sustained ₹-cross
                        if (float(cd[i][4]) >= op + _thr
                                and float(cd[i + 1][4]) >= op + _thr):
                            x["cross"] = cd[i][0][11:16]
                            x["cross_px"] = round(float(cd[i][4]), 1)
                            x["rmove"] = round(float(cd[i][4]) - op, 1)
                            break
                time.sleep(0.06)
            except Exception:
                continue
        # ── 🔄 STAGE 3b — DOWN-TO-UP: fell ≥₹2 below open, now bounced
        #    ≥ max(₹5, 1%) off the day low (sustained) = recovery candidate. ──
        d2u = []
        for r in d2upool:
            c = hist.get(r["s"]) or {}
            if (c.get("avg") or 0) >= 100000:
                d2u.append({"s": r["s"], "px": round(r["last"], 1),
                            "op": round(r["op"], 1), "lo": round(r["lo"], 1),
                            "dip": round(r["op"] - r["lo"], 1),
                            "bnc": round(r["last"] - r["lo"], 1),
                            "avg20": c.get("avg") or 0, "p5": c.get("p5"),
                            "pc": c.get("pc")})
        d2u = d2u[:15]
        for x in d2u:
            k = uni.get(x["s"]) or ""
            if not k:
                continue
            try:
                rq = urllib.request.Request(
                    f"https://api.upstox.com/v2/historical-candle/intraday/{k}/1minute",
                    headers={"Accept": "application/json", "User-Agent": UP_UA,
                             "Authorization": f"Bearer {tok}"})
                cd = _up_closed(((_json.loads(urllib.request.urlopen(rq, timeout=10)
                                   .read().decode("utf-8")) or {}).get("data") or {}).get("candles") or [])
                if not cd and _sess_d:        # 🌙 v2 EMPTY (overnight/holiday/lag): pull
                    #    the last session via v3. Young 1–14-candle stocks
                    #    during the live opening are NOT overwritten —
                    #    they stay visible (fallback was wiping them).
                    try:                       #    NEW day (empty) — pull the last
                        _sd = _sess_d          #    session's candles via v3
                        _pv = (datetime.strptime(_sd, "%Y-%m-%d") - _dtd(days=1)).strftime("%Y-%m-%d")
                        for _f in (_sd, _pv):
                            try:
                                rq3 = urllib.request.Request(
                                    f"https://api.upstox.com/v3/historical-candle/{k}/minutes/1/{_sd}/{_f}",
                                    headers={"Accept": "application/json", "User-Agent": UP_UA,
                                             "Authorization": f"Bearer {tok}"})
                                _c3 = ((_json.loads(urllib.request.urlopen(rq3, timeout=10)
                                                   .read().decode("utf-8")) or {}).get("data") or {}).get("candles") or []
                                cd = [c for c in _c3 if str(c[0])[:10] == _sd]
                                if len(cd) >= 15:
                                    break
                            except Exception:
                                cd = []
                    except Exception:
                        cd = []
                _intra_ok[x["s"]] = len(cd) >= 1        # 🚫 intraday data present? (≥1 candle =
                    #    trading — 15 candles are needed only for cross math,
                    #    so young stocks STAY visible during the opening)
                if len(cd) >= 15:
                    cd = cd[::-1]
                    if x.get("pc"):
                        x["chg"] = round((x["px"] / x["pc"] - 1) * 100, 2)
                    _lo = min(float(c[3]) for c in cd)
                    _li = next(i for i, c in enumerate(cd) if float(c[3]) == _lo)
                    _bthr = max(5.0, 0.01 * x["px"])     # ₹5 off the low — or 1%
                    for i in range(_li, len(cd) - 1):    # sustained bounce
                        if (float(cd[i][4]) >= _lo + _bthr
                                and float(cd[i + 1][4]) >= _lo + _bthr):
                            x["b_t"] = cd[i][0][11:16]
                            x["b_px"] = round(float(cd[i][4]), 1)
                            break
                    if x.get("b_t") and x["avg20"]:
                        try:
                            _mins = max(int(x["b_t"][:2]) * 60 + int(x["b_t"][3:])
                                        - (9 * 60 + 15), 1)
                            _vby = sum(float(c[5]) for c in cd
                                       if c[0][11:16] <= x["b_t"])
                            x["pace"] = round((_vby / x["avg20"]) / (_mins / 375.0), 1)
                        except Exception:
                            pass
                    try:                                  # 🟢 LIVE momentum:
                        _lastc = float(cd[-1][4])         # ₹ move in the last
                        _ref = float(cd[-16][4]) if len(cd) >= 16 else float(cd[0][4])
                        x["now"] = round(_lastc - _ref, 1)
                    except Exception:
                        pass
                time.sleep(0.06)
            except Exception:
                continue
        # risers first — "what is moving up RIGHT NOW" tops the list
        d2u.sort(key=lambda x: (-(x["now"] if x.get("now") is not None else -999.0),
                                -x["bnc"]))
        # ── 💰 STAGE 3c — MICRO SETUPS: liquid ₹200+ stock drifting up
        #    (+₹1.5 from open) breaks its last-30-minute ceiling with volume,
        #    held 2 candles. The simple "₹3–4 for the day" entry — small
        #    move, high hit-rate, no spike-chasing. ──
        micro = []
        _seenm = set()
        for r in (candpool + d2upool):
            s = r["s"]
            if s in _seenm:
                continue
            _seenm.add(s)
            c = hist.get(s) or {}
            if ((c.get("avg") or 0) >= 100000 and r["last"] >= 200.0
                    and (r["last"] - r["op"]) >= 1.5 and len(micro) < 40):
                micro.append({"s": s, "px": round(r["last"], 1),
                              "avg20": c.get("avg") or 0, "p5": c.get("p5"),
                              "pc": c.get("pc")})
        for x in micro:
            k = uni.get(x["s"]) or ""
            if not k:
                continue
            try:
                rq = urllib.request.Request(
                    f"https://api.upstox.com/v2/historical-candle/intraday/{k}/1minute",
                    headers={"Accept": "application/json", "User-Agent": UP_UA,
                             "Authorization": f"Bearer {tok}"})
                cd = _up_closed(((_json.loads(urllib.request.urlopen(rq, timeout=10)
                                   .read().decode("utf-8")) or {}).get("data") or {}).get("candles") or [])
                if not cd and _sess_d:        # 🌙 v2 EMPTY (overnight/holiday/lag): pull
                    #    the last session via v3. Young 1–14-candle stocks
                    #    during the live opening are NOT overwritten —
                    #    they stay visible (fallback was wiping them).
                    try:                       #    NEW day (empty) — pull the last
                        _sd = _sess_d          #    session's candles via v3
                        _pv = (datetime.strptime(_sd, "%Y-%m-%d") - _dtd(days=1)).strftime("%Y-%m-%d")
                        for _f in (_sd, _pv):
                            try:
                                rq3 = urllib.request.Request(
                                    f"https://api.upstox.com/v3/historical-candle/{k}/minutes/1/{_sd}/{_f}",
                                    headers={"Accept": "application/json", "User-Agent": UP_UA,
                                             "Authorization": f"Bearer {tok}"})
                                _c3 = ((_json.loads(urllib.request.urlopen(rq3, timeout=10)
                                                   .read().decode("utf-8")) or {}).get("data") or {}).get("candles") or []
                                cd = [c for c in _c3 if str(c[0])[:10] == _sd]
                                if len(cd) >= 15:
                                    break
                            except Exception:
                                cd = []
                    except Exception:
                        cd = []
                _intra_ok[x["s"]] = len(cd) >= 1        # 🚫 intraday data present? (≥1 candle =
                    #    trading — 15 candles are needed only for cross math,
                    #    so young stocks STAY visible during the opening)
                if len(cd) >= 15:
                    cd = cd[::-1]
                    if x.get("pc"):
                        x["chg"] = round((x["px"] / x["pc"] - 1) * 100, 2)
                    for i in range(30, len(cd) - 1):
                        _lvl = max(float(c[2]) for c in cd[i - 30:i])   # 30-min ceiling
                        _brk = float(cd[i][4])
                        _vol_ok = True
                        try:
                            _avg30 = (sum(float(c[5]) for c in cd[i - 30:i]) / 30.0) or 1.0
                            _vol_ok = float(cd[i][5]) >= 1.2 * _avg30
                        except Exception:
                            pass
                        if (_brk >= _lvl + 0.5 and float(cd[i + 1][4]) >= _lvl + 0.5
                                and _vol_ok):
                            x["brk_t"] = cd[i][0][11:16]
                            x["brk_lvl"] = round(_lvl, 1)
                            x["brk_px"] = round(_brk, 1)
                            try:
                                # 📊 SNIPER info line (2-4 Nov study: indicator
                                #    GATES hurt hit-rate; shown as info, never
                                #    gating). RSI-14 (simple) · VWAP gap ·
                                #    break-volume ratio vs prior 30 min.
                                _cl = [float(c[4]) for c in cd[:i + 1]]
                                _vv = [float(c[5]) for c in cd[:i + 1]]
                                _tp = [((float(c[2]) + float(c[3]) + float(c[4])) / 3.0)
                                       for c in cd[:i + 1]]
                                _ag = sum(max(_cl[_j] - _cl[_j - 1], 0.0)
                                          for _j in range(len(_cl) - 14, len(_cl))) / 14.0
                                _al = sum(max(_cl[_j - 1] - _cl[_j], 0.0)
                                          for _j in range(len(_cl) - 14, len(_cl))) / 14.0
                                x["sn_rsi"] = round(100.0 if _al <= 0 else
                                                    100 - 100 / (1 + _ag / _al), 0)
                                _vs = sum(_t * _v for _t, _v in zip(_tp, _vv))
                                if _vs > 0 and sum(_vv) > 0:
                                    x["sn_vw"] = round((_brk / (_vs / sum(_vv)) - 1) * 100, 1)
                                try:
                                    if _avg30:
                                        x["sn_vr"] = round(float(cd[i][5]) / _avg30, 1)
                                except Exception:
                                    pass
                            except Exception:
                                pass
                            break
                time.sleep(0.06)
            except Exception:
                continue
        # merge cross info onto display rows (for the 🚀 chips)
        _cmap = {x["s"]: x for x in cand if x.get("cross")}
        for r in rows:
            _cx = _cmap.get(r["s"])
            if _cx:
                r["cross"] = _cx["cross"]
                r["cross_px"] = _cx.get("cross_px")
                r["rmove"] = _cx.get("rmove")
                r["gap"] = _cx.get("gap")
                r["pace"] = _cx.get("pace")
        # 🚫 INTRADAY-VERIFIED (user request 29 Sep): a mover whose intraday
        #    data was checked and MISSING (not trading / suspended today) is
        #    removed from the tab — you cannot trade it intraday. Unchecked
        #    stocks are kept (no evidence either way).
        rows = [r for r in rows if _intra_ok.get(r["s"], True)]
        # ── 💎 PREMIUM display rows — ₹1000–3000, its own list, same filters ──
        premdisp = sorted([r for r in rank if PREM_MIN < r["last"] <= PREM_MAX],
                          key=lambda r: -r["fo"])[:30]
        prows = []
        for r in premdisp:
            s = r["s"]
            c = hist.get(s) or {}
            try:
                chg = (r["last"] / c["pc"] - 1) * 100 if c.get("pc") else r["fo"] * 100
            except Exception:
                chg = r["fo"] * 100
            prows.append({"s": s, "px": round(r["last"], 1), "chg": round(chg, 2),
                          "avg20": (c.get("avg") or 0), "p5": c.get("p5"),
                          "curated": s in cur, "listed": True if usearch is None else s in usearch})
        prows = [x for x in prows if x["chg"] >= 2.0
                 and (x["avg20"] or 0) >= 100000][:20]
        _pmap = {x["s"]: x for x in candp if x.get("cross")}
        for r in prows:
            _px = _pmap.get(r["s"])
            if _px:
                r["cross"] = _px["cross"]
                r["cross_px"] = _px.get("cross_px")
                r["rmove"] = _px.get("rmove")
                r["gap"] = _px.get("gap")
        prows = [r for r in prows if _intra_ok.get(r["s"], True)]
        # ── 📲 ALERTS — market hours only, one ping per stock per day,
        #    fresh/recency-checked (≤12 min), deduped + persisted ──
        try:
            _n = now_ist()
            _mkt = ((9 * 60 + 15) <= (_n.hour * 60 + _n.minute) <= (15 * 60 + 20)
                    and _n.weekday() < 5)
        except Exception:
            _mkt = False
        if _mkt and tg:
            try:
                _ha = rt_load().get("hotalerts") or {}
                if _ha.get("day") != today:
                    _ha = {"day": today, "syms": {}, "d2u": {}, "micro": {}}
                _ha.setdefault("syms", {})
                _ha.setdefault("d2u", {})
                _ha.setdefault("micro", {})
                _nowm = _n.hour * 60 + _n.minute
                # ── ⏪ CATCH-UP WINDOW (user request 11 Oct: "tab closes by
                #    itself → app sleeps → picks are missed"). If the last
                #    successful sweep stamp is stale (>10 min) or from a
                #    previous day, the app was OFF — reach freshness back to
                #    the gap start so picks that fired while it slept still
                #    ping, marked ⏪ with their REAL time (≤90 min back; only
                #    this day's candles are ever scanned, and one-ping-per-
                #    stock dedupe makes replays safe). ──
                _gap_from = None
                try:
                    _sw = float(((rt_load().get("hot") or {}).get("sw")) or 0)
                    if _sw <= 0:
                        _gap_from = None     # 🆕 FRESH START (user 21 Oct: "whenever
                                            # I upload new program it starts fresh —
                                            # suppose I start at 10, THAT is where the
                                            # market analysis should start"). No sweep
                                            # stamp = new runtime: analysis begins NOW;
                                            # the 09:15+ morning is NOT replayed (was:
                                            # replay from 09:15 → a wall of stale ⏪
                                            # catch-ups right after every deploy)
                    else:
                        _age = time.time() - _sw
                        if _age > 600:                       # >10 min stale
                            _sdt = now_ist() - _dtd(seconds=_age)
                            if _sdt.strftime("%Y-%m-%d") != today:
                                _gap_from = None             # last sweep on a previous
                                                            # day → fresh day start →
                                                            # same rule: begin from now
                            else:
                                _gap_from = max(9 * 60 + 15,
                                                _sdt.hour * 60 + _sdt.minute - 1)
                                                            # in-session tab-sleep:
                                                            # ⏪ catch-up STAYS ON (the
                                                            # 11 Oct "tab closes by
                                                            # itself" fix is untouched)
                    if _gap_from is not None:
                        _gap_from = max(_gap_from, _nowm - 90)   # replay ≤ 90 min
                        if _gap_from > _nowm - 12:
                            _gap_from = None                    # window adds nothing
                except Exception:
                    _gap_from = None
                _rg = None
                try:
                    _rg = nifty_regime()
                except Exception:
                    _rg = None
                # NIFTY MORNING ROADMAP (user 25 Oct B): one 09:15 message
                _nifty_roadmap(_rg)
                # ── 🔔 FOLLOW-UPS on today's earlier alerts — ONE per stock:
                #    ✅ +2% reached → book profit · ⚠️ back below the alert
                #    price → the move is failing, tighten/exit. ──
                for _s, _rec in list(_ha["syms"].items()):
                    if not (isinstance(_rec, dict) and _rec.get("px") and not _rec.get("done")):
                        continue        # old-format record or follow-up already sent
                    try:
                        _q = Q.get(_s) or {}
                        _last = float(_q.get("last_price")
                                      or ((_q.get("ohlc") or {}).get("close")) or 0)
                    except Exception:
                        _last = 0.0
                    if _last <= 0:
                        continue
                    _ap = float(_rec["px"])
                    _nm2 = _esc(_s.replace(".NS", ""))
                    _pmt = "💎 PREMIUM " if _rec.get("prem") else ""
                    try:
                        if _last >= _ap * 1.02:
                            if tg_send(f"✅ <b>{_pmt}HOT ALERT +2% · {_nm2}</b> · {_hot_badge(_ha, _s, _last)}\n"
                                       f"₹{_last:.1f} — target reached (alert was "
                                       f"₹{_ap:.1f} at {_rec.get('t', '?')}).\n"
                                       "Book profit or trail your stop loss."):
                                _rec["done"] = "tgt"
                                _rec["done_t"] = now_ist().strftime("%H:%M")
                                rt_save("hotalerts", **_ha)
                        elif _last < _ap * 0.997:
                            # 🧊 CALM FADES (user "FIX ALL" 13 Oct): a single dip
                            #    NEVER warns — the dip must still be there on a
                            #    later sweep (≥5 min after first sighting), and no
                            #    warnings inside 5 min of the alert itself. Most
                            #    shakeouts recover (measured 13 Oct: 11 of 11 did).
                            try:
                                _am = (int(str(_rec.get("t", "09:00"))[:2]) * 60
                                       + int(str(_rec.get("t", "09:00"))[3:5]))
                            except Exception:
                                _am = 0
                            if _nowm - _am >= 5:
                                if _rec.get("warn") is None:
                                    _rec["warn"] = _nowm          # first sight — hold
                                elif _nowm - int(_rec.get("warn") or 0) >= 5:
                                    if tg_send(f"⚠️ <b>{_pmt}HOT ALERT FADING · {_nm2}</b> · {_hot_badge(_ha, _s, 0)}\n"
                                               f"₹{_last:.1f} — still below the alert price "
                                               f"₹{_ap:.1f} (alerted {_rec.get('t', '?')}, dipping "
                                               f"{_nowm - int(_rec.get('warn') or 0)} min).\n"
                                               "The move is failing — tighten or exit."):
                                        _rec["done"] = "fade"
                                        _rec["done_t"] = now_ist().strftime("%H:%M")
                                        rt_save("hotalerts", **_ha)
                        else:
                            if _rec.get("warn") is not None:
                                _rec["warn"] = None                # recovered — calm restored
                    except Exception:
                        pass
                # ── ⚡ RE-IGNITION watch (user GO 23 Oct — the SSWL fix):
                #    faded alerts crossing back above their alert price ──
                _reignition_check(Q, _ha)
                # 💰 MICRO follow-ups — the ₹3–4 scorekeeper: ✅ +₹3.5 done /
                #    ⚠️ back below the entry. One per stock per day.
                for _s, _rec in list((_ha.get("micro") or {}).items()):
                    if not (isinstance(_rec, dict) and _rec.get("px") and not _rec.get("done")):
                        continue
                    try:
                        _q = Q.get(_s) or {}
                        _last = float(_q.get("last_price")
                                      or ((_q.get("ohlc") or {}).get("close")) or 0)
                    except Exception:
                        _last = 0.0
                    if _last <= 0:
                        continue
                    _ap = float(_rec["px"])
                    _nm3 = _esc(_s.replace(".NS", ""))
                    try:
                        if _last >= _ap + 3.5:
                            if tg_send(f"\u2705 <b>SNIPER \u20B93\u20134 DONE \u00b7 {_nm3}</b> \u00b7 {_hot_badge(_ha, _s, _last)}\n\n"
                                       f"\U0001F3AF <b>TARGET HIT</b> \u2192 <code>\u20B9 {_last:.1f}</code>  "
                                       f"(+\u20B9{_last - _ap:.1f})\n"
                                       f"\U0001F7E2 entry was \u20B9{_ap:.1f} at {_rec.get('t', '?')}\n\n"
                                       "Day's target met \u2014 book it. Small and steady wins."):
                                _rec["done"] = "tgt"
                                _rec["done_t"] = now_ist().strftime("%H:%M")
                                rt_save("hotalerts", **_ha)
                        elif _last < float(_rec.get("lvl") or (_ap - 1.5)):
                            if tg_send(f"\u26A0\uFE0F <b>SETUP FAILED \u00b7 {_nm3}</b> \u00b7 {_hot_badge(_ha, _s, 0)}\n\n"
                                       f"\U0001F534 <b>BELOW EXIT</b> \u2192 <code>\u20B9 {_last:.1f}</code>\n"
                                       f"\U0001F7E2 entry \u20B9{_ap:.1f} \u00b7 exit line was "
                                       f"\u20B9{(_rec.get('lvl') or _ap):.1f}\n\n"
                                       "Exit \u2014 the breakout has failed."):
                                _rec["done"] = "fade"
                                _rec["done_t"] = now_ist().strftime("%H:%M")
                                rt_save("hotalerts", **_ha)
                    except Exception:
                        pass
                # ── 🔄 D2U FOLLOW-UPS (user request 13 Oct "tune down-to-up"):
                #    give every recovery ping its verdict — ✅ +2% above the
                #    bounce = worked · ⚠️ back below the day low = failed.
                #    Measured 13 Oct: 15/18 closed above bounce, 0 new lows —
                #    this adds closure, not noise (no entry-rule change: every
                #    stricter variant tested was worse). ──
                for _s, _rec in list((_ha.get("d2u") or {}).items()):
                    if not (isinstance(_rec, dict) and _rec.get("bp") and not _rec.get("done")):
                        continue        # old-format record (plain time) — skip
                    try:
                        _q = Q.get(_s) or {}
                        _last = float(_q.get("last_price")
                                      or ((_q.get("ohlc") or {}).get("close")) or 0)
                    except Exception:
                        _last = 0.0
                    if _last <= 0:
                        continue
                    _bp = float(_rec["bp"])
                    _lo = float(_rec.get("lo") or 0)
                    _nm4 = _esc(_s.replace(".NS", ""))
                    try:
                        if _last >= _bp * 1.02:
                            if tg_send(f"✅ <b>DOWN-TO-UP +2% · {_nm4}</b> · {_hot_badge(_ha, _s, _last)}\n"
                                       f"₹{_last:.1f} — recovery worked (bounce was "
                                       f"₹{_bp:.1f} at {_rec.get('t', '?')}).\n"
                                       "Book profit or trail your stop loss."):
                                _rec["done"] = "tgt"
                                _rec["done_t"] = now_ist().strftime("%H:%M")
                                rt_save("hotalerts", **_ha)
                        elif _lo > 0 and _last < _lo:
                            if tg_send(f"⚠️ <b>DOWN-TO-UP FAILED · {_nm4}</b> · {_hot_badge(_ha, _s, 0)}\n"
                                       f"₹{_last:.1f} — back below the day low ₹{_lo:.1f} "
                                       f"(bounce was ₹{_bp:.1f} at {_rec.get('t', '?')}).\n"
                                       "The recovery failed — exit, don't wait."):
                                _rec["done"] = "fade"
                                _rec["done_t"] = now_ist().strftime("%H:%M")
                                rt_save("hotalerts", **_ha)
                    except Exception:
                        pass
                # ── 🌅 OPENING WINDOW (user request 12 Oct): 09:15–09:29 the
                #    1-min candles are too young for cross math — ping ₹-movers
                #    DIRECTLY from the live sweep: up ≥₹3 from open, liquid,
                #    gap <4%, zero delay, first sweep after open. From 09:30
                #    the normal candle-confirmed engine takes over. ──
                if _nowm < 9 * 60 + 30:
                    for x in cand:
                        try:
                            if x["s"] in _ha["syms"]:
                                continue
                            _g = ((x["op"] / x["pc"] - 1) * 100) if x.get("pc") else 0.0
                            if _g >= 4.0:
                                continue          # gap-up trap filter stays ON
                            if not x.get("c2"):
                                continue          # 🧊 2 candle-closes must be held (13 Oct)
                            _nm0 = _esc(x["s"].replace(".NS", ""))
                            _msg = (f"🚀 <b>HOT ALERT · {_nm0}</b> · {_hot_badge(_ha, x['s'], x['px'])}\n"
                                    f"🌅 opening mover · 2 candle-closes held — live now\n"
                                    f"₹{x['px']:.1f} · +₹{x['px'] - x['op']:.1f} from open"
                                    + (f" ({(x['px'] / x['pc'] - 1) * 100:+.1f}% today)"
                                       if x.get("pc") else "") + "\n"
                                    + (f"📈 past week: {x['p5']:+.1f}%\n"
                                       if x.get("p5") is not None else "")
                                    + (((f"{_rg['ico']} NIFTY {_rg['chg']:+.2f}% today" + ((f" \u00b7 last 15 min: "
                                       + ("rising \U0001F4C8" if (_rg.get("mom") or 0) > 5
                                          else ("falling \U0001F4C9" if (_rg.get("mom") or 0) < -5 else "flat"))
                                       + "\n") if _rg.get("mom") else "\n"))) if _rg else "")
                                    + _c5_block(x)
                                    + _sr_levels(x["s"], uni, tok, hist, x["px"])
                                    + "⚠️ Fresh mover — NOT a combo pick · higher risk · use your stop loss")
                            if tg_send(_msg):
                                _ha["syms"][x["s"]] = {"t": now_ist().strftime("%H:%M"),
                                                       "px": x["px"], "ow": 1}
                                rt_save("hotalerts", **_ha)
                        except Exception:
                            pass
                    for x in candp:         # 💎 premium ₹1000–3000 — opening window
                        try:
                            if x["s"] in _ha["syms"]:
                                continue
                            _g = ((x["op"] / x["pc"] - 1) * 100) if x.get("pc") else 0.0
                            if _g >= 4.0:
                                continue          # gap-up trap filter stays ON
                            if not x.get("c2"):
                                continue          # 🧊 2 candle-closes must be held (13 Oct)
                            _nm0 = _esc(x["s"].replace(".NS", ""))
                            _msg = (f"💎 <b>PREMIUM HOT ALERT · {_nm0}</b> · {_hot_badge(_ha, x['s'], x['px'])}\n"
                                    f"🌅 opening mover · ₹1000–3000 band · 2 closes held — live now\n"
                                    f"₹{x['px']:.1f} · +₹{x['px'] - x['op']:.1f} from open"
                                    + (f" ({(x['px'] / x['pc'] - 1) * 100:+.1f}% today)"
                                       if x.get("pc") else "") + "\n"
                                    + (f"📈 past week: {x['p5']:+.1f}%\n"
                                       if x.get("p5") is not None else "")
                                + (((f"{_rg['ico']} NIFTY {_rg['chg']:+.2f}% today" + ((f" \u00b7 last 15 min: "
                                       + ("rising \U0001F4C8" if (_rg.get("mom") or 0) > 5
                                          else ("falling \U0001F4C9" if (_rg.get("mom") or 0) < -5 else "flat"))
                                       + "\n") if _rg.get("mom") else "\n"))) if _rg else "")
                                + _c5_block(x)
                                + _sr_levels(x["s"], uni, tok, hist, x["px"])
                                + "⚠️ Premium band — bigger rupees at risk · NOT a combo pick · use your stop loss")
                            if tg_send(_msg):
                                _ha["syms"][x["s"]] = {"t": now_ist().strftime("%H:%M"),
                                                       "px": x["px"], "ow": 1, "prem": 1}
                                rt_save("hotalerts", **_ha)
                        except Exception:
                            pass
                for x in cand:          # 🚀 fresh ₹-movers
                    try:
                        _xm = int(x["cross"][:2]) * 60 + int(x["cross"][3:])
                    except Exception:
                        _xm = -1
                    _det = max(_xm, 9 * 60 + 30)      # 🌅 opening wave: 1-min scan needs 15
                    _cu = (_gap_from is not None      # candles → earliest POSSIBLE detection 09:30
                           and _gap_from <= _det <= _nowm - 12)   # ⏪ missed while undetectable/off
                    _fresh = ((0 <= _nowm - _det <= 12) or _cu)   # fresh from first sight OR catch-up
                    if (x.get("cross") and _fresh and (x.get("gap") or 0) < 4.0
                            and x["s"] not in _ha["syms"]):
                        _msg = (f"🚀 <b>HOT ALERT · {_esc(x['s'].replace('.NS', ''))}</b> · {_hot_badge(_ha, x['s'], x['px'])}\n"
                                + (f"⏪ <i>catch-up · app was off — move started "
                                   f"{x['cross']} ({_nowm - _xm} min ago)</i>\n" if _cu else "")
                                + f"₹{x['px']:.1f} · +₹{x.get('rmove') or 0:.1f} from open"
                                + (f" ({x['chg']:+.1f}% today)" if x.get("chg") is not None else "")
                                + "\n"
                                f"started moving {x['cross']} @ ₹{x.get('cross_px') or x['px']:.1f}\n"
                                + f"🎯 dip toward ₹{x.get('cross_px') or x['px']:.1f} = safer entry — don't chase the green candle\n"
                                + _c5_block(x)
                                + _sr_levels(x["s"], uni, tok, hist, x["px"])
                                + (f"💧 volume {x['pace']:.1f}× normal pace\n"
                                   if x.get("pace") else "")
                                + (f"📈 past week: {x['p5']:+.1f}%\n"
                                   if x.get("p5") is not None else "")
                                + (((f"{_rg['ico']} NIFTY {_rg['chg']:+.2f}% today" + ((f" \u00b7 last 15 min: "
                                       + ("rising \U0001F4C8" if (_rg.get("mom") or 0) > 5
                                          else ("falling \U0001F4C9" if (_rg.get("mom") or 0) < -5 else "flat"))
                                       + "\n") if _rg.get("mom") else "\n"))) if _rg else "")
                                + "⚠️ Fresh mover — NOT a combo pick · use your stop loss")
                        try:
                            if tg_send(_msg):
                                _ha["syms"][x["s"]] = {"t": x["cross"],   # REAL event time
                                                       "px": (x.get("cross_px") or x["px"]),
                                                       **({"cu": 1} if _cu else {})}
                                rt_save("hotalerts", **_ha)   # persist NOW — restart-safe
                        except Exception:
                            pass
                for x in candp:         # 💎 premium ₹1000–3000 movers (post-09:30)
                    try:
                        _xm = int(x["cross"][:2]) * 60 + int(x["cross"][3:])
                    except Exception:
                        _xm = -1
                    _det = max(_xm, 9 * 60 + 30)   # same opening-wave detection rule
                    _cu = (_gap_from is not None
                           and _gap_from <= _det <= _nowm - 12)
                    _fresh = ((0 <= _nowm - _det <= 12) or _cu)
                    if (x.get("cross") and _fresh and (x.get("gap") or 0) < 4.0
                            and x["s"] not in _ha["syms"]):
                        _msg = (f"💎 <b>PREMIUM HOT ALERT · {_esc(x['s'].replace('.NS', ''))}</b> · {_hot_badge(_ha, x['s'], x['px'])}\n"
                                + (f"⏪ <i>catch-up · app was off — move started "
                                   f"{x['cross']} ({_nowm - _xm} min ago)</i>\n" if _cu else "")
                                + f"₹{x['px']:.1f} · +₹{x.get('rmove') or 0:.1f} from open"
                                + (f" ({x['chg']:+.1f}% today)" if x.get("chg") is not None else "")
                                + "\n"
                                f"started moving {x['cross']} @ ₹{x.get('cross_px') or x['px']:.1f}\n"
                                + f"🎯 dip toward ₹{x.get('cross_px') or x['px']:.1f} = safer entry — don't chase the green candle\n"
                                + _c5_block(x)
                                + _sr_levels(x["s"], uni, tok, hist, x["px"])
                                + (f"📈 past week: {x['p5']:+.1f}%\n"
                                   if x.get("p5") is not None else "")
                                + (((f"{_rg['ico']} NIFTY {_rg['chg']:+.2f}% today" + ((f" \u00b7 last 15 min: "
                                       + ("rising \U0001F4C8" if (_rg.get("mom") or 0) > 5
                                          else ("falling \U0001F4C9" if (_rg.get("mom") or 0) < -5 else "flat"))
                                       + "\n") if _rg.get("mom") else "\n"))) if _rg else "")
                                + "⚠️ ₹1000–3000 band · bigger rupees at risk · NOT a combo pick · use your stop loss")
                        try:
                            if tg_send(_msg):
                                _ha["syms"][x["s"]] = {"t": x["cross"],
                                                       "px": (x.get("cross_px") or x["px"]),
                                                       **({"cu": 1} if _cu else {}), "prem": 1}
                                rt_save("hotalerts", **_ha)
                        except Exception:
                            pass
                for x in d2u:           # 🔄 down-to-up recoveries
                    try:
                        _bm = int(x["b_t"][:2]) * 60 + int(x["b_t"][3:])
                    except Exception:
                        _bm = -1
                    _det = max(_bm, 9 * 60 + 30)      # 🌅 opening wave: same 15-candle rule —
                    _cu = (_gap_from is not None      # early bounces undetectable before 09:30
                           and _gap_from <= _det <= _nowm - 12)   # ⏪ missed while undetectable/off
                    _fresh = ((0 <= _nowm - _det <= 12) or _cu)   # fresh from first sight OR catch-up
                    if (x.get("b_t") and _fresh and x["s"] not in _ha["d2u"]):
                        _mom = x.get("now")               # honest momentum emoji (23 Oct
                        _mom_s = ("" if _mom is None else   # fix: was ALWAYS green even on -Rs)
                                  (f"🟢 +₹{_mom:.1f} in the last 15 min\n" if _mom > 0.2 else
                                   (f"🔴 −₹{abs(_mom):.1f} in the last 15 min\n" if _mom < -0.2 else
                                    "➖ flat (15 min)\n")))
                        _msg = (f"🔄 <b>DOWN-TO-UP · {_esc(x['s'].replace('.NS', ''))}</b> · {_hot_badge(_ha, x['s'], x['px'])}\n"
                                + (f"⏪ <i>catch-up · app was off — bounce at "
                                   f"{x['b_t']} ({_nowm - _bm} min ago)</i>\n" if _cu else "")
                                + f"₹{x['px']:.1f} · fell ₹{x['dip']:.1f} below open to ₹{x['lo']:.1f}\n"
                                f"now +₹{x['bnc']:.1f} off the low · recovering since {x['b_t']}"
                                f" @ ₹{x.get('b_px') or x['px']:.1f}\n"
                                + _mom_s
                                + (f"💧 volume {x['pace']:.1f}× normal pace\n"
                                   if x.get("pace") else "")
                                + (f"📈 past week: {x['p5']:+.1f}%\n"
                                   if x.get("p5") is not None else "")
                                + (((f"{_rg['ico']} NIFTY {_rg['chg']:+.2f}% today" + ((f" \u00b7 last 15 min: "
                                       + ("rising \U0001F4C8" if (_rg.get("mom") or 0) > 5
                                          else ("falling \U0001F4C9" if (_rg.get("mom") or 0) < -5 else "flat"))
                                       + "\n") if _rg.get("mom") else "\n"))) if _rg else "")
                                + "⚠️ Recovery attempt — bounces can fail · NOT a combo pick · use your stop loss")
                        try:
                            if tg_send(_msg):
                                _ha["d2u"][x["s"]] = {"t": x["b_t"],        # REAL event time
                                                      "bp": (x.get("b_px") or x["px"]),
                                                      "lo": x.get("lo") or x["px"]}
                                rt_save("hotalerts", **_ha)
                        except Exception:
                            pass
                # ── 🔥 BIG-MOVER NET (user 15 Oct: "RACE +20% never pinged —
                #    we should not miss that"). Two ways in, ONE label:
                #    (a) 🟢 GREEN-CANDLE UPTREND (user 15 Oct night: "uptrend
                #        stock based candle, stock full of green candle will
                #        form — those also take"): 6 consecutive GREEN 1-min
                #        candles + up from open = steady climb BUILDING —
                #        caught during the build, not after the fact.
                #    (b) ≥4% above TODAY'S OPEN — for runners whose climb
                #        wasn't 6 straight greens (choppy climbers).
                #    Main band ₹100–1000, liquid, never pinged, gap-filter on,
                #    first 12 per day. Honest label — don't chase it. ──
                try:
                    # 🔥 never fires before 09:30 — the opening window's
                    # 2-candle 🚀 confirm owns 09:15–09:30 (user's own
                    # "give it 2 min" rule, measured −70% fakes on 1-tick)
                    _big_n = (999 if _nowm < 9 * 60 + 30 else
                              sum(1 for v in _ha["syms"].values()
                                  if isinstance(v, dict) and v.get("big")))
                    # ── 🚫 RED-MARKET GATE (user 20 Oct: "after the message
                    #    it goes down" — Monday red day 3/3 🔥 died; no 🔥
                    #    when NIFTY ≤ −0.50% vs prev close. AUDITABLE: skips
                    #    logged to rt 'fireskipped' + shown on the tab) ──
                    _fr_ok = not (_rg and float(_rg.get("chg") or 0) <= -0.50)

                    def _fskip(_s, _why):
                        try:
                            _fs = rt_load().get("fireskipped") or {}
                            _td = now_ist().strftime("%Y-%m-%d")
                            if _fs.get("day") != _td:
                                _fs = {"day": _td, "m": {}}
                            if _s not in _fs["m"] and len(_fs["m"]) < 40:
                                _fs["m"][_s] = {"t": now_ist().strftime("%H:%M"), "r": _why}
                                rt_save("fireskipped", **_fs)
                        except Exception:
                            pass
                    # ── (a) 🟢 green-candle uptrend: un-pinged ₹100–1000
                    #    movers ≥1% above open, top-12 by % this sweep ──
                    if 0 <= _big_n < 20:
                        _ug = []
                        for r in rank:
                            try:
                                if (MIN_PRICE <= r["last"] <= MAX_PRICE
                                        and r["fo"] >= 0.01
                                        and r["s"] not in _ha["syms"]
                                        and ((hist.get(r["s"]) or {}).get("avg") or 0) >= 100000):
                                    _ug.append(r)
                            except Exception:
                                continue
                        _ug.sort(key=lambda r: -r["fo"])
                        for r in _ug[:12]:
                            if _big_n >= 20:
                                break
                            _k2 = uni.get(r["s"]) or ""
                            if not _k2:
                                continue
                            try:
                                rq2 = urllib.request.Request(
                                    f"https://api.upstox.com/v2/historical-candle/intraday/{_k2}/1minute",
                                    headers={"Accept": "application/json", "User-Agent": UP_UA,
                                             "Authorization": f"Bearer {tok}"})
                                cd2 = _up_closed(((_json.loads(urllib.request.urlopen(rq2, timeout=10)
                                                    .read().decode("utf-8")) or {}).get("data") or {}).get("candles") or [])
                                if len(cd2) >= 6:
                                    cd2 = cd2[::-1]             # oldest first
                                    _op2 = float(cd2[0][1])
                                    _g6 = all(float(c[4]) > float(c[1]) for c in cd2[-6:])
                                    # 🔍 QUALITY (user 20 Oct): staircase must
                                    # have real VOLUME (≥1.5× the day's earlier
                                    # pace) and strong bodies (≥5 of 6 candles
                                    # close in the upper half of their range —
                                    # long upper wicks = exhaustion, not entry)
                                    _q6 = cd2[-6:]
                                    _pr6 = cd2[:-6]
                                    _volok = True
                                    _vr = 0.0
                                    if len(_pr6) >= 5:
                                        try:
                                            _pv = sum(float(c[5]) for c in _pr6) / len(_pr6)
                                            _v6 = sum(float(c[5]) for c in _q6) / 6.0
                                            _volok = (not _pv) or _v6 >= 1.5 * _pv
                                            _vr = (_v6 / _pv) if _pv else 0.0
                                        except Exception:
                                            _volok = True
                                    _wk = 0
                                    for c in _q6:
                                        try:
                                            _hh, _ll, _cc = float(c[2]), float(c[3]), float(c[4])
                                            _wk += 1 if (_hh <= _ll) or ((_cc - _ll) / (_hh - _ll)) >= 0.5 else 0
                                        except Exception:
                                            _wk += 1
                                    _g6 = _g6 and _volok and _wk >= 5
                                    if _g6 and r["last"] >= _op2 + max(1.5, 0.005 * _op2):
                                        _pc3 = (hist.get(r["s"]) or {}).get("pc")
                                        if _pc3 and (_op2 / _pc3 - 1) * 100 >= 4.0:
                                            pass                # gap-up trap stays ON
                                        elif not _fr_ok:
                                            _fskip(r["s"], "red")
                                        else:
                                            _nm6 = _esc(r["s"].replace(".NS", ""))
                                            _msg = (f"🔥 <b>BIG MOVER · {_nm6}</b> · {_hot_badge(_ha, r['s'], r['last'])}\n"
                                                    f"₹{r['last']:.1f} · +{100 * (r['last'] / r['op'] - 1):.1f}% "
                                                    f"above today's open ₹{r['op']:.1f}\n"
                                                    "🟢 6 green candles in a row — steady uptrend building\n"
                                                    + (f"💧 staircase volume {_vr:.1f}× normal pace\n" if _vr else "")
                                                    + f"🎯 don't chase — a dip toward ₹{r['op'] * 1.02:.1f} "
                                                      f"(open +2%) is the safer entry\n"
                                                    + (((f"{_rg['ico']} NIFTY {_rg['chg']:+.2f}% today" + ((f" \u00b7 last 15 min: "
                                       + ("rising \U0001F4C8" if (_rg.get("mom") or 0) > 5
                                          else ("falling \U0001F4C9" if (_rg.get("mom") or 0) < -5 else "flat"))
                                       + "\n") if _rg.get("mom") else "\n"))) if _rg else "")
                                                    + "⚠️ Uptrend alert — NOT a fresh entry · NOT a combo pick · use your stop loss")
                                            try:
                                                if tg_send(_msg):
                                                    _ha["syms"][r["s"]] = {"t": now_ist().strftime("%H:%M"),
                                                                           "px": round(r["last"], 1),
                                                                           "ow": 1, "big": 1}
                                                    _big_n += 1
                                                    rt_save("hotalerts", **_ha)
                                            except Exception:
                                                pass
                                time.sleep(0.06)
                            except Exception:
                                continue
                    # ── 🟢 GREEN STAIRCASE CONFIRM (user 21 Oct night: an
                    #    already-alerted stock printing next-next green
                    #    candles = the move strengthening → say so. One per
                    #    stock per day, standing 🔥 gates (09:30+, red) ──
                    _stair_confirm(rank, _ha, uni, tok, hist, _rg, _fr_ok)
                    # ── (b) ≥4% above open — choppy climbers the green rule
                    #    missed (no 6-straight-greens) ──
                    _bg = []
                    for r in rank:
                        try:
                            if (MIN_PRICE <= r["last"] <= MAX_PRICE
                                    and r["last"] >= r["op"] * 1.04
                                    and r["s"] not in _ha["syms"]
                                    and ((hist.get(r["s"]) or {}).get("avg") or 0) >= 100000):
                                _bg.append(r)
                        except Exception:
                            continue
                    _bg.sort(key=lambda r: -r["fo"])
                    for r in _bg[:15]:
                        if _big_n >= 20:
                            break
                        if not _fr_ok:
                            _fskip(r["s"], "red")
                            continue
                        _pc2 = (hist.get(r["s"]) or {}).get("pc")
                        if _pc2 and (r["op"] / _pc2 - 1) * 100 >= 4.0:
                            continue          # gap-up trap filter stays ON
                        _cc2 = (_cmap.get(r["s"]) or {}).get("cross")
                        _nm5 = _esc(r["s"].replace(".NS", ""))
                        _msg = (f"🔥 <b>BIG MOVER · {_nm5}</b> · {_hot_badge(_ha, r['s'], r['last'])}\n"
                                f"₹{r['last']:.1f} · +{100 * (r['last'] / r['op'] - 1):.1f}% "
                                f"above today's open ₹{r['op']:.1f}\n"
                                + (f"started {_cc2}\n" if _cc2 else "")
                                + f"🎯 already running — do NOT chase. A dip toward ₹{r['op'] * 1.02:.1f} "
                                  f"(open +2%) is the safer entry\n"
                                + (((f"{_rg['ico']} NIFTY {_rg['chg']:+.2f}% today" + ((f" \u00b7 last 15 min: "
                                       + ("rising \U0001F4C8" if (_rg.get("mom") or 0) > 5
                                          else ("falling \U0001F4C9" if (_rg.get("mom") or 0) < -5 else "flat"))
                                       + "\n") if _rg.get("mom") else "\n"))) if _rg else "")
                                + "⚠️ Big move alert — NOT a fresh entry · NOT a combo pick · use your stop loss")
                        try:
                            if tg_send(_msg):
                                _ha["syms"][r["s"]] = {"t": now_ist().strftime("%H:%M"),
                                                       "px": round(r["last"], 1),
                                                       "ow": 1, "big": 1}
                                _big_n += 1
                                rt_save("hotalerts", **_ha)
                        except Exception:
                            pass
                    # ── 💎 PREMIUM 🔥 (user 17 Oct: "TECHM y not came" —
                    #    ₹1000–3000 climbers were invisible: 💎 only candle-
                    #    checks the TOP-25 BY RUPEES, so on crowded mornings
                    #    a steady +₹20 climber (TECHM #15→#37) never entered
                    #    the pool. Same 🔥 rules here, premium band, shared
                    #    20/day cap, same 09:30 gate + gap-up trap.) ──
                    _ugp = []
                    for r in rank:
                        try:
                            if (PREM_MIN < r["last"] <= PREM_MAX
                                    and r["fo"] >= 0.01
                                    and r["s"] not in _ha["syms"]
                                    and ((hist.get(r["s"]) or {}).get("avg") or 0) >= 100000):
                                _ugp.append(r)
                        except Exception:
                            continue
                    _ugp.sort(key=lambda r: -r["fo"])
                    for r in _ugp[:8]:                # green-6, premium band
                        if _big_n >= 20:
                            break
                        _k3 = uni.get(r["s"]) or ""
                        if not _k3:
                            continue
                        try:
                            rq3b = urllib.request.Request(
                                f"https://api.upstox.com/v2/historical-candle/intraday/{_k3}/1minute",
                                headers={"Accept": "application/json", "User-Agent": UP_UA,
                                         "Authorization": f"Bearer {tok}"})
                            cd3 = _up_closed(((_json.loads(urllib.request.urlopen(rq3b, timeout=10)
                                                .read().decode("utf-8")) or {}).get("data") or {}).get("candles") or [])
                            if len(cd3) >= 6:
                                cd3 = cd3[::-1]           # oldest first
                                _op3 = float(cd3[0][1])
                                _g6p = all(float(c[4]) > float(c[1]) for c in cd3[-6:])
                                # 🔍 QUALITY: same volume + wick rules (premium)
                                _q6p = cd3[-6:]
                                _pr6p = cd3[:-6]
                                _volokp = True
                                _vrp = 0.0
                                if len(_pr6p) >= 5:
                                    try:
                                        _pvp = sum(float(c[5]) for c in _pr6p) / len(_pr6p)
                                        _v6p = sum(float(c[5]) for c in _q6p) / 6.0
                                        _volokp = (not _pvp) or _v6p >= 1.5 * _pvp
                                        _vrp = (_v6p / _pvp) if _pvp else 0.0
                                    except Exception:
                                        _volokp = True
                                _wkp = 0
                                for c in _q6p:
                                    try:
                                        _hhp, _llp, _ccp = float(c[2]), float(c[3]), float(c[4])
                                        _wkp += 1 if (_hhp <= _llp) or ((_ccp - _llp) / (_hhp - _llp)) >= 0.5 else 0
                                    except Exception:
                                        _wkp += 1
                                _g6p = _g6p and _volokp and _wkp >= 5
                                if _g6p and r["last"] >= _op3 + max(1.5, 0.005 * _op3):
                                    _pc4 = (hist.get(r["s"]) or {}).get("pc")
                                    if _pc4 and (_op3 / _pc4 - 1) * 100 >= 4.0:
                                        pass              # gap-up trap stays ON
                                    elif not _fr_ok:
                                        _fskip(r["s"], "red")
                                    else:
                                        _nm7 = _esc(r["s"].replace(".NS", ""))
                                        _msg = (f"🔥 <b>BIG MOVER · {_nm7} · 💎</b> · {_hot_badge(_ha, r['s'], r['last'])}\n"
                                                f"₹{r['last']:.1f} · +{100 * (r['last'] / r['op'] - 1):.1f}% "
                                                f"above today's open ₹{r['op']:.1f}\n"
                                                "🟢 6 green candles in a row — steady uptrend building\n"
                                                + (f"💧 staircase volume {_vrp:.1f}× normal pace\n" if _vrp else "")
                                                + f"🎯 don't chase — a dip toward ₹{r['op'] * 1.02:.1f} "
                                                  f"(open +2%) is the safer entry\n"
                                                + (((f"{_rg['ico']} NIFTY {_rg['chg']:+.2f}% today" + ((f" \u00b7 last 15 min: "
                                       + ("rising \U0001F4C8" if (_rg.get("mom") or 0) > 5
                                          else ("falling \U0001F4C9" if (_rg.get("mom") or 0) < -5 else "flat"))
                                       + "\n") if _rg.get("mom") else "\n"))) if _rg else "")
                                                + "⚠️ ₹1000–3000 band — bigger rupees at risk · NOT a fresh entry · "
                                                  "NOT a combo pick · use your stop loss")
                                        try:
                                            if tg_send(_msg):
                                                _ha["syms"][r["s"]] = {"t": now_ist().strftime("%H:%M"),
                                                                       "px": round(r["last"], 1),
                                                                       "ow": 1, "big": 1, "prem": 1}
                                                _big_n += 1
                                                rt_save("hotalerts", **_ha)
                                        except Exception:
                                            pass
                            time.sleep(0.06)
                        except Exception:
                            continue
                    _bgp = []
                    for r in rank:
                        try:
                            if (PREM_MIN < r["last"] <= PREM_MAX
                                    and r["last"] >= r["op"] * 1.04
                                    and r["s"] not in _ha["syms"]
                                    and ((hist.get(r["s"]) or {}).get("avg") or 0) >= 100000):
                                _bgp.append(r)
                        except Exception:
                            continue
                    _bgp.sort(key=lambda r: -r["fo"])
                    for r in _bgp[:10]:               # ≥4% backup, premium band
                        if _big_n >= 20:
                            break
                        if not _fr_ok:
                            _fskip(r["s"], "red")
                            continue
                        _pc5 = (hist.get(r["s"]) or {}).get("pc")
                        if _pc5 and (r["op"] / _pc5 - 1) * 100 >= 4.0:
                            continue          # gap-up trap filter stays ON
                        _cc3 = (_cmap.get(r["s"]) or {}).get("cross")
                        _nm8 = _esc(r["s"].replace(".NS", ""))
                        _msg = (f"🔥 <b>BIG MOVER · {_nm8} · 💎</b> · {_hot_badge(_ha, r['s'], r['last'])}\n"
                                f"₹{r['last']:.1f} · +{100 * (r['last'] / r['op'] - 1):.1f}% "
                                f"above today's open ₹{r['op']:.1f}\n"
                                + (f"started {_cc3}\n" if _cc3 else "")
                                + f"🎯 already running — do NOT chase. A dip toward ₹{r['op'] * 1.02:.1f} "
                                  f"(open +2%) is the safer entry\n"
                                + (((f"{_rg['ico']} NIFTY {_rg['chg']:+.2f}% today" + ((f" \u00b7 last 15 min: "
                                       + ("rising \U0001F4C8" if (_rg.get("mom") or 0) > 5
                                          else ("falling \U0001F4C9" if (_rg.get("mom") or 0) < -5 else "flat"))
                                       + "\n") if _rg.get("mom") else "\n"))) if _rg else "")
                                + "⚠️ ₹1000–3000 band — bigger rupees at risk · NOT a fresh entry · "
                                  "NOT a combo pick · use your stop loss")
                        try:
                            if tg_send(_msg):
                                _ha["syms"][r["s"]] = {"t": now_ist().strftime("%H:%M"),
                                                       "px": round(r["last"], 1),
                                                       "ow": 1, "big": 1, "prem": 1}
                                _big_n += 1
                                rt_save("hotalerts", **_ha)
                        except Exception:
                            pass
                except Exception:
                    pass
                # ── 🚫 SMART GATES (user choice C, 9 Oct study) ──
                # (A) AFTERNOON CUTOFF: no 💰 pings after 13:30 — late
                #     breakouts run out of fuel (Fri study: 53% wins in the
                #     morning, 0/1 after 13:30, and exits can't recover late).
                # (B) DEEP-RED PAUSE: NIFTY ≤ −1% at sweep time → micro pings
                #     stop + ONE clear message (Thu −1.64% day: only 7 of 24
                #     setups worked — 17 losing pings would have been skipped).
                #     If NIFTY recovers above −1%, pings resume automatically.
                try:
                    _red_pause = bool(_rg and float(_rg.get("chg") or 0) <= -1.0)
                except Exception:
                    _red_pause = False
                if _red_pause and not _ha.get("mpause"):
                    if tg_send("\u23F8\uFE0F <b>SNIPER \u20B93\u20134 SETUPS PAUSED \u00b7 DEEP RED MARKET</b>\n"
                               f"{_rg.get('ico', '\uD83D\uDD34')} NIFTY {float(_rg.get('chg') or 0):+.2f}% today\n"
                               "Breakouts fail on deep-red days (measured: 7 of 24 on the last one).\n"
                               "No more \U0001F4B0 pings today \u2014 protect capital, sit this one out. \U0001F6AB"):
                        _ha["mpause"] = True
                        rt_save("hotalerts", **_ha)
                for x in micro:          # 💰 ₹3–4 setups (30-min ceiling break)
                    try:
                        _bm = int(x["brk_t"][:2]) * 60 + int(x["brk_t"][3:])
                    except Exception:
                        _bm = -1
                    _cu = (_gap_from is not None
                           and _gap_from <= _bm <= _nowm - 12)       # ⏪ happened in the gap
                    _fresh = ((0 <= _nowm - _bm <= 12) or _cu)   # ≤12 min ago OR missed while off
                    if (x.get("brk_t") and _fresh and x["s"] not in _ha["micro"]
                            and x["s"] not in _ha["syms"]       # no double-ping: hot alert already covered it
                            and x["px"] >= (x.get("brk_lvl") or 0)   # still above the ceiling it broke
                            and 9 * 60 + 35 <= _bm <= 11 * 60  # 🎯 SNIPER: morning window only, REAL break
                                                                 #    time (2-4 Nov study: 79% hit before
                                                                 #    11:00 vs 17% after — lunch chop kills)
                            and not _red_pause):               # 🚫 B: deep-red pause
                        _sn_e = round((x.get("brk_lvl") or x["px"]) * 1.0015, 1)
                        _sn_x = round((x.get("brk_lvl") or x["px"]) * 0.999, 1)
                        _sn_t = round(_sn_e + 3.5, 1)
                        _msg = (f"\U0001F3AF <b>SNIPER \u20B93\u20134 \u00b7 {_esc(x['s'].replace('.NS', ''))}</b> \u00b7 {_hot_badge(_ha, x['s'], x['px'])}\n"
                                + (f"\u23EA <i>catch-up \u00b7 app was off \u2014 break at "
                                   f"{x['brk_t']} ({_nowm - _bm} min ago)</i>\n" if _cu else "")
                                + f"broke its 30-min ceiling \u20B9{x['brk_lvl']:.1f} at {x['brk_t']}\n\n"
                                f"\U0001F7E2 <b>BUY ZONE</b> \u2192 <code>\u20B9 {_sn_e:.1f}</code>  (ceiling +0.15%)\n"
                                f"\U0001F3AF <b>TARGET</b> \u2192 <code>\u20B9 {_sn_t:.1f}</code>  (+\u20B93.5)\n"
                                f"\U0001F534 <b>EXIT</b>   \u2192 <code>below \u20B9 {_sn_x:.1f}</code>\n"
                                f"\U0001F4CD now \u20B9{x['px']:.1f} \u2014 buy IN the zone, don\u2019t chase above it\n\n"
                                + (f"\U0001F4C8 {x['chg']:+.1f}% today \u00b7 "
                                   f"\U0001F4A7 liquid"
                                   + (f" \u00b7 week {x['p5']:+.1f}%\n" if x.get("p5") is not None else "\n")
                                   if x.get("chg") is not None else "")
                                + (f"\U0001F4CA RSI {x['sn_rsi']:.0f} \u00b7 VWAP {x['sn_vw']:+.1f}% \u00b7 break vol {x['sn_vr']:.1f}\u00d7\n"
                                   if x.get("sn_rsi") is not None else "")
                                + ("\u26A0\uFE0F spike zone \u2014 heavy-volume extension, pullback risk\n"
                                   if (x.get("sn_vr") or 0) > 8
                                   and x["px"] >= (x.get("brk_lvl") or 0) * 1.01 else "")
                                + (((f"{_rg['ico']} NIFTY {_rg['chg']:+.2f}% today" + ((f" \u00b7 last 15 min: "
                                       + ("rising \U0001F4C8" if (_rg.get("mom") or 0) > 5
                                          else ("falling \U0001F4C9" if (_rg.get("mom") or 0) < -5 else "flat"))
                                       + "\n") if _rg.get("mom") else "\n"))) if _rg else "")
                                + "\u2139\uFE0F information only \u2014 not auto-traded")
                        try:
                            if tg_send(_msg):
                                _ha["micro"][x["s"]] = {"t": x["brk_t"],        # REAL event time
                                                        "px": _sn_e,             # 🎯 buy zone = ceiling+0.15%
                                                        "lvl": _sn_x,            # 🎯 exit line = ceiling−0.1% buffer
                                                        "tgt": _sn_t,
                                                        **({"cu": 1} if _cu else {})}
                                rt_save("hotalerts", **_ha)
                        except Exception:
                            pass
                rt_save("hotalerts", **_ha)
            except Exception:
                pass
        stats = {"n": len(Q),
                 "n3": sum(1 for x in rows if x["chg"] >= 3),
                 "band_ok": sum(1 for x in rows if MIN_PRICE <= x["px"] <= MAX_PRICE),
                 "liq": sum(1 for x in rows if (x["avg20"] or 0) >= 100000),
                 "on_board": sum(1 for x in rows if x["curated"]),
                 "new_list": sum(1 for x in rows if not x["listed"]),
                 "d2u": len(d2u),
                 "micro": sum(1 for x in micro if x.get("brk_t")),
                 "prem": len(prows)}
        return {"rows": rows, "prows": prows, "candp": candp, "d2u": d2u, "micro": micro,
                "stats": stats, "ts": now_ist().strftime("%H:%M"), "day": today}
    except Exception:
        return {"err": "fail"}


def maybe_daily_scorecard():
    """📊 SELF-SCORE (user request 11 Oct): once per trading day after 15:45,
    grade every ping this app actually sent today against the real closing
    prices and push ONE Telegram report. The hot tab keeps ticking till
    16:30 so this fires ~16:00 while the page is open. One-shot per day via
    rt 'scorecard'; daily micro win-rate is kept in rt 'scorehist'."""
    try:
        _n = now_ist()
        _m = _n.hour * 60 + _n.minute
        if _n.weekday() >= 5 or not (15 * 60 + 45 <= _m <= 16 * 60 + 59):
            return
        rt = rt_load()
        today = _n.strftime("%Y-%m-%d")
        if (rt.get("scorecard") or {}).get("day") == today:
            return
        _ha = rt.get("hotalerts") or {}
        if _ha.get("day") != today:
            return                                  # alert system never ran today
        if not up_token_valid():
            return
        syms = sorted(set(list(_ha.get("syms") or {}) + list(_ha.get("micro") or {})))
        closes = {}
        if syms:
            try:
                uni = hot_universe()
                keys = [uni.get(s) for s in syms if uni.get(s)]
                for i in range(0, len(keys), 500):
                    rq = urllib.request.Request(
                        "https://api.upstox.com/v2/market-quote/ohlc?interval=1d&instrument_key="
                        + ",".join(keys[i:i + 500]),
                        headers={"Accept": "application/json", "User-Agent": UP_UA,
                                 "Authorization": f"Bearer {up_auth_token()}"})
                    data = (_json.loads(urllib.request.urlopen(rq, timeout=20)
                                        .read().decode("utf-8")) or {}).get("data") or {}
                    for k, v in data.items():
                        try:
                            closes[(k.split(":")[-1] or "") + ".NS"] = float(
                                (v or {}).get("last_price") or ((v or {}).get("ohlc") or {}).get("close") or 0)
                        except Exception:
                            pass
            except Exception:
                pass
        lines = [f"📊 <b>DAILY SCORECARD · {_n.strftime('%a %d %b')}</b> (auto self-score)"]
        try:
            _rg = nifty_regime()
            if _rg:
                lines.append(f"{_rg.get('ico')} NIFTY {float(_rg.get('chg') or 0):+.2f}% today")
        except Exception:
            pass
        # 🚀 hot alerts
        hs = _ha.get("syms") or {}
        up_n = 0
        if hs:
            lines.append("")
            lines.append(f"🚀 HOT ALERTS — {len(hs)} sent")
            for s, r in sorted(hs.items(),
                               key=lambda kv: kv[1].get("t", "?") if isinstance(kv[1], dict) else "?"):
                if not isinstance(r, dict):
                    continue
                ap = float(r.get("px") or 0)
                cl = closes.get(s)
                if ap and cl:
                    pct = (cl / ap - 1) * 100
                    up_n += 1 if cl > ap else 0
                    tag = "✅" if r.get("done") == "tgt" else "⚠️" if r.get("done") == "fade" else "⏳"
                    lines.append(f"   {tag} {'💎' if r.get('prem') else ''}"
                                 f"{_esc(s.replace('.NS', ''))} ₹{ap:.1f} → ₹{cl:.1f} ({pct:+.1f}%)")
            lines.append(f"   {up_n}/{len(hs)} closed above alert")
        # 💰 micro setups
        ms = _ha.get("micro") or {}
        _w = _f = _o = 0
        _net = 0.0
        if ms:
            for s, r in ms.items():
                if not isinstance(r, dict):
                    continue
                px = float(r.get("px") or 0)
                lvl = float(r.get("lvl") or px)
                d = r.get("done")
                cl = closes.get(s)
                if d == "tgt" or (not d and cl and px and cl >= px + 3.5):
                    _w += 1
                    _net += 3.5
                elif d == "fade":
                    _f += 1
                    _net -= max(0.0, px - lvl)
                elif cl and px and cl < lvl:
                    _f += 1
                    _net -= max(0.0, px - cl)
                else:
                    _o += 1
            lines.append("")
            lines.append(f"🎯 SNIPER ₹3–4 SETUPS — {len(ms)} pinged")
            lines.append(f"   ✅ {_w} hit target · ⚠️ {_f} exited at ceiling · ⏳ {_o} neither")
            lines.append(f"   🧮 sim net (1 share each): ₹{_net:+.1f}")
        # 🔄 down-to-up
        ds = _ha.get("d2u") or {}
        if ds:
            _dw = sum(1 for v in ds.values() if isinstance(v, dict) and v.get("done") == "tgt")
            _df = sum(1 for v in ds.values() if isinstance(v, dict) and v.get("done") == "fade")
            lines.append("")
            lines.append(f"🔄 DOWN-TO-UP — {len(ds)} recovery pings sent"
                         + (f" · ✅ {_dw} worked · ⚠️ {_df} failed" if (_dw or _df) else ""))
        if not hs and not ms and not ds:
            lines.append("")
            lines.append("Quiet day — no pings sent by this app.")
        # history line
        hist = rt.get("scorehist") or {}
        if ms:
            hist[today] = round(100.0 * _w / max(1, len(ms)), 0)
        tail = [f"{v:.0f}%" for k, v in sorted(hist.items()) if v is not None][-5:]
        if tail:
            lines.append("")
            lines.append("📚 micro win-rate, last days: " + " · ".join(tail))
        try:                                    # 🏅 v14 honest first-touch score
            hot_eval_pending(force_today=True)
            lines += hot_stats_lines(today)
        except Exception:
            pass
        lines.append("")
        lines.append("Auto-report — no action needed.")
        if tg_send("\n".join(lines)):
            rt_save("scorecard", day=today)
            if ms:
                rt_save("scorehist", **hist)
    except Exception:
        pass


def _pc_engine_running():
    """True when alert_runner.py is running on this machine (it holds a local port)."""
    try:
        import socket as _sk
        with _sk.create_connection(("127.0.0.1", 47613), timeout=0.3):
            return True
    except Exception:
        return False


def hot_movers_tab(ss):
    """🚀 Separate watch-only tab — today's whole-market spikes + exactly WHY
    each one is not on our combo board. No Telegram, no picks, no radar
    changes: pure visibility (the RAYMONDREL/ELECON blind-spot fix)."""
    try:
        st.markdown(
            "<div style='background:linear-gradient(90deg,#1a1005,#0f1a2e);border:1px solid #f59e0b55;"
            "border-radius:14px;padding:14px 18px;margin-bottom:12px;'>"
            "<div style='color:#fbbf24;font-size:20px;font-weight:900;'>🚀 HOT MOVERS — whole-market spike radar</div>"
            "<div style='color:#94a3b8;font-size:12px;margin-top:4px;'>Every NSE equity in one sweep — shown only if ₹60+, liquid (≥1L/day) and trading intraday. "
            "Finds sudden runners a trend board can never see on day one (RAYMONDREL / ELECON style) — "
            "and shows exactly WHY each one is missing from our combo board.</div></div>", unsafe_allow_html=True)
        _tg_on = st.checkbox(
            "📲 Telegram alerts — 🚀 fresh ₹-movers & 🔄 down-to-up & 💰 ₹3–4 setups (30-min break)",
            value=bool(ss.get("hot_tg", True)), key="hot_tg",
            help="One ping per stock per day, market hours only, ₹100–₹1000 band, ≥1L/day "
                 "volume. For costlier stocks the trigger scales to 1% of price (₹500 stock "
                 "→ +₹5) so big-priced noise never spams. NOT combo picks.")
        # 🏅 v14 PRECISION — minimum quality grade for NEW-entry pings
        try:
            _hc = hot_cfg()
            _cur = _hc.get("min_grade", "ALL")
            _lbl = {"ALL": "ALL alerts (grade shown on each)",
                    "A": "A and A+ only (max 1 failed check)",
                    "A+": "A+ only — every live check passes (fewest, most precise)"}
            _sel = st.selectbox(
                "🏅 Minimum alert quality (live Upstox checks: VWAP · circuit room · spread · "
                "order book · strength vs NIFTY · NIFTY mood · time)",
                HQ_GRADES, index=HQ_GRADES.index(_cur) if _cur in HQ_GRADES else 0,
                format_func=lambda g: _lbl.get(g, g), key="hot_min_grade",
                help="Suppressed alerts are still LOGGED and scored, so the table below shows "
                     "whether the filter really helps. Missing data never blocks an alert.")
            if _sel != _cur:
                rt_save("hotcfg", min_grade=_sel)
        except Exception:
            pass
        _n = now_ist()
        _mkt_open = (9 * 60 + 15) <= (_n.hour * 60 + _n.minute) <= (15 * 60 + 25) and _n.weekday() < 5
        # 🌙 evening tick: keep the page alive till 16:30 on trading days so
        #    the 16:00 SELF-SCORE report can fire (sweeps stay market-hours)
        _tick_on = ((9 * 60 + 15) <= (_n.hour * 60 + _n.minute) <= (16 * 60 + 30)
                    and _n.weekday() < 5)
        hot = ss.get("hot") or ((rt_load().get("hot") or {}).get("last"))
        # 🔥 PRE-OPEN WARM-UP ticks (09:00–09:14, user 21 Oct evening): while
        #    waiting for the open, pre-cache daily history so the first 09:15
        #    sweep is seconds — first 🚀 ~09:16 instead of ~09:18+.
        try:
            _om0 = _n.hour * 60 + _n.minute
            if _n.weekday() < 5 and 9 * 60 <= _om0 <= 9 * 60 + 14 and up_token_valid():
                from streamlit_autorefresh import st_autorefresh
                st_autorefresh(interval=2 * 60 * 1000, key="hot_warm")
                _w = _warmup_tick()
                if _w and not _w.get("err"):
                    if _w.get("fin"):
                        st.caption(f"🔥 Pre-open warm-up complete — {_w.get('done')} stocks pre-cached. "
                                   "The 09:15 first sweep will be fast.")
                    else:
                        st.caption(f"🔥 Pre-open warm-up: {_w.get('done')}/{_w.get('total')} stocks pre-cached "
                                   "(makes the 09:15 opening sweep much faster)…")
        except Exception:
            pass
        if _tick_on and up_token_valid():
            try:
                from streamlit_autorefresh import st_autorefresh
                # 🌅 faster heartbeat in the opening window (user request 12 Oct):
                #    2-min ticks 09:14–09:36 so opening movers ping with minimal
                #    delay; normal 5-min cadence the rest of the day.
                _om = _n.hour * 60 + _n.minute
                _opn = (_n.weekday() < 5 and 9 * 60 + 14 <= _om <= 9 * 60 + 36)
                # ⚡ 09:16 START (user 15 Oct: "hot mover should start 9:16 —
                #    then only we can find good one"): 1-minute cadence for the
                #    first 10 minutes so a sweep always lands just after the
                #    09:16 candle opens — the earliest moment the 2-candle
                #    confirm (09:15 close + live 09:16) can fire.
                _fast0 = (_n.weekday() < 5 and 9 * 60 + 15 <= _om <= 9 * 60 + 25)
                # ⏱ v14: screen + sweep every 2 min all day (1 min 09:15–09:25)
                st_autorefresh(interval=(1 if _fast0 else 2) * 60 * 1000,
                               key="hot_tick")
                if _mkt_open and _pc_engine_running():
                    # 🖥️ the PC alert engine is scanning + sending — this page
                    #    only SHOWS its latest results (no double alerts)
                    hot = ((rt_load().get("hot") or {}).get("last")) or hot
                    _sw0 = ((rt_load().get("hot") or {}).get("sw")) or 0
                    st.caption("🖥️ PC alert engine is running — showing its results "
                               f"(last sweep {int(max(0, time.time() - _sw0))} s ago). "
                               "Telegram alerts are sent by the engine, not this page.")
                elif _mkt_open:
                    _lastsw = ((rt_load().get("hot") or {}).get("sw")) or 0
                    if time.time() - _lastsw > (60 if _fast0 else 110):
                        _fresh = hot_scan(tg=_tg_on)    # every click no longer re-sweeps
                        if _fresh.get("err"):
                            hot = ss.get("hot") or hot  # keep the last GOOD view on failure
                        else:
                            hot = _fresh
                            ss["hot"] = hot
                            try:
                                rt_save("hot", last=hot, sw=time.time())
                            except Exception:
                                pass
            except Exception:
                pass
        maybe_daily_scorecard()   # 📊 16:00 self-score (all guards inside)
        # 🏅 v14 MEASURED ACCURACY — every alert scored by first touch
        try:
            with st.expander("🏅 MEASURED ALERT ACCURACY — honest first-touch scoring "
                             f"(+{HQ_TGT}% target vs −{HQ_STOP}% stop, from the REAL send price)",
                             expanded=False):
                _om2 = _n.hour * 60 + _n.minute
                if _om2 >= 15 * 60 + 30 or _n.weekday() >= 5:
                    _lgd = ((rt_load().get("alertlog") or {}).get("days")) or {}
                    _std = ((rt_load().get("alertstats") or {}).get("days")) or {}
                    if any(d not in _std for d in _lgd):
                        with st.spinner("Scoring logged alerts on 1-min candles…"):
                            hot_eval_pending()
                if st.button("📊 Score alerts now (uses candles so far)", key="hq_eval_now"):
                    with st.spinner("Scoring…"):
                        _nn = hot_eval_pending(force_today=True)
                    st.caption(f"Scored {_nn} alerts.")
                _tab, _cnt = hot_stats_table()
                if not _cnt:
                    st.info("No scored alerts yet. Every 🚀/💎/🔥/🔄/🎯 entry alert is now logged with "
                            "its real send price; scoring runs after 15:30 (or press the button).")
                else:
                    st.caption(f"{_cnt} alerts over the last 30 logged days. WIN = +{HQ_TGT}% touched "
                               f"before −{HQ_STOP}%; same-candle = LOSS; 'open' = exited 15:20. "
                               f"Avg net includes ~{HQ_COST}% costs. Needs 100+ alerts before "
                               "any number is trustworthy.")
                    st.dataframe(pd.DataFrame(_tab), hide_index=True, **STRETCH)
                    st.caption("Read it like this: if 'grade A+' wins clearly more than 'grade B/C' over "
                               "100+ alerts, switch the minimum grade to A+. A 'failed X' row much worse "
                               "than ALL means that check matters; similar to ALL means it doesn't.")
        except Exception:
            pass
        if st.button("🔍 SCAN WHOLE MARKET", type="primary", key="hot_start",
                     help="~2500 stocks in one sweep — seconds after the first scan of the day"):
            pr = st.progress(0.0)
            hot = hot_scan(progress=pr.progress, tg=_tg_on)
            ss["hot"] = hot
            if not hot.get("err"):
                try:
                    rt_save("hot", last=hot, sw=time.time())
                except Exception:
                    pass
            pr.empty()
        if not hot:
            st.info("Press 🔍 SCAN WHOLE MARKET — the sweep covers EVERY NSE equity, not just our board. "
                    "Works live during market hours AND after close (shows the full day).")
            return
        if hot.get("err"):
            if hot["err"] == "no_token":
                st.warning("📡 Upstox token needed for the whole-market sweep — connect it in 📡 Data "
                           "(the same token the scanner already uses).")
            else:
                st.error("Sweep failed — press the button again in a minute.")
            return
        _st = hot.get("stats") or {}
        st.markdown(
            f"<div style='color:#cbd5e1;font-size:12px;margin:2px 0 10px;'>Sweep {hot.get('ts', '?')} · "
            f"<b style='color:#fbbf24;'>{_st.get('n', 0)}</b> stocks scanned · "
            f"<b style='color:#fbbf24;'>{_st.get('n3', 0)}</b> up ≥3% · "
            f"<b style='color:#4ade80;'>{_st.get('band_ok', 0)}</b> in our ₹100–₹1000 band · "
            f"<b style='color:#4ade80;'>{_st.get('liq', 0)}</b> liquid (≥1L/day) · "
            f"<b style='color:#60a5fa;'>{_st.get('on_board', 0)}</b> already on our board · "
            f"<b style='color:#f87171;'>{_st.get('new_list', 0)}</b> brand-new listings</div>",
            unsafe_allow_html=True)
        try:
            _ha = rt_load().get("hotalerts") or {}
            _al = _ha.get("syms") or {} if _ha.get("day") == hot.get("day") else {}
        except Exception:
            _al = {}
        if _al:
            _chips = " ".join(
                f"<span style='background:rgba(245,158,11,0.15);border:1px solid rgba(245,158,11,0.5);"
                f"border-radius:10px;padding:4px 10px;margin:3px;display:inline-block;color:#fbbf24;"
                f"font-weight:700;font-size:12px;'>{('🔥' if isinstance(_r, dict) and _r.get('big') else '🚀')} {_esc(s.replace('.NS', ''))} · "
                f"{(_r.get('t') if isinstance(_r, dict) else _r)}"
                + (" ✅" if isinstance(_r, dict) and _r.get("done") == "tgt" else "")
                + (" ⚠️" if isinstance(_r, dict) and _r.get("done") == "fade" else "")
                + "</span>"
                for s, _r in list(_al.items())[:15])
            st.markdown("<div style='font-size:15px;font-weight:800;color:#fbbf24;margin:12px 0 4px;'>"
                        "🚀 TODAY'S HOT ALERTS — sent to Telegram</div>"
                        f"<div style='margin-bottom:6px;'>{_chips}</div>", unsafe_allow_html=True)
        try:
            _al2 = (_ha.get("d2u") or {}) if _ha.get("day") == hot.get("day") else {}
        except Exception:
            _al2 = {}
        if _al2:
            _chips2 = " ".join(
                f"<span style='background:rgba(74,222,128,0.12);border:1px solid rgba(74,222,128,0.5);"
                f"border-radius:10px;padding:4px 10px;margin:3px;display:inline-block;color:#4ade80;"
                f"font-weight:700;font-size:12px;'>🔄 {_esc(s.replace('.NS', ''))} · "
                f"{(_r.get('t') if isinstance(_r, dict) else _r)}"
                + (" ✅" if isinstance(_r, dict) and _r.get("done") == "tgt" else "")
                + (" ⚠️" if isinstance(_r, dict) and _r.get("done") == "fade" else "")
                + "</span>"
                for s, _r in list(_al2.items())[:15])
            st.markdown("<div style='font-size:15px;font-weight:800;color:#4ade80;margin:12px 0 4px;'>"
                        "🔄 TODAY'S DOWN-TO-UP ALERTS — sent to Telegram</div>"
                        f"<div style='margin-bottom:6px;'>{_chips2}</div>", unsafe_allow_html=True)
        try:
            _al3 = (_ha.get("micro") or {}) if _ha.get("day") == hot.get("day") else {}
        except Exception:
            _al3 = {}
        if _al3:
            _chips3 = " ".join(
                f"<span style='background:rgba(96,165,250,0.12);border:1px solid rgba(96,165,250,0.5);"
                f"border-radius:10px;padding:4px 10px;margin:3px;display:inline-block;color:#93c5fd;"
                f"font-weight:700;font-size:12px;'>💰 {_esc(s.replace('.NS', ''))} · "
                f"{(_r.get('t') if isinstance(_r, dict) else _r)}"
                + (" ✅" if isinstance(_r, dict) and _r.get("done") == "tgt" else "")
                + (" ⚠️" if isinstance(_r, dict) and _r.get("done") == "fade" else "")
                + "</span>"
                for s, _r in list(_al3.items())[:15])
            st.markdown("<div style='font-size:15px;font-weight:800;color:#93c5fd;margin:12px 0 4px;'>"
                        "💰 TODAY'S ₹3–4 SETUPS — sent to Telegram</div>"
                        f"<div style='margin-bottom:6px;'>{_chips3}</div>", unsafe_allow_html=True)
        try:
            _bigl = sorted(((r.get("t", "?"), s.replace(".NS", ""), r)
                            for s, r in (_al or {}).items()
                            if isinstance(r, dict) and r.get("big")), key=lambda z: str(z[0]))
        except Exception:
            _bigl = []
        if _bigl:
            st.markdown("<div style='font-size:15px;font-weight:800;color:#f87171;margin:12px 0 4px;'>"
                        "🔥 BIG MOVERS — caught by the uptrend/big-move net (₹100–1000 + 💎 ₹1000–3000)</div>", unsafe_allow_html=True)
            for t, s, r in _bigl:
                _bs = (" ✅ +2% hit" + (f" {r.get('done_t')}" if r.get("done_t") else "")) if r.get("done") == "tgt" \
                      else (" ⚠️ faded" + (f" {r.get('done_t')}" if r.get("done_t") else "")) if r.get("done") == "fade" else " ⏳ running"
                st.markdown(f"<div style='background:#0f1a2e;border-left:4px solid #f87171;border-radius:10px;"
                            f"padding:8px 14px;margin:4px 0;color:#cbd5e1;font-size:13px;'>"
                            f"<b style='color:white;'>{t}</b> · 🔥 <b>{_esc(s)}</b>"
                            + (" <span style='color:#fbbf24;font-size:11px;'>💎 ₹1000–3000</span>" if r.get("prem") else "")
                            + f" · alert ₹{(r.get('px') or 0):.1f}"
                            f"<b style='color:#f87171;'>{_bs}</b></div>", unsafe_allow_html=True)
        try:
            _fsx = rt_load().get("fireskipped") or {}
            if _fsx.get("day") == hot.get("day") and _fsx.get("m"):
                _nmx = ", ".join(sorted(s.replace(".NS", "") for s in _fsx["m"]))
                st.markdown(
                    f"<div style='background:#1a1210;border:1px dashed #f87171;border-radius:10px;"
                    f"padding:7px 14px;margin:6px 0;color:#fca5a5;font-size:12px;'>"
                    f"🚫 <b>{len(_fsx['m'])} big mover(s) NOT alerted today — red-market gate</b> "
                    f"(NIFTY ≤ −0.50% when they qualified): {_nmx}</div>", unsafe_allow_html=True)
        except Exception:
            pass
        rows = hot.get("rows") or []
        if not rows:
            st.success("No big movers (≥2%) right now — quiet market. 🎯 The combo board is the right "
                       "place to be on days like this.")
        for x in rows:
            _why = []
            if x.get("cross") and (x.get("gap") or 0) < 4.0:
                _why.insert(0, f"🚀 started {x['cross']}")
            if x.get("p5") is not None:
                _why.append(f"week {x['p5']:+.1f}%")
            _why.append("on our board" if x["curated"] else "NOT on our board")
            if x["px"] > MAX_PRICE:
                _why.append(f"₹>{MAX_PRICE:.0f} band")
            elif x["px"] < MIN_PRICE:
                _why.append(f"₹<{MIN_PRICE:.0f} band")
            if x["avg20"]:
                _why.append("💧 liquid" if x["avg20"] >= 100000 else "⚠️ thin <1L/day")
            if not x["listed"]:
                _why.append("🆕 new listing")
            _col = "#fbbf24" if x["chg"] >= 5 else "#cbd5e1"
            st.markdown(
                f"<div style='background:#0f1a2e;border:1px solid #1e293b;border-left:4px solid {_col};"
                f"border-radius:10px;padding:8px 14px;margin:6px 0;display:flex;justify-content:space-between;'>"
                f"<div><b style='color:white;font-size:14px;'>{_esc(x['s'].replace('.NS', ''))}</b> "
                f"<span style='color:#94a3b8;font-size:11px;'>₹{x['px']:.1f}</span></div>"
                f"<div style='text-align:right;'><b style='color:{_col};font-size:14px;'>+{x['chg']:.2f}%</b> "
                f"<span style='color:#64748b;font-size:10px;'> · {' · '.join(_why)}</span></div></div>",
                unsafe_allow_html=True)
        st.caption("🚀 started HH:MM = crossed +₹3 from open and HELD it (2 candles — a ₹10/day mover "
                   "caught at ₹3; for costlier stocks the line is 1%, e.g. ₹500 → +₹5). "
                   "Gap-ups that open already +4% high are NOT marked. "
                   "Honest stats (1,483 real cases, Sep 15–23): only ~18% of fresh movers reach +1.5% by close, "
                   "~55% close BELOW their start point — treat every alert as a WATCH; your candle reading is the filter. "
                   "Watch-only — NOT picks. One-day spikes are the hardest trades (many fade the next day). "
                   "Use this tab to see what the market is doing; the 🎯 combo board stays your pick machine. "
                   "Note: a stock that gap-opens high and stays flat shows a lower % here.")

        # ── 💎 PREMIUM MOVERS — ₹1000–3000, its OWN section (user request 12
        #    Oct): never mixed into the main ₹100–1000 list above.
        #    User follow-up same day: show ONLY stocks this app actually
        #    PINGED today — unpinged premium movers stay off the page. ──
        prows = hot.get("prows") or []
        try:
            _hl_p = rt_load().get("hotalerts") or {}
            _pinged_p = (set((_hl_p.get("syms") or {}).keys())
                         if _hl_p.get("day") == now_ist().strftime("%Y-%m-%d") else set())
            prows = [x for x in prows if x["s"] in _pinged_p]
        except Exception:
            pass
        st.markdown("<div style='background:#1a1035;border:2px solid #a78bfa;border-radius:14px;"
                    "padding:10px 16px;color:#ddd6fe;font-size:15px;font-weight:800;margin:18px 0 6px;'>"
                    "💎 PREMIUM MOVERS · ₹1000–3000 — pinged today</div>", unsafe_allow_html=True)
        if not prows:
            st.caption("💎 No premium alerts yet today — this section lists only ₹1000–3000 stocks that "
                       "were actually pinged to Telegram (💎 PREMIUM HOT ALERT).")
        for x in prows:
            _why = []
            if x.get("cross") and (x.get("gap") or 0) < 4.0:
                _why.insert(0, f"🚀 started {x['cross']}")
            if x.get("p5") is not None:
                _why.append(f"week {x['p5']:+.1f}%")
            _why.append("on our board" if x["curated"] else "NOT on our board")
            if x["avg20"]:
                _why.append("💧 liquid" if x["avg20"] >= 100000 else "⚠️ thin <1L/day")
            if not x["listed"]:
                _why.append("🆕 new listing")
            _col = "#a78bfa" if x["chg"] >= 5 else "#cbd5e1"
            st.markdown(
                f"<div style='background:#171128;border:1px solid #2d2350;border-left:4px solid {_col};"
                f"border-radius:10px;padding:8px 14px;margin:6px 0;display:flex;justify-content:space-between;'>"
                f"<div><b style='color:white;font-size:14px;'>💎 {_esc(x['s'].replace('.NS', ''))}</b> "
                f"<span style='color:#94a3b8;font-size:11px;'>₹{x['px']:.1f}</span></div>"
                f"<div style='text-align:right;'><b style='color:{_col};font-size:14px;'>+{x['chg']:.2f}%</b> "
                f"<span style='color:#64748b;font-size:10px;'> · {' · '.join(_why)}</span></div></div>",
                unsafe_allow_html=True)
        st.caption("💎 ₹1000–3000 band — kept SEPARATE from the main list, and shows ONLY premium stocks "
                   "this app actually pinged today (💎 PREMIUM HOT ALERT) — nothing else, zero noise. "
                   "Same alert rules: liquid ≥1L/day, sustained +max(₹3, 1%) cross, gap-up filter. "
                   "Bigger prices = bigger rupees per move — size your positions carefully.")

        # ── 📲 SENT LOG (user request 6 Oct): the exact pings THIS app sent to
        #    Telegram today, with times — the ground truth, kept at the bottom.
        #    If a stock is missing here, no ping went out for it (window missed,
        #    app asleep, or filtered) — no more guessing vs Telegram.
        try:
            _hl = rt_load().get("hotalerts") or {}
            _today_h = now_ist().strftime("%Y-%m-%d")
            _sh = sorted(((r.get("t", "?"), s.replace(".NS", ""), r)
                          for s, r in (_hl.get("syms") or {}).items()
                          if isinstance(r, dict)), key=lambda z: z[0])
            _sd = []
            for _s2, _v2 in ((_hl.get("d2u") or {}).items()):
                _r2 = _v2 if isinstance(_v2, dict) else {"t": str(_v2)}
                _sd.append((_r2.get("t", "?"), _s2.replace(".NS", ""), _r2))
            _sd.sort(key=lambda z: str(z[0]))
            _sm = sorted(((r.get("t", "?"), s.replace(".NS", ""), r)
                          for s, r in (_hl.get("micro") or {}).items()
                          if isinstance(r, dict)), key=lambda z: z[0])
        except Exception:
            _sh, _sd, _sm = [], [], []
        if _hl.get("day") == _today_h and (_sh or _sd or _sm):
            st.markdown("<div style='background:#052e16;border:2px solid #16a34a;border-radius:14px;"
                        "padding:12px 18px;color:#bbf7d0;font-size:15px;font-weight:800;margin:18px 0 6px;'>"
                        "📲 SENT TO TELEGRAM — today's actual pings from THIS app (with time)</div>",
                        unsafe_allow_html=True)
            def _sent_state(r, kind):
                if not isinstance(r, dict):
                    return ""
                d = r.get("done")
                _dt = f" {r.get('done_t')}" if r.get("done_t") else ""
                if kind == "hot":
                    return (" ✅ +2% hit" + _dt) if d == "tgt" else (" ⚠️ faded" + _dt) if d == "fade" else " ⏳ running"
                return (" ✅ ₹3–4 done" + _dt) if d == "tgt" else (" ⚠️ failed" + _dt) if d == "fade" else " ⏳ running"
            for t, s, r in _sh:
                st.markdown(f"<div style='background:#0f1a2e;border-left:4px solid #fbbf24;border-radius:10px;"
                            f"padding:8px 14px;margin:4px 0;color:#cbd5e1;font-size:13px;'>"
                            f"<b style='color:white;'>{t}</b> · {'💎' if (r or {}).get('prem') else ('🔥' if (r or {}).get('big') else '🚀')} "
                            f"<b>{_esc(s)}</b> · alert ₹{(r.get('px') or 0):.1f}"
                            f"<b style='color:#fbbf24;'>{_sent_state(r, 'hot')}</b></div>", unsafe_allow_html=True)
            # GREEN STAIRCASE confirms are Telegram-only sends — show them
            #    in the SENT LOG too (user request 23 Oct evening: complete
            #    evening check). Rendered as their own lines.
            for t, s, r in _sh:
                if isinstance(r, dict) and r.get("stair"):
                    st.markdown(f"<div style='background:#052e16;border-left:4px solid #4ade80;border-radius:10px;"
                                f"padding:8px 14px;margin:4px 0;color:#cbd5e1;font-size:13px;'>"
                                f"<b style='color:white;'>{r['stair']}</b> · 🟢 <b>{_esc(s)}</b> · staircase confirm"
                                f" — move strengthening</div>", unsafe_allow_html=True)
            for t, s, r in _sd:
                _d2 = r.get("done")
                _d2t = f" {r.get('done_t')}" if r.get("done_t") else ""
                _st2 = (" ✅ +2%" + _d2t) if _d2 == "tgt" else (" ⚠️ failed" + _d2t) if _d2 == "fade" else " ⏳ running"
                st.markdown(f"<div style='background:#0f1a2e;border-left:4px solid #4ade80;border-radius:10px;"
                            f"padding:8px 14px;margin:4px 0;color:#cbd5e1;font-size:13px;'>"
                            f"<b style='color:white;'>{t}</b> · 🔄 <b>{_esc(s)}</b> · bounce ₹{(r.get('bp') or 0):.1f}"
                            f"<b style='color:#4ade80;'>{_st2}</b></div>",
                            unsafe_allow_html=True)
            for t, s, r in _sm:
                st.markdown(f"<div style='background:#0f1a2e;border-left:4px solid #93c5fd;border-radius:10px;"
                            f"padding:8px 14px;margin:4px 0;color:#cbd5e1;font-size:13px;'>"
                            f"<b style='color:white;'>{t}</b> · 💰 <b>{_esc(s)}</b> · entry ₹{(r.get('px') or 0):.1f}"
                            f"<b style='color:#93c5fd;'>{_sent_state(r, 'micro')}</b></div>", unsafe_allow_html=True)
            st.caption("This list = what THIS app actually sent (its own send records). Missing here = no ping "
                       "went out — the 12-min freshness window passed before a sweep, or the app wasn't open. "
                       "Your deployed app keeps its own list on its page.")
        elif _hl.get("day") == _today_h:
            st.caption("📲 SENT LOG: no pings sent by this app yet today — the list fills the moment a "
                       "🚀/🔄/💰 goes to Telegram.")
    except Exception as e:
        st.warning(f"⚠️ Hot movers problem: {type(e).__name__}: {e}")


def d2u_tab(ss):
    """🔄 DOWN-TO-UP — stocks that FELL today and are now RECOVERING ₹5+ off
    their lows. Same sweep engine as 🚀 HOT MOVERS (this tab renders the
    recovery side; alerts fire from there too). Watch-only."""
    try:
        st.markdown(
            "<div style='background:linear-gradient(90deg,#051a0f,#0f1a2e);border:1px solid #4ade8055;"
            "border-radius:14px;padding:14px 18px;margin-bottom:12px;'>"
            "<div style='color:#4ade80;font-size:20px;font-weight:900;'>🔄 DOWN-TO-UP — recovery radar</div>"
            "<div style='color:#94a3b8;font-size:12px;margin-top:4px;'>Stocks that fell at least ₹2 below "
            "their open today and have now bounced ₹5+ (or 1%) off the day's low — the 'went down but "
            "coming back up' list you asked for. ₹100–₹1000 · liquid only.</div></div>", unsafe_allow_html=True)
        hot = ss.get("hot") or ((rt_load().get("hot") or {}).get("last"))
        if not hot:
            st.info("No sweep yet — during market hours this tab updates itself every "
                    "5 min automatically (or press 🔍 SCAN WHOLE MARKET in the 🚀 HOT "
                    "MOVERS tab for an instant refresh).")
            return
        d2u = hot.get("d2u") or []
        _risers = sum(1 for x in d2u if (x.get("now") or 0) > 0.2)
        st.markdown(f"<div style='color:#cbd5e1;font-size:12px;margin:2px 0 10px;'>Sweep "
                    f"{hot.get('ts', '?')} · <b style='color:#4ade80;'>{len(d2u)}</b> recoveries · "
                    f"<b style='color:#4ade80;'>{_risers} rising right now</b> · "
                    f"auto-updates every 5 min in market hours</div>", unsafe_allow_html=True)
        if not d2u:
            st.success("No down-to-up recoveries right now — nothing fell and bounced back ₹5+ today.")
            return
        for x in d2u:
            _why = []
            _n_ = x.get("now")
            if _n_ is not None:                       # 🟢 live 15-min momentum
                _why.insert(0, (f"🟢 rising +₹{_n_:.1f} (15 min)" if _n_ > 0.2
                                else (f"🔴 slipping −₹{abs(_n_):.1f} (15 min)" if _n_ < -0.2
                                      else "➖ flat (15 min)")))
            if x.get("b_t"):
                _why.append(f"🔄 since {x['b_t']}")
            if x.get("p5") is not None:
                _why.append(f"week {x['p5']:+.1f}%")
            _why.append("💧 liquid" if (x.get("avg20") or 0) >= 100000 else "⚠️ thin")
            st.markdown(
                f"<div style='background:#0f1a2e;border:1px solid #1e293b;border-left:4px solid #4ade80;"
                f"border-radius:10px;padding:8px 14px;margin:6px 0;'>"
                f"<b style='color:white;font-size:14px;'>{_esc(x['s'].replace('.NS', ''))}</b> "
                f"<span style='color:#94a3b8;font-size:11px;'>₹{x['px']:.1f}"
                + (f" ({x['chg']:+.1f}% today)" if x.get("chg") is not None else "") + "</span>"
                f"<div style='color:#cbd5e1;font-size:12px;margin-top:3px;'>"
                f"fell ₹{x['dip']:.1f} below open → low ₹{x['lo']:.1f} · "
                f"<b style='color:#4ade80;'>bounced +₹{x['bnc']:.1f}</b> off the low"
                + (f" · recovering since {x['b_t']} @ ₹{x['b_px']:.1f}" if x.get("b_t") else "")
                + (f" · 💧 {x['pace']:.1f}× pace" if x.get("pace") else "")
                + "</div>"
                f"<div style='color:#64748b;font-size:10px;margin-top:2px;'>{' · '.join(_why)}</div></div>",
                unsafe_allow_html=True)
        st.caption("⚠️ Recoveries are the trickiest trades — a bounce off the low can be a dead-cat "
                   "bounce that rolls over again. The 📈 past-week line helps (recoveries in uptrending "
                   "stocks work far better than in falling ones). Watch-only — NOT combo picks; your "
                   "candle reading is the filter.")
    except Exception as e:
        st.warning(f"⚠️ Down-to-up problem: {type(e).__name__}: {e}")


def combo_tab(ss, mst_s):
    # 🚀 AUTO-START — the combo radar begins BY ITSELF at 9:20 on market days
    # (the 🏅 consensus snapshots 9:30–10:15 depend on it running). Pressing
    # ⏹ Stop keeps it stopped for the rest of the day.
    if (not ss.get("cb_on") and mst_s == "open"
            and (now_ist().hour * 60 + now_ist().minute >= 9 * 60 + 20 or ss.get("up_kick"))
            and not up_wait_reason()          # ⏳ API-FIRST: hold for the Upstox login (till 9:35)
            and ss.get("cb_stop_day") != now_ist().strftime("%Y-%m-%d")
            and ss.get("cb_auto", False)      # 🚫 OFF by default — YOU press START
            and _pilot_ok("cb", ss)):
        try:
            _w, _nm = build_watchlist(ss.get("cb_src"), ss.get("cb_n", 75))
        except Exception:
            _w, _nm = [], {}
        if _w:
            ss["cb_watch"] = _w; ss["cb_names"] = _nm
            ss["cb_on"] = True; ss["cb"] = None; ss["cb_last"] = 0
            rt_save("cb", on=True, src=ss.get("cb_src"), n=ss.get("cb_n", 75), watch=_w, names=_nm)
            ss["_cb_autostarted"] = True
            blog(f"🚀 combo AUTO-START · {len(_w)} stocks · n={ss.get('cb_n', 500)}")
            st.rerun()

    # ♾️ AUTO-RESUME — the combo scan keeps running across page refreshes
    if not ss.get("cb_on"):
        _rt = rt_load().get("cb") or {}
        if _rt.get("on") and _rt.get("watch"):
            if time.time() - (_rt.get("last_scan") or 0) > 2700:   # 🧹 stale (>45 min) — old data, start clean
                rt_clear("cb")
                _rt = {}
        if _rt.get("on") and _rt.get("watch"):
            ss["cb_on"] = True
            ss["cb_watch"] = _rt["watch"]; ss["cb_names"] = _rt.get("names") or {}
            ss["cb"] = _rt.get("combos") or None
            ss["cb_last"] = _rt.get("last_scan", 0)
            ss["cb_ts_str"] = _rt.get("ts_str") or "—"
            if _rt.get("src"):
                ss["cb_src"] = _rt["src"]
            if _rt.get("n"):
                ss["cb_n"] = _rt["n"]
            ss["_cb_resumed"] = True

    cons_announce()   # 📲 reopen later/evening: today's final result still gets delivered

    st.markdown(_H("""<div style='background:linear-gradient(135deg,#1e1b4b,#0f3d2e);border-radius:18px;
    padding:18px 22px;margin-bottom:12px;'>
    <div style='color:white;font-size:20px;font-weight:900;'>🎯 COMBO — live money ∩ calculation</div>
    <div style='color:#c7d2fe;font-size:12.5px;margin-top:6px;line-height:1.7;'>The accuracy booster you asked for:
    a stock appears here only when <b> BOTH </b> agree — ⚡ it is <b>actually climbing right now</b> (live candles)
    <b>AND</b> 🧮 the <b>calculation</b> says uptrend/BUY/above-200EMA. 🎯 PERFECT = strongest possible agreement.
    ⚠️ LIVE ONLY = money moving but math neutral (risky momentum). 🧮 CALC ONLY = math likes it, money not yet
    (breakout watchlist).</div></div>"""), unsafe_allow_html=True)
    st.markdown(_H("""<div style='background:#0b1220;border:1px dashed #1e293b;border-radius:12px;padding:10px 16px;
    color:#94a3b8;font-size:12px;margin-bottom:10px;line-height:1.8;'>⏰ <b style='color:#e2e8f0;">Best time to run this
    (IST):</b> 🥇 <b style='color:#4ade80;'>9:45 – 11:00 AM</b> (opening noise settles, real trend confirms) ·
    🥈 1:30 – 2:30 PM (afternoon build) · 🥉 2:45 – 3:10 PM (closing strength). <b style='color:#f87171;">Avoid
    9:15–9:35</b> — opening fake spikes. One clean scan at ~9:45 + one re-scan at ~2:45 is the professional routine.
    </div>"""), unsafe_allow_html=True)
    if mst_s == "open" and now_ist().time() < dtime(9, 45):
        st.markdown("<div style='background:#3f2d04;border:1px solid #f59e0b;border-radius:10px;padding:8px 14px;"
                    "color:#fde68a;font-size:12px;margin-bottom:10px;'>⚠️ It's before 9:45 AM — you CAN scan now, but "
                    "scores settle after 9:45–10:00. A re-scan at 9:45+ is worth it.</div>", unsafe_allow_html=True)

    _regime_banner()
    with st.expander("⚙️ UNIVERSE · REFRESH", expanded=not ss.get("cb_watch")):
        k1, k2 = st.columns(2)
        with k1:
            _keys = list(DASH_SRC.keys())
            _def = _keys.index("🌐 Full NSE (auto-fill to your count)") if "🌐 Full NSE (auto-fill to your count)" in _keys else 0
            st.selectbox("Universe", _keys, index=_def, key="cb_src")
            st.slider("How many stocks", 50, 500, 75, 25, key="cb_n")
        with k2:
            st.selectbox("Auto-refresh every", ["1 min", "2 min", "3 min", "5 min"], index=1, key="cb_int")
            st.caption("🎯 TOP-75 board — top 25 × 3 result windows = the 75 you actually "
                       "watch. Lightest load, same PERFECT picks (they always rank at the top). "
                       "📡 Yahoo + Upstox auto-fallback · radar follows YOUR start.")
            ss["cb_auto"] = st.checkbox("🚀 Auto-start at 9:20 by itself", value=bool(ss.get("cb_auto", False)),
                                        key="cb_auto_ck",
                                        help="OFF by default — press 🎯 START COMBO SCAN yourself. "
                                             "The radar then runs on YOUR timing, whatever the clock says.")
            st.caption("One scan = live 5-minute candles + daily history for the whole board (~1–2 min).")
        s1, s2, s3 = st.columns(3)
        with s1:
            start_cb = st.button("🎯 START COMBO SCAN", type="primary", **STRETCH, key="cb_start")
        with s2:
            rescan_cb = st.button("🔄 Scan now", **STRETCH, key="cb_rescan")
        with s3:
            stop_cb = st.button("⏹ Stop", **STRETCH, key="cb_stop")

    if stop_cb:
        ss["cb_on"] = False
        ss["cb_stop_day"] = now_ist().strftime("%Y-%m-%d")
        rt_clear("cb")
    if start_cb:
        watch, names = build_watchlist(ss.get("cb_src"), ss.get("cb_n", 75))
        ss["cb_watch"] = watch; ss["cb_names"] = names
        ss["cb_on"] = True; ss["cb"] = None; ss["cb_last"] = 0
        rt_save("cb", on=True, src=ss.get("cb_src"), n=ss.get("cb_n", 75), watch=watch, names=names)

    if not ss.get("cb_on"):
        if mst_s == "open" and up_wait_reason():
            st.markdown("<div style='background:#3a2a06;border:1px solid #f59e0b;border-radius:12px;padding:12px 18px;"
                        "color:#fde68a;font-size:13px;line-height:1.8;'>⏳ <b>API-FIRST — the radar is HOLDING for your "
                        "Upstox login.</b> Open the 📡 panel below → login → paste the code → <b>Activate</b> — the "
                        "radar + coach start the same second, snapshots begin 9:30. (Skipping today? Auto-start on "
                        "Yahoo at 9:35.)</div>", unsafe_allow_html=True)
        st.markdown("<div style='background:#0b1220;border-radius:20px;padding:44px;text-align:center;'>"
                    "<div style='font-size:44px;'>🎯</div>"
                    "<div style='font-size:20px;font-weight:900;color:#f1f5f9;margin-top:10px;'>COMBO SCANNER</div>"
                    "<div style='color:#64748b;font-size:13px;margin-top:8px;'>All-India board · live climb + "
                    "calculation agreement · 🎯 PERFECT picks · 🐢 slow-steady riders</div>"
                    "<div style='color:#94a3b8;font-size:12px;margin-top:12px;'>↑ Best at <b>9:45–11:00 AM IST</b> · "
                    "press <b style='color:#22c55e;'>🎯 START COMBO SCAN</b></div></div>", unsafe_allow_html=True)
        up_settings_ui("_cb2")     # 📡 API-FIRST: activate right here → radar starts instantly
        return

    if ss.get("_cb_autostarted"):
        ss["_cb_autostarted"] = False
        st.success("🚀 Combo radar AUTO-STARTED — snapshotting TOP-20 through your ⏱️ windows "
                   "(RESULT 1 ~09:40 · RESULT 2 ~10:00 · RESULT 3 ~10:15 · FINAL ~10:20). "
                   "The 📤 send button is ready whenever you are.")
    if ss.get("_cb_resumed"):
        ss["_cb_resumed"] = False
        st.info("♾️ Combo scan resumed automatically — a page refresh does NOT stop it. "
                "Press ⏹ Stop to end the session.")
    if not _pilot_ok("cb", ss) and (rt_load().get("cb") or {}).get("on"):
        st.caption("🤖 AUTOPILOT is driving the desk — this page is a live read-only view.")

    try:
        from streamlit_autorefresh import st_autorefresh
        _sec = int(ss.get("cb_int", "2 min").split()[0]) * 60
        if feed_status()[0] == "fallback":
            _sec = max(_sec, 360)    # 📡 fallback sweeps are heavier — refresh every 6 min,
        if mst_s == "open":          # so the page never kills a sweep mid-flight again
            st_autorefresh(interval=_sec * 1000, key="cb_tick")
    except Exception:
        pass

    watch = ss.get("cb_watch") or []
    names = ss.get("cb_names") or {}
    _sec = int(ss.get("cb_int", "2 min").split()[0]) * 60
    due = mst_s == "open" and time.time() - ss.get("cb_last", 0) > (_sec - 10)
    if due and not _pilot_ok("cb", ss):
        due = False
        _cb_view_sync(ss)                 # 🤖 autopilot drives — live view only
    _want_scan = (rescan_cb or due
                  or (not ss.get("cb") and time.time() - ss.get("cb_last", 0) > 90))
    if _want_scan:
        _pilot_beat("cb", ss)
        cb_bg_start(watch, names)          # 🧵 refresh-proof background sweep
    _bg_done = _CB_BG.get("done") or 0.0
    if _bg_done and _bg_done > (ss.get("cb_last") or 0):
        # 🧵 background sweep finished → harvest the board
        ss["cb"] = _CB_BG.get("res") or []
        cons_capture(ss["cb"])              # 🏅 9:30/9:45/10:00/10:15 TOP-20 snapshots
        cons_announce(names)               # 📲 guaranteed Telegram delivery of the final list
        try:                                # 🏔️ 52-week-high club (cached 30 min)
            if time.time() - ss.get("cb_52w_ts", 0) > 1800:
                ss["cb_52w"] = high52_map([c["sym"] for c in ss["cb"][:48]])
                ss["cb_52w_ts"] = time.time()
            _h52 = ss.get("cb_52w") or {}
            for c in ss["cb"]:
                _hh = _h52.get(c["sym"])
                c["near52"] = bool(_hh and _hh["dist"] >= -2.5)
        except Exception:
            pass
        ss["cb_last"] = time.time()
        ss["cb_ts_str"] = now_ist().strftime("%d %b %Y · %H:%M")
        blog(f"📊 board HARVESTED · {len(ss['cb'])} rows")
        try:                                # 🩺 connection probe (20 stocks)
            _prb = fetch_chunk(tuple(watch[:20]), "5m", "1d") if watch else {}
            ss["cb_health"] = {"ts": now_ist().strftime("%H:%M:%S"), "probe": len(_prb)}
        except Exception:
            ss["cb_health"] = {"ts": now_ist().strftime("%H:%M:%S"), "probe": 0}
        ss.pop("cb_recheck", None)
        rt_save("cb", on=True, watch=watch, names=names, combos=ss["cb"],
                last_scan=ss["cb_last"], ts_str=ss.get("cb_ts_str"),
                src=ss.get("cb_src"), n=ss.get("cb_n", 75))
    # ⚡ EARLY BOARD — volume-confirmed openers 9:15–10:10, BEFORE the results.
    #    Pure price+volume (no calculation needed): catches the strong openers
    #    the consensus windows only complete by 10:20.
    try:
        _t_eb = now_ist().hour * 60 + now_ist().minute
        if mst_s == "open" and ss.get("cb") and 9 * 60 + 15 <= _t_eb < 10 * 60 + 10:
            _eb = [c for c in ss["cb"]
                   if (c.get("chg_day") or 0) >= 1.0 and (c.get("vr") or 0) >= 2.0
                   and MIN_PRICE <= (c.get("price") or 0) <= MAX_PRICE]
            _eb.sort(key=lambda c: -((c.get("chg_day") or 0) * (c.get("vr") or 0)))
            ss["cb_early"] = _eb[:8]
            if ss["cb_early"]:
                _chips = " ".join(
                    f"<span style='background:rgba(250,204,21,0.12);border:1px solid rgba(250,204,21,0.4);"
                    f"border-radius:10px;padding:6px 12px;margin:3px;display:inline-block;'>"
                    f"<b style='color:#fde68a;'>{c['name']}</b> "
                    f"<span style='color:#4ade80;'>{c['chg_day']:+.1f}%</span> · "
                    f"vol <b>{c['vr']:.1f}×</b> · ₹{c['price']:,.0f}</span>" for c in ss["cb_early"])
                st.markdown(f"<div style='background:#2a2306;border:2px solid #facc15;border-radius:14px;"
                            f"padding:12px 16px;margin:10px 0;'><b style='color:#facc15;'>⚡ EARLY BOARD — "
                            f"volume-confirmed openers</b> <span style='color:#a16207;font-size:11px;'>"
                            f"(price + volume only · the 09:40/10:00 results are still the real signal)</span>"
                            f"<div style='margin-top:6px;'>{_chips}</div></div>", unsafe_allow_html=True)
            _sent = set((rt_load().get("cb") or {}).get("early_sent") or [])
            for _slot, _lbl in ((9 * 60 + 30, "09:30"), (9 * 60 + 45, "09:45")):
                if _t_eb >= _slot and _lbl not in _sent and _eb:
                    _lines = [f"⚡ <b>EARLY BOARD · {_lbl}</b> — volume-confirmed openers",
                              "<i>Early momentum, calculation not complete yet — the 09:40/10:00 "
                              "consensus results remain the real signal.</i>", ""]
                    for c in _eb[:5]:
                        _lines.append(f"🚀 <b>{_esc(c['name'])}</b> {c['chg_day']:+.1f}% · "
                                      f"vol {c['vr']:.1f}× · ₹{c['price']:,.2f}")
                    _lines.append("\n⚠️ Don't chase high — wait for a small dip, SL always.")
                    if tg_send("\n".join(_lines)):
                        _sent.add(_lbl)
                        rt_save("cb", early_sent=sorted(_sent))
                        blog(f"⚡ EARLY BOARD {_lbl} sent · {min(5, len(_eb))} openers")
    except Exception:
        pass
    # 🌐 ranked board landed in the background? swap once — only before the
    #    first consensus snapshot, so windows are never disturbed
    try:
        if ss.get("cb_on") and not ss.get("cb_ranked_swapped"):
            _cs = cons_state()
            if not sum(int(w.get("n") or 0) for w in (_cs.get("wins") or {}).values()):
                _rw, _rn = rank_universe(ss.get("cb_n", 75))
                if _rw and _rw != ss.get("cb_watch"):
                    ss["cb_watch"] = _rw
                    ss["cb_names"] = _rn
                    ss["cb_ranked_swapped"] = True
                    rt_save("cb", on=True, watch=_rw, names=_rn, combos=ss.get("cb") or [],
                            src=ss.get("cb_src"), n=ss.get("cb_n", 75))
    except Exception:
        pass
    # 🏅 TODAY'S RESULTS — pinned to the page, impossible to miss
    try:
        cons_results_panel()
    except Exception:
        pass
    if cb_bg_alive():
        st.info("🧵 Full-board scan running in the BACKGROUND — refresh-proof, the board lands by "
                "itself in ~2–3 minutes. You can refresh or switch tabs freely; this page updates "
                "the moment the board is ready.")
        try:
            from streamlit_autorefresh import st_autorefresh
            if mst_s == "open":
                st_autorefresh(interval=15 * 1000, key="cb_bg_tick")   # quick poll while scanning
        except Exception:
            pass

    combos = ss.get("cb") or []
    _cbh = ss.get("cb_health") or {}
    if not combos and not cb_bg_alive():
        _pr = int(_cbh.get("probe") or -1)
        if _pr == 0:
            st.markdown("<div style='background:#2a0e0e;border:1px solid #ef4444;border-radius:12px;padding:14px 18px;"
                        "color:#fecaca;font-size:13px;line-height:1.8;'>❌ <b>DATA FEED FAILED — the 20-stock connection "
                        "test returned NOTHING.</b><br>The server↔Yahoo link is down (host overload or temporary "
                        "block). <b>The program is fine; the connection is not.</b> Auto-retry every cycle — if this "
                        "red box stays <b>15+ minutes</b>, reboot the app <b>ONCE</b> and wait 5 minutes.</div>",
                        unsafe_allow_html=True)
        elif 0 < _pr < 12:
            st.warning(f"⚠️ PARTIAL DATA — connection test got only {_pr}/20 stocks. The server connection is "
                       f"struggling; scores may be incomplete. Auto-retry on the next scan — no action needed.")
        else:
            if _FEED.get("fb_fail", 0) > _FEED.get("fb", 0) and time.time() - _FEED.get("fb_fail", 0) < 900:
                st.error("📡 The Upstox fallback tried but returned no candles. Check the 📡 panel — "
                         "if the green ANALYTICS box is showing, wait for the next scan cycle; if the "
                         "token expired, paste a fresh one.")
            elif feed_status()[0] == "fallback":
                st.info("📡 Yahoo is resting (global throttle) — the Upstox fallback is carrying the "
                        "board. Scores appear within a couple of scan cycles; everything else runs normally.")
            else:
                st.info("No scorable stocks yet — first reliable scores from ~9:45 AM IST (see the timing note above)."
                        + (f" 🩺 Connection test: {_pr}/20 OK — the data line is healthy; the filters just "
                           "haven't found agreement yet." if _pr >= 0 else ""))
        return
    if mst_s == "closed":
        st.markdown("<div style='background:#3f2d04;border:1px solid #f59e0b;border-radius:10px;padding:8px 14px;"
                    "color:#fde68a;font-size:12px;margin-bottom:10px;'>🔴 Market closed — this is today's FULL-SESSION "
                    "combo review: who had both live money AND calculation agreement today.</div>", unsafe_allow_html=True)

    # 🕒 FRESHNESS — when was this scan made? (an old scan's uptrend may have ENDED)
    _age = int((time.time() - ss.get("cb_last", 0)) / 60)
    _ts = ss.get("cb_ts_str") or "—"
    _agc = "#4ade80" if _age <= 6 else ("#fbbf24" if _age <= 15 else "#f87171")
    st.markdown(f"<div style='background:#0b1220;border:1px solid #1e293b;border-radius:10px;padding:8px 14px;"
                f"color:#94a3b8;font-size:12px;margin-bottom:10px;'>🕒 Last scan: <b style='color:#e2e8f0;'>{_ts} IST</b>"
                f" · <b style='color:{_agc};'>{_age} min ago</b>"
                + (" — <b style='color:#f87171;'>old scan: an uptrend may have ENDED. Press 🔄 Scan now.</b>"
                   if _age > 15 and mst_s == "open" else "")
                + " · every card below shows 🕒 <b>NOW vs SCAN</b> — still on / fading / ended.</div>",
                unsafe_allow_html=True)
    _fsm, _fsb = feed_status()
    if _fsm == "fallback":
        st.markdown(f"<div style='background:#0b2540;border:1px solid #0ea5e9;border-radius:10px;"
                    f"padding:8px 14px;color:#bae6fd;font-size:12px;margin-bottom:10px;'>"
                    f"📡 <b>LIVE FALLBACK ACTIVE (since {_fsb} IST)</b> — Yahoo is slow right now, so the "
                    f"radar switched to <b>Upstox real-time data</b> automatically. The board loads "
                    f"normally; Yahoo is re-checked every 5 minutes. <b>No interruption.</b></div>", unsafe_allow_html=True)
    try:
        _rg = nifty_regime()
        if _rg and _rg["lab"] == "RED" and mst_s == "open":
            st.markdown(f"<div style='background:#2a0e0e;border:2px solid #dc2626;border-radius:12px;"
                        f"padding:10px 16px;color:#fecaca;font-size:13px;margin-bottom:10px;'>"
                        f"{_rg['ico']} <b>NIFTY {_rg['chg']:+.2f}% — calculations UNRELIABLE today.</b> "
                        f"Uptrend maths misfires on red days — avoid longs or trade half size with tight SL. "
                        f"The results will carry this same warning.</div>", unsafe_allow_html=True)
    except Exception:
        pass

    # 🔄 live re-check of the top picks (current price vs scan price)
    _rc = ss.get("cb_recheck") or {}
    if time.time() - _rc.get("ts", 0) > 90:
        try:
            _syms = [c["sym"] for c in combos[:30]]
            _got = fetch_chunk(tuple(_syms), "5m", "1d")
            ss["cb_recheck"] = {"ts": time.time(),
                                "prices": {s: round(float(_got[s]["Close"].iloc[-1]), 2)
                                           for s in _syms if s in _got and len(_got[s])}}
        except Exception:
            ss["cb_recheck"] = {"ts": time.time(), "prices": {}}
        _rc = ss["cb_recheck"]
    _now_map = _rc.get("prices") or {}   # useful live AND after close (review)
    _scan_short = (_ts.split("·")[-1]).strip() if _ts != "—" else ""

    perfect = [c for c in combos if c["verdict"] == "🎯 PERFECT"]
    match = [c for c in combos if c["verdict"] == "✅ MATCH"]
    liveonly = [c for c in combos if c["verdict"] == "⚠️ LIVE ONLY"]
    calconly = [c for c in combos if c["verdict"] == "🧮 CALC ONLY"]
    a1, a2, a3, a4, a5 = st.columns(5)
    with a1: st.metric("🎯 Perfect", len(perfect), "live + calc agree")
    with a2: st.metric("✅ Match", len(match), "good agreement")
    with a3: st.metric("⚠️ Live only", len(liveonly), "momentum, no math")
    with a4: st.metric("🧮 Calc only", len(calconly), "breakout watchlist")
    with a5: st.metric("Scanned", len(combos))

    top = perfect + match
    if top:
        st.markdown(f"<div style='color:#94a3b8;font-size:12px;font-weight:900;margin:10px 0 4px;'>"
                    f"🎯 THE PICKS — live climb + calculation agree ({len(top)})</div>", unsafe_allow_html=True)
        st.markdown("".join(_combo_row(i + 1, c, _scan_short, _now_map) for i, c in enumerate(top[:30])),
                    unsafe_allow_html=True)
    else:
        st.info("No PERFECT/MATCH picks right now — the two engines don't agree on anything this moment. "
                "That's the system protecting you (no trade is better than a bad trade). Re-scan later.")

    st.caption("🌋 The VOLCANO eruption radar now lives in the 🎯 Coach tab — it watches "
               "continuously with the coach engine (every ~80 s), together with the whole "
               "combo board when this radar runs.")

    if liveonly:
        with st.expander(f"⚠️ LIVE ONLY — climbing but calculation neutral ({len(liveonly)}) · higher risk"):
            st.markdown("".join(_combo_row(i + 1, c, _scan_short, _now_map) for i, c in enumerate(liveonly[:20])),
                        unsafe_allow_html=True)
    if calconly:
        with st.expander(f"🧮 CALC ONLY — math likes them, money not moving yet ({len(calconly)}) · breakout watchlist"):
            st.markdown("".join(_combo_row(i + 1, c, _scan_short, _now_map) for i, c in enumerate(calconly[:20])),
                        unsafe_allow_html=True)
    with st.expander("📋 Full combo board (sortable) + download"):
        disp = pd.DataFrame([{"Stock": c["name"], "Symbol": c["sym"], "Price": c["price"],
                              "Day%": c["chg_day"], "ClimbScore": c["climb"], "GreenCandles%": c["green"],
                              "Slope1h%": c["slope1h"], "Vol×": c["vr"], "Signal": c["sig"],
                              "Trend": c["dtr"], "Conf%": c["conf"], "200EMA": "Above" if c["above200"] else "Below",
                              "ComboScore": c["combo"], "Verdict": c["verdict"],
                              "ScanTime": _ts, "Buy@": c.get("buy_at"), "SL": c.get("sl"),
                              "SellT1": c.get("t1"), "SellT2": c.get("t2"),
                              "Support": c.get("support"), "Resist": c.get("resistance"),
                              "ResDist%": c.get("res_dist"),
                              "SlowSteady": "🐢" if c["steady"] else ""} for c in combos])
        try:
            st.dataframe(disp, **STRETCH, height=420, hide_index=True)
        except Exception:
            st.dataframe(disp, **STRETCH)
        try:
            st.download_button("⬇️ Download combo board (CSV)", data=disp.to_csv(index=False).encode(),
                               file_name=f"combo_picks_{now_ist().strftime('%Y%m%d_%H%M')}.csv",
                               mime="text/csv", **STRETCH, key="cb_csv")
        except Exception:
            pass

    # ── ⏱️ SNAPSHOT SCHEDULE — YOUR analysis windows ──
    with st.expander("⏱️ SNAPSHOT SCHEDULE — your analysis windows"):
        _cc = cons_cfg_load()
        _w1 = _cc["wins"][0]
        _w2 = (_cc["wins"][1] if len(_cc["wins"]) > 1
               else {"start": "09:40", "end": "10:00", "every": 10})
        st.markdown("**WINDOW 1 — morning consensus**")
        _a1, _b1, _c1 = st.columns(3)
        with _a1:
            _ns1 = st.text_input("From (like 9.30)", value=_w1["start"], key="cons_from1")
        with _b1:
            _ne1 = st.text_input("To (like 10.15)", value=_w1["end"], key="cons_to1")
        with _c1:
            _ev1 = st.number_input("Every N min", 2, 30, int(_w1["every"]), key="cons_every1")
        st.markdown("**WINDOW 2 — late-morning confirmation**")
        _a2, _b2, _c2, _d2 = st.columns(4)
        with _a2:
            _ns2 = st.text_input("From (like 10.15)", value=_w2["start"], key="cons_from2")
        with _b2:
            _ne2 = st.text_input("To (like 10.45)", value=_w2["end"], key="cons_to2")
        with _c2:
            _ev2 = st.number_input("Every N min", 2, 30, int(_w2["every"]), key="cons_every2")
        with _d2:
            _en2 = st.checkbox("Window 2 ON", value=len(_cc["wins"]) > 1, key="cons_en2")
        if st.button("✅ APPLY SCHEDULE", key="cons_apply", **STRETCH):
            _errs, _wins = [], []
            for _lbl, _ns, _ne, _ev, _on in (("Window 1", _ns1, _ne1, int(_ev1), True),
                                              ("Window 2", _ns2, _ne2, int(_ev2), _en2)):
                if not _on:
                    continue
                _a, _b = _hmm(_ns), _hmm(_ne)
                _nsl = (_b - _a) // max(2, _ev) + 1 if (_a is not None and _b is not None
                                                        and _b >= _a) else 0
                if _a is None or _b is None:
                    _errs.append(f"⏰ {_lbl}: time not understood — write like 9.30 or 09:30")
                elif _b < _a:
                    _errs.append(f"⏰ {_lbl}: 'To' must be AFTER 'From'")
                elif _nsl < 2:
                    _errs.append(f"⏰ {_lbl}: window too small for that interval")
                elif _nsl > 12:
                    _errs.append(f"⚠️ {_lbl}: that makes {_nsl} snapshots (max 12) — increase minutes or shorten")
                else:
                    _wins.append({"start": f"{_a // 60:02d}:{_a % 60:02d}",
                                  "end": f"{_b // 60:02d}:{_b % 60:02d}", "every": _ev})
            if _errs:
                for _e in _errs:
                    st.error(_e)
            else:
                rt_save("conscfg", v=2, wins=_wins)
                rt_save("cons", day="RESET", wins={}, n=0, snaps={}, ts={}, date=None,
                        result_ts=None, announced_day=None)   # fresh analysis, all windows
                try:
                    rt_save("co", cons_day=None, cons_locks={})   # allow re-lock on new windows
                except Exception:
                    pass
                ss["_cons_applied"] = True
                st.rerun()
        if ss.get("_cons_applied"):
            ss["_cons_applied"] = False
            st.success("✅ Schedule APPLIED — today's snapshots reset for ALL windows. "
                       "Next scans follow your new times; each window gives its own result.")
        for _wi, _w in enumerate(cons_cfg_load()["wins"]):
            _sl = cons_slots_win(_w)
            if _sl:
                st.caption(f"📸 WINDOW {_wi + 1}: " + " · ".join(l for l, _m in _sl)
                           + f" ({len(_sl)} scans) → result right after {_sl[-1][0]}")

    # ── 🏅 STABLE PICKS — one result PER window ──
    _namesL = ss.get("cb_names") or {}
    _nwins = len(cons_cfg_load()["wins"])
    for _wi, _w in enumerate(cons_cfg_load()["wins"]):
        _t1c, _t2c, _cmc = cons_compute(_wi)
        if not _cmc["n"] or not _cmc["slots"]:
            continue
        _win_lbl = f"{_w['start']}–{_w['end']}"
        _res_no = f"RESULT {_wi + 1} · " if _nwins > 1 else ""
        with st.expander(f"🏅 {_res_no}STABLE PICKS · {_win_lbl} · {_cmc['n']}/{_cmc['total']} scans",
                         expanded=(_wi == 0)):
            st.caption(f"📸 {_cmc.get('date') or now_ist().strftime('%a %d %b %Y')} — TOP-20 snapshots of "
                       f"window {_wi + 1}. A stock appearing in {_cmc['need']}+ of {_cmc['total']} scans is "
                       f"genuinely strong, not a flicker — after this window's last snapshot the 🎯 coach "
                       f"follows ONLY these (kept positions stay).")
            _tss = _cmc.get("ts") or {}
            _slotline = " · ".join(f"{l} <b>{_tss.get(l, '⏳ pending')}</b>" for l, _m in _cmc["slots"])
            _res = f" · 🏁 result at <b>{_cmc['result_ts']}</b>" if _cmc.get("result_ts") else ""
            st.markdown(_H(f"<div style='background:#0b1220;border:1px solid #1e293b;border-radius:10px;"
                           f"padding:8px 12px;color:#94a3b8;font-size:12px;margin-bottom:8px;'>"
                           f"🕒 Scans: {_slotline}{_res}</div>"), unsafe_allow_html=True)
            if _t1c:
                for _s in _t1c:
                    _cnt, _bst = _cmc["counts"][_s], _cmc["best"][_s]
                    st.markdown(_H(f"<div style='display:flex;justify-content:space-between;background:#052e16;"
                                   f"border:1px solid #22c55e;border-radius:10px;padding:7px 12px;margin:4px 0;flex-wrap:wrap;gap:6px;'>"
                                   f"<b style='color:#bbf7d0;'>🏅 {_esc(_namesL.get(_s, _s.replace('.NS','')))}</b>"
                                   f"<span style='color:#4ade80;font-family:monospace;font-weight:800;'>"
                                   f"{_cnt}/{_cmc['total']} scans · best rank #{_bst}</span></div>"), unsafe_allow_html=True)
            else:
                st.info(f"{_cmc['n']}/{_cmc['total']} snapshots captured — stocks appearing "
                        f"{_cmc['need']}×+ will show here. Full result after the "
                        f"{_cmc['slots'][-1][0]} snapshot (keep this radar running).")
            if _t2c:
                st.caption(f"🔁 Appeared {_cmc['need'] - 1}× (watchlist): " + ", ".join(
                    _namesL.get(s, s.replace(".NS", "")) for s in _t2c[:10]))

    # ── 🏔️ 52-WEEK HIGH CLUB ──
    _h52u = ss.get("cb_52w") or {}
    _club = [(c, _h52u[c["sym"]]) for c in combos if c["sym"] in _h52u and _h52u[c["sym"]]["dist"] >= -2.5]
    if _club:
        with st.expander(f"🏔️ 52-WEEK HIGH CLUB — {len(_club)} stock(s) within 2.5% of their 52-week high"):
            st.caption("Stocks near their 52-week high are the market's strongest — buyers keep "
                       "defending them. Fresh breakouts here often run furthest.")
            for c, h in _club[:20]:
                st.markdown(_H(f"<div style='display:flex;justify-content:space-between;background:#0f172a;"
                               f"border:1px solid #1e293b;border-left:3px solid #f59e0b;border-radius:10px;"
                               f"padding:7px 12px;margin:4px 0;flex-wrap:wrap;gap:6px;'>"
                               f"<b style='color:#f1f5f9;'>🏔️ {_esc(c['name'])} "
                               f"<span style='color:#64748b;font-size:11px;'>{c['verdict']}</span></b>"
                               f"<span style='color:#e2e8f0;font-family:monospace;'>₹{c['price']:,.2f} · "
                               f"<span style='color:{'#22c55e' if c['chg_day'] >= 0 else '#ef4444'};'>{c['chg_day']:+.2f}%</span>"
                               f" · 52W high ₹{h['hi52']:,.2f} ({h['dist']:+.2f}%)</span></div>"),
                            unsafe_allow_html=True)

    # ── 📤 SEND PICKS TO TELEGRAM (whenever YOU want — full plan + open buttons) ──
    with st.expander("📤 SEND PICKS TO TELEGRAM (on demand)"):
        _prio = {"🎯 PERFECT": 0, "✅ MATCH": 1}
        _pool = [c for c in combos if c.get("verdict") in _prio or c.get("dtr") == "UPTREND"]
        _cms = cons_compute(cons_last_win())[2]
        _cmap, _cmn = _cms.get("counts") or {}, _cms.get("n") or 0
        _pool.sort(key=lambda c: (-_cmap.get(c["sym"], 0),
                                  _prio.get(c.get("verdict"), 2), -c.get("combo", 0)))
        _nsend = st.slider("How many picks to send", 5, 20, 10, key="cb_tgn")
        st.caption(f"Filter: 🎯 PERFECT + ✅ MATCH + UPTREND · {len(_pool)} of "
                   f"{len(combos)} qualify · each pick arrives with full BUY/SL/T1/T2 plan and "
                   "one-tap 📈 Google · 📊 TradingView buttons.")
        if st.button("📤 SEND to Telegram now", key="cb_tg_go", **STRETCH):
            if not _pool:
                st.info("No PERFECT / UPTREND picks on the board right now — scan again later.")
            else:
                _sel = _pool[:_nsend]
                _tot = len(_sel)
                _prg = st.progress(0.0, text="📤 Sending picks…")
                tg_send(f"\U0001F3AF <b>COMBO PICKS \u00b7 {now_ist().strftime('%H:%M')}</b>\n"
                        f"<i>{_tot} pick(s) \u00b7 PERFECT &amp; UPTREND first \u00b7 full plan below \u2014 "
                        f"tap a button under any stock to open it</i>")
                _ok_n = 0
                for _i, c in enumerate(_sel, 1):
                    _msg = (f"\U0001F3AF <b>{_esc(c['name'])}</b> \u00b7 {c.get('verdict', '\u2014')}\n"
                            f"\U0001F4C8 {str(c.get('sig', '')).title()} \u00b7 {c.get('dtr', '')} \u00b7 "
                            f"conf {c.get('conf', 0):.0f}% \u00b7 score {c.get('combo', 0):.0f}\n"
                            f"\U0001F4B0 Now <code>\u20B9{c['price']:,.2f}</code> \u00b7 "
                            f"<b>{c['chg_day']:+.2f}%</b> today\n"
                            f"\U0001F7E2 BUY <code>\u20B9{c.get('buy_at') or 0:,.2f}</code> \u00b7 "
                            f"\U0001F6D1 SL <code>\u20B9{c.get('sl') or 0:,.2f}</code>\n"
                            f"\U0001F3AF T1 <code>\u20B9{c.get('t1') or 0:,.2f}</code> \u00b7 "
                            f"\u2705 T2 <code>\u20B9{c.get('t2') or 0:,.2f}</code>\n"
                            f"\U0001F6E1\uFE0F support \u20B9{c.get('support') or 0:,.2f} \u00b7 "
                            f"\U0001F6A7 resist \u20B9{c.get('resistance') or 0:,.2f}")
                    if _cmap.get(c["sym"], 0) >= 2:
                        _msg += f"\n\U0001F3C5 STABLE \u00b7 appeared {_cmap[c['sym']]}/{_cmn} morning scans"
                    if c.get("near52"):
                        _msg += "\n\U0001F3D8\uFE0F Near 52-WEEK HIGH"
                    if tg_send(_msg, buttons=stock_buttons(c["sym"])):
                        _ok_n += 1
                    _prg.progress(_i / _tot, text=f"\U0001F4E4 Sent {_i}/{_tot}\u2026")
                    time.sleep(0.6)
                _prg.empty()
                if _ok_n:
                    st.success(f"\u2705 Sent {_ok_n} picks (full plans + open buttons) to all phones.")
                else:
                    st.error("Couldn't send \u2014 check the \U0001F514 Telegram box settings on the \u26A1 tab.")


def dashboard_tab(ss, mst_s, ml, mm):
    MONO = "ui-monospace,Menlo,Consolas,monospace"

    # ♾️ AUTO-RESUME — the terminal keeps running across page refreshes
    if not ss.get("dash_watch"):
        _rt = rt_load().get("dash") or {}
        if _rt.get("watch"):
            ss["dash_watch"] = _rt["watch"]
            ss["dash_names"] = _rt.get("names") or {}
            _st = _rt.get("state") or {}
            if _st.get("rows"):
                for r in _st["rows"].values():
                    r.pop("spark", None)
                ss["dash"] = _st
            ss["dash_per"] = _rt.get("per") or "5d"
            if _rt.get("iv"):
                ss["dash_iv"] = _rt["iv"]
            if _rt.get("auto") is not None:
                ss["dash_auto"] = _rt["auto"]
            ss["_dash_resumed"] = True

    # ---------- settings ----------
    with st.expander("⚙️ WATCHLIST · SPEED · REFRESH", expanded=not ss.get("dash_watch")):
        c1, c2 = st.columns(2)
        with c1:
            _keys = list(DASH_SRC.keys())
            _full = _keys.index("🌐 Full NSE (auto-fill to your count)") if "🌐 Full NSE (auto-fill to your count)" in _keys else 0
            src = st.selectbox("Universe", _keys, index=_full, key="dash_src")
            custom_txt = ""
            if DASH_SRC.get(src) == "custom":
                custom_txt = st.text_area("Symbols (comma/space separated · max 500)",
                                          placeholder="RELIANCE, TCS, SUZLON, ZENSARTECH …",
                                          height=80, key="dash_custom")
            n_sel = st.slider("How many stocks (minimum 200 recommended)", 100, 500, 500, 50, key="dash_n",
                              help="Full-NSE fills up to this many. The board GUARANTEES at least "
                                   "min(200, list size) live stocks — missing symbols are auto-retried.")
        with c2:
            dash_iv = st.selectbox("Timeframe", ["5m", "15m", "30m", "1h"], index=1, key="dash_iv")
            st.checkbox("⚡ Light mode (5d history — fastest, recommended for 300–500 stocks)",
                        value=True, key="dash_light")
            st.slider("Stocks refreshed per cycle (stalest first)", 50, 500, 200, 50, key="dash_batch",
                      help="Each cycle re-downloads only this many — the whole board rotates, "
                           "so it stays live without hammering Yahoo.")
        b1, b2, b3 = st.columns(3)
        with b1:
            start = st.button("🚀 START TERMINAL", type="primary", **STRETCH, key="dash_start")
        with b2:
            refresh_now = st.button("🔄 Refresh a batch now", **STRETCH, key="dash_refresh_btn")
        with b3:
            wipe = st.button("🧹 Clear board", **STRETCH, key="dash_wipe")

    if wipe:
        ss["dash_watch"] = None; ss["dash"] = None
        rt_clear("dash")

    if start:
        watch, names = build_watchlist(src, n_sel, custom_txt)
        ss["dash_watch"] = watch
        ss["dash_names"] = names
        ss["dash"] = None
        ss["dash_per"] = "5d" if ss.get("dash_light", True) else DASH_PER.get(ss.get("dash_iv", "15m"), "1mo")

    watch = ss.get("dash_watch")
    if not watch:
        st.markdown("<div style='background:#0b1220;border-radius:20px;padding:56px;text-align:center;'>"
                    "<div style='font-size:52px;'>🔴</div>"
                    "<div style='font-size:22px;font-weight:900;color:#f1f5f9;margin-top:10px;'>"
                    "LIVE MARKET TERMINAL</div>"
                    "<div style='color:#64748b;font-size:13px;margin-top:8px;'>"
                    "Up to 500 NSE stocks · guaranteed 200+ live · uptrend leaderboard · flip alerts · "
                    "who JUST turned uptrend · NIFTY pulse</div>"
                    "<div style='color:#94a3b8;font-size:12px;margin-top:14px;'>↑ Choose a universe and press "
                    "<b style='color:#22c55e;'>🚀 START TERMINAL</b></div></div>", unsafe_allow_html=True)
        return

    if ss.get("_dash_resumed"):
        ss["_dash_resumed"] = False
        st.info("♾️ Terminal resumed automatically — a page refresh does NOT stop it. "
                "Press 🧹 Clear board to end the session.")

    iv = ss.get("dash_iv", "15m")
    per = ss.get("dash_per") or "5d"
    batch = ss.get("dash_batch", 200)

    if start or not ss.get("dash"):
        with st.spinner("🔴 First sweep — building the live board (guaranteeing 200+)…"):
            dash_refresh(ss, watch, iv, per, batch=len(watch), progress=True,
                         ensure_min=min(200, len(watch)))
    if refresh_now or ss.get("dash_auto"):
        dash_refresh(ss, watch, iv, per, batch=batch,
                     ensure_min=min(200, len(watch)) if len(ss.get("dash", {}).get("rows", {})) < 200 else 0)

    # ♾️ persist the running terminal — survives page refresh, resumes anywhere
    try:
        _st8 = ss.get("dash") or {}
        _rows8 = {k: {kk: vv for kk, vv in v.items() if kk != "spark"}
                  for k, v in (_st8.get("rows") or {}).items()}
        rt_save("dash", watch=watch, names=ss.get("dash_names") or {}, per=per, iv=iv,
                auto=bool(ss.get("dash_auto")), state={**_st8, "rows": _rows8})
    except Exception:
        pass

    state = ss.get("dash") or {"rows": {}, "alerts": []}
    rows = state.get("rows", {})
    data = list(rows.values())
    holes = len(watch) - len(rows)
    now = time.time()
    ages = [now - r["ts"] for r in data]
    avg_age = (sum(ages) / len(ages)) if ages else 0

    # ================= PANEL 1 — TERMINAL HEADER =================
    idx = fetch_indices()
    def _idx_cell(lbl, d):
        if not d:
            return f"<div style='text-align:center;opacity:.45;'><div style='color:#64748b;font-size:9px;font-weight:800;letter-spacing:1px;'>{lbl}</div><div style='color:#64748b;font-size:12px;'>—</div></div>"
        c = "#22c55e" if d["chg"] >= 0 else "#ef4444"
        return (f"<div style='text-align:center;'><div style='color:#64748b;font-size:9px;font-weight:800;letter-spacing:1px;'>{lbl}</div>"
                f"<div style='color:#f1f5f9;font-weight:900;font-size:15px;font-family:{MONO};'>{d['price']:,.1f}</div>"
                f"<div style='color:{c};font-size:11px;font-weight:800;font-family:{MONO};'>{d['chg']:+.2f}%</div></div>")
    live_c = "#22c55e" if len(rows) >= min(200, len(watch)) else "#f59e0b"
    st.markdown(_H(f"""
    <div style='background:linear-gradient(135deg,#0b1220,#0f172a);border:1px solid #1e293b;border-radius:18px;
    padding:16px 22px;margin-bottom:12px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:14px;'>
      <div><div style='display:flex;align-items:center;gap:9px;'>
        <span style='width:10px;height:10px;border-radius:50%;background:#22c55e;display:inline-block;
        box-shadow:0 0 10px #22c55e;'></span>
        <span style='color:#f1f5f9;font-size:19px;font-weight:900;letter-spacing:.5px;'>LIVE MARKET TERMINAL</span></div>
        <div style='color:#64748b;font-size:11px;margin-top:3px;font-family:{MONO};'>
        {len(rows):,}/{len(watch):,} stocks live · avg age {_fmt_age(avg_age)} · tf {iv} ·
        {'light' if per=='5d' else 'full'} mode · {datetime.now().strftime('%d %b %H:%M:%S')}</div></div>
      <div style='display:flex;gap:18px;align-items:center;flex-wrap:wrap;'>
        {_idx_cell('NIFTY 50', idx.get('NIFTY 50'))}
        {_idx_cell('BANK NIFTY', idx.get('BANK NIFTY'))}
        <div style='text-align:center;'><div style='color:#64748b;font-size:9px;font-weight:800;letter-spacing:1px;'>BOARD</div>
        <div style='color:{live_c};font-size:13px;font-weight:900;font-family:{MONO};'>
        {'✓ 200+ GUARANTEED' if len(rows)>=200 else f'{len(rows)} live' + (' · filling…' if holes>0 else '')}</div>
        <div style='color:#64748b;font-size:10px;'>{ml}</div></div>
      </div></div>"""), unsafe_allow_html=True)

    if not data:
        st.info("No data yet — press 🔄 Refresh a batch now.")
        return

    # live controls row
    q1, q2 = st.columns([1, 1])
    with q1:
        st.checkbox("🔴 LIVE auto-refresh (keeps scanning — late uptrends get caught)", value=False, key="dash_auto")
    with q2:
        st.selectbox("Every", ["1 min", "2 min", "3 min", "5 min"], index=1, key="dash_int")

    # ── 🧠 DAY MEMORY — ONE snapshot/day (today's board), verified next day ──
    try:
        _st = ss.get("dash") or {}
        if rows and time.time() - _st.get("last_snap", 0) > 600:
            if snaps_save(rows):
                ss["dash"]["last_snap"] = time.time()
    except Exception:
        pass
    mc1, mc2 = st.columns([3, 1])
    with mc1:
        _ls = (ss.get("dash") or {}).get("last_snap", 0)
        st.markdown("<div style='background:#0f172a;border:1px dashed #1e293b;border-radius:10px;padding:7px 12px;"
                    "color:#64748b;font-size:11px;'>🧠 <b style='color:#94a3b8;'>Day memory (1/day):</b> "
                    f"today's board last saved {datetime.fromtimestamp(_ls, TZ_IST).strftime('%d %b %H:%M') if _ls else '— (saves automatically once the board is live)'}"
                    f" · 1 snapshot per day · memory: {_ukey()} · verify next day in the 🌙 EOD Review tab</div>", unsafe_allow_html=True)
    with mc2:
        if st.button("📸 Snapshot now", key="dash_snap", **STRETCH):
            if snaps_save(rows):
                ss["dash"]["last_snap"] = time.time()
                st.success("✅ Today's calculation saved — verify it tomorrow in 🌙 EOD Review.")
            else:
                st.error("Couldn't write snapshot file.")

    # ================= PANEL 2 — KPI STRIP =================
    n_up = sum(1 for r in data if r["dtr"] == "UPTREND")
    n_dn = sum(1 for r in data if r["dtr"] == "DOWNTREND")
    n_sd = len(data) - n_up - n_dn
    sbuy = sum(1 for r in data if r["sig"] in ("STRONG BUY", "BUY"))
    ssell = sum(1 for r in data if r["sig"] in ("STRONG SELL", "SELL"))
    adv = sum(1 for r in data if r["chg"] > 0); dec = sum(1 for r in data if r["chg"] < 0)
    tot = len(data)
    pu = adv / tot * 100; pd_ = dec / tot * 100; pf = 100 - pu - pd_
    kpis = (_kpi("📈 UPTREND", n_up, f"{n_up/tot*100:.0f}% of board", "#22c55e")
            + _kpi("📉 DOWNTREND", n_dn, f"{n_dn/tot*100:.0f}% of board", "#ef4444")
            + _kpi("➡️ SIDEWAYS", n_sd, f"{n_sd/tot*100:.0f}% of board", "#94a3b8")
            + _kpi("🟢 BUY SIGNALS", sbuy, f"strong: {sum(1 for r in data if r['sig']=='STRONG BUY')}", "#4ade80")
            + _kpi("🔴 SELL SIGNALS", ssell, f"strong: {sum(1 for r in data if r['sig']=='STRONG SELL')}", "#f87171"))
    st.markdown(f"<div style='display:flex;gap:10px;flex-wrap:wrap;margin-bottom:10px;'>{kpis}</div>", unsafe_allow_html=True)
    st.markdown(_H(f"""<div style='background:#0f172a;border:1px solid #1e293b;border-radius:14px;padding:12px 16px;margin-bottom:12px;'>
    <div style='display:flex;height:14px;border-radius:7px;overflow:hidden;'>
    <div style='background:#16a34a;width:{pu:.1f}%;'></div><div style='background:#334155;width:{pf:.1f}%;'></div>
    <div style='background:#dc2626;width:{pd_:.1f}%;'></div></div>
    <div style='display:flex;justify-content:space-between;color:#64748b;font-size:11px;font-weight:700;margin-top:6px;font-family:{MONO};'>
    <span style='color:#22c55e;'>▲ {adv} advancing ({pu:.0f}%)</span>
    <span>MARKET BREADTH — TODAY</span>
    <span style='color:#ef4444;'>▼ {dec} declining ({pd_:.0f}%)</span></div></div>"""), unsafe_allow_html=True)

    # ================= PANEL 3 — FLIP ALERTS =================
    alerts = state.get("alerts", [])
    if alerts:
        chips = "".join(f"<span style='background:rgba(245,158,11,.12);border:1px solid rgba(245,158,11,.35);color:#fbbf24;"
                        f"font-size:11px;font-weight:700;padding:4px 10px;border-radius:8px;margin:3px 4px 3px 0;display:inline-block;'>"
                        f"⏱ {a['ts']} · <b>{a['name']}</b> · {a['txt']}</span>" for a in alerts[:14])
        st.markdown(f"<div style='background:#0f172a;border:1px solid #1e293b;border-radius:14px;padding:12px 16px;margin-bottom:12px;'>"
                    f"<div style='color:#f59e0b;font-size:11px;font-weight:900;letter-spacing:1px;margin-bottom:6px;'>🔔 LIVE FLIP ALERTS — signals & trends changing now</div>"
                    f"{chips}</div>", unsafe_allow_html=True)

    # ================= PANEL 4 — UPTREND LEADERBOARD =================
    ups = sorted([r for r in data if r["dtr"] == "UPTREND"], key=lambda x: -x["score"])
    st.markdown(_H(f"""<div style='background:#0b1220;border:1px solid #14532d;border-radius:18px;padding:16px 18px;margin-bottom:12px;'>
    <div style='display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;'>
    <div style='color:#4ade80;font-size:15px;font-weight:900;letter-spacing:.5px;'>🚀 UPTREND LEADERBOARD
    <span style='color:#64748b;font-size:12px;font-weight:600;'>· {len(ups)} stocks rising now · ranked by score</span></div>
    <div style='color:#64748b;font-size:10px;font-family:{MONO};'>CONF bar · SCORE bar · 15m sparkline</div></div></div>"""),
                unsafe_allow_html=True)
    if not ups:
        st.markdown("<div style='background:#0f172a;border:1px solid #1e293b;border-radius:14px;padding:18px;color:#94a3b8;"
                    "font-size:13px;'>No clean daily uptrend on this board right now — that's information too. "
                    "Keep 🔴 LIVE on; the 🆕 panel below will flag the moment one turns.</div>", unsafe_allow_html=True)
    else:
        top_show = ups[:100]
        rows_html = "".join(_lb_row(i + 1, r, now) for i, r in enumerate(top_show))
        st.markdown(rows_html, unsafe_allow_html=True)
        if len(ups) > 40:
            chips = "".join(f"<span style='background:rgba(34,197,94,.10);border:1px solid rgba(34,197,94,.3);color:#86efac;"
                            f"font-size:11px;font-weight:700;padding:3px 10px;border-radius:14px;margin:2px 3px 2px 0;display:inline-block;'>"
                            f"{r['name']} {r['chg']:+.1f}%</span>" for r in ups[40:120])
            st.markdown(f"<div style='margin-top:6px;'>{chips}</div>", unsafe_allow_html=True)
        # analyze buttons for top 12
        st.markdown("<div style='color:#64748b;font-size:11px;font-weight:800;margin:8px 0 6px;'>🔍 OPEN FULL ANALYSIS — top setups:</div>",
                    unsafe_allow_html=True)
        show_btn = ups[:12]
        for rr in range(0, len(show_btn), 4):
            cols = st.columns(4)
            for cc_, r in zip(cols, show_btn[rr:rr + 4]):
                with cc_:
                    if st.button(f"📊 {r['name'][:14]}", key=f"dg_{r['sym']}", **STRETCH):
                        ss["sym"] = r["sym"]; ss["stock_name"] = r["name"]; ss["analyzed"] = True
                        st.success(f"✅ {r['name']} loaded — open the '📊 Analyze Stock' tab.")

    # ================= PANEL 5 — JUST TURNED UPTREND =================
    fresh = sorted([r for r in data if r.get("up_since") and now - r["up_since"] < 3600],
                   key=lambda x: -x["score"])
    if fresh:
        chips = "".join(f"<span style='background:rgba(34,197,94,.14);border:1px solid #22c55e;color:#4ade80;"
                        f"font-size:12px;font-weight:800;padding:5px 12px;border-radius:9px;margin:3px 4px 3px 0;display:inline-block;'>"
                        f"🆕 {r['name']} · since {datetime.fromtimestamp(r['up_since']).strftime('%H:%M')} · {r['chg']:+.1f}% · score {r['score']:.0f}</span>"
                        for r in fresh[:25])
        st.markdown(f"<div style='background:#0f172a;border:1px solid #14532d;border-radius:14px;padding:12px 16px;margin-bottom:12px;'>"
                    f"<div style='color:#4ade80;font-size:11px;font-weight:900;letter-spacing:1px;margin-bottom:6px;'>"
                    f"🆕 JUST TURNED UPTREND (last 60 min) — the late movers you asked for</div>{chips}</div>",
                    unsafe_allow_html=True)

    # ================= PANEL 6 — DOWNTREND =================
    dns = sorted([r for r in data if r["dtr"] == "DOWNTREND"], key=lambda x: x["sp"], reverse=True)
    if dns:
        chips = "".join(f"<span style='background:rgba(239,68,68,.10);border:1px solid rgba(239,68,68,.35);color:#f87171;"
                        f"font-size:11px;font-weight:700;padding:3px 10px;border-radius:14px;margin:2px 3px 2px 0;display:inline-block;'>"
                        f"{r['name']} {r['chg']:+.1f}%</span>" for r in dns[:40])
        st.markdown(_H(f"""<div style='background:#0b1220;border:1px solid #7f1d1d;border-radius:16px;padding:14px 16px;margin-bottom:12px;'>
        <div style='color:#f87171;font-size:13px;font-weight:900;margin-bottom:6px;'>📉 DOWNTREND — {len(dns)} stocks
        <span style='color:#64748b;font-size:11px;font-weight:600;'>· avoid longs · top 40 shown</span></div>{chips}</div>"""),
                    unsafe_allow_html=True)

    # ================= PANEL 7 — SECTOR BREADTH =================
    sec_chips = ""
    for sn, sdict in SECTORS_FOR_BREADTH.items():
        mem = [rows[s] for s in sdict.values() if s in rows]
        if not mem:
            continue
        upn = sum(1 for r in mem if r["dtr"] == "UPTREND")
        pctu = upn / len(mem) * 100
        clr = "#4ade80" if pctu >= 60 else "#fbbf24" if pctu >= 40 else "#f87171"
        sec_chips += (f"<span style='background:#0f172a;border:1px solid #1e293b;color:{clr};font-size:11px;"
                      f"font-weight:800;padding:4px 12px;border-radius:9px;margin:3px 4px 3px 0;display:inline-block;'>"
                      f"{sn} · {upn}/{len(mem)} up ({pctu:.0f}%)</span>")
    if sec_chips:
        st.markdown(f"<div style='background:#0b1220;border:1px solid #1e293b;border-radius:14px;padding:12px 16px;margin-bottom:12px;'>"
                    f"<div style='color:#94a3b8;font-size:11px;font-weight:900;letter-spacing:1px;margin-bottom:6px;'>🏭 SECTOR BREADTH — who is in an uptrend</div>"
                    f"{sec_chips}</div>", unsafe_allow_html=True)

    # ================= DEEP-DIVE TABS (top 6) =================
    top6 = ups[:6] if ups else []
    if top6:
        st.markdown('<div class="sh">🔍 DEEP DIVE — TOP 6 UPTREND SETUPS</div>', unsafe_allow_html=True)
        tbs = st.tabs([f"{r['name'][:11]} · {r['conf']:.0f}%" for r in top6])
        for tb, r in zip(tbs, top6):
            with tb:
                k1, k2, k3, k4 = st.columns(4)
                with k1: st.metric("Price", f"₹{r['price']:,.2f}", f"{r['chg']:+.2f}% today")
                with k2: st.metric("Signal", r["sig"], f"{r['conf']:.0f}% conf")
                with k3: st.metric("Daily trend", "🟢 UPTREND", "score " + f"{r['score']:.0f}")
                with k4: st.metric("200 EMA", "Above ⬆" if r["above200"] else "Below ⬇",
                                   (f"₹{r['ema200']:,.2f}" if r.get("ema200") else "—"))
                try:
                    st.plotly_chart(spark_fig(r), **STRETCH)
                except Exception:
                    pass
                st.markdown(f"<div class='sc-r'><b style='color:{r['sc']};'>{r['act']}</b><div style='color:#cbd5e1;"
                            f"font-size:12px;margin-top:6px;'>Entry ₹{r['buy_at']:.2f} · Stop ₹{r['sl']:.2f} · "
                            f"T1 ₹{r['t1']:.2f} · T2 ₹{r['t2']:.2f} · R:R 1:{r['rr']} · intraday: {r['itrend'].title()} · "
                            f"RSI {r['rsi']:.0f} · vol {r['vr']:.1f}x avg</div>"
                            f"<div style='color:#64748b;font-size:11px;margin-top:4px;'>Quick plan from the live board — the full "
                            f"Analyze tab adds pivots, Fibonacci, circuits, news & ML.</div></div>", unsafe_allow_html=True)
                if st.button(f"📊 Open FULL analysis → {r['name'][:14]}", key=f"dt_{r['sym']}",
                             **STRETCH, type="primary"):
                    ss["sym"] = r["sym"]; ss["stock_name"] = r["name"]; ss["analyzed"] = True
                    st.success("Loaded — open the '📊 Analyze Stock' tab.")

    # ================= DATA TABLE + CSV =================
    with st.expander("📋 Full data table · CSV export · load any stock"):
        def _n(v, nd=1):
            try:
                return None if (v is None or (isinstance(v, float) and np.isnan(v))) else round(float(v), nd)
            except Exception:
                return None
        disp_rows = [{
            "Stock": r["name"], "Symbol": r["sym"], "Price": round(r["price"], 2),
            "% Today": r["chg"], "Signal": r["sig"], "Conf": r["conf"],
            "Buy%": r["bp"], "Sell%": r["sp"], "D-Trend": r["dtr"],
            "200EMA": ("Above" if r["above200"] else "Below") if r["above200"] is not None else "—",
            "I-Momentum": r["itrend"].title(), "RSI": _n(r["rsi"]), "ADX": _n(r["adx"]),
            "Vol×": r["vr"], "Score": r["score"], "Buy@": r["buy_at"], "SL": r["sl"],
            "T2": r["t2"], "R:R": r["rr"], "AgeS": _n(now - r["ts"], 0),
        } for r in sorted(data, key=lambda x: -x["score"])]
        disp = pd.DataFrame(disp_rows)
        try:
            st.dataframe(disp, **STRETCH, height=440, hide_index=True)
        except Exception:
            st.dataframe(disp, **STRETCH)
        lc1, lc2 = st.columns([2, 1])
        with lc1:
            pick = st.text_input("Load any board stock into the Analyze tab — type its exact name (e.g. HAL)",
                                 placeholder="Exact name from the table…", key="dash_pick")
        with lc2:
            st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
            if st.button("📊 Load into Analyze tab", key="dash_load", **STRETCH):
                hit = [r for r in data if r["name"].upper() == (pick or "").strip().upper()]
                if hit:
                    ss["sym"] = hit[0]["sym"]; ss["stock_name"] = hit[0]["name"]; ss["analyzed"] = True
                    st.success(f"✅ {hit[0]['name']} loaded — open the '📊 Analyze Stock' tab.")
                else:
                    st.warning("Type the exact stock name as shown in the table (e.g. HAL).")
        try:
            st.download_button("⬇️ Download board as CSV", data=disp.to_csv(index=False).encode(),
                               file_name=f"live_board_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                               mime="text/csv", **STRETCH)
        except Exception:
            pass

    st.markdown("<div style='color:#64748b;font-size:11px;margin-top:8px;'>⚠️ Live board = live data, but signals are "
                "probabilities, not predictions. Open the full analysis (and always use a stop) before trading. "
                "Educational use only.</div>", unsafe_allow_html=True)

    # ---- auto-refresh hook ----
    if ss.get("dash_auto") and mst_s == "open":   # 🛌 after close: no auto-tick
        secs = {"1 min": 60, "2 min": 120, "3 min": 180, "5 min": 300}[ss.get("dash_int", "2 min")]
        _smooth = False
        try:
            from streamlit_autorefresh import st_autorefresh
            st_autorefresh(interval=secs * 1000, key="dash_tick")
            _smooth = True
        except Exception:
            _smooth = False
        if not _smooth:
            st.info(f"🔴 LIVE (basic mode) — refreshing the stalest batch every {secs}s. "
                    "For perfectly smooth auto-refresh:  pip install streamlit-autorefresh")
            try:
                time.sleep(secs)
            except Exception:
                pass
            try:
                st.rerun()
            except RuntimeError:
                pass



# ============================================================
# 🌙 EOD REVIEW TAB — before vs after (did the board get it right?)
# ============================================================
def eod_review_tab(ss):
    st.markdown(_H("""<div style='background:linear-gradient(135deg,#1e1b4b,#312e81);border-radius:18px;
    padding:20px 24px;margin-bottom:16px;'>
    <div style='color:white;font-size:20px;font-weight:900;'>🌙 EOD REVIEW — before vs after</div>
    <div style='color:#c7d2fe;font-size:13px;margin-top:6px;'>The 🔴 dashboard saves a <b>memory snapshot</b>
    automatically — ONE snapshot per day (that day's calculation) — exactly what it showed you. Pick a day below and press
    VERIFY: the app fetches what prices <b>ACTUALLY did afterwards</b> and scores every call — how many stocks went
    as per the calculation, how many hit T1/T2, how many hit the stop. This is your real accuracy record.</div></div>"""),
                unsafe_allow_html=True)
    _uk = _ukey()
    _shared = _uk == "main"
    uc1, uc2, uc3 = st.columns([2.3, 1.4, 1])
    with uc1:
        st.markdown("<div style='background:" + ("#3f2d04;border:1px solid #f59e0b" if _shared else "#04260f;border:1px solid #16a34a") +
                    ";border-radius:10px;padding:8px 12px;color:#d1d5db;font-size:11.5px;'>🧑‍🤝‍🧑 Your memory name: <b style=\"" +
                    ("#fbbf24" if _shared else "#4ade80") + "\">" + _uk + "</b>" +
                    (" — <b>shared default.</b> If a friend also uses this app, each of you must set your own name here "
                     "(any word). Then memories, scorecards and journals can never mix." if _shared else
                     " — your own separate memory ✓ (snapshots, scorecard & journal are yours alone)") + "</div>",
                    unsafe_allow_html=True)
    with uc2:
        _nm = st.text_input("memory name", value="", key="mu_name", placeholder="type a name… e.g. ravi",
                            label_visibility="collapsed")
    with uc3:
        st.markdown("<div style='height:2px;'></div>", unsafe_allow_html=True)
        if st.button("🔗 Use this name", key="mu_go", **STRETCH):
            _clean = "".join(ch for ch in _nm.strip().lower() if ch.isalnum() or ch in "_-")[:16]
            if _clean:
                st.query_params["u"] = _clean
                st.rerun()
            else:
                st.error("Type a name first (letters/numbers).")

    with st.expander("💾 Where is my data saved? · Backup & Restore (Streamlit Cloud)"):
        st.markdown(_H("""<div style='background:#0f172a;border:1px solid #1e293b;border-radius:12px;padding:12px 16px;
        color:#94a3b8;font-size:12px;line-height:1.8;'>
        ● <b style='color:#e2e8f0;'>On your own PC:</b> memory saves automatically in the same folder as this app —
        one set of files <b>per person</b> (<code>board_snapshots_NAME.json</code>, <code>eod_results_NAME.json</code>,
        <code>trade_journal_NAME.json</code>; NAME is your memory name, "main" if not set) — permanent, nothing to upload.<br>
        ● <b style='color:#e2e8f0;'>On Streamlit Cloud:</b> the files live inside the app's private cloud container —
        they survive while the app runs/sleeps, but are <b style='color:#f87171;'>wiped whenever the app redeploys</b>
        (each GitHub update). VERIFY always works (it fetches live market prices by itself) — only past days' memory
        needs restoring: press ⬇️ Backup before you update the app, and ⬆️ Restore after.</div>"""),
                    unsafe_allow_html=True)
        _bk = {"snapshots": snaps_load(), "eod": eod_load(),
               "exported": datetime.now().strftime("%Y-%m-%d %H:%M")}
        st.download_button("⬇️ Backup memory (download .json)", data=_json.dumps(_bk).encode(),
                           file_name=f"ai_trader_memory_{_ukey()}_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                           mime="application/json", **STRETCH, key="eod_backup_dl")
        _up = st.file_uploader("⬆️ Restore memory (.json backup)", type=["json"], key="eod_restore")
        if _up is not None:
            try:
                _d = _json.loads(_up.read().decode("utf-8"))
                _news = _newe = 0
                _olds = snaps_load(); _ids = {s.get("id") for s in _olds}
                _srcs = _d.get("snapshots") if isinstance(_d, dict) else (_d if isinstance(_d, list) else [])
                _add = [s for s in _srcs if isinstance(s, dict) and s.get("id") and s.get("id") not in _ids and s.get("rows")]
                if _add:
                    _json.dump(sorted(_olds + _add, key=lambda x: x.get("saved", ""))[-40:],
                               open(snap_file(), "w", encoding="utf-8"))
                    _news = len(_add)
                if isinstance(_d, dict) and _d.get("eod"):
                    _olde = eod_load(); _eids = {x.get("id") for x in _olde}
                    _adde = [x for x in _d["eod"] if isinstance(x, dict) and x.get("id") not in _eids]
                    if _adde:
                        _json.dump(sorted(_olde + _adde, key=lambda x: x.get("date", ""))[-100:],
                                   open(eod_file(), "w", encoding="utf-8"), indent=2)
                        _newe = len(_adde)
                if _news or _newe:
                    st.success(f"✅ Restored {_news} day-snapshots + {_newe} scorecard entries — pick a day below.")
                else:
                    st.info("Nothing new in that backup (I already have it all).")
            except Exception as _e:
                st.error(f"Couldn't read that backup: {_e}")

    snaps = snaps_load()
    if not snaps:
        st.info("🧠 No board memory yet. Open the 🔴 Live Dashboard tab → START TERMINAL → let it run "
                "(a snapshot saves automatically within seconds of the board going live) → come back here.")
        return
    snaps = sorted(snaps, key=lambda s: s.get("saved", ""), reverse=True)
    _tdy = datetime.now().strftime("%Y-%m-%d")
    labels = [f"{s['saved']}  ·  {len(s['rows'])} stocks  ·  "
              + ("✅ full results ready" if s['saved'][:10] < _tdy else "⏳ today · partial so far")
              for s in snaps]
    _defi = next((i for i, s in enumerate(snaps) if s['saved'][:10] < _tdy), 0)
    c1, c2 = st.columns([3, 1])
    with c1:
        si = st.selectbox("WHICH DAY'S calculation (the ‘before’) should I verify?", labels, index=_defi, key="eod_snap")
    with c2:
        st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
        go = st.button("▶ VERIFY NOW (the ‘after’)", type="primary", **STRETCH, key="eod_go")
    snap = snaps[labels.index(si)]
    st.caption("How it works: pick YESTERDAY'S calculation → VERIFY → the app itself fetches today's real market "
               "prices (Yahoo) and scores every call — direction accuracy, T1/T2 hits, stops. No manual file work: "
               "comparing with the market is always automatic.")
    if go:
        with st.spinner(f"🔍 Fetching what actually happened after {snap['saved']} …"):
            try:
                results, summary = verify_snapshot(snap)
                ss["eod_cache"] = {"id": snap["id"], "results": results, "summary": summary}
                if summary.get("n_valid", 0) >= max(10, int(summary["checked"] * 0.2)):
                    eod_save({"id": snap["id"], "date": snap["saved"][:10],
                              **{k: summary[k] for k in ("checked", "n_up", "up_ok", "up_acc",
                                                          "n_buy", "n_t1", "n_sl", "buy_wr")}})
            except Exception as e:
                st.error(f"Verification failed: {type(e).__name__}: {e}")
    cached = ss.get("eod_cache")
    if cached and cached.get("id") == snap.get("id"):
        s = cached["summary"]; res = cached["results"]
        st.markdown(f"<div style='background:#0f172a;border:1px solid #1e293b;border-radius:14px;padding:12px 16px;"
                    f"margin-bottom:12px;color:#94a3b8;font-size:12px;'>🔎 Verified snapshot <b>{s['snap']}</b> "
                    f"· {s['checked']} stocks checked against real prices after that time</div>", unsafe_allow_html=True)
        if s.get("n_valid", 0) == 0:
            st.markdown(_H(f"""<div style='background:#3f2d04;border:1px solid #f59e0b;border-radius:12px;
            padding:14px 18px;margin-bottom:12px;color:#fde68a;font-size:13px;line-height:1.8;'>
            <b style='color:#fbbf24;font-size:15px;'>⚠️ Nothing could be verified yet — this is NOT 0% accuracy.</b><br>
            Every stock came back <b>NO DATA</b>: the app could not download any prices after this snapshot
            right now. Usual reasons:<br>
            1. You verified <b>before the next trading session finished</b> — verify after <b>~3:30 PM IST</b>
            on a trading day.<br>
            2. The snapshot was saved <b>after market close or on a weekend/holiday</b> — its "next day"
            hasn't traded yet.<br>
            3. Yahoo didn't answer from the server just then (it throttles cloud servers) — simply
            <b>press VERIFY again</b>.<br>
            Latest market candle the app can see right now:
            <b>{s.get('last_candle') or 'unknown — Yahoo not answering, press VERIFY again'}</b>.
            Nothing was saved to the scorecard for this attempt.</div>"""), unsafe_allow_html=True)
        elif s.get("n_valid", 0) < s["checked"] * 0.5:
            st.warning(f"⚠️ Only {s['n_valid']}/{s['checked']} stocks could be verified — Yahoo throttling. "
                       "Press VERIFY again to fill in the rest before trusting these numbers.")
        _acc_txt = f"{s['up_acc']:.0f}%" if s.get("up_acc") is not None else "—"
        _wr_txt = f"{s['buy_wr']:.0f}%" if s.get("buy_wr") is not None else "—"
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        with m1: st.metric("Stocks checked", s["checked"], f"{s.get('n_valid', 0)} with real data")
        with m2: st.metric("📈 Uptrend calls", s["n_up"], f"avg move {s['avg_up']:+.2f}%")
        with m3: st.metric("Uptrend accuracy", _acc_txt, f"{s['up_ok']}/{s['n_up']} closed higher")
        with m4: st.metric("🔴 Downtrend avg", f"{s['avg_dn']:+.2f}%", "avoid-long list")
        with m5: st.metric("BUY signals", s["n_buy"], f"{s['n_t1']} hit T1/T2 · {s['n_sl']} hit SL")
        with m6: st.metric("Buy win-rate", _wr_txt, "of resolved (T1 vs SL)")
        acc = max(0.0, min(100.0, s["up_acc"])) if s.get("up_acc") is not None else None
        if acc is not None:
            st.markdown(_H(f"""<div style='background:#0f172a;border:1px solid #1e293b;border-radius:12px;padding:12px 16px;margin-bottom:12px;'>
            <div style='display:flex;height:14px;border-radius:7px;overflow:hidden;'>
            <div style='background:#16a34a;width:{acc:.1f}%;'></div>
            <div style='background:#334155;width:{100-acc:.1f}%;'></div></div>
            <div style='display:flex;justify-content:space-between;color:#64748b;font-size:11px;font-weight:700;margin-top:6px;'>
            <span style='color:#22c55e;'>▲ {s['up_ok']} calls right</span>
            <span>BOARD DIRECTION ACCURACY</span>
            <span style='color:#ef4444;'>▼ {s['n_up'] - s['up_ok']} calls wrong</span></div></div>"""),
                        unsafe_allow_html=True)
        okr = sorted([x for x in res if isinstance(x.get("moved"), (int, float))], key=lambda x: -x["moved"])
        if okr:
            best = "".join(f"<span style='background:rgba(34,197,94,.14);border:1px solid #22c55e;color:#4ade80;"
                           f"font-size:11px;font-weight:800;padding:4px 10px;border-radius:9px;margin:3px 4px 3px 0;display:inline-block;'>"
                           f"👍 {x['name']} {x['moved']:+.1f}%</span>" for x in okr[:10])
            worst = "".join(f"<span style='background:rgba(239,68,68,.12);border:1px solid rgba(239,68,68,.4);color:#f87171;"
                            f"font-size:11px;font-weight:800;padding:4px 10px;border-radius:9px;margin:3px 4px 3px 0;display:inline-block;'>"
                            f"👎 {x['name']} {x['moved']:+.1f}%</span>" for x in okr[-10:][::-1])
            st.markdown(f"<div style='background:#0b1220;border:1px solid #1e293b;border-radius:14px;padding:12px 16px;"
                        f"margin-bottom:12px;'><div style='color:#94a3b8;font-size:11px;font-weight:900;margin-bottom:6px;'>"
                        f"🎯 BEST calls after this snapshot</div>{best}"
                        f"<div style='color:#94a3b8;font-size:11px;font-weight:900;margin:10px 0 6px;'>💀 WORST calls</div>{worst}</div>",
                        unsafe_allow_html=True)
        disp = pd.DataFrame([{
            "Stock": x.get("name"), "Symbol": x.get("sym"),
            "Signal@snap": x.get("sig"), "Trend@snap": x.get("dtr"),
            "Price@snap": x.get("price"), "After_Last": x.get("last"),
            "Moved%": x.get("moved"), "High": x.get("hi"), "Low": x.get("lo"),
            "T1": x.get("t1"), "T2": x.get("t2"), "SL": x.get("sl"),
            "Outcome": x.get("outcome"), "Score@snap": x.get("score"),
        } for x in res])
        try:
            st.dataframe(disp, **STRETCH, height=420, hide_index=True)
        except Exception:
            st.dataframe(disp, **STRETCH)
        try:
            st.download_button("⬇️ Download EOD review (CSV)", data=disp.to_csv(index=False).encode(),
                               file_name=f"eod_review_{snap['id']}.csv", mime="text/csv",
                               **STRETCH)
        except Exception:
            pass
    hist = eod_load()
    if hist:
        with st.expander(f"🏦 Scorecard history — {len(hist)} past verifications"):
            h = pd.DataFrame([{"Date": d.get("date"), "Stocks": d.get("checked"),
                               "UptrendCalls": d.get("n_up"), "UptrendAcc%": d.get("up_acc"),
                               "Buys": d.get("n_buy"), "T1/T2Wins": d.get("n_t1"),
                               "SLosses": d.get("n_sl"), "BuyWinRate%": d.get("buy_wr")}
                              for d in sorted(hist, key=lambda x: x.get("date", ""), reverse=True)])
            try:
                st.dataframe(h, **STRETCH, hide_index=True)
            except Exception:
                st.dataframe(h, **STRETCH)
            st.caption("Memory files live next to the app, one set per person (memory name) — "
                       "on your PC they persist forever; on Streamlit Cloud they survive until the app redeploys.")


# ============================================================
# SCANNER
# ============================================================
def resolve_category(cat):
    d = CAT_MAP.get(cat)
    if d is None:
        uni = fetch_universe()
        return dict(uni["name_map"])
    return d


def scan_one(args):
    name, sym, iv, per = args
    try:
        res = run_analysis(sym, iv, per)
        if not res:
            return None
        plan = make_plan(res['price'], res['atr'], None, res['sig'])
        return {
            'name': name, 'sym': sym, 'price': res['price'], 'sig': res['sig'], 'sc': res['sc'],
            'conf': res['conf'], 'bp': res['bp'], 'sp': res['sp'], 'atr': res['atr'],
            'tr': res['trend'], 'vr': res['vr'], 'gap': plan['gap_pct'], 'act': plan['act'],
            'sit': plan['sit'], 'ac': plan['ac'], 'buy_at': plan['buy_at'], 'sl': plan['sl'],
            't1': plan['t1'], 't2': plan['t2'], 't3': plan['t3'], 't2p': plan['t2p'],
            't1p': plan['t1p'], 't3p': plan['t3p'], 'sl_pct': plan['sl_pct'], 'rr': plan['rr'],
        }
    except Exception:
        return None


def run_scan(stocks, iv, per, min_conf, stype, workers=10, cap_n=None, stats_out=None):
    items = list(stocks.items())
    if cap_n:
        items = items[:cap_n]
    args = [(n, s, iv, per) for n, s in items]
    results = []; total = len(args); cnt = [0]

    def _pass(todo, label):
        got = 0
        bar = st.progress(0); stat = st.empty()
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(scan_one, a): a for a in todo}
            for f in concurrent.futures.as_completed(futs):
                cnt[0] += 1
                bar.progress(min(cnt[0] / total, 1.0))
                stat.markdown(f"<div style='background:#16233d;border:1px solid #bfdbfe;border-radius:8px;"
                              f"padding:8px 16px;display:inline-block;color:#60a5fa;font-size:13px;font-weight:600;'>"
                              f"🔍 {label} {min(cnt[0], total)}/{total} · ✅ data OK {len(results)}</div>",
                              unsafe_allow_html=True)
                try:
                    r = f.result(timeout=15)
                    if r:
                        results.append(r); got += 1
                except Exception:
                    pass
        bar.empty(); stat.empty()
        return got

    ok = _pass(args, "Scanning")
    # ── anti-throttle: if Yahoo didn't answer for many stocks, retry them ONCE
    done_syms = {r["sym"] for r in results}
    todo2 = [a for a in args if a[1] not in done_syms]
    retried = 0
    if todo2 and len(todo2) > max(5, int(total * 0.2)):
        cnt[0] = total - len(todo2)
        retried = _pass(todo2[:400], "Retrying failed (Yahoo throttle)")
    if stats_out is not None:
        stats_out["total"] = total
        stats_out["ok"] = len({r["sym"] for r in results})
        stats_out["fails"] = max(total - stats_out["ok"], 0)
    results = [r for r in results if MIN_PRICE <= (r.get("price") or 0) <= MAX_PRICE]
    if stype == "BUY":
        results = [r for r in results if r['conf'] >= min_conf and r['bp'] > r['sp'] and r['sit'] not in ('SELL', 'GAP_DN')]
        results.sort(key=lambda x: (x['tr'] == 'UPTREND', x['bp'], x['conf']), reverse=True)
    elif stype == "SELL":
        results = [r for r in results if r['conf'] >= min_conf and r['sp'] > r['bp']]
        results.sort(key=lambda x: x['sp'], reverse=True)
    else:
        results = [r for r in results if r['conf'] >= min_conf]
        results.sort(key=lambda x: x['conf'], reverse=True)
    return results


# ============================================================
# MAIN APP
# ============================================================
def blog(msg):
    """🗒️ boot log — every key step with a timestamp, so a stall can be located
    in one glance:  cat /opt/app/boot_log.txt"""
    try:
        with open(f"boot_log_{_ukey()}.txt", "a", encoding="utf-8") as f:
            f.write(f"{now_ist().strftime('%H:%M:%S')} {msg}\n")
    except Exception:
        pass


def deploy_wipe():
    """🧹 FRESH DEPLOY = CLEAN SLATE — when APP_VERSION changes, erase ALL
    market data (sessions, boards, caches, snapshots, rankings). Credentials
    (Upstox token, Telegram) are KEPT — only data dies."""
    import glob
    wiped = 0
    try:
        vfn = f"last_version_{_ukey()}.txt"
        last = ""
        try:
            last = open(vfn, encoding="utf-8").read().strip()
        except Exception:
            pass
        if last == APP_VERSION:
            return False
        _u = _ukey()   # 🎯 wipe ONLY this desk's data — the main app is untouchable
        for pat in (f"runtime_{_u}.json", f"universe_rank_{_u}_*.json", f"board_snapshots_{_u}*.json",
                    f"cons_state_{_u}.json", f"conscfg_{_u}.json", f"eod_results_{_u}*.json",
                    f"alerts_{_u}*.json", f"candle_cache_{_u}*.pkl"):
            for f in glob.glob(pat):
                try:
                    _os.remove(f)
                    wiped += 1
                except Exception:
                    pass
        try:
            open(vfn, "w", encoding="utf-8").write(APP_VERSION)
        except Exception:
            pass
    except Exception:
        pass
    blog(f"🧹 deploy wipe · {APP_VERSION} · {wiped} data files erased (creds kept)")
    return True


def main():
    ss = st.session_state
    deploy_wipe()   # 🧹 program updated → ALL previous data erased, fresh start
    blog(f"boot · {APP_VERSION} · market={mkt_status()[0]}")
    defaults = {'analyzed': False, 'sym': 'RELIANCE.NS', 'stock_name': 'RELIANCE',
                'capital': 10000, 'target': 500, 'iv': '15m', 'per': '1mo',
                'scan_results': None, 'search_results': None}
    for k, v in defaults.items():
        if k not in ss:
            ss[k] = v
    mst_s, ml, mm = mkt_status()
    tg_daily_cleanup()   # no-op now: auto-delete disabled — messages stay
    pass   # 🎯 COMBO DESK: the MAIN app handles morning purge + ONLINE messages
    try:                  # 🧹 NEW-DAY RESET — yesterday's data never leaks into today
        _nd = now_ist().strftime("%Y-%m-%d")
        if (rt_load().get("dayrst") or {}).get("day") != _nd:
            _keepcap = (rt_load().get("co") or {}).get("cap")   # 💰 capital survives the reset
            for _eng in ("co", "cb", "mv", "bc", "cons"):   # dead sessions + old boards/alerts/snapshots
                rt_clear(_eng)
            if _keepcap:
                rt_save("co", cap=_keepcap)
            for _k in ("co_log", "co_feed", "co_volc", "co_ctx", "mv_alerts", "bc_alerts",
                       "cb", "co_pos", "dash", "mv", "bc", "bc_prev", "mv_prevform", "cb_ranked_swapped"):
                ss.pop(_k, None)
            rt_save("dayrst", day=_nd)
    except Exception:
        pass
    pass   # 🎯 (avoids double ONLINE messages)
    mclr = "#22c55e" if mst_s == "open" else "#f59e0b" if mst_s == "pre" else "#ef4444"

    # live breadth badge for the navbar once the dashboard has data
    dash_state = ss.get("dash") or {}
    drows = dash_state.get("rows", {})
    breadth_badge = ""
    if drows:
        up = sum(1 for r in drows.values() if r["dtr"] == "UPTREND")
        dn = sum(1 for r in drows.values() if r["dtr"] == "DOWNTREND")
        breadth_badge = (f"<div style='background:rgba(255,255,255,0.12);border-radius:10px;padding:8px 16px;'>"
                         f"<div style='color:#fbbf24;font-weight:700;font-size:12px;'>🔴 Live board</div>"
                         f"<div style='color:white;font-weight:900;font-size:16px;'>📈{up} · 📉{dn} · {len(drows)} watched</div></div>")

    st.markdown(_H(f"""<div class='navbar'><div style='display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;'>
    <div><span style='font-size:28px;font-weight:900;color:white;'>💹 Claude AI Trade Pro</span>
    <span style='font-size:14px;color:#93c5fd;margin-left:12px;'>{_esc(APP_VERSION)}</span></div>
    <div style='display:flex;gap:12px;align-items:center;flex-wrap:wrap;'>
    <div style='background:rgba(255,255,255,0.15);border-radius:10px;padding:8px 16px;text-align:center;'>
    <div style='color:{mclr};font-weight:700;font-size:13px;'>{ml}</div><div style='color:#93c5fd;font-size:10px;'>{mm}</div></div>
    {breadth_badge}
    <div style='background:rgba(255,255,255,0.12);border-radius:10px;padding:8px 16px;'>
    <div style='color:#fbbf24;font-weight:700;font-size:12px;'>Focus</div><div style='color:white;font-weight:900;font-size:16px;'>Uptrend + Levels</div></div>
    </div></div></div>"""), unsafe_allow_html=True)

    # ── 🎯 FOUR PANELS: scan + RESULTS + 🚀 HOT MOVERS + 🔄 D2U ──
    _tab_cb, _tab_res, _tab_hot, _tab_d2u = st.tabs(
        ["🎯 COMBO SCAN", "🏅 99% RESULTS", "🚀 HOT MOVERS", "🔄 DOWN-TO-UP"])
    with _tab_cb:
        try:
            combo_tab(ss, mst_s)
        except Exception as e:
            st.warning(f"⚠️ Combo problem: {type(e).__name__}: {e}")
    with _tab_res:
        try:
            results_tab()
        except Exception as e:
            st.warning(f"⚠️ Results problem: {type(e).__name__}: {e}")
    with _tab_hot:
        try:
            hot_movers_tab(ss)
        except Exception as e:
            st.warning(f"⚠️ Hot movers problem: {type(e).__name__}: {e}")
    with _tab_d2u:
        try:
            d2u_tab(ss)
        except Exception as e:
            st.warning(f"⚠️ Down-to-up problem: {type(e).__name__}: {e}")

    st.markdown("<div style='text-align:center;color:#64748b;font-size:10px;padding:16px;border-top:2px solid #1e293b;margin-top:20px;'>⚠️ EDUCATIONAL PURPOSE ONLY · NOT FINANCIAL ADVICE · ALWAYS USE STOP LOSS · TRADE AT YOUR OWN RISK · Past performance ≠ future results</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
