import os, requests
from datetime import datetime

api_key = os.environ.get("TRADIER_API_KEY", "")
if not api_key:
    print("ERROR: TRADIER_API_KEY not set")
    exit()

positions = [
    {"id": 32, "ticker": "MSFT",  "strike": 415.0, "exp": "2026-05-15", "type": "call", "entry": 14.12, "contracts": 1},
    {"id": 33, "ticker": "GOOGL", "strike": 340.0, "exp": "2026-05-15", "type": "call", "entry": 8.94,  "contracts": 1},
    {"id": 34, "ticker": "AAPL",  "strike": 270.0, "exp": "2026-05-15", "type": "call", "entry": 9.57,  "contracts": 1},
    {"id": 35, "ticker": "META",  "strike": 695.0, "exp": "2026-05-15", "type": "call", "entry": 21.58, "contracts": 1},
    {"id": 36, "ticker": "GLD",   "strike": 450.0, "exp": "2026-05-15", "type": "call", "entry": 7.48,  "contracts": 1},
]

headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
total_pnl = 0

print(f"P&L Verification — {datetime.now().strftime('%H:%M:%S')}")
print("=" * 70)

for p in positions:
    r = requests.get(
        "https://api.tradier.com/v1/markets/options/chains",
        headers=headers,
        params={"symbol": p["ticker"], "expiration": p["exp"], "greeks": "false"},
        timeout=8
    )
    if r.status_code != 200:
        print(f"#{p['id']} {p['ticker']} — Tradier error {r.status_code}")
        continue

    options = r.json().get("options", {}).get("option", []) or []
    match = next((c for c in options
                  if abs(float(c.get("strike", 0)) - p["strike"]) < 0.01
                  and c.get("option_type", "").lower() == p["type"]), None)

    if not match:
        print(f"#{p['id']} {p['ticker']} — contract not found in chain")
        continue

    bid  = float(match.get("bid", 0) or 0)
    ask  = float(match.get("ask", 0) or 0)
    last = float(match.get("last", 0) or 0)
    mid  = round((bid + ask) / 2, 2) if bid > 0 and ask > 0 else last

    pnl     = round((mid - p["entry"]) * 100 * p["contracts"], 2)
    r_mult  = round(pnl / (p["entry"] * 100 * p["contracts"]), 2)
    total_pnl += pnl

    sign = "+" if pnl >= 0 else ""
    print(f"#{p['id']} {p['ticker']:5} {p['strike']} CALL | "
          f"entry=${p['entry']:.2f} bid={bid} ask={ask} mid={mid:.2f} | "
          f"P&L: {sign}${pnl:.2f} ({r_mult:+.2f}R)")

print("=" * 70)
sign = "+" if total_pnl >= 0 else ""
print(f"Total P&L: {sign}${total_pnl:.2f}")
print("\nNote: market is closed — these are EOD prices, may differ from intraday highs")
