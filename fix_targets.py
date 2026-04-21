import sqlite3
conn = sqlite3.connect('scanner_data_live.db')
conn.execute("UPDATE positions SET target_price = round(entry_price * 1.50, 2) WHERE status = 'OPEN'")
conn.commit()
print('Updated', conn.total_changes, 'positions')
conn.close()
