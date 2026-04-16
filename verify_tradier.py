import os, requests
from datetime import datetime

api_key = os.environ.get("TRADIER_API_KEY", "")
if not api_key:
    print("ERROR: TRADIER_API_KEY not set")
    exit()

base = "https://api.tradier.com/v1"
headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}

print(f"Testing Tradier API at {datetime.now().strftime('%H:%M:%S')}")
print(f"Key: ...{api_key[-6:]}\n")

# Test 1: Stock quote
print("── Stock quote (AAPL) ──")
r = requests.get(f"{base}/markets/quotes", headers=headers,
                 params={"symbols": "AAPL"}, timeout=8)
print(f"Status: {r.status_code}")
if r.status_code == 200:
    q = r.json()["quotes"]["quote"]
    print(f"Last: ${q['last']}  Change: {q['change']}  Volume: {q['volume']:,}")
    from datetime import timezone
    ts = datetime.fromtimestamp(q['trade_date']/1000)
    print(f"Trade time: {ts.strftime('%Y-%m-%d %H:%M:%S')}")
    age_mins = (datetime.now() - ts).total_seconds() / 60
    if age_mins < 5:
        print(f"✓ REAL-TIME data (age: {age_mins:.1f} min)")
    elif age_mins < 20:
        print(f"⚠ Possibly delayed (age: {age_mins:.1f} min)")
    else:
        print(f"✗ DELAYED data (age: {age_mins:.1f} min)")

# Test 2: Option chain for one of your positions
print("\n── Option chain (NVDA May 1 165 PUT) ──")
r2 = requests.get(f"{base}/markets/options/chains", headers=headers,
                  params={"symbol": "NVDA", "expiration": "2026-05-01", "greeks": "false"},
                  timeout=8)
print(f"Status: {r2.status_code}")
if r2.status_code == 200:
    options = r2.json().get("options", {}).get("option", []) or []
    match = next((c for c in options
                  if abs(float(c.get("strike",0)) - 165.0) < 0.01
                  and c.get("option_type","").lower() == "put"), None)
    if match:
        bid  = match.get("bid", 0)
        ask  = match.get("ask", 0)
        mid  = round((bid + ask) / 2, 2) if bid and ask else None
        print(f"NVDA 165 PUT: bid={bid} ask={ask} mid={mid}")
        print(f"✓ Option chain data returned ({len(options)} contracts total)")
    else:
        print(f"NVDA 165 PUT not found ({len(options)} contracts returned)")
else:
    print(f"Error: {r2.text[:200]}")

print("\n── Summary ──")
print("If both tests show ✓ your system is getting live Tradier data")
