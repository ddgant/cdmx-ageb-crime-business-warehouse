-- =====================================================================
-- 04_validation.sql : integrity checks and proof that every required KPI
-- can be computed from the warehouse alone. Each row is one check.
-- =====================================================================
SELECT check_name, expected, actual, (expected = actual) AS pass
FROM (
    SELECT 'dim_ageb rows = staged AGEB polygons' AS check_name,
           (SELECT COUNT(*) FROM stg.ageb)::NUMERIC AS expected,
           (SELECT COUNT(*) FROM dw.dim_ageb)::NUMERIC AS actual
    UNION ALL SELECT 'every AGEB has a population fact',
           (SELECT COUNT(*) FROM dw.dim_ageb)::NUMERIC,
           (SELECT COUNT(*) FROM dw.fact_population_ageb)::NUMERIC
    UNION ALL SELECT 'population in warehouse = census total of AGEB that have a polygon',
           (SELECT SUM(c.pobtot) FROM stg.census c JOIN stg.ageb a USING (cvegeo))::NUMERIC,
           (SELECT SUM(pobtot) FROM dw.fact_population_ageb)::NUMERIC
    UNION ALL SELECT 'establishments loaded = staged DENUE rows',
           (SELECT COUNT(*) FROM stg.denue)::NUMERIC,
           (SELECT COUNT(*) FROM dw.fact_establishment)::NUMERIC
    UNION ALL SELECT 'crimes loaded = staged crimes with a valid point',
           (SELECT COUNT(*) FROM stg.crime WHERE coord_quality = 'ok')::NUMERIC,
           (SELECT COUNT(*) FROM dw.fact_crime_incident)::NUMERIC
    UNION ALL SELECT 'KPI view total_businesses = establishments with an AGEB',
           (SELECT COUNT(*) FROM dw.fact_establishment WHERE ageb_key IS NOT NULL)::NUMERIC,
           (SELECT SUM(total_businesses) FROM dw.vw_ageb_kpis)::NUMERIC
    UNION ALL SELECT 'KPI view total_crimes = incidents with an AGEB',
           (SELECT COUNT(*) FROM dw.fact_crime_incident WHERE ageb_key IS NOT NULL)::NUMERIC,
           (SELECT SUM(total_crimes) FROM dw.vw_ageb_kpis)::NUMERIC
    UNION ALL SELECT 'orphan establishments (bad FK) = 0', 0::NUMERIC,
           (SELECT COUNT(*) FROM dw.fact_establishment e
              LEFT JOIN dw.dim_scian s USING (scian_key) WHERE s.scian_key IS NULL)::NUMERIC
    UNION ALL SELECT 'AGEB areas all positive', 0::NUMERIC,
           (SELECT COUNT(*) FROM dw.dim_ageb WHERE area_km2 IS NULL OR area_km2 <= 0)::NUMERIC
    UNION ALL SELECT 'establishments with valid coords but wrong SRID', 0::NUMERIC,
           (SELECT COUNT(*) FROM dw.fact_establishment
             WHERE geom IS NOT NULL AND ST_SRID(geom) <> 4326)::NUMERIC
    UNION ALL SELECT 'every warehouse column has a comment (data dictionary complete)', 0::NUMERIC,
           (SELECT COUNT(*) FROM information_schema.columns c
             WHERE c.table_schema = 'dw'
               AND col_description((quote_ident(c.table_schema) || '.' || quote_ident(c.table_name))::regclass,
                                   c.ordinal_position) IS NULL)::NUMERIC
) t;

-- Coverage of the spatial integration (informational)
SELECT 'establishments' AS fact, ageb_source, COUNT(*) AS n,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct
FROM dw.fact_establishment GROUP BY ageb_source
UNION ALL
SELECT 'crime', CASE WHEN ageb_key IS NULL THEN 'unassigned' ELSE 'spatial' END, COUNT(*),
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)
FROM dw.fact_crime_incident GROUP BY (ageb_key IS NULL)
ORDER BY 1, 2;

-- KPI sample: ten densest AGEBs (demographic + economic KPIs)
SELECT cvegeo, total_population, ROUND(population_density_km2::NUMERIC, 0) AS pop_density_km2,
       ROUND(eap_rate_pct::NUMERIC, 1) AS eap_rate_pct, total_businesses,
       ROUND(businesses_per_1000::NUMERIC, 1) AS biz_per_1000,
       dominant_sector_name
FROM dw.vw_ageb_kpis
WHERE total_population IS NOT NULL
ORDER BY population_density_km2 DESC NULLS LAST
LIMIT 10;
