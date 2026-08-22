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
try:
    cur.execute('SELECT * FROM "SUSPENSE_DATA_FACUL_CLEAN" LIMIT 0')
    cols = [desc[0] for desc in cur.description]
    print("Columns in DB via cursor description:", cols)
except Exception as e:
    print("Error:", e)
