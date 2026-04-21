import sqlite3
conn = sqlite3.connect('scanner_data.db')
conn.row_factory = sqlite3.Row
rows = conn.execute(
    "SELECT id, ticker, strategy, option_type, strike, expiration, "
    "entry_price, contracts, entry_time FROM positions WHERE status='OPEN' ORDER BY id"
).fetchall()
for r in rows:
    d = dict(r)
    print(f"#{d['id']} {d['ticker']} | {d['strategy']} | {d['option_type']} | "
          f"strike={d['strike']} | exp={d['expiration']} | "
          f"entry=${d['entry_price']} | contracts={d['contracts']} | {d['entry_time'][:16]}")
