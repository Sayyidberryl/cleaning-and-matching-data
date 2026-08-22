import re

def insert_postgres_logic(file_path, table_name, insert_before):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Remove any existing postgres blocks to be safe
    content = re.sub(r'# ---------------------------------------------------------\s*# EXPORT TO POSTGRESQL.*?except Exception as e:\s*print\(f"  \[WARN\] PostgreSQL export failed: \{e\}"\)\s*', '', content, flags=re.DOTALL)
    content = re.sub(r'# ---------------------------------------------------------\s*# EXPORT TO POSTGRESQL.*?except Exception as e:\s*print\(f"      -> Database export failed: \{e\}"\)\s*', '', content, flags=re.DOTALL)

    postgres_block = f"""
    # ---------------------------------------------------------
    # EXPORT TO POSTGRESQL
    # ---------------------------------------------------------
    import os
    from sqlalchemy import create_engine
    from dotenv import load_dotenv
    
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
        df.to_sql(table_name, con=engine, if_exists="append", index=False)
        print(f"      -> Successfully exported {{len(df):,}} rows to table '{{table_name}}'")
    except Exception as e:
        print(f"  [WARN] PostgreSQL export failed: {{e}}")
"""

    if insert_before in content:
        content = content.replace(insert_before, postgres_block + "\n" + insert_before)
    else:
        print(f"ERROR: {insert_before} not found in {file_path}")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

insert_postgres_logic("C:/Users/berryl/Desktop/starcore/indore/production_script/cleaning_facul.py", "table_facul_clean_2026", '    print(f"\\n{\'=\' * 50}")')
insert_postgres_logic("C:/Users/berryl/Desktop/starcore/indore/production_script/cleaning_osbal.py", "table_osbal_clean_2026", '    print(f"\\n{\'=\' * 50}")')
insert_postgres_logic("C:/Users/berryl/Desktop/starcore/indore/production_script/prod_sus_1.py", "table_suspense_ver1_2026", '    elapsed = time.perf_counter() - t_start')
insert_postgres_logic("C:/Users/berryl/Desktop/starcore/indore/production_script/prod_sus_2.py", "table_suspense_ver2_2026", '    elapsed = time.perf_counter() - t_start')

print("All files updated successfully")
