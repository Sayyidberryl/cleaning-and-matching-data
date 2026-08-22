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

conn.autocommit = True
cur = conn.cursor()

tables_to_drop = [
    "SUSPENSE_DATA_OSBAL_CLEAN",
    "SUSPENSE_DATA_SUSPENSE_V1",
    "SUSPENSE_DATA_SUSPENSE_V2"
]

for tbl in tables_to_drop:
    try:
        cur.execute(f'DROP TABLE IF EXISTS "{tbl}"')
        print(f"Dropped empty table: {tbl}")
    except Exception as e:
        print(f"Error dropping {tbl}: {e}")
