# Use-case review and MySQL walkthrough

> This is a reference for the earlier manual MySQL exercise. For the current SQLite code, commands and file map, see [VIVA_GUIDE.md](VIVA_GUIDE.md).

Use this as a manual lab. Each section ends with something you can check.
The current project uses SQLite. The MySQL code below is a proposed change
to apply and verify on your machine.

## Use Case 1 — Inspect, clean and load

| Task | Status in the current project | Where to show it |
|---|---|---|
| 1. Read and inspect | Done. The crime CSV has 498 parsed rows and 20 source columns. The import reads one incident CSV and five reference CSVs. | Run `python pipeline.py --inspect` in the environment. It prints the first ten rows, shape and types before cleaning. Source fields start as strings so that codes such as `0820` retain their leading zero. |
| 2. Clean | Done. Dates are parsed, text is stripped, selected categorical values are uppercased and missing key fields are validated. Missing location descriptions use `UNKNOWN`. Four location descriptions and 29 coordinate pairs were missing in the original input. | `read_source()` and `clean_crimes()` in `pipeline.py` (the earlier importer), and `reports/quality_report.json`. |
| 3. Date features | Done. The cleaned date yields year, month, weekday, and an hour when an incident has an explicit time. Weekday is stored as an integer, 0 = Monday through 6 = Sunday. The heatmap labels display the names. | `clean_crimes()`. To show the names directly, run `pd.to_datetime(frame["date"], format="mixed").dt.day_name()` against a cleaned preview DataFrame. |
| 4. NumPy missingness | Done. The NumPy mean of each boolean missing-value column, multiplied by 100, gives its percentage. The highest input missingness was 5.82%, so there are no columns above 50% to drop. | `missing_percent` and `columns_over_50_percent_missing` in `reports/quality_report.json`. |
| 5. Store in MySQL | Pending. The existing relational schema and import have been exercised on SQLite. | Follow the MySQL schema, loader and Flask steps below. |

The original import yielded **23 primary offence categories** from the IUCR
join. It repaired missing closing quotes in the coordinate field on CSV lines
498 and 499. These were CSV quoting defects. The audit shows zero invalid key
records, year mismatches or out-of-range coordinates. There are no explicit
incident times. **443 of 498 records** fall on 3–4 May 2016, so the annual totals
reflect uneven coverage.

### Review of the other PDF use cases

| Use case | Current implementation | What to verify again on MySQL |
|---|---|---|
| 2. Exploratory analysis | Annual incident counts, top ten offence categories with shares, arrest percentages, a month × weekday heatmap, and leading community counts. | Open the dashboard; compare the top ten and totals against the same selection in SQLite or the original baseline. |
| 3. Statistical insights | Community mean, box plot and named IQR outliers, plus a Pearson correlation heatmap. Hourly analysis is implemented, and the source input shows the unavailable state because it has dates only. | Check that community results and the hourly message render. Use the **Time of day** panel to explain the source limitation. |
| 4. Database reporting | Summary tables, SQL reporting queries, stored views read into Pandas, and charts drawn from the query results. | Compare `vw_crime_yearly` with `summary_yearly` and run the top-five query. Apply a CRUD change and check that the reporting summaries update. |
| Instructor's web app | Flask, Jinja HTML, search, sort, filters, and incident and community CRUD. The API exposes GET, POST, PUT, PATCH and DELETE. | Test both record lists and one complete create → edit → delete cycle on MySQL. |

## Checkpoint 1 — Install MySQL and connect from PowerShell

1. From [MySQL Community Server downloads](https://dev.mysql.com/downloads/mysql/),
   choose **8.4 LTS**, **Microsoft Windows**, and the **x86, 64-bit MSI Installer**.
   Use the server MSI, which bundles
   [MySQL Configurator](https://dev.mysql.com/doc/refman/8.4/en/mysql-configurator.html).
2. Run Configurator. Choose **Development Computer** if offered, enable TCP/IP on
   **3306**, use the default Windows service setting, and set a root password.
   For the local demo, leave the firewall port option unchecked. Apply the
   configuration. The service name is typically `MySQL84`.
3. Open PowerShell in `chicago-crime-explorer` and check the service and client.

~~~powershell
Get-Service -Name 'MySQL*'
$mysql = 'C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe'
& $mysql --protocol=TCP -h 127.0.0.1 -P 3306 -u root -p -e "SELECT VERSION();"
~~~

Use the actual installation path if you chose a different one. If installation
requests administrator access, use the approved installation process for your PC.

Connect as root from the **same project directory**. Type the root password at
the prompt. Run the SQL below at the `mysql>` prompt. Replace the placeholder
with a new local app password and keep the same value for the Python test.

~~~powershell
& $mysql --protocol=TCP -h 127.0.0.1 -P 3306 -u root -p
~~~

~~~sql
CREATE DATABASE chicago_crime_mysql
    CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

CREATE USER 'chicago_app'@'127.0.0.1'
    IDENTIFIED BY 'YOUR_LOCAL_APP_PASSWORD';

GRANT SELECT, INSERT, UPDATE, DELETE, SHOW VIEW
    ON chicago_crime_mysql.* TO 'chicago_app'@'127.0.0.1';

EXIT;
~~~

Root creates the schema. The Python app account gets data and view permissions
on this one database. Keep both passwords off the repository and out of chat.

## Checkpoint 2 — Install the driver and test SQLAlchemy

Open [requirements.txt](../chicago-crime-explorer/requirements.txt) and add
`PyMySQL[rsa]` at the end. The extra supports MySQL's SHA-2 authentication.
See [PyMySQL installation](https://pymysql.readthedocs.io/en/latest/user/installation.html).

~~~powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$secret = Read-Host 'Password for chicago_app' -AsSecureString
$env:CHICAGO_MYSQL_PASSWORD = [System.Net.NetworkCredential]::new('', $secret).Password
Remove-Variable secret
~~~

In [database.py](../chicago-crime-explorer/database.py), add this function
immediately before `create_db_engine()`. The existing imports already include
`os` and `URL`.

~~~python
def mysql_url():
    return URL.create(
        "mysql+pymysql",
        username="chicago_app",
        password=os.environ["CHICAGO_MYSQL_PASSWORD"],
        host="127.0.0.1",
        port=3306,
        database="chicago_crime_mysql",
        query={"charset": "utf8mb4"},
    )
~~~

Then insert these two lines at the start of `create_db_engine()`, immediately
before `path = Path(db_path).resolve()`. Leave the SQLite branch below it.

~~~python
    if isinstance(db_path, URL):
        return create_engine(db_path, pool_pre_ping=True, isolation_level="REPEATABLE READ")
~~~

`URL.create()` accepts the password as entered, including characters such as
`@` or `/`. PyMySQL is the Python driver. SQLAlchemy builds queries and manages
connections. [SQLAlchemy engine configuration](https://docs.sqlalchemy.org/en/21/core/engines.html).

~~~powershell
@'
from sqlalchemy import text
from database import create_db_engine, mysql_url

with create_db_engine(mysql_url()).connect() as connection:
    print(connection.execute(text("SELECT VERSION(), DATABASE()")).one())
'@ | .\.venv\Scripts\python.exe -
~~~

Expected output includes `8.4.x` and `chicago_crime_mysql`. The password
environment variable is scoped to this terminal; set it again in a new one.

## Checkpoint 3 — Create the MySQL tables and views

Make your own copy of the SQLite schema.

~~~powershell
Copy-Item .\sql\schema.sql .\sql\schema_mysql.sql
~~~

In `sql/schema_mysql.sql` make these edits.

1. Replace the opening `PRAGMA foreign_keys = ON;` with
   `SET SESSION default_storage_engine = InnoDB;`.
2. Use `DOUBLE` in place of `REAL` for coordinates and percentages.
3. In `chicago_crime` use `id BIGINT AUTO_INCREMENT PRIMARY KEY`,
   `case_number VARCHAR(32) NOT NULL UNIQUE`, and `date DATETIME NOT NULL`.
   Keep the existing `date_of_update` text column because the Python code writes
   an ISO timestamp including a timezone offset.
4. Use `iucr_code VARCHAR(4)` in **both** `iucr` and `chicago_crime`. Leave the
   `PRIMARY KEY` on the definition inside `iucr`. In `pipeline_run` set
   `run_id VARCHAR(32) PRIMARY KEY`. In `summary_category` set
   `primary_type VARCHAR(120) PRIMARY KEY`.
5. Remove the six inline `REFERENCES ...` clauses and preserve their column
   definitions and commas. Append these statements. MySQL 8.4 needs separate
   `FOREIGN KEY` clauses to enforce the references.
   [MySQL CREATE TABLE reference](https://dev.mysql.com/doc/refman/8.4/en/create-table.html).

~~~sql
ALTER TABLE ward_office_record
    ADD FOREIGN KEY (ward_no) REFERENCES ward_office(ward_no);

ALTER TABLE chicago_crime
    ADD FOREIGN KEY (iucr_code) REFERENCES iucr(iucr_code),
    ADD FOREIGN KEY (beat_num) REFERENCES police_beat_info(beat_num),
    ADD FOREIGN KEY (district_code) REFERENCES district_ps_info(district_code),
    ADD FOREIGN KEY (ward_no) REFERENCES ward_office(ward_no),
    ADD FOREIGN KEY (community_code) REFERENCES city_community(community_code);
~~~

Connect as root again from the project folder and run these at the `mysql>`
prompt. Use the existing `views.sql` as written.

~~~sql
USE chicago_crime_mysql;
source sql/schema_mysql.sql
source sql/views.sql
SHOW FULL TABLES;
SHOW CREATE TABLE chicago_crime;
~~~

Check that `vw_crime_enriched`, `vw_crime_yearly` and `vw_crime_by_category`
appear and that `SHOW CREATE TABLE` shows the five foreign keys. If one of the
schema commands fails, fix it before loading any data. MySQL DDL can commit
implicitly. [MySQL implicit commits](https://dev.mysql.com/doc/refman/8.4/en/implicit-commit.html).

## Checkpoint 4 — Reuse the cleaning code and load MySQL

In `pipeline.py` (the earlier importer), add `from sqlalchemy import text`
with the other imports. Extend the database import with `create_db_engine`,
`mysql_url` and `refresh_summaries`.

In `run_pipeline()`, cut the block from `missing_files = ...` through
`crimes = clean_crimes(...)`. Place this block immediately above `run_pipeline()`,
under `def prepare_import(dataset_dir, archive_dir):`. In the moved block,
replace the four directory setup lines, starting with `db_path.parent.mkdir(...)`
and ending with `archive_dir.mkdir(exist_ok=True)`, with:

~~~python
    archive_dir.mkdir(parents=True, exist_ok=True)
~~~

At the end of the new `prepare_import()` function add:

~~~python
    return frames, crimes, rejected, report
~~~

Where you removed the block inside `run_pipeline()`, add the call below. This
keeps the SQLite loader and tests working.

~~~python
    report_dir.mkdir(parents=True, exist_ok=True)
    frames, crimes, rejected, report = prepare_import(dataset_dir, db_path.parent / "raw")
~~~

Add this function immediately before `if __name__ == "__main__":`.

~~~python
def run_mysql_pipeline(dataset_dir=DATASET_DIR):
    engine = create_db_engine(mysql_url())
    report_dir = REPORT_DIR / "mysql"
    try:
        with engine.begin() as connection:
            already_loaded = connection.scalar(text("SELECT COUNT(*) FROM pipeline_run"))
            existing_crimes = connection.scalar(text("SELECT COUNT(*) FROM chicago_crime"))
            if already_loaded or existing_crimes:
                raise ValueError("MySQL has records already. Use an empty schema for a new import.")

            frames, crimes, rejected, report = prepare_import(
                Path(dataset_dir), DB_PATH.parent / "raw"
            )
            for table in [*KEYS, "ward_office", "ward_office_record"]:
                frames[table].to_sql(table, connection, if_exists="append", index=False)
            crimes.to_sql("chicago_crime", connection, if_exists="append", index=False)
            if rejected:
                pd.DataFrame(rejected).to_sql(
                    "quarantine", connection, if_exists="append", index=False
                )

            refresh_summaries(connection)
            report["table_counts"] = {
                table: connection.scalar(text(f"SELECT COUNT(*) FROM {table}"))
                for table in [*FILES, "ward_office", "summary_yearly", "summary_category"]
            }
            report["joined_records"] = connection.scalar(text("SELECT COUNT(*) FROM vw_crime_enriched"))
            if report["joined_records"] != len(crimes):
                raise ValueError("The joined and imported crime counts differ.")

            connection.execute(text(
                "INSERT INTO pipeline_run (run_id, completed_at, report_json) "
                "VALUES (:run_id, :completed_at, :audit)"
            ), {
                "run_id": report["run_id"],
                "completed_at": report["completed_at"],
                "audit": json.dumps(report),
            })
            yearly = pd.read_sql_query(text("SELECT * FROM vw_crime_yearly ORDER BY year"), connection)
            categories = pd.read_sql_query(
                text("SELECT * FROM vw_crime_by_category ORDER BY crime_count DESC, primary_type"),
                connection,
            )

        report_dir.mkdir(parents=True, exist_ok=True)
        yearly.to_csv(report_dir / "yearly_summary.csv", index=False)
        categories.to_csv(report_dir / "category_summary.csv", index=False)
        crimes.to_csv(report_dir / "cleaned_crimes.csv", index=False)
        (report_dir / "quality_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report
    finally:
        engine.dispose()
~~~

In the CLI section, put this before `args = parser.parse_args()`:

~~~python
    parser.add_argument("--mysql", action="store_true", help="Load the CSVs into an empty MySQL schema")
~~~

Immediately after the `if args.inspect:` block, before `already_exists = DB_PATH.exists()`, add:

~~~python
    if args.mysql:
        if args.reset:
            parser.error("--reset applies only to the SQLite file")
        result = run_mysql_pipeline(args.dataset_dir)
        print(f"MySQL import: {result['accepted_records']} incidents")
        print(f"Reports: {REPORT_DIR / 'mysql'}")
        parser.exit()
~~~

Run the import in the terminal where you set the password.

~~~powershell
.\.venv\Scripts\python.exe pipeline.py --mysql
& $mysql --protocol=TCP -h 127.0.0.1 -P 3306 -u chicago_app -p chicago_crime_mysql
~~~

~~~sql
SELECT COUNT(*) AS incidents, SUM(arrest = 1) AS arrests FROM chicago_crime;
SELECT COUNT(DISTINCT primary_type) AS categories FROM vw_crime_enriched;
SELECT COUNT(*) AS communities FROM city_community;
SELECT * FROM vw_crime_yearly ORDER BY year;
~~~

Expected for this fresh CSV import: **498 incidents**, **124 arrests**,
**23 categories**, and **77 communities**. Edits made in the working SQLite
database are a separate dataset. If those edits need to move later, migrate
them as a separate step after the baseline works.

## Checkpoint 5 — Point Flask at MySQL

In [app.py](../chicago-crime-explorer/app.py), add `import os`, add
`from sqlalchemy import URL`, and extend the database import with `mysql_url`.
Import `storage` from `api` and remove `reflect_tables` from the `app.py` imports.

Change the beginning of `create_app()`, through the `app = Flask(__name__)` line:

~~~python
def create_app(db_path=None, testing=False):
    if db_path is None:
        db_path = mysql_url() if os.environ.get("CHICAGO_DB_BACKEND") == "mysql" else DB_PATH
    source = db_path if isinstance(db_path, URL) else Path(db_path)
    app = Flask(__name__)
~~~

In `app.config.update(...)` replace `DB_PATH=Path(db_path)` with `DB_PATH=source`.
Set up the engine and lazy table discovery as follows:

~~~python
    app.extensions["engine"] = create_db_engine(source)
    app.extensions["tables"] = {}
~~~

Replace the nested `selection(args)` in `app.py` with:

~~~python
    def selection(args):
        storage()
        return load_selection(app.config["DB_PATH"], args)
~~~

In [api.py](../chicago-crime-explorer/api.py), add `from pathlib import Path`
and replace `storage()` with:

~~~python
def storage():
    source = current_app.config["DB_PATH"]
    message = "Import the data with pipeline.py for the configured database."
    if isinstance(source, Path) and not source.is_file():
        abort(503, message=message)
    engine = current_app.extensions["engine"]
    tables = current_app.extensions["tables"]
    if not tables:
        tables = reflect_tables(engine)
        current_app.extensions["tables"] = tables
    if "vw_crime_enriched" not in tables or "pipeline_run" not in tables:
        abort(503, message=message)
    return engine, tables
~~~

In `list_items()` replace `column = column.collate("NOCASE")` with
`column = func.lower(column)`. That makes case-insensitive ordering portable.
In `lookup_options()` replace the `result["latest_date"]` assignment with:

~~~python
        latest = connection.execute(select(func.max(crime.c.date))).scalar()
        result["latest_date"] = str(latest) if latest is not None else None
~~~

In `analysis.py` (the earlier reporting module), in `load_snapshot()`,
replace the explicit `BEGIN` line. Keep the remainder of the queries and
Pandas calculations as written.

~~~python
        if engine.dialect.name == "mysql":
            connection.exec_driver_sql("START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY")
        else:
            connection.exec_driver_sql("BEGIN")
~~~

This uses InnoDB's repeatable read snapshot when reading charts.
[MySQL transaction syntax](https://dev.mysql.com/doc/refman/8.4/en/commit.html).

### Final checks

Run the existing tests first. They create temporary SQLite databases, so they
check that the original backend still works. Then launch MySQL mode on a
separate local port.

~~~powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
$env:CHICAGO_DB_BACKEND = 'mysql'
.\.venv\Scripts\python.exe -m flask --app app run --port 5059
~~~

At `http://127.0.0.1:5059/`, check the dashboard and record lists, then add,
edit and delete a fresh demonstration incident. Check the totals after each
step. Verify a linked community cannot be deleted. Try the API methods at
`http://127.0.0.1:5059/api/docs/` and compare a summary table to its view.

To use SQLite again, stop Flask and clear the backend selection.

~~~powershell
Remove-Item Env:CHICAGO_DB_BACKEND
.\.venv\Scripts\python.exe -m flask --app app run --port 5057
~~~

For the viva, explain the swap in one sentence: the CSV cleaning and HTML
pages use the same Python code, while SQLAlchemy connects to MySQL through
PyMySQL and MySQL enforces the table keys and transactions.
