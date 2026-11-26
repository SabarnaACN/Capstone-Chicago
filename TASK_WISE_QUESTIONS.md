# Chicago Crime Explorer: Task-wise Questions

A structured question bank for understanding the assignment and preparing for the viva.

**Source:** [Document 1.pdf](../Document%201.pdf). The task descriptions below paraphrase the assignment. The preparation questions are written for this project; they are not presented as verbatim questions from the PDF.

**Database choice:** The PDF permits SQLite when MySQL is unavailable. This project uses SQLite, as agreed. References to database loading, queries, views and summary tables below refer to this implementation.

**How to use this file:** Prepare each task in this order: explain its purpose, describe the approach, show the relevant output, and discuss any data limitation. The study guide maps each task to the Python function or SQL file that implements it. [Task-to-code walkthrough](VIVA_GUIDE.md#where-each-task-lives-in-the-code).

## Contents

- [Project understanding](#project-understanding)
- [Use Case 1: Load and Clean Chicago Crime Data](#use-case-1-load-and-clean-chicago-crime-data)
- [Use Case 2: Exploratory Analysis and Visualization](#use-case-2-exploratory-analysis-and-visualization)
- [Use Case 3: Statistical Insights and Pattern Detection](#use-case-3-statistical-insights-and-pattern-detection)
- [Use Case 4: Database Reporting and Integration](#use-case-4-database-reporting-and-integration)
- [Additional questions about this solution](#additional-questions-about-this-solution)
- [Setup and demonstration questions](#setup-and-demonstration-questions)
- [Final revision checklist](#final-revision-checklist)

---

## Project understanding

1. What problem does the Chicago Crime Explorer project address?
2. How do the six CSV files relate to one another?
3. What happens at each stage of the pipeline: extraction, cleaning, database loading, analysis and reporting?
4. What can this historical sample tell us, and which conclusions require a more complete dataset?

## Use Case 1: Load and Clean Chicago Crime Data

**Objective:** Read the source files, inspect and clean the data, derive useful features, and store the results in a relational database.

### Task 1.1: Load and inspect the CSV files

**Assignment task:** Load the dataset into a Pandas DataFrame, inspect the first ten rows, and examine its shape, schema and data types.

**Questions to prepare:**

1. How many source files are provided, and what information does each contain?
2. How do you display the first ten rows, number of rows and columns, column names, and data types?
3. Why should codes such as IUCR be read as text rather than ordinary numbers?
4. Why does a normal CSV read merge the final two crime records, and how does the validated import recover them?

**Evidence to show:** [use_case_1.py](../chicago-crime-explorer/use_case_1.py); run `python use_case_1.py --inspect` from the app folder.

### Task 1.2: Clean and validate the data

**Assignment task:** Convert dates, handle missing key fields, standardize categorical values, and investigate anomalies.

**Questions to prepare:**

1. How are date strings converted into datetime values, and what happens when a date is invalid?
2. Which fields contain missing values, and why are missing location descriptions and coordinates handled differently?
3. How do you standardize whitespace, letter case, boolean values and IUCR codes?
4. How are malformed CSV rows, duplicate crime records and Pandera validation failures handled without losing their original contents?
5. What date-format anomalies or obvious outliers did you check for?

**Evidence to show:** [use_case_1.py](../chicago-crime-explorer/use_case_1.py); the `quality` object at `/api/analytics`.

### Task 1.3: Generate date-derived features

**Assignment task:** Extract year, month and day of week from the incident date.

**Questions to prepare:**

1. How are year, month and day-of-week features derived from a datetime column?
2. Why derive the analytical year from the incident date and compare it with the supplied year?
3. What is the difference between a date-only record and a record with an explicitly observed time?

**Evidence to show:** Date-feature logic in [use_case_1.py](../chicago-crime-explorer/use_case_1.py); the derived columns in the notebook or the dashboard selection CSV.

### Task 1.4: Measure missing values using NumPy

**Assignment task:** Calculate missing-value percentages per column and consider columns with more than 50% missing values.

**Questions to prepare:**

1. What is the formula for the percentage of missing values in a column?
2. How does taking the NumPy mean of a boolean missing-value array produce a missing-value proportion?
3. Does any supplied crime column exceed 50% missingness, and how does the requirement to preserve data influence your decision about dropping columns?

**Evidence to show:** `missing_percent` in [use_case_1.py](../chicago-crime-explorer/use_case_1.py); `quality.missing_percent` at `/api/analytics`.

### Task 1.5: Store the cleaned records in the database

**Assignment task:** Design related database tables and insert the cleaned data. This project uses the permitted SQLite alternative.

**Questions to prepare:**

1. What are the primary and foreign keys in the crime table and its lookup tables?
2. How are cleaned Pandas DataFrames inserted into the existing database tables?
3. How do you check that lookup joins preserve the number of incidents?
4. What happens if an incident references a code that is absent from a lookup table?

**Evidence to show:** [sql/schema.sql](../chicago-crime-explorer/sql/schema.sql); loading and integrity checks in [use_case_1.py](../chicago-crime-explorer/use_case_1.py).

### Use Case 1: Assignment review questions

- How many unique crime categories exist after joining the IUCR reference?
- Are there anomalies in date formats or obvious outliers in the supplied data?

## Use Case 2: Exploratory Analysis and Visualization

**Objective:** Describe the selected incidents using counts, percentages, grouped summaries and charts.

### Task 2.1: Analyze incident counts across years

**Assignment task:** Calculate and plot the number of incidents per year, then interpret the result.

**Questions to prepare:**

1. How do Pandas grouping and SQL `GROUP BY` calculate annual incident counts?
2. Which year has the largest count in the supplied records?
3. Why does a higher count in this sample not establish that citywide crime increased?

**Evidence to show:** Dashboard **Incidents over time** and **Summary tables → Annual breakdown**.

### Task 2.2: Analyze crime categories

**Assignment task:** Plot the ten most frequent primary crime categories and calculate their counts and percentages.

**Questions to prepare:**

1. How is the primary crime category obtained from the IUCR reference?
2. How are categories ranked and the top ten selected?
3. What denominator is used for a category's percentage, and why should it include all selected incidents?

**Evidence to show:** Dashboard **Summary tables → Counts and shares by offence**.

### Task 2.3: Analyze arrest flags

**Assignment task:** Calculate the percentage of incidents with recorded arrests and compare the results across years.

**Questions to prepare:**

1. How is the arrest percentage calculated from the TRUE and FALSE flags?
2. How should unknown arrest flags affect the numerator and denominator?
3. Why must yearly arrest percentages be presented alongside their record counts?
4. What conclusions cannot be drawn from an arrest flag alone?

**Evidence to show:** Dashboard **Arrests by year → Percentage** and **Annual breakdown**.

### Task 2.4: Build a month-by-weekday heatmap

**Assignment task:** Group incidents by month and day of week, pivot the frequencies, and visualize them with Seaborn.

**Questions to prepare:**

1. How are month and weekday frequencies transformed into a two-dimensional table?
2. What do a cell's number and colour represent?
3. Does a zero cell mean no crime occurred in Chicago, or only that no matching incident appears in this sample?

**Evidence to show:** Dashboard **Month and weekday**; `calendar` chart in [use_case_2.py](../chicago-crime-explorer/use_case_2.py).

### Task 2.5: Identify communities with the highest counts

**Assignment task:** List and plot the ten community areas with the largest incident counts.

**Questions to prepare:**

1. How are community codes joined to community names?
2. Which communities have the largest selected counts?
3. Why can raw counts and population-adjusted counts produce different rankings?

**Evidence to show:** Dashboard **Community comparison** and the **Per 10,000 residents** option.

### Use Case 2: Assignment review questions

- Which crime category is most frequent?
- Is the arrest percentage consistent across years?
- Which month has the highest incident frequency in the supplied records?

## Use Case 3: Statistical Insights and Pattern Detection

**Objective:** Use numerical summaries and visual methods to explore variation, outliers and associations.

### Task 3.1: Analyze incidents by hour

**Assignment task:** Derive the incident hour, group records by hour, and draw an hourly distribution where timestamps support it.

**Questions to prepare:**

1. What information must the incident-date field contain before hourly analysis is meaningful?
2. Why must a date converted to midnight not automatically be treated as a midnight incident?
3. How does the application behave when no explicitly recorded incident times are available?

**Evidence to show:** Dashboard **Time of day** and `hourly_counts()` in [use_case_3.py](../chicago-crime-explorer/use_case_3.py).

**Data limitation:** The supplied crime CSV contains dates without times. Explain the unavailable analysis rather than inventing hourly observations.

### Task 3.2: Analyze community counts and IQR outliers

**Assignment task:** Use NumPy to calculate the mean community count, inspect the count distribution with a box plot, and identify outliers using the IQR method.

**Questions to prepare:**

1. How are the mean and standard deviation of community incident counts calculated?
2. Why include supplied communities with zero selected records in the unfiltered comparison?
3. How are Q1, Q3, IQR and the lower and upper outlier fences calculated?
4. Which communities lie outside the fences, and why does that not make the result a community safety score?

**Evidence to show:** Dashboard **Community count outliers** and `community_outliers()` in [use_case_3.py](../chicago-crime-explorer/use_case_3.py).

### Task 3.3: Analyze numerical correlations

**Assignment task:** Calculate a numerical correlation matrix with Pandas and display it as a heatmap.

**Questions to prepare:**

1. What does a Pearson correlation coefficient between -1 and +1 describe?
2. Why are identifiers and geographic codes excluded from this calculation?
3. Why are constant columns omitted, and what limitation applies to treating weekday as a numerical feature?
4. Why does an observed correlation not prove causation?

**Evidence to show:** Dashboard **Numeric relationships**; `numeric_correlations()` in [use_case_3.py](../chicago-crime-explorer/use_case_3.py).

## Use Case 4: Database Reporting and Integration

**Objective:** Store reusable analytical results, query them with SQL, read them into Pandas and present database-backed charts.

### Task 4.1: Design and populate summary tables

**Assignment task:** Create database tables and load data through Python. Populate summary tables for reporting.

**Questions to prepare:**

1. What is the difference between an incident table and a summary table?
2. What do `summary_yearly` and `summary_category` store?
3. How are summary tables refreshed when the source data is imported again?

**Evidence to show:** [sql/schema.sql](../chicago-crime-explorer/sql/schema.sql); summary-table population in [use_case_1.py](../chicago-crime-explorer/use_case_1.py).

### Task 4.2: Write the required SQL queries

**Assignment task:** Compute annual crime counts, the five most frequent crime categories with percentages, and annual arrest counts.

**Questions to prepare:**

1. How do you write a query to count incidents per year?
2. How do you select the top five categories while calculating their percentages against all incidents?
3. How do you count TRUE arrest flags per year?
4. Why should the top-five SQL requirement and top-ten visualization use the same underlying category definitions?

**Evidence to show:** [sql/reporting_queries.sql](../chicago-crime-explorer/sql/reporting_queries.sql); the SQL results saved in the analysis notebook under Use Case 4.

### Task 4.3: Create stored database views

**Assignment task:** Create `vw_crime_yearly` and `vw_crime_by_category`.

**Questions to prepare:**

1. What SELECT statement does each required view represent?
2. How does a stored view differ from a populated summary table?
3. What role does the additional `vw_crime_enriched` view play in this project?

**Evidence to show:** [sql/views.sql](../chicago-crime-explorer/sql/views.sql); the dashboard annual and category charts.

### Task 4.4: Read SQL views into Pandas

**Assignment task:** Read database views into DataFrames for further analysis.

**Questions to prepare:**

1. How does `pd.read_sql_query()` retrieve a view's result through a SQLAlchemy connection?
2. Why does the application analyze database output after ingestion?
3. How does the notebook verify that SQL results and Pandas calculations agree?
4. What do a SQLAlchemy engine, a connection, `text()` and a bound parameter do?

**Evidence to show:** `load_selection()` in [use_case_4.py](../chicago-crime-explorer/use_case_4.py); the dashboard annual and category tables.

### Task 4.5: Visualize database-derived results

**Assignment task:** Use Matplotlib and Seaborn to plot the data extracted from the database.

**Questions to prepare:**

1. How do database results flow into the chart-generation functions?
2. Which charts use Matplotlib directly, and which use Seaborn?
3. How can a viewer inspect the numerical results and incident records behind a chart?

**Evidence to show:** [use_case_4.py](../chicago-crime-explorer/use_case_4.py); dashboard charts and tables, and the **Crime records** screen.

---

## Additional questions about this solution

These questions concern implementation choices and added features in this project. They are separate from the assignment's four task groups.

### Data preservation and reliable totals

1. Why keep the original CSVs alongside the cleaned tables?
2. What can the import audit tell you about the source CSV?
3. Why are ward geography and multiple ward-office records stored separately?
4. What could go wrong if all ward-office records were joined directly into incident aggregates?
5. Why does importing the same source again not append duplicate incidents?
6. What information is retained for a quarantined record?
7. How does Pandera collect multiple failed validation rules with lazy=True?

### Dashboard and report export

1. How do the HTML forms submit to Flask, and which database functions do the pages and JSON API share?
2. How do year, category and community filters affect charts and downloaded records?
3. Which displayed tables describe the complete snapshot rather than the filtered selection?
4. What do the HTML report, selected CSV and result-metadata JSON contain?
5. How can you reproduce the report using the same dashboard filters?
6. Why must dashboard/chart responses avoid stale caching after a successful write?

### Verification and limitations

1. Which checks demonstrate that the cleaning process recovered the supplied incidents?
2. How do you verify that database joins have not inflated totals?
3. How are empty selections, API validation failures and malformed source rows tested?
4. Why is this implementation described as a batch proof of concept?
5. What better data would be needed before attempting forecasting or operational recommendations?

## Setup and demonstration questions

1. Why is a virtual environment useful for this project?
2. Why are the tested application dependencies listed in requirements.txt?
3. Which Python commands create the environment, import CSVs and start Flask?
4. Where is the SQLite database created, and why is a separate database server unnecessary?
5. How would you configure the project if the dataset directory moved?
6. Which files and setup steps are needed to run it on another computer?

**Useful files:** [requirements.txt](../chicago-crime-explorer/requirements.txt), [Run the current project](VIVA_GUIDE.md#run-the-current-project).

## Final revision checklist

Before the viva, confirm that you can:

- [ ] Explain the problem and the complete pipeline in one minute.
- [ ] Describe each of the four use cases and show its outputs.
- [ ] Explain the two CSV quote repairs and the handling of repeated reference records.
- [ ] Write or explain annual-count, top-five-category and annual-arrest SQL queries.
- [ ] Explain arrest percentage, category share, population adjustment and IQR.
- [ ] Explain why hourly analysis is unavailable for the supplied files.
- [ ] Distinguish an SQL view from a summary table.
- [ ] Apply a filter and trace a displayed number to its incident records.
- [ ] Export and open the HTML summary report.
- [ ] Explain the automated checks and the limits of this historical sample.


## Flask forms, CRUD and dashboard questions

1. Why is Flask responsible for both the HTML frontend and REST API?
2. What is the difference between GET, POST, PUT, PATCH and DELETE?
3. Which fields must be supplied when creating a crime record?
4. Why are IDs immutable and date-derived fields calculated by the server?
5. How does PATCH preserve fields not included in the request?
6. How does PUT reset omitted optional fields to their defaults?
7. Why can an unused community be deleted while a linked community cannot?
8. What do response codes 201, 204, 404, 409 and 422 mean?
9. How do Marshmallow schemas and Flask-Smorest automate validation and OpenAPI?
10. How can you demonstrate every HTTP method in the local Swagger UI?
11. Why do the record mutation and summary-table refresh use one transaction?
12. What happens if an update violates a unique key or foreign key?
13. How does Flask redirect after a successful form POST, and how does the dashboard read fresh totals and images?
14. How can you demonstrate that a chart changes after creating an incident?
15. Why does doubling a population halve its per-10,000 figure without changing its count?
16. How do you clear filters to find a saved record outside the current selection?
17. How do you preserve edits across a restart or a normal pipeline run?
18. When should the explicit pipeline --reset option be used?
19. Why are import-audit figures separate from working-data totals?
20. Which browser checks demonstrate the complete create, update and delete flow?
21. How does Jinja populate a record table from the Python results?
22. Why does the edit page accept POST while the API supports both PUT and PATCH?
23. How does the form keep submitted values when validation fails?
24. Why do search, filter and sort controls use GET? How do the Next and Previous links keep that selection?
