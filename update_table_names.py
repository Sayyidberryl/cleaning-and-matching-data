import re

replacements = {
    "C:/Users/berryl/Desktop/starcore/indore/production_script/cleaning_facul.py": ("table_facul_clean_2026", "SUSPENSE_DATA_FACUL_CLEAN"),
    "C:/Users/berryl/Desktop/starcore/indore/production_script/cleaning_osbal.py": ("table_osbal_clean_2026", "SUSPENSE_DATA_OSBAL_CLEAN"),
    "C:/Users/berryl/Desktop/starcore/indore/production_script/prod_sus_1.py": ("table_suspense_ver1_2026", "SUSPENSE_DATA_SUSPENSE_V1"),
    "C:/Users/berryl/Desktop/starcore/indore/production_script/prod_sus_2.py": ("table_suspense_ver2_2026", "SUSPENSE_DATA_SUSPENSE_V2"),
}

for file_path, (old_name, new_name) in replacements.items():
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    content = content.replace(f'table_name = "{old_name}"', f'table_name = "{new_name}"')
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

print("Table names updated successfully")
