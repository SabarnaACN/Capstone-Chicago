# Flask CRUD Project: Viva Guide

For the manual MySQL lab and use-case audit, see [MySQL walkthrough](MYSQL_WALKTHROUGH.md).

## Run the current project

From the Capstone folder in PowerShell, run

```powershell
cd chicago-crime-explorer
.\.venv\Scripts\python.exe app.py
```

Open http://127.0.0.1:5057. The working database is `chicago.db` beside `app.py`. At cleanup it contained 499 incidents and 125 recorded arrests. The notebook reads the six original CSVs in `data/`, so its baseline is 498 incidents and 124 recorded arrests. This difference lets me explain what persisted after a demo.

## Where each task lives in the code

Start with [Use Case 1](../chicago-crime-explorer/use_case_1.py), then read [Use Case 2](../chicago-crime-explorer/use_case_2.py), [Use Case 3](../chicago-crime-explorer/use_case_3.py) and [Use Case 4](../chicago-crime-explorer/use_case_4.py). The import inspection command is `python use_case_1.py --inspect` from the app folder with the virtual environment active.

Follow one incident from its CSV row to a chart. Use the notebook for the original import and the dashboard for the current database. Edits made during a demo change the dashboard totals.

| Task | Code to open | What goes in and what comes out |
|---|---|---|
| 1.1 Load and inspect | `use_case_1.py` · `read_source()` and `--inspect` | A named CSV becomes a DataFrame. The inspection command prints its first ten rows, dimensions and data types. |
| 1.2 Clean and validate | `use_case_1.py` · `prepare_dimensions()`, `convert_incident_fields()`, `valid_incidents()` | Lookup tables get unique keys. Dates and codes are standardized. Invalid or duplicate incidents go into quarantine with their source row. |
| 1.3 Derive calendar fields | `use_case_1.py` · `clean_crimes()` | An accepted incident date supplies the year, month and weekday. The hour stays empty for date-only records. |
| 1.4 Measure missing values | `use_case_1.py` · `clean_crimes()` | A true/false grid marks empty fields. NumPy averages each column to give its missing percentage. |
| 1.5 Load SQLite | `use_case_1.py` · `write_database()`, `sql/schema.sql` | The lookup tables load first, followed by incidents. The pipeline checks foreign keys and the incident count after the joins. |
| 2.1–2.3 Explore years, offences and arrests | `use_case_2.py` · `annual_summary()`, `category_summary()`, `summarize()` | Selected incidents become yearly counts, offence shares and arrest percentages. Only known arrest flags enter the arrest denominator. |
| 2.4–2.5 Compare weekdays and communities | `use_case_2.py` · `plot_exploration()`, `community_counts()` | A cross-tab counts incidents by month and weekday. Joining counts to the community list preserves areas with zero selected incidents. |
| 3.1 Check incident times | `use_case_3.py` · `hourly_counts()` | Explicit times become counts by hour. The source has zero recorded times, so the dashboard shows insufficient data. |
| 3.2 Find community outliers | `use_case_3.py` · `community_outliers()` | Community counts supply Q1, Q3 and the IQR. Counts outside the two fences are flagged and named on the dashboard. |
| 3.3 Compare numeric fields | `use_case_3.py` · `numeric_correlations()` | Varying numeric columns supply a Pearson correlation matrix and the strongest pair. The heatmap uses the same matrix. |
| 4.1–4.3 Build summaries, queries and views | `sql/schema.sql`, `sql/reporting_queries.sql`, `sql/views.sql` | The views calculate yearly and offence totals. The reporting queries use them for annual arrests and the top five offences. `refresh_summaries()` in `database.py` updates the stored summaries after an incident edit. |
| 4.4–4.5 Report from SQL | `use_case_4.py` · `load_selection()`, `chart_png()` | SQLAlchemy reads SQLite views into Pandas. Flask uses the results for the **Summary tables** and chart images. Filtered selections are recalculated from their matching rows. |
| Web app and CRUD | `app.py`, `schemas.py`, `api.py`, `database.py` | A form or JSON request supplies values. Marshmallow checks them, `change()` starts a transaction, and `save_record()` or `delete_record()` writes the change. The next dashboard request reads it. |

**A short viva demonstration.** Show the notebook's first ten rows, open **Trends and counts**, and explain which incidents contribute to the arrest percentage. Under **Statistical patterns**, show why an hour cannot be inferred from a date. Finish by adding a community, editing its population, and deleting it from **Communities**. To demonstrate a graph changing, add an incident, reopen the dashboard, then delete that demo incident.

## Notebook walkthrough

Open the [analysis notebook](../chicago-crime-explorer/chicago_crime_analysis.ipynb).
For a short demo, show the first ten rows and the two parser repairs. Use the
annual charts and the two busiest dates to explain the limits of the sample.
Finish with the top-five SQL chart and the checks that compare its output to
Pandas. The notebook builds an independent SQLite snapshot from the CSVs.

## One-minute explanation

"My application is Chicago Crime Explorer. It imports a crime CSV and five
lookup CSVs, cleans the data with Pandas, validates required fields with Pandera,
and stores related tables in SQLite.

Flask renders the dashboard, record tables and forms with Jinja. The browser
uses GET for reading and POST for saving a form. Marshmallow validates the
inputs, then SQLAlchemy saves the record and updates the reporting tables in
one transaction. Flask redirects to the list. The dashboard reads the latest
saved data when I open it.

My extra automation is schema-driven input validation and generated OpenAPI
documentation through Flask-Smorest, plus lazy batch validation through Pandera.
I can demonstrate POST, PUT, PATCH and DELETE in the local Swagger UI.

The original CSVs remain unchanged. The sample is small and uneven, so I explain
its limitations rather than claiming citywide trends."

## A practical five-minute demonstration

1. Start Flask with the command above and open the dashboard.
2. Note the current incident and arrest counts on the dashboard. The original
   CSV import had **498 incidents**, **124 arrest flags** and **24.90% arrests**.
   The working database can include edits from earlier demos.
3. Add an unused case number such as VIVA-TEST-001 dated 2016-05-04, offence 0820,
   community 1, arrest No. Open **Dashboard**. Incidents and THEFT each gain one
   record, and the arrest count stays the same.
4. Find your case in **Crime records**, edit its arrest flag to Yes, and open
   the dashboard. The arrest count increases by one.
5. Open **/api/docs/**. Explain GET, POST, PUT, PATCH and DELETE. Demonstrate
   invalid input and the difference between replacing and partially updating.
6. Create a community with an unused code and population 1,000. Add a demo
   incident to it. Its count is 1 and its per-10,000 figure is 10. Double the
   population to 2,000: the figure becomes 5 while the incident count stays 1.
7. Try deleting the linked community. Show the protected-deletion message.
8. Delete its demo incident, then the community. Delete your demonstration case too.
   The totals return to what you recorded in step 2.
9. Open **Chart options**, choose **Top 5** and **Count**, then use **Apply filters**.
   Show the annual results table, the named IQR outliers and the correlation heatmap.

Use fresh case numbers if your previous demonstration records still exist.
Incident IDs are generated automatically. Clear active filters if a saved
record falls outside the current selection.

## HTTP methods in plain language

| Method | Meaning | Our application |
|---|---|---|
| GET | Read | List records or retrieve one |
| POST | Create | Add an incident or community |
| PUT | Replace editable representation | Require core fields; reset omitted optional values |
| PATCH | Partial update | Change only fields included in the request |
| DELETE | Remove | Delete a working record; reject deletion of a referenced community |

Successful creation returns 201. Successful reads/updates return 200.
Successful deletion returns 204. Missing records return 404. Conflicts return
409. Invalid input returns 422.

### PUT versus PATCH example

Suppose an incident has a block value and arrest=true.

- PATCH with only arrest=false preserves its block, date, offence and community.
- PUT with the required core fields but no block/arrest resets block and arrest
  to their documented defaults. This is full replacement of editable fields.
- IDs and calculated date fields cannot be edited directly.

The browser form sends a POST to the edit page. Python compares the submitted
values to the stored record and saves the changed fields. Use Swagger UI to
show the actual PUT and PATCH requests.

## Extra tools and concepts to study

**Why Flask-Smorest?**  
It uses Marshmallow schemas to validate requests and serialize responses.
The same route/schema definitions generate OpenAPI documentation, reducing
manual validation and documentation code.

**What is OpenAPI?**  
A machine-readable description of endpoints, methods, inputs and responses.
Swagger UI reads it and provides an interactive interface for trying requests.

**Why SQLAlchemy Core?**  
It supplies table-aware SQL construction, parameter binding and transactions.
The existing SQL tables can be reflected instead of duplicating every table
definition in ORM classes.

**What does engine.begin() do?**  
It opens a transaction. Normal completion commits; an exception rolls back.
We update the incident and refresh summary tables inside that transaction.

**Why enable SQLite foreign keys?**  
Foreign-key enforcement must be enabled on each connection. It prevents invalid
references even when code bypasses the application forms.

**Why is a linked community protected from deletion?**  
Removing it would break existing incident references. The API returns 409 and
leaves the data unchanged.

**Why Pandera?**  
It declares required CSV field rules. With lazy=True, it reports multiple
failures together. Invalid records are quarantined with their source contents.

**What is the difference between import validation and API validation?**  
Pandera validates batches of CSV data. Marshmallow validates individual incoming
API requests. Both fit different entry points.

**Why no Streamlit or startup script?**  
Flask serves the HTML pages and the API from the same Python process. Running `app.py` starts both.

**How do the graphs reflect a CRUD change?**  
After the form commits, Flask sends a 303 redirect to a GET page. When I return
to the dashboard, Python reads SQLite again. The browser asks Flask for the
chart images linked in the new page.

**What does Jinja do?**  
It inserts values into HTML on the server. It loops through results to build
rows, preselects filters, and reuses the same layout on each page. Look at
`records.html` for a simple example.

**Why redirect after a successful POST?**  
The last browser action becomes a GET, so refreshing the list reads the rows
again. If validation fails, the form displays the field errors and keeps the
submitted values so I can correct them.

**How do search and paging work?**  
The GET form places the options in the URL. SQLAlchemy filters matching rows,
sorts them, and uses LIMIT and OFFSET to return one page. Pagination links
carry the same filters and sort order.

**Do changes survive a restart?**  
Yes. They are committed to SQLite. Starting Flask does not reload the CSVs.
A normal pipeline run preserves an existing working database; --reset is the
explicit way to discard app edits and rebuild.

## Graphs and formulas

- **Time counts:** incident counts per observed year/month. Uneven sampling
  means this does not establish a citywide rise or fall.
- **Category share:** category count / all selected incidents × 100.
- **Arrest percentage:** TRUE arrest flags / known arrest flags × 100.
  Unknown flags are not counted in the denominator.
- **Calendar heatmap:** observed month/weekday frequencies. Zero cells indicate
  no matching supplied record, not proof that no crime occurred.
- **Population context:** sample count / supplied population × 10,000.
  Population has no reference year, so this is not an annual crime rate.
- **IQR:** Q3 − Q1. Flag counts below Q1 − 1.5×IQR or above Q3 + 1.5×IQR.
  The default comparison includes all supplied communities, including zeros.
- **Correlation:** linear association between varying numeric features.
  It is not causation; weekday is cyclic and needs cautious interpretation.
- **Hourly analysis:** unavailable for date-only records. Do not turn their
  datetime representation at midnight into an observed incident time.

## Verified original sample

| Measure | Value |
|---|---|
| Incidents / quarantined | 498 / 0 |
| Arrest flags / percentage | 124 / 24.90% |
| Largest category | THEFT: 105 incidents, 21.08% |
| 2012 incidents / arrests | 2 / 2 |
| 2013 incidents / arrests | 1 / 1 |
| 2014 incidents / arrests | 1 / 0 |
| 2015 incidents / arrests | 4 / 2 |
| 2016 incidents / arrests | 490 / 119 |
| Distinct dates | 46 |
| Two busiest dates | 3–4 May 2016: 443 incidents, 88.96% |
| Recorded incident times | 0 |
| Missing coordinate pairs | 29 |
| Communities with incidents | 70 of 77 |
| Beat rows / unique keys | 277 / 275 |
| Office records / unique wards | 58 / 50 |
| Community Q1 / Q3 / IQR | 2 / 9 / 7 |
| Upper IQR fence / outliers | 19.5 / 3 |

These are import-baseline figures. App edits change working-data results.

## Data decisions worth explaining

Two final CSV rows have missing closing quotes. A strict parser recognizes the
specific final coordinate pattern, repairs it and logs the source row.
It recovers both incidents instead of silently merging them.

Ward-office records are one-to-many per ward. Keeping office versions separate
from unique ward keys prevents joins from multiplying incidents.

Missing coordinates are retained. Missing location descriptions become UNKNOWN.
The six CSVs keep their supplied names in `data/`. The import records the rows it repaired, the rows it rejected and the missing-value percentages in SQLite.

The import audit describes the source snapshot. Live views, graph responses
and application exports describe the working database after CRUD.

## Follow one record through the project

1. **Read.** `read_source()` opens one named CSV and returns a Pandas table. For incidents it also records the original line number so a repair can be traced.
2. **Clean.** `prepare_dimensions()` makes the lookup keys unique. `clean_crimes()` receives the incident table and those lookups. It returns accepted rows and records any rejected rows and their reasons. A date-only incident gets a year, month and weekday. Its hour stays empty.
3. **Load.** `write_database()` creates the tables from `sql/schema.sql`, inserts the lookups and incidents, then builds the reporting views. A count check verifies that the joins return exactly one row per accepted incident. The import audit lives in the database.
4. **Edit.** When I save a form, Flask receives its values, Marshmallow checks them and SQLAlchemy writes the change. If an incident changes, its summary tables are refreshed in the same transaction. The next dashboard request reads the new totals.
5. **Display.** `load_selection()` applies the active filters. `summarize()` calculates counts and percentages, and `chart_png()` draws the image the browser displays. The HTML report download contains the selected annual and top-five offence tables.

## Files to start with

| File | What to trace |
|---|---|
| `app.py` | Start with `records()`. It validates the GET query, fetches one page, and returns the Jinja template. Then follow `record_form()` for add, edit and delete. |
| `templates/records.html` | Find the `for row` loop and the pagination links. |
| `schemas.py` | Read the required fields for an incident and a community. Both the forms and the API use these input rules. |
| `api.py` | Compare the HTML form with the JSON methods. Both call the same list and write functions. |
| `database.py` | Follow the transaction, foreign keys, and reporting-table refresh. |
| `use_case_2.py` to `use_case_4.py` | Follow `load_selection()` in Use Case 4, then `summarize()` in Use Case 2 and `chart_png()` in Use Case 4. |
| `use_case_1.py` and `sql/` | Follow one incident from a CSV row through cleaning into the fact table and reporting views. |
