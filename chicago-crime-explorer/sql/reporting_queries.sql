-- Crime count and arrest count per year.
SELECT *
FROM vw_crime_yearly
ORDER BY year;

-- Percentages use all incidents, including categories outside the top five.
SELECT *
FROM vw_crime_by_category
ORDER BY crime_count DESC, primary_type
LIMIT 5;

-- The community lookup has one row per key, so each incident is counted once.
SELECT
    community_code,
    community_name,
    COUNT(*) AS crime_count
FROM vw_crime_enriched
GROUP BY community_code, community_name
ORDER BY crime_count DESC, community_name
LIMIT 10;

-- Check date coverage before interpreting annual counts.
SELECT
    SUBSTR(date, 1, 10) AS incident_date,
    COUNT(*) AS crime_count
FROM chicago_crime
GROUP BY incident_date
ORDER BY crime_count DESC
LIMIT 5;

-- The base and enriched counts should match.
SELECT
    (SELECT COUNT(*) FROM chicago_crime) AS base_count,
    (SELECT COUNT(*) FROM vw_crime_enriched) AS joined_count;
