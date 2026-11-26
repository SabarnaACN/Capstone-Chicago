"""Use case 3: hourly counts, community outliers and correlations."""

import numpy as np
import seaborn as sns


def hourly_counts(incidents):
    timed = incidents.loc[incidents["has_time"] == 1]
    counts = timed.groupby("hour").size()
    if counts.empty:
        return counts
    return counts.reindex(range(24), fill_value=0)


def community_outliers(areas):
    values = areas["crime_count"].to_numpy()
    q1, q3 = np.percentile(values, [25, 75]) if len(values) else (0.0, 0.0)
    iqr = q3 - q1
    lower, upper = float(q1 - 1.5 * iqr), float(q3 + 1.5 * iqr)
    areas["is_outlier"] = ~areas["crime_count"].between(lower, upper)
    areas = areas.sort_values(["crime_count", "community_name"], ascending=[False, True])
    outliers = areas.loc[areas["is_outlier"], ["community_name", "crime_count"]]
    spread = {
        "q1": float(q1),
        "q3": float(q3),
        "lower": lower,
        "upper": upper,
        "mean": float(np.mean(values)) if len(values) else 0.0,
        "std": float(np.std(values)) if len(values) else 0.0,
        "outliers": int(areas["is_outlier"].sum()),
    }
    return areas, outliers, spread


def numeric_correlations(df):
    numeric = df[["year", "month", "day_of_week", "arrest", "domestic"]].rename(columns={
        "year": "Year", "month": "Month", "day_of_week": "Weekday",
        "arrest": "Arrest flag", "domestic": "Domestic flag",
    })
    correlation = numeric.loc[:, numeric.nunique() > 1].corr(min_periods=2)
    upper_triangle = np.triu(np.ones(correlation.shape, dtype=bool), k=1)
    pairs = correlation.where(upper_triangle).stack().dropna()
    strongest = None
    if not pairs.empty:
        left, right = pairs.abs().idxmax()
        strongest = {"left": left, "right": right, "coefficient": float(pairs.loc[left, right])}
    return correlation, strongest


def plot_pattern(axis, kind, df, stats):
    message = ""
    if kind == "outliers":
        sns.boxplot(x=stats["communities"]["crime_count"], ax=axis)
        axis.axvline(stats["iqr"]["upper"], linestyle="--", color="gray")
        axis.set_xlabel("Incidents per community")
    elif kind == "correlation":
        if stats["strongest_correlation"] is None:
            message = "Too little variation for a correlation matrix"
        else:
            sns.heatmap(stats["correlation"], ax=axis, annot=True, fmt=".2f",
                        vmin=-1, vmax=1, center=0, cmap="vlag")
    elif kind == "hourly":
        counts = hourly_counts(df)
        if counts.empty:
            message = "Hourly analysis unavailable: source contains dates only"
        else:
            counts.plot(ax=axis)
            axis.set(xlabel="Recorded hour", ylabel="Incidents")
    return message
