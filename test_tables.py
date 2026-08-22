from sqlalchemy import create_engine, inspect, text
from dotenv import load_dotenv
import os

load_dotenv()
db_user = os.environ.get("DB_USER")
db_pass = os.environ.get("DB_PASS")
db_host = os.environ.get("DB_HOST")
db_port = os.environ.get("DB_PORT")
db_name = os.environ.get("DB_NAME")

conn_str = f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
engine = create_engine(conn_str)

inspector = inspect(engine)
tables = inspector.get_table_names()

target_tables = [
    "SUSPENSE_DATA_FACUL_CLEAN",
    "SUSPENSE_DATA_OSBAL_CLEAN",
    "SUSPENSE_DATA_SUSPENSE_V1",
    "SUSPENSE_DATA_SUSPENSE_V2",
    "suspense_data_facul_clean",
    "suspense_data_osbal_clean",
    "suspense_data_suspense_v1",
    "suspense_data_suspense_v2",
]

print(f"Total tables in DB: {len(tables)}")
found = False
for t in target_tables:
    if t in tables:
        found = True
        print(f"Table '{t}' found.")
        with engine.connect() as conn:
            try:
                res = conn.execute(text(f'SELECT * FROM "{t}" LIMIT 1'))
                row = res.fetchone()
                print(f"  -> Can read from '{t}'. Rows exist: {bool(row)}")
            except Exception as e:
                print(f"  -> Error reading from '{t}': {e}")
                
if not found:
    print("None of the target tables were found.")
