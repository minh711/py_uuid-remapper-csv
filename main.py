"""
UUID remapper for CSV datasets.

What this script does:
1. Reads every CSV file inside INPUT_DIR
2. Detects UUIDv4 values in TARGET_ID_COLUMN
3. Generates a new UUIDv4 for each old UUID
4. Updates:
   - the original ID column values
   - all exact text matches across ALL CSV files and ALL columns
5. Writes updated CSVs into OUTPUT_DIR

Design goals:
- Configurable variables at the top
- Referential integrity preservation
- Exact-cell replacement only
- Safe two-pass replacement process
- Easy to extend later
"""

from pathlib import Path
import pandas as pd
import uuid
import re
from typing import Dict

# ============================================================
# CONFIGURATION
# ============================================================

# Folder settings
INPUT_DIR = Path("input")
OUTPUT_DIR = Path("output")

# CSV settings
CSV_GLOB_PATTERN = "*.csv"
CSV_ENCODING = "utf-8"
CSV_SEPARATOR = ","

# Column settings
TARGET_ID_COLUMN = "id"

# UUID settings
UUID_VERSION = 4
CASE_INSENSITIVE_UUID_MATCH = True

# Output settings
SAVE_UUID_MAPPING_FILE = True
UUID_MAPPING_FILENAME = "uuid_mapping.csv"

# Pandas settings
KEEP_EMPTY_STRINGS = True

# Logging settings
VERBOSE = True

# ============================================================
# UUID REGEX
# ============================================================

UUID_V4_REGEX = re.compile(
    r"^[0-9a-f]{8}-"
    r"[0-9a-f]{4}-"
    r"4[0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-"
    r"[0-9a-f]{12}$",
    re.IGNORECASE if CASE_INSENSITIVE_UUID_MATCH else 0,
)

# ============================================================
# HELPERS
# ============================================================


def log(message: str):
    if VERBOSE:
        print(message)


def is_uuid_v4(value) -> bool:
    """
    Check whether a value is a valid UUIDv4 string.
    """

    if not isinstance(value, str):
        return False

    return bool(UUID_V4_REGEX.fullmatch(value.strip()))


def generate_uuid() -> str:
    """
    Generate UUID based on configured UUID version.
    """

    if UUID_VERSION == 4:
        return str(uuid.uuid4())

    raise ValueError(f"Unsupported UUID version: {UUID_VERSION}")


def generate_unique_uuid(existing: set) -> str:
    """
    Generate a UUID that does not already exist.
    """

    while True:
        new_id = generate_uuid()

        if new_id not in existing:
            existing.add(new_id)
            return new_id


# ============================================================
# VALIDATION
# ============================================================

if not INPUT_DIR.exists():
    raise FileNotFoundError(f"Input directory not found: {INPUT_DIR}")

OUTPUT_DIR.mkdir(exist_ok=True)

csv_files = sorted(INPUT_DIR.glob(CSV_GLOB_PATTERN))

if not csv_files:
    raise FileNotFoundError(f"No CSV files found using pattern: {CSV_GLOB_PATTERN}")

# ============================================================
# LOAD CSV FILES
# ============================================================

tables: Dict[str, pd.DataFrame] = {}

log("Loading CSV files...")

for file in csv_files:

    df = pd.read_csv(
        file,
        dtype=str,
        keep_default_na=not KEEP_EMPTY_STRINGS,
        encoding=CSV_ENCODING,
        sep=CSV_SEPARATOR,
    )

    if KEEP_EMPTY_STRINGS:
        df = df.fillna("")

    tables[file.name] = df

    log(f"Loaded: {file.name} ({len(df)} rows)")

# ============================================================
# PASS 1:
# BUILD UUID MAPPING
# ============================================================

uuid_map: Dict[str, str] = {}
all_new_ids = set()

log(f"\nScanning for UUIDv4 values in '{TARGET_ID_COLUMN}' columns...")

for filename, df in tables.items():

    if TARGET_ID_COLUMN not in df.columns:
        continue

    for old_id in df[TARGET_ID_COLUMN]:

        if is_uuid_v4(old_id):

            if old_id not in uuid_map:
                uuid_map[old_id] = generate_unique_uuid(all_new_ids)

log(f"Found {len(uuid_map)} UUIDs to replace.")

# ============================================================
# PASS 2:
# REPLACE EXACT CELL MATCHES
# ============================================================

log("\nUpdating references across all tables...")

for filename, df in tables.items():

    log(f"Processing: {filename}")

    for column in df.columns:

        # Exact-cell replacement only
        df[column] = df[column].map(lambda x: uuid_map.get(x, x))

# ============================================================
# SAVE OUTPUT FILES
# ============================================================

log("\nWriting updated CSV files...")

for filename, df in tables.items():

    output_path = OUTPUT_DIR / filename

    df.to_csv(
        output_path,
        index=False,
        encoding=CSV_ENCODING,
        sep=CSV_SEPARATOR,
    )

    log(f"Saved: {output_path}")

# ============================================================
# SAVE UUID MAPPING FILE
# ============================================================

if SAVE_UUID_MAPPING_FILE:

    mapping_df = pd.DataFrame(
        [
            {
                "old_uuid": old_uuid,
                "new_uuid": new_uuid,
            }
            for old_uuid, new_uuid in uuid_map.items()
        ]
    )

    mapping_output_path = OUTPUT_DIR / UUID_MAPPING_FILENAME

    mapping_df.to_csv(
        mapping_output_path,
        index=False,
        encoding=CSV_ENCODING,
        sep=CSV_SEPARATOR,
    )

    log(f"Saved mapping file: {mapping_output_path}")

# ============================================================
# SUMMARY
# ============================================================

log("\nDone.")
log(f"Updated {len(tables)} tables.")
log(f"Replaced {len(uuid_map)} UUIDs.")
