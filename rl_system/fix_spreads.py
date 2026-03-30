"""
Run this once to fix existing spread positions that are missing short leg data.
Place in your Options folder and run: python3 fix_spreads.py
"""
import sqlite3, json, os

db_path = 'scanner_data.db'
if not os.path.exists(db_path):
    db_path = 'rl_system/scanner_data.db'

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

rows = conn.execute(
    "SELECT id, ticker, strategy, notes, raw_scanner_data FROM positions WHERE status='OPEN'"
).fetchall()

updated = 0
for r in rows:
    d = dict(r)
    strategy = (d.get("strategy") or "").upper()

    if "SPREAD" not in strategy:
        continue

    # Check if notes already has short leg data
    try:
        notes = json.loads(d.get("notes") or "{}")
        if notes.get("spread") and notes.get("short_strike"):
            print(f"#{d['id']} {d['ticker']} — already has short leg data, skipping")
            continue
    except Exception:
        pass

    # Try to get short leg from raw_scanner_data
    short_strike   = None
    short_opt_type = None
    try:
        raw = json.loads(d.get("raw_scanner_data") or "{}")
        short_leg = raw.get("trade", {}).get("short_leg", {})
        if short_leg:
            short_strike   = short_leg.get("strike")
            short_opt_type = short_leg.get("option_type")
    except Exception:
        pass

    if short_strike:
        new_notes = json.dumps({
            "short_strike":      short_strike,
            "short_option_type": short_opt_type,
            "spread":            True
        })
        conn.execute(
            "UPDATE positions SET notes = ? WHERE id = ?",
            (new_notes, d["id"])
        )
        print(f"#{d['id']} {d['ticker']} — updated with short_strike={short_strike} type={short_opt_type}")
        updated += 1
    else:
        print(f"#{d['id']} {d['ticker']} — no short leg found in raw_scanner_data")
        print(f"  You'll need to update manually. Strategy: {d['strategy']}")

conn.commit()
conn.close()
print(f"\nDone — {updated} position(s) updated")
