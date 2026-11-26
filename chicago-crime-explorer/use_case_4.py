"""Use case 4: read SQL views, serve charts and export the summary."""

import io
import json
from html import escape
from threading import RLock
from typing import NamedTuple

import pandas as pd
from matplotlib.figure import Figure
from sqlalchemy import text

from database import create_read_engine
from use_case_2 import plot_exploration, summarize
from use_case_3 import plot_pattern


CHART_LOCK = RLock()
PATTERN_CHARTS = {"outliers", "correlation", "hourly"}
CHARTS = {
    "yearly",
    "monthly",
    "categories",
    "top5",
    "arrest-counts",
    "arrests",
    "calendar",
    "communities",
    "normalized",
    "outliers",
    "correlation",
    "hourly",
}


class Selection(NamedTuple):
    incidents: pd.DataFrame
    stats: dict
    filters: dict
    quality: dict
    full_total: int


def load_selection(db_path, filters):
    columns = {"year": "year", "category": "primary_type", "community_code": "community_code"}
    conditions = [f"{column} = :{name}" for name, column in columns.items() if name in filters]
    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    engine = create_read_engine(db_path)
    with engine.connect() as db:
        db.exec_driver_sql("BEGIN")
        incidents = pd.read_sql_query(
            text("SELECT * FROM vw_crime_enriched" + where + " ORDER BY date, id"), db, params=filters
        )
        area_where = " WHERE community_code = :community_code" if "community_code" in filters else ""
        areas = pd.read_sql_query(text("SELECT * FROM city_community" + area_where), db, params=filters)
        yearly = categories = None
        if where:
            full_total = db.execute(text("SELECT COUNT(*) FROM chicago_crime")).scalar_one()
        else:
            full_total = len(incidents)
            yearly = pd.read_sql_query("SELECT * FROM vw_crime_yearly ORDER BY year", db)
            categories = pd.read_sql_query(
                "SELECT * FROM vw_crime_by_category ORDER BY crime_count DESC, primary_type", db
            )
        audit = db.execute(text("SELECT report_json FROM pipeline_run")).scalar_one()

    incidents["date"] = pd.to_datetime(incidents["date"], format="mixed")
    stats = summarize(incidents, areas, yearly, categories)
    return Selection(incidents, stats, filters, json.loads(audit), full_total)


def chart_png(kind, incidents, stats):
    image = io.BytesIO()
    with CHART_LOCK:
        figure = Figure(figsize=(7.2, 4.5), layout="constrained")
        axis = figure.subplots()
        message = ""
        if incidents.empty:
            message = "No records match these filters"
        elif kind in PATTERN_CHARTS:
            message = plot_pattern(axis, kind, incidents, stats)
        else:
            plot_exploration(axis, kind, incidents, stats)
        if message:
            axis.text(0.5, 0.5, message, ha="center", va="center", wrap=True)
            axis.set_axis_off()
        figure.savefig(image, format="png", dpi=140)
    image.seek(0)
    return image


def summary_json(stats, filters, quality):
    summary = {name: value for name, value in stats.items() if not isinstance(value, pd.DataFrame)}
    summary["filters"] = filters
    summary["pipeline_run_id"] = quality["run_id"]
    return summary


def make_report(stats, filters):
    parts = [
        '<!doctype html><html lang="en"><meta charset="utf-8"><title>Chicago crime summary</title>',
        "<h1>Chicago crime summary</h1>",
        f"<p>{stats['total']} selected incidents and {stats['arrests']} recorded arrests.</p>",
        "<p>Filters: " + escape(json.dumps(filters)) + "</p>",
    ]
    for title, name in [("Annual counts", "yearly"), ("Top five offences", "categories")]:
        table = stats[name].head(5) if name == "categories" else stats[name]
        parts.extend([f"<h2>{title}</h2>", table.to_html(index=False, na_rep="—")])
    return "\n".join(parts) + "</html>"
