import os
import pandas as pd
import shutil
import difflib
import yaml
from glob import glob

OLD_DIR = "inputs/old_version"
NEW_DIR = "inputs/new_version"
OUT_DIR = "migrated_output"

with open("detected_changes.yaml") as f:
    changes = yaml.safe_load(f)

RENAMED = changes.get("renamed_tables", {})
MOVED = changes.get("moved_tables", {})
NEW = changes.get("new_tables", {})
COLUMN_CHANGES = changes.get("column_changes", {})
SCENARIO_CHANGES = changes.get("scenario_changes", {})

def rel_path(full_path, base):
    return os.path.relpath(full_path, base)

def move_csvs(src_folder, dest_folder, label="Moved"):
    os.makedirs(dest_folder, exist_ok=True)
    for file in glob(os.path.join(src_folder, "*.csv")):
        shutil.copy(file, dest_folder)
        print(f"{label} {rel_path(file, OLD_DIR)} → {rel_path(dest_folder, OUT_DIR)}")

def sync_and_reorganize():
    old_struct = pd.read_csv(os.path.join(OLD_DIR, "csv_structure.csv"))
    new_struct = pd.read_csv(os.path.join(NEW_DIR, "csv_structure.csv"))

    # Drop rows with missing paths and cast to string
    old_struct = old_struct.dropna(subset=["path"])
    new_struct = new_struct.dropna(subset=["path"])
    old_map = dict(zip(old_struct.table, old_struct.path.astype(str)))
    new_map = dict(zip(new_struct.table, new_struct.path.astype(str)))

    # Handle renamed tables
    for old_name, new_name in RENAMED.items():
        if old_name in old_map and new_name in new_map:
            src = os.path.join(OLD_DIR, old_map[old_name])
            dst = os.path.join(OUT_DIR, new_map[new_name])
            if os.path.exists(src) and glob(os.path.join(src, "*.csv")):
                move_csvs(src, dst, label="Renamed")
            else:
                os.makedirs(dst, exist_ok=True)

    # Handle moved tables
    for name, paths in MOVED.items():
        src = os.path.join(OLD_DIR, paths["from"])
        dst = os.path.join(OUT_DIR, paths["to"])
        if os.path.exists(src) and glob(os.path.join(src, "*.csv")):
            move_csvs(src, dst, label="Moved")
        else:
            os.makedirs(dst, exist_ok=True)

    # Handle new tables (create empty dirs)
    for name in NEW:
        path = new_map.get(name)
        if path:
            os.makedirs(os.path.join(OUT_DIR, path), exist_ok=True)

    # Handle unchanged/common tables
    common_tables = (set(old_map) & set(new_map)) - set(RENAMED.keys()) - set(MOVED.keys()) - set(NEW.keys())
    for name in common_tables:
        src = os.path.join(OLD_DIR, old_map[name])
        dst = os.path.join(OUT_DIR, new_map[name])
        if os.path.exists(src) and glob(os.path.join(src, "*.csv")):
            move_csvs(src, dst, label="Copied")
        else:
            os.makedirs(dst, exist_ok=True)

    shutil.copy(os.path.join(NEW_DIR, "csv_structure.csv"), os.path.join(OUT_DIR, "csv_structure.csv"))
    print("Copied new csv_structure.csv")

def apply_column_changes():
    for rel_path_key, change in COLUMN_CHANGES.items():
        out_folder = os.path.join(OUT_DIR, rel_path_key)
        new_folder = os.path.join(NEW_DIR, rel_path_key)

        if not os.path.exists(out_folder) or not os.path.exists(new_folder):
            continue

        # Get correct column order from the NEW version
        new_files = glob(os.path.join(new_folder, "*.csv"))
        if not new_files:
            continue
        new_columns = pd.read_csv(new_files[0], nrows=0).columns.tolist()

        renamed = change.get("renamed_columns", {})
        dropped = change.get("dropped_columns", [])
        added = change.get("added_columns", [])

        for f in glob(os.path.join(out_folder, "*.csv")):
            df = pd.read_csv(f)

            # Fix columns
            df.rename(columns=renamed, inplace=True)
            for col in dropped:
                if col in df.columns:
                    df.drop(columns=col, inplace=True)
            for col in added:
                if col not in df.columns:
                    df[col] = ""

            # Reorder columns
            df = df.reindex(columns=new_columns)

            df.to_csv(f, index=False)
            print(f"Updated headers in: {rel_path(f, OUT_DIR)}")

def update_scenarios():
    old = pd.read_csv(os.path.join(OLD_DIR, "scenarios.csv"))
    new = pd.read_csv(os.path.join(NEW_DIR, "scenarios.csv"))
    colname = old.columns[0]

    renamed_keys = SCENARIO_CHANGES.get("renamed_keys", {})
    new_keys = SCENARIO_CHANGES.get("new_rows", [])

    # Apply renaming
    old[colname] = old[colname].replace(renamed_keys)

    # Append new rows (with only ID set)
    combined = old.copy()
    for k in new_keys:
        if k not in set(combined[colname]):
            row = pd.Series({colname: k})
            combined = pd.concat([combined, pd.DataFrame([row])], ignore_index=True)

    # Reorder rows to match NEW version's order
    new_order = new[colname].tolist()
    combined = combined.set_index(colname).reindex(new_order).reset_index()

    combined.to_csv(os.path.join(OUT_DIR, "scenarios.csv"), index=False)
    print("Updated scenarios.csv with renamed and new rows (ordered by new version)")

def migrate_temporal():
    old_temporal_dir = os.path.join(OLD_DIR, "temporal")
    new_temporal_dir = os.path.join(NEW_DIR, "temporal")
    out_temporal_dir = os.path.join(OUT_DIR, "temporal")

    if not os.path.exists(old_temporal_dir) or not os.path.exists(new_temporal_dir):
        print("No temporal directory found in old or new structure. Skipping temporal migration.")
        return

    # Get reference structure from first new temporal subdir
    new_subdirs = [d for d in os.listdir(new_temporal_dir) if os.path.isdir(os.path.join(new_temporal_dir, d))]
    if not new_subdirs:
        print("No temporal subdirectories found in new structure.")
        return

    reference_subdir = os.path.join(new_temporal_dir, new_subdirs[0])
    reference_files = glob(os.path.join(reference_subdir, "*.csv"))
    reference_structures = {
        os.path.basename(f): pd.read_csv(f, nrows=0).columns.tolist()
        for f in reference_files
    }

    # Process each old temporal subdir
    for subdir in os.listdir(old_temporal_dir):
        old_path = os.path.join(old_temporal_dir, subdir)
        if not os.path.isdir(old_path):
            continue

        new_path = os.path.join(new_temporal_dir, subdir)
        out_path = os.path.join(out_temporal_dir, subdir)
        os.makedirs(out_path, exist_ok=True)

        # Step 1: Copy all old CSVs
        for f in glob(os.path.join(old_path, "*.csv")):
            shutil.copy(f, out_path)

        # Step 2: Ensure all reference CSVs are present
        for ref_file, ref_columns in reference_structures.items():
            target_file = os.path.join(out_path, ref_file)
            if not os.path.exists(target_file):
                # Add new CSV if missing
                pd.DataFrame(columns=ref_columns).to_csv(target_file, index=False)
                print(f"Added new CSV to temporal subfolder: {rel_path(target_file, OUT_DIR)}")
                continue

            # Step 3: Fix structure of existing CSV
            df = pd.read_csv(target_file)

            # Rename columns using best-effort matching
            current_cols = df.columns.tolist()
            renamed = {
                old: new for old in current_cols
                if (match := difflib.get_close_matches(old, ref_columns, n=1, cutoff=0.85))
                and match[0] not in current_cols
                and old not in ref_columns
                and (new := match[0])
            }

            df.rename(columns=renamed, inplace=True)

            # Drop extra columns
            for col in df.columns:
                if col not in ref_columns:
                    df.drop(columns=col, inplace=True)

            # Add missing columns
            for col in ref_columns:
                if col not in df.columns:
                    df[col] = ""

            # Reorder columns
            df = df.reindex(columns=ref_columns)

            df.to_csv(target_file, index=False)
            print(f"Updated temporal CSV: {rel_path(target_file, OUT_DIR)}")


def main():
    sync_and_reorganize()
    update_scenarios()
    apply_column_changes()
    migrate_temporal()  # <- new addition
    print("Migration complete. Check output in:", OUT_DIR)

if __name__ == "__main__":
    main()
