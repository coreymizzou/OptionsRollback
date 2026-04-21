import sqlite3
conn = sqlite3.connect('scanner_data_live.db')
conn.execute("UPDATE positions SET stop_price = round(entry_price * 0.67, 2), target_price = round(entry_price * 1.66, 2) WHERE status = 'OPEN'")
conn.commit()
print('Updated', conn.total_changes, 'positions')
conn.close()
