import pandas as pd
import sqlite3

files = ['stops.txt', 'routes.txt', 'trips.txt', 'stop_times.txt']
db_name = 'bmtc.db'

conn = sqlite3.connect(db_name)

print(f"DB '{db_name}' created")

for file in files:
    table_name = file.split('.')[0].lower()

    df = pd.read_csv(file)

    df.to_sql(table_name, conn, if_exists='replace', index=False)
    print(f"Table '{table_name}' created and populated successfully.")

conn.close()
print("DB setup complete.")