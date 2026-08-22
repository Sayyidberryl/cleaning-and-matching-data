import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
engine = create_engine('postgresql+psycopg2://viy4user:fild42op61nx@10.10.125.91:5432/fsi_db')

with engine.connect() as conn:
    print('FACUL rows:', conn.execute(text('SELECT COUNT(*) FROM "SUSPENSE_DATA_FACUL_CLEAN"')).scalar())
    print('OSBAL rows:', conn.execute(text('SELECT COUNT(*) FROM "SUSPENSE_DATA_OSBAL_CLEAN"')).scalar())
