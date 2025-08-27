import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List

import pandas as pd

def safe_filename(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")
    return s[:100] or "sheet"

def to_json_serializable(df: pd.DataFrame, na_mode: str) -> pd.DataFrame:
    """
    Convert NaN/NaT according to na_mode:
    - "null": convert to None (-> JSON null)
    - "empty": convert to empty string
    - "nan": leave as-is (may become NaN which isn't valid JSON without special handling)
    """
    if na_mode == "null":
        return df.where(pd.notnull(df), None)
    elif na_mode == "empty":
        return df.fillna("")
    else:
        # "nan": do nothing
        return df

def main():
    parser = argparse.ArgumentParser(description="Convert .xls to .json (per-sheet + combined).")
    parser.add_argument("xls_path", help="Path to the .xls file")
    parser.add_argument("--outdir", default=".", help="Output directory (default: current dir)")
    parser.add_argument("--orient", default="records",
                        help="pandas DataFrame.to_dict orient (default: records). "
                             "Common options: records, dict, list, split, index, columns, table")
    parser.add_argument("--na", default="null", choices=["null", "empty", "nan"],
                        help='How to output empty cells: "null" (JSON null), "empty" (""), or "nan" (leave as NaN). '
                             'Default: null')
    parser.add_argument("--strings", action="store_true",
                        help="Try to read all cells as strings to preserve leading zeros, IDs, etc.")
    args = parser.parse_args()

    xls_path = args.xls_path
    outdir = args.outdir
    orient = args.orient
    na_mode = args.na
    as_strings = args.strings

    if not os.path.exists(xls_path):
        print(f"Error: file not found: {xls_path}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(outdir, exist_ok=True)

    try:
        # engine for .xls should be xlrd (installed via pip)
        xls = pd.ExcelFile(xls_path)
    except Exception as e:
        print("Failed to open XLS. Make sure 'xlrd' is installed (pip install xlrd).", file=sys.stderr)
        raise

    combined: Dict[str, Any] = {}
    created_files: List[str] = []

    for sheet_name in xls.sheet_names:
        # dtype=str to preserve leading zeros if requested
        parse_kwargs = {"dtype": str} if as_strings else {}
        df = xls.parse(sheet_name, **parse_kwargs)

        # Normalize empty cells per user choice
        df = to_json_serializable(df, na_mode)

        # Convert to list-of-dicts or other shape, based on orient
        if orient == "records":
            data_obj = df.to_dict(orient="records")
        else:
            data_obj = df.to_dict(orient=orient)

        combined[sheet_name] = data_obj

        out_path = os.path.join(outdir, f"{safe_filename(sheet_name)}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data_obj, f, ensure_ascii=False, indent=2)
        created_files.append(out_path)

    combined_path = os.path.join(outdir, "combined_sheets.json")
    with open(combined_path, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)
    created_files.append(combined_path)

    print("Created JSON files:")
    for p in created_files:
        print(p)

if __name__ == "__main__":
    main()
