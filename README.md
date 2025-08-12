# GridPath Migration Tool

This tool automates the process of **detecting changes** between two versions of a GridPath input dataset and **migrating** CSV files from an old version to a new version while preserving data consistency.

---

## 📌 Features

1. **Change Detection (`detected_changes.py`)**
   - Compares old and new GridPath input directories.
   - Identifies:
     - Renamed tables
     - Moved tables
     - New tables
     - Column additions, deletions, and renames within CSV files
     - Scenario-related changes
   - Saves all detected changes into `detected_changes.yaml`.

2. **Migration (`migrate.py`)**
   - Uses the `detected_changes.yaml` file to guide migration.
   - Copies CSV data from the old version into the corresponding new version structure.
   - Handles:
     - Table renames
     - Folder moves
     - Adding missing CSVs in the new version
     - Adjusting CSV columns to match the new version's format
   - Creates `migrated_output` with the updated structure.

---

## 📂 Project Structure

