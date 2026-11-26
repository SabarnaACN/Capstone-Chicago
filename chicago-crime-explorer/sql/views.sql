CREATE VIEW vw_crime_enriched AS
SELECT
    c.*,
    COALESCE(i.primary_type, 'UNKNOWN') AS primary_type,
    i.description AS offence_description,
    COALESCE(a.community_name, 'Unknown community') AS community_name,
    a.population,
    COALESCE(d.district_name, 'Unknown district') AS district_name
FROM chicago_crime c
LEFT JOIN iucr i ON c.iucr_code = i.iucr_code
LEFT JOIN city_community a ON c.community_code = a.community_code
LEFT JOIN district_ps_info d ON c.district_code = d.district_code;

CREATE VIEW vw_crime_yearly AS
SELECT
    year,
    COUNT(*) AS crime_count,
    SUM(CASE WHEN arrest = 1 THEN 1 ELSE 0 END) AS arrest_count,
    COUNT(arrest) AS arrest_known_count,
    ROUND(
        100.0 * SUM(CASE WHEN arrest = 1 THEN 1 ELSE 0 END)
        / NULLIF(COUNT(arrest), 0),
        2
    ) AS arrest_percentage
FROM chicago_crime
GROUP BY year;

CREATE VIEW vw_crime_by_category AS
SELECT
    primary_type,
    COUNT(*) AS crime_count,
    ROUND(
        100.0 * COUNT(*)
        / NULLIF((SELECT COUNT(*) FROM chicago_crime), 0),
        2
    ) AS percentage
FROM vw_crime_enriched
GROUP BY primary_type;
