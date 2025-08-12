# GridPath Migration Tool

The **GridPath Migration Tool** is a utility for migrating model input and output CSV files from one version of a GridPath project to another.  
It is designed to detect changes between versions, handle table and file moves, and ensure that CSV structures remain consistent across migrations.

---

## Features

- **Change Detection**
  - Identifies added, removed, renamed, or moved tables between two versions of a GridPath project.
  - Detects subfolder table changes and matches new tables to moved tables by comparing CSV column structures.
  - Maintains a `detected_changes.yaml` file to record structural differences for migration.

- **Table Migration**
  - Moves existing CSV files from the old version to the corresponding new version paths.
  - Creates empty CSVs (without headers) at original moved locations to maintain path integrity.
  - Copies additional CSVs found in the new version that are not in the old version.
  - Preserves column structure by aligning CSV headers with the new version’s definitions.

- **Temporal Data Handling**
  - Detects temporal CSVs from the old version and migrates them to the new version.
  - Ensures that all temporal files match the column requirements of the target version.

---

## How It Works

The tool consists of two main scripts:

### 1. `detected_changes.py`
- Compares the old and new project directory structures.
- Builds lists of:
  - **moved_tables** – tables that changed location.
  - **new_tables** – tables that are newly introduced.
  - **create_and_move_tables** – special cases where a table is moved and a related new table should be created.
- Matches moved subfolder tables by comparing CSV column headers.
- Updates the change tracking file (`detected_changes.yaml`).

### 2. `migrate.py`
- Reads the `detected_changes.yaml` file and performs the actual migration.
- Moves and renames CSV files based on detected changes.
- Creates empty CSV files for replaced/moved tables.
- Ensures all migrated CSVs match the column structure of the target version.
- Adds missing CSVs present in the new version but absent in the old version.

## Folder Structure

gridpath-migration-tool/
- inputs/
  - old_version/ # Place your OLD GridPath version input CSV files here
  - new_version/ # Place your NEW GridPath version example input CSV files here
- migrated_output/ # The migrated version will be output here
- detected_changes.py
- detected_changes.yaml # The YAML file will be formed after running detected_changes.py
- migrate.py

---

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/jacobophilip/gridpath-migration-tool.git
   cd gridpath-migration-tool
