import re

files_to_update = [
    "C:/Users/berryl/Desktop/starcore/indore/production_script/prod_sus_1.py",
    "C:/Users/berryl/Desktop/starcore/indore/production_script/prod_sus_2.py"
]

for file_path in files_to_update:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # The pattern to match the engine.begin() block
    pattern = r'# Hapus isi tabel jika sudah ada \(update tanpa drop struktur table\), atau buat jika belum ada\s+with engine\.begin\(\) as conn:\s+try:\s+conn\.execute\(text\(f"DELETE FROM \{table_name\}"\)\)\s+except Exception:\s+pass # Tabel mungkin belum ada'

    # Remove the block
    new_content = re.sub(pattern, "", content)
    
    # Also I need to remove the broken duplicate block in prod_sus_2.py if it exists
    broken_pattern = r'    try:\s+engine = create_engine\(conn_str\)\s+table_name = "table_suspense_ver2_2026"\s+df\.to_sql\(table_name, con=engine, if_exists="append", index=False\)\s+print\(f"      -> Successfully exported \{len\(df\):,\} rows to table \'\{table_name\}\'"\)\s+except Exception as e:\s+print\(f"      -> Database export failed: \{e\}"\)\s+try:\s+'
    new_content = re.sub(broken_pattern, "    try:\n        ", new_content)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)

print("Logic removed successfully")
