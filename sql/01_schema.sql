-- =====================================================================
-- Mexico City (CDMX) Urban Intelligence - Geospatial Data Warehouse
-- 01_schema.sql : extensions, schemas, dimensions and fact tables
-- Geographic unit of analysis: INEGI urban AGEB (13-character CVEGEO)
-- Storage CRS: EPSG:4326 (geom). Metric CRS for area: EPSG:32614 (UTM 14N)
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE SCHEMA IF NOT EXISTS stg;   -- cleaned staging tables written by the ETL
CREATE SCHEMA IF NOT EXISTS dw;    -- dimensional model

-- ---------------------------------------------------------------------
-- DIMENSIONS
-- ---------------------------------------------------------------------

-- Geographic dimension: one row per urban AGEB in the study area
CREATE TABLE IF NOT EXISTS dw.dim_ageb (
    ageb_key      SERIAL PRIMARY KEY,
    cvegeo        VARCHAR(13) NOT NULL UNIQUE,   -- ENT(2)+MUN(3)+LOC(4)+AGEB(4)
    cve_ent       CHAR(2)     NOT NULL,
    cve_mun       CHAR(3)     NOT NULL,
    cve_loc       CHAR(4)     NOT NULL,
    cve_ageb      VARCHAR(4)  NOT NULL,
    nom_mun       VARCHAR(100),                  -- alcaldia name
    area_km2      NUMERIC(12,6),                 -- computed from geom_utm
    geom          GEOMETRY(MultiPolygon, 4326) NOT NULL,
    geom_utm      GEOMETRY(MultiPolygon, 32614) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_dim_ageb_geom     ON dw.dim_ageb USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_dim_ageb_geom_utm ON dw.dim_ageb USING GIST (geom_utm);

-- Calendar dimension
CREATE TABLE IF NOT EXISTS dw.dim_date (
    date_key     INTEGER PRIMARY KEY,            -- yyyymmdd
    full_date    DATE NOT NULL UNIQUE,
    year         SMALLINT NOT NULL,
    quarter      SMALLINT NOT NULL,
    month        SMALLINT NOT NULL,
    month_name   VARCHAR(12) NOT NULL,
    day          SMALLINT NOT NULL,
    day_of_week  SMALLINT NOT NULL,              -- 1=Monday ... 7=Sunday
    day_name     VARCHAR(12) NOT NULL,
    is_weekend   BOOLEAN NOT NULL
);

-- Hour-of-day dimension with time bands
CREATE TABLE IF NOT EXISTS dw.dim_time (
    hour_key   SMALLINT PRIMARY KEY CHECK (hour_key BETWEEN 0 AND 23),
    time_band  VARCHAR(12) NOT NULL              -- night, morning, afternoon, evening
);

-- Crime classification
CREATE TABLE IF NOT EXISTS dw.dim_crime_type (
    crime_type_key  SERIAL PRIMARY KEY,
    crime_category  VARCHAR(100) NOT NULL,       -- analytical group built by the ETL
    crime_type      VARCHAR(300) NOT NULL,       -- specific offense ('delito') as in source
    fgj_category    VARCHAR(100),                -- original FGJ category, kept for traceability
    UNIQUE (crime_category, crime_type)
);

-- SCIAN economic activity classification (DENUE)
CREATE TABLE IF NOT EXISTS dw.dim_scian (
    scian_key       SERIAL PRIMARY KEY,
    codigo_act      VARCHAR(6) NOT NULL UNIQUE,  -- 6-digit SCIAN class
    sector_code     VARCHAR(5) NOT NULL,         -- SCIAN sector ('31-33','48-49' grouped as INEGI does)
    sector_name     VARCHAR(200),
    subsector_code  VARCHAR(3),
    activity_name   VARCHAR(300),
    macro_group     VARCHAR(10) NOT NULL
        CHECK (macro_group IN ('retail','services','other'))
);

-- Business size (DENUE employment stratum)
CREATE TABLE IF NOT EXISTS dw.dim_business_size (
    size_key    SERIAL PRIMARY KEY,
    per_ocu     VARCHAR(40) NOT NULL UNIQUE,     -- label as in DENUE, e.g. '0 a 5 personas'
    min_emp     INTEGER,
    max_emp     INTEGER
);

-- Age groups used in the demographic fact
CREATE TABLE IF NOT EXISTS dw.dim_age_group (
    age_group_key  SMALLINT PRIMARY KEY,
    label          VARCHAR(20) NOT NULL UNIQUE,
    min_age        SMALLINT NOT NULL,
    max_age        SMALLINT                       -- NULL = open-ended
);

-- ---------------------------------------------------------------------
-- FACTS
-- ---------------------------------------------------------------------

-- Grain: one row per AGEB (Census 2020 snapshot)
CREATE TABLE IF NOT EXISTS dw.fact_population_ageb (
    ageb_key      INTEGER PRIMARY KEY REFERENCES dw.dim_ageb(ageb_key),
    pobtot        INTEGER,    -- total population
    pobfem        INTEGER,
    pobmas        INTEGER,
    p_12ymas      INTEGER,    -- population aged 12+ (base for activity rate)
    pea           INTEGER,    -- economically active population
    pe_inac       INTEGER,    -- economically inactive population
    pocupada      INTEGER,    -- employed population
    pdesocup      INTEGER,    -- unemployed population
    vivtot        INTEGER,    -- total dwellings
    tvivhab       INTEGER,    -- occupied dwellings
    prom_ocup     NUMERIC(6,2),
    graproes      NUMERIC(6,2),
    census_year   SMALLINT NOT NULL DEFAULT 2020
);

-- Grain: one row per AGEB x age group
CREATE TABLE IF NOT EXISTS dw.fact_population_age (
    ageb_key       INTEGER  NOT NULL REFERENCES dw.dim_ageb(ageb_key),
    age_group_key  SMALLINT NOT NULL REFERENCES dw.dim_age_group(age_group_key),
    population     INTEGER,
    PRIMARY KEY (ageb_key, age_group_key)
);

-- Grain: one row per DENUE establishment
CREATE TABLE IF NOT EXISTS dw.fact_establishment (
    establishment_key  BIGSERIAL PRIMARY KEY,
    denue_id           VARCHAR(20) NOT NULL UNIQUE,   -- source traceability
    ageb_key           INTEGER REFERENCES dw.dim_ageb(ageb_key),  -- NULL if outside any AGEB
    scian_key          INTEGER NOT NULL REFERENCES dw.dim_scian(scian_key),
    size_key           INTEGER REFERENCES dw.dim_business_size(size_key),
    nom_estab          VARCHAR(300),
    ageb_source        VARCHAR(10) CHECK (ageb_source IN ('spatial','denue_code')),
    coord_quality      VARCHAR(10) NOT NULL CHECK (coord_quality IN ('ok','invalid')),
    geom               GEOMETRY(Point, 4326)          -- NULL when source coordinates are invalid
);
CREATE INDEX IF NOT EXISTS idx_fact_est_ageb  ON dw.fact_establishment (ageb_key);
CREATE INDEX IF NOT EXISTS idx_fact_est_scian ON dw.fact_establishment (scian_key);
CREATE INDEX IF NOT EXISTS idx_fact_est_geom  ON dw.fact_establishment USING GIST (geom);

-- Grain: one row per reported crime incident
CREATE TABLE IF NOT EXISTS dw.fact_crime_incident (
    incident_key    BIGSERIAL PRIMARY KEY,
    source_id       VARCHAR(50),                      -- id in source file, if any
    ageb_key        INTEGER REFERENCES dw.dim_ageb(ageb_key),  -- NULL if outside study area
    crime_type_key  INTEGER NOT NULL REFERENCES dw.dim_crime_type(crime_type_key),
    date_key        INTEGER REFERENCES dw.dim_date(date_key),
    hour_key        SMALLINT REFERENCES dw.dim_time(hour_key),
    geom            GEOMETRY(Point, 4326) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_fact_crime_ageb ON dw.fact_crime_incident (ageb_key);
CREATE INDEX IF NOT EXISTS idx_fact_crime_type ON dw.fact_crime_incident (crime_type_key);
CREATE INDEX IF NOT EXISTS idx_fact_crime_date ON dw.fact_crime_incident (date_key);
CREATE INDEX IF NOT EXISTS idx_fact_crime_geom ON dw.fact_crime_incident USING GIST (geom);

-- ---------------------------------------------------------------------
-- ETL TRACEABILITY
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dw.etl_source_log (
    log_id       SERIAL PRIMARY KEY,
    source_name  VARCHAR(60) NOT NULL,
    source_file  VARCHAR(200),
    edition      VARCHAR(40),
    rows_staged  INTEGER,
    rows_loaded  INTEGER,
    note         TEXT,
    loaded_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- STATIC REFERENCE DATA
-- ---------------------------------------------------------------------
INSERT INTO dw.dim_time (hour_key, time_band)
SELECT h,
       CASE WHEN h BETWEEN 0  AND 5  THEN 'night'
            WHEN h BETWEEN 6  AND 11 THEN 'morning'
            WHEN h BETWEEN 12 AND 17 THEN 'afternoon'
            ELSE 'evening' END
FROM generate_series(0, 23) AS h
ON CONFLICT (hour_key) DO NOTHING;

INSERT INTO dw.dim_age_group (age_group_key, label, min_age, max_age) VALUES
    (1, '0-2',   0,  2),
    (2, '3-5',   3,  5),
    (3, '6-11',  6, 11),
    (4, '12-14', 12, 14),
    (5, '15-17', 15, 17),
    (6, '18-24', 18, 24),
    (7, '25-59', 25, 59),
    (8, '60+',   60, NULL)
ON CONFLICT (age_group_key) DO NOTHING;
