import sqlite3

# Connect to the database
conn = sqlite3.connect('tickers.db')
cursor = conn.cursor()

# Create table if it does not exist
cursor.execute('''
CREATE TABLE IF NOT EXISTS tickers (
	id INTEGER PRIMARY KEY,
	symbol TEXT NOT NULL,
	Name TEXT NOT NULL
)
''')

# Insert a sample record if it does not exist
cursor.execute("INSERT OR IGNORE INTO tickers (symbol, Name) VALUES ('TSLA', 'Tesla')")

# Update the symbol name
cursor.execute("UPDATE tickers SET Name = 'Tesla Inc' WHERE symbol = 'TSLA'")

# Commit the changes and close the connection
conn.commit()
conn.close()