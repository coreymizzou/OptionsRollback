import sqlite3, json
conn = sqlite3.connect('scanner_data_live.db')
rows = conn.execute("SELECT id, ticker, strategy, notes FROM positions WHERE status='OPEN' AND strategy LIKE '%SPREAD%'").fetchall()
for r in rows:
    print(f"#{r[0]} {r[1]} {r[2]}")
    try:
        notes = json.loads(r[3] or '{}')
        print(f"  notes: {notes}")
    except:
        print(f"  raw notes: {r[3]}")
conn.close()
