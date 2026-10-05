-- =====================================================================
-- 03_views.sql : analytical views. All KPIs are computed from dw.* only.
-- =====================================================================

-- Business counts per AGEB
CREATE OR REPLACE VIEW dw.vw_ageb_business AS
SELECT
    e.ageb_key,
    COUNT(*)                                           AS total_businesses,
    COUNT(*) FILTER (WHERE s.macro_group = 'retail')   AS retail_businesses,
    COUNT(*) FILTER (WHERE s.macro_group = 'services') AS service_businesses
FROM dw.fact_establishment e
JOIN dw.dim_scian s USING (scian_key)
WHERE e.ageb_key IS NOT NULL
GROUP BY e.ageb_key;

-- Dominant economic sector per AGEB (ties broken by lowest sector code)
CREATE OR REPLACE VIEW dw.vw_ageb_dominant_sector AS
SELECT ageb_key, sector_code, sector_name, n_establishments
FROM (
    SELECT e.ageb_key, s.sector_code, s.sector_name,
           COUNT(*) AS n_establishments,
           ROW_NUMBER() OVER (PARTITION BY e.ageb_key
                              ORDER BY COUNT(*) DESC, s.sector_code) AS rn
    FROM dw.fact_establishment e
    JOIN dw.dim_scian s USING (scian_key)
    WHERE e.ageb_key IS NOT NULL
    GROUP BY e.ageb_key, s.sector_code, s.sector_name
) t
WHERE rn = 1;

-- Crime counts per AGEB
CREATE OR REPLACE VIEW dw.vw_ageb_crime AS
SELECT ageb_key, COUNT(*) AS total_crimes
FROM dw.fact_crime_incident
WHERE ageb_key IS NOT NULL
GROUP BY ageb_key;

-- Crime by AGEB x type x year x time band (for "incidents by type and time")
CREATE OR REPLACE VIEW dw.vw_crime_type_time AS
SELECT c.ageb_key,
       ct.crime_category,
       ct.crime_type,
       d.year,
       d.month,
       d.day_name,
       d.is_weekend,
       t.time_band,
       COUNT(*) AS incidents
FROM dw.fact_crime_incident c
JOIN dw.dim_crime_type ct USING (crime_type_key)
LEFT JOIN dw.dim_date d USING (date_key)
LEFT JOIN dw.dim_time t USING (hour_key)
WHERE c.ageb_key IS NOT NULL
GROUP BY c.ageb_key, ct.crime_category, ct.crime_type,
         d.year, d.month, d.day_name, d.is_weekend, t.time_band;

-- Population by age group, pivoted (counts and shares)
CREATE OR REPLACE VIEW dw.vw_ageb_age_groups AS
SELECT
    pa.ageb_key,
    SUM(pa.population) FILTER (WHERE g.label = '0-2')   AS pop_0_2,
    SUM(pa.population) FILTER (WHERE g.label = '3-5')   AS pop_3_5,
    SUM(pa.population) FILTER (WHERE g.label = '6-11')  AS pop_6_11,
    SUM(pa.population) FILTER (WHERE g.label = '12-14') AS pop_12_14,
    SUM(pa.population) FILTER (WHERE g.label = '15-17') AS pop_15_17,
    SUM(pa.population) FILTER (WHERE g.label = '18-24') AS pop_18_24,
    SUM(pa.population) FILTER (WHERE g.label = '25-59') AS pop_25_59,
    SUM(pa.population) FILTER (WHERE g.label = '60+')   AS pop_60_plus
FROM dw.fact_population_age pa
JOIN dw.dim_age_group g USING (age_group_key)
GROUP BY pa.ageb_key;

-- Master KPI view: one row per AGEB with every required KPI
CREATE OR REPLACE VIEW dw.vw_ageb_kpis AS
SELECT
    a.ageb_key,
    a.cvegeo,
    a.area_km2,
    -- Demographic
    p.pobtot                                                     AS total_population,
    p.pobtot / NULLIF(a.area_km2, 0)                             AS population_density_km2,
    100.0 * p.pea / NULLIF(p.p_12ymas, 0)                        AS eap_rate_pct,
    ag.pop_0_2, ag.pop_3_5, ag.pop_6_11, ag.pop_12_14,
    ag.pop_15_17, ag.pop_18_24, ag.pop_25_59, ag.pop_60_plus,
    100.0 * ag.pop_60_plus / NULLIF(p.pobtot, 0)                 AS share_60_plus_pct,
    100.0 * (ag.pop_0_2 + ag.pop_3_5 + ag.pop_6_11
             + ag.pop_12_14 + ag.pop_15_17) / NULLIF(p.pobtot, 0) AS share_under_18_pct,
    -- Economic
    COALESCE(b.total_businesses, 0)                              AS total_businesses,
    COALESCE(b.total_businesses, 0) / NULLIF(a.area_km2, 0)      AS business_density_km2,
    1000.0 * COALESCE(b.total_businesses, 0) / NULLIF(p.pobtot, 0) AS businesses_per_1000,
    COALESCE(b.retail_businesses, 0)  / NULLIF(a.area_km2, 0)    AS retail_density_km2,
    COALESCE(b.service_businesses, 0) / NULLIF(a.area_km2, 0)    AS service_density_km2,
    ds.sector_code                                               AS dominant_sector_code,
    ds.sector_name                                               AS dominant_sector_name,
    -- Public safety
    COALESCE(c.total_crimes, 0)                                  AS total_crimes,
    1000.0 * COALESCE(c.total_crimes, 0) / NULLIF(p.pobtot, 0)   AS crime_rate_per_1000,
    100.0  * COALESCE(c.total_crimes, 0)
           / NULLIF(COALESCE(b.total_businesses, 0), 0)          AS crimes_per_100_businesses,
    a.geom
FROM dw.dim_ageb a
LEFT JOIN dw.fact_population_ageb p  USING (ageb_key)
LEFT JOIN dw.vw_ageb_age_groups   ag USING (ageb_key)
LEFT JOIN dw.vw_ageb_business     b  USING (ageb_key)
LEFT JOIN dw.vw_ageb_dominant_sector ds USING (ageb_key)
LEFT JOIN dw.vw_ageb_crime        c  USING (ageb_key);
