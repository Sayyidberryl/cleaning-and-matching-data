import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
db_user = os.environ.get('DB_USER', 'postgres')
db_pass = os.environ.get('DB_PASS', 'postgres')
db_host = os.environ.get('DB_HOST', 'localhost')
db_port = os.environ.get('DB_PORT', '5432')
db_name = os.environ.get('DB_NAME', 'postgres')

conn = psycopg2.connect(
    dbname=db_name,
    user=db_user,
    password=db_pass,
    host=db_host,
    port=db_port
)

cur = conn.cursor()
# Find all empty tables (0 columns)
cur.execute("""
    SELECT t.table_name
    FROM information_schema.tables t
    LEFT JOIN information_schema.columns c
      ON t.table_name = c.table_name AND t.table_schema = c.table_schema
    WHERE t.table_schema = 'public'
    GROUP BY t.table_name
    HAVING COUNT(c.column_name) = 0
""")
empty_tables = [row[0] for row in cur.fetchall()]
print("Empty tables (0 columns):", empty_tables)

