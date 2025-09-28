import sqlite3
import os

db = os.path.join(os.path.dirname(__file__), '..', 'instance', 'wedding.db')
db = os.path.abspath(db)
print('DB path:', db)
conn = sqlite3.connect(db)
rows = list(conn.execute("PRAGMA table_info('guest')"))
if not rows:
    print('No guest table or empty schema')
else:
    print('guest table columns:')
    for r in rows:
        print(r)
conn.close()
