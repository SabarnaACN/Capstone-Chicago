"""Use case 1: inspect, clean and load the CSV data into SQLite."""

import argparse
import csv
import json
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import numpy as np
import pandas as pd
import pandera.pandas as pa

from database import DATASET_DIR, DB_PATH, ROOT


FILES = {
    "city_community": "chicago_city_community.csv",
    "district_ps_info": "chicago_district_ps_info.csv",
    "iucr": "iucr_codes.csv.csv",
    "police_beat_info": "chicago_police_beat_info.csv",
    "ward_office_record": "chicago_ward_offices.csv",
    "chicago_crime": "chicago_crime_dataset.csv",
}
KEYS = {
    "city_community": "community_code",
    "district_ps_info": "district_code",
    "iucr": "iucr_code",
    "police_beat_info": "beat_num",
}
CRIME_RULES = pa.DataFrameSchema({
    "id": pa.Column(pd.Int64Dtype(), pa.Check.gt(0)),
    "case_number": pa.Column(pd.StringDtype()),
    "date": pa.Column(nullable=False),
})


def read_incidents(path, repairs, rejected):
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    columns = next(csv.reader([lines[0]]))
    records = []
    for row, original in enumerate(lines[1:], 2):
        if not original.strip():
            continue
        # Two supplied rows lack the closing quote around their final coordinate pair.
        repair = re.search(r',"\(-?\d+(?:\.\d+)?,\s*-?\d+(?:\.\d+)?\)\s*$', original)
        line = original + '"' if repair else original
        try:
            values = next(csv.reader([line], strict=True))
            if len(values) != len(columns):
                raise ValueError("Unexpected column count")
        except (csv.Error, ValueError) as error:
            rejected.append({
                "source_file": path.name,
                "source_row": row,
                "reason": str(error),
                "raw_record": original,
            })
            continue
        if repair:
            repairs.append({"source_row": row, "action": "Added missing closing quote to final coordinate field"})
        records.append(values + [row])
    return pd.DataFrame(records, columns=columns + ["source_row"])


def read_source(path, repairs, rejected):
    if path.name == FILES["chicago_crime"]:
        frame = read_incidents(path, repairs, rejected)
    else:
        frame = pd.read_csv(path, dtype="string", keep_default_na=False)
        frame["source_row"] = range(2, len(frame) + 2)
    frame.columns = frame.columns.str.strip().str.lower()
    frame = frame.rename(columns={"iucr": "iucr_code", "index code": "index_code", "ward": "ward_no"})
    columns = frame.columns.drop("source_row")
    frame[columns] = frame[columns].apply(lambda field: field.astype("string").str.strip()).replace("", pd.NA)
    return frame


def number(values, integer=False):
    values = pd.to_numeric(values.astype("string").str.replace(",", ""), errors="coerce")
    return values.where(values.mod(1).eq(0)).astype("Int64") if integer else values


def prepare_dimensions(sources):
    dimensions = {}
    for name, key in KEYS.items():
        table = sources[name].drop(columns="source_row").copy()
        if name == "iucr":
            table[key] = table[key].str.upper().str.zfill(4)
            table["primary_type"] = table["primary_type"].str.upper().fillna("UNKNOWN")
        else:
            table[key] = number(table[key], integer=True)
        table = table.drop_duplicates()
        if table[key].isna().any() or table[key].duplicated().any():
            raise ValueError(f"Missing or conflicting lookup key in {name}")
        dimensions[name] = table

    community = dimensions["city_community"]
    for column in community.columns.drop(["community_code", "community_name"]):
        community[column] = number(community[column], integer=(column == "population"))
    district = dimensions["district_ps_info"]
    for column in ["x_coordinate", "y_coordinate", "latitude", "longitude"]:
        district[column] = number(district[column])
    beats = dimensions["police_beat_info"]
    for column in ["district", "sector", "beat"]:
        beats[column] = number(beats[column], integer=True)

    offices = sources["ward_office_record"].copy()
    offices["ward_no"] = number(offices["ward_no"], integer=True)
    if offices["ward_no"].isna().any():
        raise ValueError("Missing ward number")
    dimensions["ward_office"] = offices[["ward_no"]].drop_duplicates()
    dimensions["ward_office_record"] = offices
    return dimensions


def convert_incident_fields(frame):
    crimes = frame.copy()
    for column in ["id", "beat_num", "district_code", "ward_no", "community_code", "year"]:
        crimes[column] = number(crimes[column], integer=True)
    for column in ["x_coordinate", "y_coordinate", "latitude", "longitude"]:
        crimes[column] = number(crimes[column])
    for column in ["arrest", "domestic"]:
        crimes[column] = crimes[column].str.upper().map({"TRUE": 1, "FALSE": 0}).astype("Int64")
    for column in ["block", "iucr_code", "location_desc"]:
        crimes[column] = crimes[column].str.upper()
    crimes["iucr_code"] = crimes["iucr_code"].str.zfill(4)
    crimes["location_desc"] = crimes["location_desc"].fillna("UNKNOWN")
    crimes["has_time"] = frame["date"].str.contains(r"(?:T|\s)\d{1,2}:\d{2}", na=False).astype(int)
    for column in ["date", "date_of_update"]:
        crimes[column] = pd.to_datetime(crimes[column], format="mixed", errors="coerce")
    return crimes


def valid_incidents(crimes, original, audit, rejected):
    invalid = pd.Series(False, index=crimes.index)
    try:
        CRIME_RULES.validate(crimes, lazy=True)
    except pa.errors.SchemaErrors as error:
        rows = error.failure_cases["index"]
        if rows.isna().any():
            raise ValueError("Invalid crime table schema") from error
        invalid.loc[rows.unique()] = True
    valid = crimes.loc[~invalid]
    duplicate = valid["id"].duplicated() | valid["case_number"].duplicated()
    reasons = {i: "Invalid required field" for i in crimes.index[invalid]}
    reasons.update({i: "Duplicate ID or case number" for i in valid.index[duplicate]})
    for i, reason in reasons.items():
        rejected.append({
            "source_file": FILES["chicago_crime"],
            "source_row": int(original.at[i, "source_row"]),
            "reason": reason,
            "raw_record": original.loc[i].to_json(),
        })
    audit["invalid_key_records"] = int(invalid.sum())
    audit["duplicate_crime_records"] = int(duplicate.sum())
    return crimes.drop(index=list(reasons)).copy()


def clean_crimes(frame, dimensions, report, rejected):
    blanks = frame.drop(columns="source_row").isna()
    percentages = np.round(blanks.to_numpy().mean(axis=0) * 100, 2)
    report["missing_percent"] = dict(zip(blanks.columns, percentages.tolist()))
    report["columns_over_50_percent_missing"] = [col for col, pct in report["missing_percent"].items() if pct > 50]
    crimes = valid_incidents(convert_incident_fields(frame), frame, report, rejected)
    dates = crimes["date"].dt
    report["year_mismatches"] = int(crimes["year"].ne(dates.year).sum())
    crimes["year"] = dates.year
    crimes["month"] = dates.month
    crimes["day_of_week"] = dates.dayofweek
    crimes["hour"] = dates.hour.where(crimes["has_time"] == 1).astype("Int64")

    report["unmatched_foreign_keys"] = {}
    for table, key in {**KEYS, "ward_office": "ward_no"}.items():
        unknown = crimes[key].notna() & ~crimes[key].isin(dimensions[table][key])
        report["unmatched_foreign_keys"][key] = int(unknown.sum())
        crimes.loc[unknown, key] = pd.NA
    lat, lon = crimes["latitude"], crimes["longitude"]
    bad = (lat.notna() & ~lat.between(-90, 90)) | (lon.notna() & ~lon.between(-180, 180))
    crimes.loc[bad, ["latitude", "longitude"]] = np.nan
    report.update(
        invalid_coordinates=int(bad.sum()),
        records_without_coordinates=int(crimes[["latitude", "longitude"]].isna().any(axis=1).sum()),
        records_with_time=int(crimes["has_time"].sum()),
        accepted_records=len(crimes),
        quarantined_records=len(rejected),
    )
    return crimes


def write_database(path, dimensions, crimes, rejected, audit):
    with closing(sqlite3.connect(path)) as db:
        for script in ("schema.sql", "views.sql"):
            db.executescript((ROOT / "sql" / script).read_text(encoding="utf-8"))
        for name, table in {**dimensions, "chicago_crime": crimes}.items():
            table.to_sql(name, db, if_exists="append", index=False)
        if rejected:
            pd.DataFrame(rejected).to_sql("quarantine", db, if_exists="append", index=False)
        db.executescript("""
            INSERT INTO summary_yearly SELECT * FROM vw_crime_yearly;
            INSERT INTO summary_category SELECT * FROM vw_crime_by_category;
        """)
        joined = db.execute("SELECT COUNT(*) FROM vw_crime_enriched").fetchone()[0]
        if joined != len(crimes) or db.execute("PRAGMA foreign_key_check").fetchone():
            raise ValueError("The import failed its database integrity checks")
        audit["joined_records"] = joined
        db.execute(
            "INSERT INTO pipeline_run VALUES (?, ?, ?)",
            (audit["run_id"], audit["completed_at"], json.dumps(audit)),
        )
        db.commit()


def run_pipeline(dataset_dir=DATASET_DIR, db_path=DB_PATH, reset=False):
    db_path = Path(db_path)
    if db_path.exists() and not reset:
        with closing(sqlite3.connect(db_path)) as db:
            columns = db.execute("PRAGMA table_info(chicago_crime)").fetchall()
            if any(name == "source_row" and required for _, name, _, required, _, _ in columns):
                raise ValueError("This older database requires a CSV row number for new incidents. Back it up before rebuilding.")
            row = db.execute("SELECT report_json FROM pipeline_run").fetchone()
            if row is None:
                raise ValueError("The existing database has no import audit.")
            return json.loads(row[0])

    repairs, rejected = [], []
    audit = {
        "run_id": uuid4().hex,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "repairs": repairs,
    }
    sources = {
        table: read_source(Path(dataset_dir) / filename, repairs, rejected)
        for table, filename in FILES.items()
    }
    dimensions = prepare_dimensions(sources)
    crimes = clean_crimes(sources["chicago_crime"], dimensions, audit, rejected)

    db_path.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=db_path.parent) as folder:
        temporary = Path(folder) / "import.db"
        write_database(temporary, dimensions, crimes, rejected, audit)
        temporary.replace(db_path)
    return audit


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, default=DATASET_DIR)
    parser.add_argument("--inspect", action="store_true", help="Show the first ten raw records")
    parser.add_argument("--reset", action="store_true", help="Rebuild the database, discarding local edits")
    args = parser.parse_args()
    if args.inspect:
        raw = read_source(args.dataset_dir / FILES["chicago_crime"], [], []).drop(columns="source_row")
        print(raw.head(10).to_string(index=False), raw.shape, raw.dtypes, sep="\n")
    else:
        audit = run_pipeline(args.dataset_dir, reset=args.reset)
        print(f"{DB_PATH.name}: {audit['accepted_records']} incidents in the original import.")
