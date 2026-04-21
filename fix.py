import sqlite3, json

conn = sqlite3.connect('scanner_data.db')
row = conn.execute("SELECT value FROM system_state WHERE key='action_state'").fetchone()
state = json.loads(row[0])

state['actions']['73'] = 'HOLD'
state['confidences']['73'] = 0.0

conn.execute("UPDATE system_state SET value=? WHERE key='action_state'", (json.dumps(state),))
conn.commit()
print('Done')