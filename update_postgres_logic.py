import re

files_to_update = [
    ("C:/Users/berryl/Desktop/starcore/indore/production_script/cleaning_facul.py", "table_facul_clean_2026"),
    ("C:/Users/berryl/Desktop/starcore/indore/production_script/cleaning_osbal.py", "table_osbal_clean_2026"),
    ("C:/Users/berryl/Desktop/starcore/indore/production_script/prod_sus_1.py", "table_suspense_ver1_2026"),
    ("C:/Users/berryl/Desktop/starcore/indore/production_script/prod_sus_2.py", "table_suspense_ver2_2026"),
]

old_block_pattern = r'# ---------------------------------------------------------\s*# EXPORT TO POSTGRESQL.*?(?:try:.*?df\.to_sql.*?except Exception as e:.*?print\(f"\s*\[WARN\] PostgreSQL export failed: \{e\}"\))'

for file_path, table_name in files_to_update:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    new_block = f"""# ---------------------------------------------------------
    # EXPORT TO POSTGRESQL
    # ---------------------------------------------------------
    from dotenv import load_dotenv
    from sqlalchemy import create_engine, text
    import os
    load_dotenv()
    
    print("  Exporting to PostgreSQL ...")
    db_user = os.environ.get("DB_USER", "postgres")
    db_pass = os.environ.get("DB_PASS", "postgres")
    db_host = os.environ.get("DB_HOST", "localhost")
    db_port = os.environ.get("DB_PORT", "5432")
    db_name = os.environ.get("DB_NAME", "postgres")
    
    conn_str = f"postgresql+psycopg2://{{db_user}}:{{db_pass}}@{{db_host}}:{{db_port}}/{{db_name}}"
    try:
        engine = create_engine(conn_str)
        table_name = "{table_name}"
        
        # Hapus isi tabel jika sudah ada (update tanpa drop struktur table), atau buat jika belum ada
        with engine.begin() as conn:
            try:
                conn.execute(text(f"DELETE FROM {{table_name}}"))
            except Exception:
                pass # Tabel mungkin belum ada
                
        df.to_sql(table_name, con=engine, if_exists="append", index=False)
        print(f"      -> Successfully exported {{len(df):,}} rows to table '{{table_name}}'")
    except Exception as e:
        print(f"  [WARN] PostgreSQL export failed: {{e}}")"""

    content = re.sub(old_block_pattern, new_block, content, flags=re.DOTALL)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

print("Update complete")
