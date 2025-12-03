import yfinance as yf
import requests
from datetime import datetime
import pytz
import re

TZ_NY = pytz.timezone('America/New_York')
today = datetime.now(TZ_NY).date()

# Safe defaults
score = 0
current_price = sma200 = 500
weekly_return = overnight_pct = dxy_change = tnx_change_bps = 0.0
vix = 20.0
breadth_50 = 50.0

# SPY data
try:
    spy = yf.Ticker("SPY")
    hist = spy.history(period="2y")
    if len(hist) > 0:
        current_price = hist['Close'].iloc[-1]
        sma200 = hist['Close'].rolling(200).mean().iloc[-1] if len(hist) >= 200 else current_price
    weekly = spy.history(period="3mo", interval="1wk")
    if len(weekly) >= 2:
        weekly_return = (weekly['Close'].iloc[-1] / weekly['Close'].iloc[-2] - 1) * 100
except: pass

# Overnight futures
try:
    html = requests.get("https://www.investing.com/indices/us-spx-500-futures", headers={'User-Agent': 'Mozilla/5.0'}).text
    match = re.search(r'last_price">([\d,]+\.?\d*)', html)
    if match:
        overnight_pct = (float(match.group(1).replace(',', '')) / current_price - 1) * 100
except: pass

# VIX
try:
    vix = yf.Ticker("^VIX").history(period="5d")['Close'].iloc[-1]
except: pass

# Dollar & yields
try:
    dxy = yf.Ticker("DX-Y.NYB").history(period="5d")['Close']
    if len(dxy) >= 2: dxy_change = (dxy.iloc[-1]/dxy.iloc[-2]-1)*100
    tnx = yf.Ticker("^TNX").history(period="5d")['Close']
    if len(tnx) >= 2: tnx_change_bps = (tnx.iloc[-1]-tnx.iloc[-2])*100
except: pass

# Breadth
try:
    html = requests.get("https://www.barchart.com/stocks/indices/sp/market-summary", headers={'User-Agent': 'Mozilla/5.0'}).text
    match = re.search(r'% Above 50-Day Average.*?(\d+\.\d+)%', html, re.DOTALL)
    if match: breadth_50 = float(match.group(1))
except: pass

# Scoring
score += 1 if current_price > sma200 else -1
score += 1 if weekly_return >= 2 else (-1 if weekly_return <= -2 else 0)
score += 1 if overnight_pct >= 0.3 else (-1 if overnight_pct <= -0.3 else 0)
score += 1 if vix < 20 else (-1 if vix > 25 else 0)
score += 1 if dxy_change < 0 and tnx_change_bps < 0 else (-1 if dxy_change > 0 and tnx_change_bps > 0 else 0)
score += 1 if breadth_50 > 60 else (-1 if breadth_50 < 40 else 0)

bias = "STRONG BULLISH" if score >= 4 else "BULLISH" if score >= 2 else "NEUTRAL" if score > -2 else "BEARISH" if score > -4 else "STRONG BEARISH"

result = f"""=== DAILY BIAS — {today.strftime('%A, %B %d, %Y')} ===
Score       : {score}/6
Trend (200SMA) : {'Above (+1)' if current_price > sma200 else 'Below (-1)'}
Weekly mom  : {weekly_return:+5.2f}%
Overnight   : {overnight_pct:+5.2f}%
VIX         : {vix:.1f}
DXY + 10Y   : {dxy_change:+.2f}% / {tnx_change_bps:+.1f}bps
Breadth 50d : {breadth_50:.1f}%

>>> FINAL BIAS: {bias} <<<"""

print(result)
with open("latest_bias.txt", "w") as f:
    f.write(result)
