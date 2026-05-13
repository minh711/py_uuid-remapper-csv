# UUID remapper for CSV datasets

## What this script does

1. Reads every CSV file inside INPUT_DIR
2. Detects UUIDv4 values in TARGET_ID_COLUMN
3. Generates a new UUIDv4 for each old UUID
4. Updates:
   - the original ID column values
   - all exact text matches across ALL CSV files and ALL columns
5. Writes updated CSVs into OUTPUT_DIR

## Design goals

- Configurable variables at the top
- Referential integrity preservation
- Exact-cell replacement only
- Safe two-pass replacement process
- Easy to extend later
