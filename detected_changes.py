import os
import pandas as pd
import difflib
import yaml
import webbrowser
from glob import glob

OLD_DIR = "inputs/old_version"
NEW_DIR = "inputs/new_version"

OLD_CSV = os.path.join(OLD_DIR, "csv_structure.csv")
NEW_CSV = os.path.join(NEW_DIR, "csv_structure.csv")
YAML_FILE = "detected_changes.yaml"

def load_table_paths(csv_path):
    df = pd.read_csv(csv_path)
    return {
        row["table"]: row["path"]
        for _, row in df.iterrows()
        if pd.notna(row["path"]) and str(row["path"]).strip()
    }

def detect_column_changes(old_path, new_path):
    old_files = glob(os.path.join(old_path, "*.csv"))
    new_files = glob(os.path.join(new_path, "*.csv"))
    if not old_files or not new_files:
        return None

    old_cols = pd.read_csv(old_files[0], nrows=0).columns.tolist()
    new_cols = pd.read_csv(new_files[0], nrows=0).columns.tolist()

    renamed = {
        old_col: match[0] for old_col in old_cols
        if (match := difflib.get_close_matches(old_col, new_cols, n=1, cutoff=0.6)) and match[0] not in old_cols
    }
    dropped = [col for col in old_cols if col not in new_cols and col not in renamed]
    added = [col for col in new_cols if col not in old_cols and col not in renamed.values()]

    if renamed or dropped or added:
        return {
            "renamed_columns": renamed,
            "dropped_columns": dropped,
            "added_columns": added
        }
    return None

def detect_table_changes(old_tables, new_tables):
    old_set, new_set = set(old_tables), set(new_tables)
    renamed, moved = {}, {}

    added = new_set - old_set
    common = old_set & new_set

    for old_name in old_set - new_set:
        match = difflib.get_close_matches(old_name, added, n=1, cutoff=0.7)
        if match:
            renamed[old_name] = match[0]
            added.remove(match[0])

    for name in common:
        if old_tables[name] != new_tables[name]:
            moved[name] = {"from": old_tables[name], "to": new_tables[name]}

    return renamed, moved, added, common

def detect_scenario_changes():
    try:
        old_df = pd.read_csv(os.path.join(OLD_DIR, "scenarios.csv"))
        new_df = pd.read_csv(os.path.join(NEW_DIR, "scenarios.csv"))
        old_keys = set(old_df.iloc[:, 0])
        new_keys = set(new_df.iloc[:, 0])

        renamed = {}
        new_only = new_keys - old_keys

        for old in old_keys:
            match = difflib.get_close_matches(old, new_only, n=1, cutoff=0.85)
            if match:
                renamed[old] = match[0]
                new_only.remove(match[0])

        return {
            "renamed_keys": renamed,
            "new_rows": sorted(new_only)
        }

    except Exception as e:
        print(f"Failed to read scenarios.csv: {e}")
        return {"renamed_keys": {}, "new_rows": []}

def main():
    old_tables = load_table_paths(OLD_CSV)
    new_tables = load_table_paths(NEW_CSV)

    renamed, moved, new_only, common = detect_table_changes(old_tables, new_tables)

    column_changes = {}

    for table in common:
        old_path = os.path.join(OLD_DIR, old_tables[table])
        new_path = os.path.join(NEW_DIR, new_tables[table])
        if os.path.exists(old_path) and os.path.exists(new_path):
            change = detect_column_changes(old_path, new_path)
            if change:
                column_changes[new_tables[table]] = change

    for old_name, new_name in renamed.items():
        if old_name in old_tables and new_name in new_tables:
            old_path = os.path.join(OLD_DIR, old_tables[old_name])
            new_path = os.path.join(NEW_DIR, new_tables[new_name])
            if os.path.exists(old_path) and os.path.exists(new_path):
                change = detect_column_changes(old_path, new_path)
                if change:
                    column_changes[new_tables[new_name]] = change

    for name, paths in moved.items():
        old_path = os.path.join(OLD_DIR, paths["from"])
        new_path = os.path.join(NEW_DIR, paths["to"])
        if os.path.exists(old_path) and os.path.exists(new_path):
            change = detect_column_changes(old_path, new_path)
            if change:
                column_changes[paths["to"]] = change

    scenario_changes = detect_scenario_changes()

    detected_changes = {
        "renamed_tables": renamed,
        "moved_tables": moved,
        "new_tables": {t: {"create_empty": True} for t in sorted(new_only)},
        "column_changes": column_changes,
        "scenario_changes": scenario_changes,
    }

    with open(YAML_FILE, "w") as f:
        yaml.dump(detected_changes, f, default_flow_style=False, sort_keys=False)

    print(f"Changes written to {YAML_FILE}")
    webbrowser.open(YAML_FILE)

if __name__ == "__main__":
    main()