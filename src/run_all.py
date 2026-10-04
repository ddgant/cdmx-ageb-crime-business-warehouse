"""Run the whole pipeline in order:  python src/run_all.py
Requires: raw data in data/raw/ (see README), PostgreSQL+PostGIS running, .env configured."""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
STEPS = ["01_clean_census.py", "02_clean_denue.py", "03_prepare_geography.py",
         "04_clean_crime.py", "05_load_staging.py", "06_build_warehouse.py"]

for s in STEPS:
    print(f"\n===== {s} =====")
    r = subprocess.run([sys.executable, str(HERE / s)], cwd=HERE)
    if r.returncode != 0:
        sys.exit(f"Step failed: {s}")
print("\nPipeline finished.")
