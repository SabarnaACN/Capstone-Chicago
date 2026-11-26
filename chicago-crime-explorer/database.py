"""SQLite connections, reflected tables and transactional CRUD operations."""

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import URL, MetaData, create_engine, delete, event, insert, select, text, update
from sqlalchemy.pool import NullPool

ROOT = Path(__file__).resolve().parent
DATASET_DIR = ROOT / "data"
DB_PATH = ROOT / "chicago.db"

REFERENCES = {
    "iucr_code": "iucr",
    "community_code": "city_community",
    "district_code": "district_ps_info",
    "ward_no": "ward_office",
    "beat_num": "police_beat_info",
}


class RecordError(Exception):
    """An expected API error; the caller converts it into an HTTP response."""

    def __init__(self, status, message, errors=None):
        self.status, self.message, self.errors = status, message, errors


def create_db_engine(db_path=DB_PATH, read_only=False):
    path = Path(db_path).resolve()
    url = URL.create(
        "sqlite+pysqlite",
        database=path.as_uri() if read_only else str(path),
        query={"mode": "ro", "uri": "true"} if read_only else {},
    )
    engine = create_engine(url, poolclass=NullPool)

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys = ON")

    return engine


def create_read_engine(db_path=DB_PATH):
    return create_db_engine(db_path, read_only=True)


def reflect_tables(engine):
    metadata = MetaData()
    metadata.reflect(bind=engine, views=True)
    return metadata.tables


def refresh_summaries(connection):
    """Refresh both reporting tables before the mutation transaction commits."""
    for table, view in [
        ("summary_yearly", "vw_crime_yearly"),
        ("summary_category", "vw_crime_by_category"),
    ]:
        connection.execute(text(f"DELETE FROM {table}"))
        connection.execute(text(f"INSERT INTO {table} SELECT * FROM {view}"))


def find_record(connection, tables, resource, identifier):
    table = tables["chicago_crime" if resource == "crimes" else "city_community"]
    key = table.c.id if resource == "crimes" else table.c.community_code
    row = connection.execute(select(table).where(key == identifier)).mappings().first()
    if row is None:
        raise RecordError(404, "Record not found.")
    record = dict(row)
    if resource == "crimes":
        category = tables["iucr"]
        area = tables["city_community"]
        record["primary_type"] = connection.execute(
            select(category.c.primary_type).where(category.c.iucr_code == row["iucr_code"])
        ).scalar()
        record["community_name"] = connection.execute(
            select(area.c.community_name).where(area.c.community_code == row["community_code"])
        ).scalar()
    return record


def save_record(connection, tables, resource, data, identifier=None):
    """Insert or update a validated payload. The enclosing transaction owns commit."""
    table = tables["chicago_crime" if resource == "crimes" else "city_community"]
    values = dict(data)
    current = find_record(connection, tables, resource, identifier) if identifier is not None else {}

    if resource == "crimes":
        for key, table_name in REFERENCES.items():
            value = values.get(key)
            if value is not None:
                reference = tables[table_name]
                exists = connection.execute(
                    select(reference.c[key]).where(reference.c[key] == value)
                ).first()
                if exists is None:
                    raise RecordError(422, "Choose an existing lookup value.", {key: ["Unknown code."]})
        if "date" in values:
            date = values["date"]
            values.update(
                date=f"{date.isoformat()} 00:00:00", year=date.year, month=date.month,
                day_of_week=date.weekday(), hour=None, has_time=0,
            )
        values["date_of_update"] = datetime.now(timezone.utc).isoformat()
        if identifier is None:
            values["source_row"] = None
    else:
        combined = {**current, **values}
        for area_column, density_column in [
            ("area_sqmile", "density_per_sqmi"),
            ("area_sqkm", "density_per_sqkm"),
        ]:
            area = combined.get(area_column)
            values[density_column] = combined["population"] / area if area else None

    if identifier is None:
        result = connection.execute(insert(table).values(**values))
        identifier = result.inserted_primary_key[0]
    else:
        key = table.c.id if resource == "crimes" else table.c.community_code
        connection.execute(update(table).where(key == identifier).values(**values))
    # Only incidents can change annual and offence totals.
    if resource == "crimes":
        refresh_summaries(connection)
    return find_record(connection, tables, resource, identifier)


def delete_record(connection, tables, resource, identifier):
    record = find_record(connection, tables, resource, identifier)
    table = tables["chicago_crime" if resource == "crimes" else "city_community"]
    key = table.c.id if resource == "crimes" else table.c.community_code
    if resource == "communities":
        linked = connection.execute(
            select(tables["chicago_crime"].c.id)
            .where(tables["chicago_crime"].c.community_code == identifier).limit(1)
        ).first()
        if linked:
            raise RecordError(409, "This community has linked crime records and cannot be deleted.")
    connection.execute(delete(table).where(key == identifier))
    if resource == "crimes":
        refresh_summaries(connection)
    return record
