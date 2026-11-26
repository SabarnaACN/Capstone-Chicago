"""Use case 2: explore incident counts and draw the descriptive charts."""

import calendar

import numpy as np
import pandas as pd
import seaborn as sns

from use_case_3 import community_outliers, numeric_correlations


def community_counts(df, communities):
    counts = df.groupby("community_code").size().rename("crime_count")
    areas = communities[["community_code", "community_name", "population"]].merge(
        counts, how="left", left_on="community_code", right_index=True
    )
    areas["crime_count"] = areas["crime_count"].fillna(0).astype(int)
    areas["per_10000"] = (
        10000 * areas["crime_count"] / areas["population"].where(areas["population"] > 0)
    )
    return community_outliers(areas)


def category_summary(df):
    total = len(df)
    categories = df.groupby("primary_type").size().rename("crime_count").reset_index()
    categories = categories.sort_values(["crime_count", "primary_type"], ascending=[False, True])
    categories["percentage"] = 100 * categories["crime_count"] / total if total else 0
    return categories


def annual_summary(df):
    yearly = df.groupby("year", as_index=False).agg(
        crime_count=("id", "size"),
        arrest_count=("arrest", "sum"),
        arrest_known_count=("arrest", "count"),
    )
    yearly["arrest_percentage"] = (
        100 * yearly["arrest_count"] / yearly["arrest_known_count"].replace(0, np.nan)
    )
    return yearly


def summarize(df, communities, yearly=None, categories=None):
    total = len(df)
    flags = df["arrest"]
    arrests = int(flags.sum())
    known_flags = int(flags.count())
    if categories is None:
        categories = category_summary(df)
    if yearly is None:
        yearly = annual_summary(df)
    areas, outliers, spread = community_counts(df, communities)
    correlation, strongest = numeric_correlations(df)
    daily = df.groupby(df["date"].dt.date).size().nlargest(2)
    months = df["month"].value_counts().sort_index()
    peak_month = int(months.idxmax()) if total else 0
    return {
        "total": total,
        "arrests": arrests,
        "known_arrests": known_flags,
        "arrest_percentage": round(100 * arrests / known_flags, 2) if known_flags else None,
        "categories": categories,
        "yearly": yearly,
        "communities": areas,
        "top_category": str(categories.iloc[0]["primary_type"]) if total else "No records",
        "top_category_pct": round(float(categories.iloc[0]["percentage"]), 2) if total else 0.0,
        "peak_month": calendar.month_name[peak_month] if total else "No records",
        "peak_month_count": int(months.max()) if total else 0,
        "correlation": correlation,
        "strongest_correlation": strongest,
        "concentration": round(float(100 * daily.sum() / total), 2) if total else 0.0,
        "date_min": df["date"].min().strftime("%d %b %Y") if total else "No records",
        "date_max": df["date"].max().strftime("%d %b %Y") if total else "No records",
        "dates_observed": int(df["date"].dt.date.nunique()),
        "communities_observed": int(df["community_code"].nunique()),
        "timed_records": int(df["has_time"].sum()),
        "outlier_communities": outliers.to_dict("records"),
        "missing_coordinates": int(df[["latitude", "longitude"]].isna().any(axis=1).sum()),
        "iqr": spread,
    }


def plot_exploration(axis, kind, df, stats):
    if kind == "yearly":
        years = stats["yearly"]
        axis.plot(years["year"], years["crime_count"], marker="o")
        axis.set(xlabel="Year", ylabel="Incidents", xticks=years["year"])
        axis.ticklabel_format(axis="x", style="plain", useOffset=False)
    elif kind == "monthly":
        df.groupby(df["date"].dt.to_period("M").astype(str)).size().plot(ax=axis, marker="o")
        axis.set(xlabel="Observed month", ylabel="Incidents")
    elif kind in ("top5", "categories"):
        limit = 5 if kind == "top5" else 10
        top = stats["categories"].head(limit).iloc[::-1]
        axis.barh(top["primary_type"], top["crime_count"])
        axis.set_xlabel("Incidents")
    elif kind in ("arrests", "arrest-counts"):
        years = stats["yearly"]
        column = "arrest_percentage" if kind == "arrests" else "arrest_count"
        axis.bar(years["year"].astype(str), years[column])
        axis.set(xlabel="Year", ylabel="Recorded arrests")
        if kind == "arrests":
            axis.set(ylabel="Arrest (%)", ylim=(0, 105))
    elif kind in ("communities", "normalized"):
        column = "per_10000" if kind == "normalized" else "crime_count"
        top = stats["communities"].nlargest(10, column).iloc[::-1]
        axis.barh(top["community_name"], top[column])
        axis.set_xlabel("Incidents per 10,000 residents" if kind == "normalized" else "Incidents")
    elif kind == "calendar":
        counts = pd.crosstab(df["month"], df["day_of_week"])
        counts = counts.reindex(index=range(1, 13), columns=range(7), fill_value=0)
        sns.heatmap(counts, ax=axis, annot=True, fmt="d", cmap="Blues",
                    xticklabels=list(calendar.day_abbr), yticklabels=list(calendar.month_abbr)[1:])
        axis.set(xlabel="Weekday", ylabel="Month")
