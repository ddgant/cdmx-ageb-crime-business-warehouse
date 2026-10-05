-- =====================================================================
-- 02_load.sql : populate dimensions and facts from the stg.* tables.
-- Idempotent: it empties the warehouse tables and reloads them.
-- Spatial integration (point -> AGEB polygon) is resolved here in PostGIS.
-- =====================================================================

TRUNCATE dw.fact_crime_incident, dw.fact_establishment, dw.fact_population_age,
         dw.fact_population_ageb, dw.dim_ageb, dw.dim_scian, dw.dim_business_size,
         dw.dim_crime_type, dw.dim_date, dw.etl_source_log
RESTART IDENTITY CASCADE;

-- 1. Geographic dimension -------------------------------------------------
INSERT INTO dw.dim_ageb (cvegeo, cve_ent, cve_mun, cve_loc, cve_ageb, nom_mun,
                         area_km2, geom, geom_utm)
SELECT s.cvegeo, s.cve_ent, s.cve_mun, s.cve_loc, s.cve_ageb, c.nom_mun,
       ST_Area(ST_Transform(s.geom, 32614)) / 1e6,
       ST_Multi(s.geom)::geometry(MultiPolygon, 4326),
       ST_Multi(ST_Transform(s.geom, 32614))::geometry(MultiPolygon, 32614)
FROM stg.ageb s
LEFT JOIN stg.census c ON c.cvegeo = s.cvegeo
ORDER BY s.cvegeo;

-- 2. Demographic facts ----------------------------------------------------
INSERT INTO dw.fact_population_ageb
    (ageb_key, pobtot, pobfem, pobmas, p_12ymas, pea, pe_inac, pocupada,
     pdesocup, vivtot, tvivhab, prom_ocup, graproes)
SELECT a.ageb_key, c.pobtot, c.pobfem, c.pobmas, c.p_12ymas, c.pea, c.pe_inac,
       c.pocupada, c.pdesocup, c.vivtot, c.tvivhab, c.prom_ocup, c.graproes
FROM stg.census c
JOIN dw.dim_ageb a ON a.cvegeo = c.cvegeo;

INSERT INTO dw.fact_population_age (ageb_key, age_group_key, population)
SELECT a.ageb_key, v.k, v.pop
FROM stg.census c
JOIN dw.dim_ageb a ON a.cvegeo = c.cvegeo
CROSS JOIN LATERAL (VALUES
    (1, c.p_0a2), (2, c.p_3a5), (3, c.p_6a11), (4, c.p_12a14),
    (5, c.p_15a17), (6, c.p_18a24), (7, c.p_25a59), (8, c.p_60ymas)
) AS v(k, pop);

-- 3. Economic dimensions --------------------------------------------------
-- SCIAN sector map. Retail = sector 46. Services = sectors 51-56, 61, 62, 71, 72, 81.
-- Everything else (including 43 wholesale and 93 government) is 'other'.
INSERT INTO dw.dim_scian (codigo_act, sector_code, sector_name, activity_name, macro_group)
SELECT DISTINCT ON (d.codigo_act)
       d.codigo_act, m.sector_code, m.sector_name, d.nombre_act,
       CASE WHEN m.sector_code = '46' THEN 'retail'
            WHEN m.sector_code IN ('51','52','53','54','55','56','61','62','71','72','81')
                 THEN 'services'
            ELSE 'other' END
FROM stg.denue d
JOIN (VALUES
    ('11','11','Agriculture, forestry, fishing and hunting'),
    ('21','21','Mining'),
    ('22','22','Utilities'),
    ('23','23','Construction'),
    ('31','31-33','Manufacturing'), ('32','31-33','Manufacturing'), ('33','31-33','Manufacturing'),
    ('43','43','Wholesale trade'),
    ('46','46','Retail trade'),
    ('48','48-49','Transportation and warehousing'), ('49','48-49','Transportation and warehousing'),
    ('51','51','Information media'),
    ('52','52','Finance and insurance'),
    ('53','53','Real estate and rental'),
    ('54','54','Professional, scientific and technical services'),
    ('55','55','Corporate management'),
    ('56','56','Business support and waste management'),
    ('61','61','Educational services'),
    ('62','62','Health care and social assistance'),
    ('71','71','Arts, entertainment and recreation'),
    ('72','72','Accommodation and food services'),
    ('81','81','Other services (except government)'),
    ('93','93','Government and international organizations')
) AS m(code2, sector_code, sector_name) ON m.code2 = LEFT(d.codigo_act, 2)
ORDER BY d.codigo_act;

INSERT INTO dw.dim_business_size (per_ocu, min_emp, max_emp)
SELECT per_ocu,
       CASE per_ocu WHEN '0 a 5 personas' THEN 0 WHEN '6 a 10 personas' THEN 6
            WHEN '11 a 30 personas' THEN 11 WHEN '31 a 50 personas' THEN 31
            WHEN '51 a 100 personas' THEN 51 WHEN '101 a 250 personas' THEN 101
            WHEN '251 y más personas' THEN 251 END,
       CASE per_ocu WHEN '0 a 5 personas' THEN 5 WHEN '6 a 10 personas' THEN 10
            WHEN '11 a 30 personas' THEN 30 WHEN '31 a 50 personas' THEN 50
            WHEN '51 a 100 personas' THEN 100 WHEN '101 a 250 personas' THEN 250
            ELSE NULL END
FROM (SELECT DISTINCT per_ocu FROM stg.denue WHERE per_ocu IS NOT NULL) x;

-- 4. Establishments: spatial join first, DENUE AGEB code as fallback -------
INSERT INTO dw.fact_establishment
    (denue_id, ageb_key, scian_key, size_key, nom_estab, ageb_source, coord_quality, geom)
SELECT d.id,
       COALESCE(sp.ageb_key, cd.ageb_key),
       s.scian_key, b.size_key, d.nom_estab,
       CASE WHEN sp.ageb_key IS NOT NULL THEN 'spatial'
            WHEN cd.ageb_key IS NOT NULL THEN 'denue_code' END,
       d.coord_quality,
       p.geom
FROM stg.denue d
CROSS JOIN LATERAL (
    SELECT CASE WHEN d.coord_quality = 'ok'
                THEN ST_SetSRID(ST_MakePoint(d.lon, d.lat), 4326) END AS geom
) p
LEFT JOIN LATERAL (
    SELECT a.ageb_key FROM dw.dim_ageb a
    WHERE p.geom IS NOT NULL AND ST_Intersects(a.geom, p.geom)
    ORDER BY a.ageb_key LIMIT 1
) sp ON TRUE
LEFT JOIN dw.dim_ageb cd ON cd.cvegeo = d.cvegeo_denue
JOIN dw.dim_scian s ON s.codigo_act = d.codigo_act
LEFT JOIN dw.dim_business_size b ON b.per_ocu = d.per_ocu;

-- 5. Crime ------------------------------------------------------------------
INSERT INTO dw.dim_date (date_key, full_date, year, quarter, month, month_name,
                         day, day_of_week, day_name, is_weekend)
SELECT TO_CHAR(g, 'YYYYMMDD')::INT, g::DATE,
       EXTRACT(YEAR FROM g), EXTRACT(QUARTER FROM g), EXTRACT(MONTH FROM g),
       (ARRAY['January','February','March','April','May','June','July','August',
              'September','October','November','December'])[EXTRACT(MONTH FROM g)::INT],
       EXTRACT(DAY FROM g), EXTRACT(ISODOW FROM g),
       (ARRAY['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'])
           [EXTRACT(ISODOW FROM g)::INT],
       EXTRACT(ISODOW FROM g) >= 6
FROM (SELECT MIN(occurred_date) AS a, MAX(occurred_date) AS b
      FROM stg.crime WHERE coord_quality = 'ok') r,
     LATERAL generate_series(r.a, r.b, INTERVAL '1 day') AS g;

INSERT INTO dw.dim_crime_type (crime_category, crime_type, fgj_category)
SELECT crime_category, crime_type, MIN(fgj_category) FROM stg.crime
WHERE crime_category IS NOT NULL AND crime_type IS NOT NULL AND coord_quality = 'ok'
GROUP BY crime_category, crime_type;

INSERT INTO dw.fact_crime_incident
    (source_id, ageb_key, crime_type_key, date_key, hour_key, geom)
SELECT c.source_id, sp.ageb_key, ct.crime_type_key,
       TO_CHAR(c.occurred_date, 'YYYYMMDD')::INT,
       c.occurred_hour, p.geom
FROM stg.crime c
CROSS JOIN LATERAL (
    SELECT ST_SetSRID(ST_MakePoint(c.lon, c.lat), 4326) AS geom
) p
LEFT JOIN LATERAL (
    SELECT a.ageb_key FROM dw.dim_ageb a
    WHERE ST_Intersects(a.geom, p.geom)
    ORDER BY a.ageb_key LIMIT 1
) sp ON TRUE
JOIN dw.dim_crime_type ct
  ON ct.crime_category = c.crime_category AND ct.crime_type = c.crime_type
WHERE c.coord_quality = 'ok';   -- incidents without a valid point are not georeferenced

-- 6. Traceability -------------------------------------------------------------
INSERT INTO dw.etl_source_log (source_name, source_file, edition, rows_staged, rows_loaded, note)
VALUES
 ('INEGI Marco Geoestadistico', '2020_1_09_A.shp', 'Censo 2020',
    (SELECT COUNT(*) FROM stg.ageb), (SELECT COUNT(*) FROM dw.dim_ageb),
    'Urban AGEB polygons, Mexico City'),
 ('INEGI Censo 2020', 'RESAGEBURB_09CSV20.csv', 'CPV 2020',
    (SELECT COUNT(*) FROM stg.census), (SELECT COUNT(*) FROM dw.fact_population_ageb),
    'AGEB totals (MZA=000); AGEB without polygon are not loaded'),
 ('INEGI DENUE', 'denue_inegi_09_.csv', '11/2024',
    (SELECT COUNT(*) FROM stg.denue), (SELECT COUNT(*) FROM dw.fact_establishment),
    'CDMX establishments'),
 ('FGJ CDMX carpetas de investigacion', 'carpetasFGJ_acumulado_2025_01.csv', '2024 (fecha_hecho)',
    (SELECT COUNT(*) FROM stg.crime), (SELECT COUNT(*) FROM dw.fact_crime_incident),
    'Only incidents with a valid point inside CDMX are loaded');
