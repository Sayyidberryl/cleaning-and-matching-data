import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

db_user = os.environ.get("DB_USER", "postgres")
db_pass = os.environ.get("DB_PASS", "postgres")
db_host = os.environ.get("DB_HOST", "localhost")
db_port = os.environ.get("DB_PORT", "5432")
db_name = os.environ.get("DB_NAME", "postgres")

conn_str = f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
engine = create_engine(conn_str)

tables = [
    "SUSPENSE_DATA_FACUL_CLEAN",
    "SUSPENSE_DATA_OSBAL_CLEAN",
    "SUSPENSE_DATA_SUSPENSE_V1",
    "SUSPENSE_DATA_SUSPENSE_V2"
]

with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
    for table in tables:
        try:
            conn.execute(text(f'ALTER TABLE "{table}" DROP COLUMN IF EXISTS "FLAG_ROW";'))
            conn.execute(text(f'ALTER TABLE "{table}" DROP COLUMN IF EXISTS flag_row;'))
            print(f"Dropped FLAG_ROW from {table} (if it existed)")
        except Exception as e:
            print(f"Error dropping from {table}: {e}")

print("Done")
