import sqlite3
conn = sqlite3.connect('scanner_data.db')
conn.execute("UPDATE positions SET status='OPEN', exit_time=NULL, exit_price=NULL, exit_reason=NULL, realized_pnl=NULL, realized_r=NULL WHERE id=73")
conn.commit()
conn.close()
print('XOM #73 reopened')
