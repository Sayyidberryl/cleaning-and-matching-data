import re

files_to_update = [
    "C:/Users/berryl/Desktop/starcore/indore/production_script/cleaning_facul.py",
    "C:/Users/berryl/Desktop/starcore/indore/production_script/cleaning_osbal.py",
    "C:/Users/berryl/Desktop/starcore/indore/production_script/prod_sus_1.py",
    "C:/Users/berryl/Desktop/starcore/indore/production_script/prod_sus_2.py"
]

import_block = """import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

"""

for file_path in files_to_update:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Hapus import yang ada di bawah
    content = content.replace("    import os\n", "")
    content = content.replace("    from sqlalchemy import create_engine\n", "")
    content = content.replace("    from sqlalchemy import create_engine, text\n", "")
    content = content.replace("    from dotenv import load_dotenv\n", "")
    
    # Masukkan import ke bagian atas, tepat setelah import pandas
    if "import pandas as pd" in content:
        content = content.replace("import pandas as pd", "import pandas as pd\n" + import_block)
    else:
        # Jika tidak ada pandas, letakkan di awal
        content = import_block + content

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

print("Imports moved to top successfully")
