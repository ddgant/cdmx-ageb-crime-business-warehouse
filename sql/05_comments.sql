-- =====================================================================
-- 05_comments.sql : column and table comments. The data dictionary
-- (docs/data_dictionary.md) is generated from these comments, so the
-- database documents itself. Run after 03_views.sql.
-- =====================================================================

COMMENT ON TABLE dw.dim_ageb IS 'Geographic dimension. One row per INEGI urban AGEB in Mexico City (unit of analysis).';
COMMENT ON COLUMN dw.dim_ageb.ageb_key IS 'Surrogate key.';
COMMENT ON COLUMN dw.dim_ageb.cvegeo IS '13-character INEGI key: state (2) + alcaldia (3) + locality (4) + AGEB (4). Natural key.';
COMMENT ON COLUMN dw.dim_ageb.cve_ent IS 'State code (''09'').';
COMMENT ON COLUMN dw.dim_ageb.cve_mun IS 'Alcaldia code (3 digits).';
COMMENT ON COLUMN dw.dim_ageb.cve_loc IS 'Locality code (4 digits).';
COMMENT ON COLUMN dw.dim_ageb.cve_ageb IS 'AGEB code (4 characters).';
COMMENT ON COLUMN dw.dim_ageb.nom_mun IS 'Alcaldia name, taken from the Census file.';
COMMENT ON COLUMN dw.dim_ageb.area_km2 IS 'Polygon area in square kilometres, computed in EPSG:32614.';
COMMENT ON COLUMN dw.dim_ageb.geom IS 'AGEB polygon in EPSG:4326 (storage and display).';
COMMENT ON COLUMN dw.dim_ageb.geom_utm IS 'AGEB polygon in EPSG:32614 (UTM 14N), used for metric calculations.';

COMMENT ON TABLE dw.dim_date IS 'Calendar dimension, one row per date that appears in the crime facts.';
COMMENT ON COLUMN dw.dim_date.date_key IS 'Surrogate key in yyyymmdd format.';
COMMENT ON COLUMN dw.dim_date.full_date IS 'Calendar date.';
COMMENT ON COLUMN dw.dim_date.year IS 'Year.';
COMMENT ON COLUMN dw.dim_date.quarter IS 'Quarter of the year (1-4).';
COMMENT ON COLUMN dw.dim_date.month IS 'Month number (1-12).';
COMMENT ON COLUMN dw.dim_date.month_name IS 'Month name in English.';
COMMENT ON COLUMN dw.dim_date.day IS 'Day of the month.';
COMMENT ON COLUMN dw.dim_date.day_of_week IS 'ISO weekday, 1 = Monday to 7 = Sunday.';
COMMENT ON COLUMN dw.dim_date.day_name IS 'Weekday name in English.';
COMMENT ON COLUMN dw.dim_date.is_weekend IS 'True for Saturday and Sunday.';

COMMENT ON TABLE dw.dim_time IS 'Hour-of-day dimension with the time bands used in the analysis.';
COMMENT ON COLUMN dw.dim_time.hour_key IS 'Hour of the day, 0-23.';
COMMENT ON COLUMN dw.dim_time.time_band IS 'night (0-5), morning (6-11), afternoon (12-17) or evening (18-23).';

COMMENT ON TABLE dw.dim_crime_type IS 'Crime classification: analytical group, specific offense and original FGJ category.';
COMMENT ON COLUMN dw.dim_crime_type.crime_type_key IS 'Surrogate key.';
COMMENT ON COLUMN dw.dim_crime_type.crime_category IS 'Analytical group built by the ETL from the offense name (10 groups, see src/crime_taxonomy.py).';
COMMENT ON COLUMN dw.dim_crime_type.crime_type IS 'Specific offense name (delito) as published by FGJ.';
COMMENT ON COLUMN dw.dim_crime_type.fgj_category IS 'Original FGJ category, kept for traceability.';

COMMENT ON TABLE dw.dim_scian IS 'SCIAN economic activity classification used by DENUE.';
COMMENT ON COLUMN dw.dim_scian.scian_key IS 'Surrogate key.';
COMMENT ON COLUMN dw.dim_scian.codigo_act IS '6-digit SCIAN class code.';
COMMENT ON COLUMN dw.dim_scian.sector_code IS 'SCIAN sector code; multi-sector groups follow INEGI ranges such as ''31-33'' and ''48-49''.';
COMMENT ON COLUMN dw.dim_scian.sector_name IS 'Sector name.';
COMMENT ON COLUMN dw.dim_scian.subsector_code IS '3-digit SCIAN subsector code.';
COMMENT ON COLUMN dw.dim_scian.activity_name IS 'Name of the 6-digit activity.';
COMMENT ON COLUMN dw.dim_scian.macro_group IS 'Analytical grouping: retail (sector 46), services (51-56, 61, 62, 71, 72, 81) or other.';

COMMENT ON TABLE dw.dim_business_size IS 'Business size, from the DENUE employment stratum.';
COMMENT ON COLUMN dw.dim_business_size.size_key IS 'Surrogate key.';
COMMENT ON COLUMN dw.dim_business_size.per_ocu IS 'Stratum label as published by DENUE.';
COMMENT ON COLUMN dw.dim_business_size.min_emp IS 'Lower bound of employees in the stratum.';
COMMENT ON COLUMN dw.dim_business_size.max_emp IS 'Upper bound of employees (NULL when open-ended).';

COMMENT ON TABLE dw.dim_age_group IS 'Age groups published by the Census, plus the derived 25-59 group.';
COMMENT ON COLUMN dw.dim_age_group.age_group_key IS 'Key, 1 (youngest) to 8 (oldest).';
COMMENT ON COLUMN dw.dim_age_group.label IS 'Group label, for example ''18-24''.';
COMMENT ON COLUMN dw.dim_age_group.min_age IS 'Lowest age in the group.';
COMMENT ON COLUMN dw.dim_age_group.max_age IS 'Highest age in the group (NULL = open-ended).';

COMMENT ON TABLE dw.fact_population_ageb IS 'Census 2020 population and economic indicators. Grain: one row per AGEB.';
COMMENT ON COLUMN dw.fact_population_ageb.ageb_key IS 'AGEB (FK to dim_ageb).';
COMMENT ON COLUMN dw.fact_population_ageb.pobtot IS 'Total population.';
COMMENT ON COLUMN dw.fact_population_ageb.pobfem IS 'Female population.';
COMMENT ON COLUMN dw.fact_population_ageb.pobmas IS 'Male population.';
COMMENT ON COLUMN dw.fact_population_ageb.p_12ymas IS 'Population aged 12 and over, the base of the economic activity rate.';
COMMENT ON COLUMN dw.fact_population_ageb.pea IS 'Economically active population (EAP).';
COMMENT ON COLUMN dw.fact_population_ageb.pe_inac IS 'Economically inactive population.';
COMMENT ON COLUMN dw.fact_population_ageb.pocupada IS 'Employed population.';
COMMENT ON COLUMN dw.fact_population_ageb.pdesocup IS 'Unemployed population.';
COMMENT ON COLUMN dw.fact_population_ageb.vivtot IS 'Total dwellings.';
COMMENT ON COLUMN dw.fact_population_ageb.tvivhab IS 'Occupied dwellings.';
COMMENT ON COLUMN dw.fact_population_ageb.prom_ocup IS 'Average occupants per occupied dwelling.';
COMMENT ON COLUMN dw.fact_population_ageb.graproes IS 'Average years of schooling.';
COMMENT ON COLUMN dw.fact_population_ageb.census_year IS 'Census year (2020).';

COMMENT ON TABLE dw.fact_population_age IS 'Population by age group. Grain: one row per AGEB and age group.';
COMMENT ON COLUMN dw.fact_population_age.ageb_key IS 'AGEB (FK to dim_ageb).';
COMMENT ON COLUMN dw.fact_population_age.age_group_key IS 'Age group (FK to dim_age_group).';
COMMENT ON COLUMN dw.fact_population_age.population IS 'Residents in the group; NULL when the Census suppresses the value.';

COMMENT ON TABLE dw.fact_establishment IS 'DENUE establishments (edition 11/2024). Grain: one row per establishment.';
COMMENT ON COLUMN dw.fact_establishment.establishment_key IS 'Surrogate key.';
COMMENT ON COLUMN dw.fact_establishment.denue_id IS 'Establishment id in DENUE (natural key).';
COMMENT ON COLUMN dw.fact_establishment.ageb_key IS 'AGEB that contains the point (FK to dim_ageb); NULL if none.';
COMMENT ON COLUMN dw.fact_establishment.scian_key IS 'Economic activity (FK to dim_scian).';
COMMENT ON COLUMN dw.fact_establishment.size_key IS 'Size stratum (FK to dim_business_size).';
COMMENT ON COLUMN dw.fact_establishment.nom_estab IS 'Establishment name.';
COMMENT ON COLUMN dw.fact_establishment.ageb_source IS 'How the AGEB was assigned: ''spatial'' (point in polygon) or ''denue_code'' (fallback on the DENUE AGEB code).';
COMMENT ON COLUMN dw.fact_establishment.coord_quality IS '''ok'' for usable coordinates, ''invalid'' for placeholders or points outside CDMX.';
COMMENT ON COLUMN dw.fact_establishment.geom IS 'Establishment point in EPSG:4326; NULL when coordinates are invalid.';

COMMENT ON TABLE dw.fact_crime_incident IS 'FGJ crime reports for 2024 by incident date. Grain: one row per reported incident.';
COMMENT ON COLUMN dw.fact_crime_incident.incident_key IS 'Surrogate key.';
COMMENT ON COLUMN dw.fact_crime_incident.source_id IS 'Row number in the raw FGJ file, for traceability.';
COMMENT ON COLUMN dw.fact_crime_incident.ageb_key IS 'AGEB that contains the point (FK to dim_ageb); NULL if none.';
COMMENT ON COLUMN dw.fact_crime_incident.crime_type_key IS 'Crime classification (FK to dim_crime_type).';
COMMENT ON COLUMN dw.fact_crime_incident.date_key IS 'Incident date (FK to dim_date).';
COMMENT ON COLUMN dw.fact_crime_incident.hour_key IS 'Incident hour (FK to dim_time); NULL when unknown.';
COMMENT ON COLUMN dw.fact_crime_incident.geom IS 'Incident point in EPSG:4326.';

COMMENT ON TABLE dw.etl_source_log IS 'One row per source loaded: file, edition and row counts, for traceability.';
COMMENT ON COLUMN dw.etl_source_log.log_id IS 'Surrogate key.';
COMMENT ON COLUMN dw.etl_source_log.source_name IS 'Source name (census, denue, crime, geography).';
COMMENT ON COLUMN dw.etl_source_log.source_file IS 'File the data came from.';
COMMENT ON COLUMN dw.etl_source_log.edition IS 'Edition or year of the source.';
COMMENT ON COLUMN dw.etl_source_log.rows_staged IS 'Rows in the staging table.';
COMMENT ON COLUMN dw.etl_source_log.rows_loaded IS 'Rows loaded into the warehouse.';
COMMENT ON COLUMN dw.etl_source_log.note IS 'Free-text note.';
COMMENT ON COLUMN dw.etl_source_log.loaded_at IS 'Load timestamp.';

COMMENT ON VIEW dw.vw_ageb_business IS 'Establishment counts per AGEB, total and by macro group.';
COMMENT ON COLUMN dw.vw_ageb_business.ageb_key IS 'AGEB key.';
COMMENT ON COLUMN dw.vw_ageb_business.total_businesses IS 'All establishments.';
COMMENT ON COLUMN dw.vw_ageb_business.retail_businesses IS 'Retail establishments (SCIAN sector 46).';
COMMENT ON COLUMN dw.vw_ageb_business.service_businesses IS 'Service establishments (SCIAN 51-56, 61, 62, 71, 72, 81).';

COMMENT ON VIEW dw.vw_ageb_dominant_sector IS 'Dominant SCIAN sector per AGEB (ties broken by lowest sector code).';
COMMENT ON COLUMN dw.vw_ageb_dominant_sector.ageb_key IS 'AGEB key.';
COMMENT ON COLUMN dw.vw_ageb_dominant_sector.sector_code IS 'Code of the sector with most establishments.';
COMMENT ON COLUMN dw.vw_ageb_dominant_sector.sector_name IS 'Name of that sector.';
COMMENT ON COLUMN dw.vw_ageb_dominant_sector.n_establishments IS 'Establishments in that sector.';

COMMENT ON VIEW dw.vw_ageb_crime IS 'Total crime incidents per AGEB.';
COMMENT ON COLUMN dw.vw_ageb_crime.ageb_key IS 'AGEB key.';
COMMENT ON COLUMN dw.vw_ageb_crime.total_crimes IS 'Incidents located in the AGEB.';

COMMENT ON VIEW dw.vw_crime_type_time IS 'Incidents by AGEB, crime type and time (year, month, weekday, time band).';
COMMENT ON COLUMN dw.vw_crime_type_time.ageb_key IS 'AGEB key.';
COMMENT ON COLUMN dw.vw_crime_type_time.crime_category IS 'Analytical crime group.';
COMMENT ON COLUMN dw.vw_crime_type_time.crime_type IS 'Specific offense.';
COMMENT ON COLUMN dw.vw_crime_type_time.year IS 'Year of the incident.';
COMMENT ON COLUMN dw.vw_crime_type_time.month IS 'Month of the incident.';
COMMENT ON COLUMN dw.vw_crime_type_time.day_name IS 'Weekday name.';
COMMENT ON COLUMN dw.vw_crime_type_time.is_weekend IS 'True for Saturday and Sunday.';
COMMENT ON COLUMN dw.vw_crime_type_time.time_band IS 'night, morning, afternoon or evening.';
COMMENT ON COLUMN dw.vw_crime_type_time.incidents IS 'Number of incidents.';

COMMENT ON VIEW dw.vw_ageb_age_groups IS 'Population by age group pivoted to one row per AGEB.';
COMMENT ON COLUMN dw.vw_ageb_age_groups.ageb_key IS 'AGEB key.';
COMMENT ON COLUMN dw.vw_ageb_age_groups.pop_0_2 IS 'Residents aged 0-2.';
COMMENT ON COLUMN dw.vw_ageb_age_groups.pop_3_5 IS 'Residents aged 3-5.';
COMMENT ON COLUMN dw.vw_ageb_age_groups.pop_6_11 IS 'Residents aged 6-11.';
COMMENT ON COLUMN dw.vw_ageb_age_groups.pop_12_14 IS 'Residents aged 12-14.';
COMMENT ON COLUMN dw.vw_ageb_age_groups.pop_15_17 IS 'Residents aged 15-17.';
COMMENT ON COLUMN dw.vw_ageb_age_groups.pop_18_24 IS 'Residents aged 18-24.';
COMMENT ON COLUMN dw.vw_ageb_age_groups.pop_25_59 IS 'Residents aged 25-59.';
COMMENT ON COLUMN dw.vw_ageb_age_groups.pop_60_plus IS 'Residents aged 60 and over.';

COMMENT ON VIEW dw.vw_ageb_kpis IS 'Master KPI view, one row per AGEB with every required indicator.';
COMMENT ON COLUMN dw.vw_ageb_kpis.ageb_key IS 'AGEB key.';
COMMENT ON COLUMN dw.vw_ageb_kpis.cvegeo IS '13-character AGEB key.';
COMMENT ON COLUMN dw.vw_ageb_kpis.area_km2 IS 'Area in km2.';
COMMENT ON COLUMN dw.vw_ageb_kpis.total_population IS 'KPI 1. Total population (Census 2020).';
COMMENT ON COLUMN dw.vw_ageb_kpis.population_density_km2 IS 'KPI 2. Residents per km2 = total_population / area_km2.';
COMMENT ON COLUMN dw.vw_ageb_kpis.eap_rate_pct IS 'KPI 3. Economic activity rate = 100 * PEA / population aged 12+.';
COMMENT ON COLUMN dw.vw_ageb_kpis.pop_0_2 IS 'KPI 4. Population aged 0-2.';
COMMENT ON COLUMN dw.vw_ageb_kpis.pop_3_5 IS 'KPI 4. Population aged 3-5.';
COMMENT ON COLUMN dw.vw_ageb_kpis.pop_6_11 IS 'KPI 4. Population aged 6-11.';
COMMENT ON COLUMN dw.vw_ageb_kpis.pop_12_14 IS 'KPI 4. Population aged 12-14.';
COMMENT ON COLUMN dw.vw_ageb_kpis.pop_15_17 IS 'KPI 4. Population aged 15-17.';
COMMENT ON COLUMN dw.vw_ageb_kpis.pop_18_24 IS 'KPI 4. Population aged 18-24.';
COMMENT ON COLUMN dw.vw_ageb_kpis.pop_25_59 IS 'KPI 4. Population aged 25-59.';
COMMENT ON COLUMN dw.vw_ageb_kpis.pop_60_plus IS 'KPI 4. Population aged 60 and over.';
COMMENT ON COLUMN dw.vw_ageb_kpis.share_60_plus_pct IS 'Share of residents aged 60+, in percent.';
COMMENT ON COLUMN dw.vw_ageb_kpis.share_under_18_pct IS 'Share of residents under 18, in percent.';
COMMENT ON COLUMN dw.vw_ageb_kpis.total_businesses IS 'KPI 5. Establishments in the AGEB (DENUE 11/2024).';
COMMENT ON COLUMN dw.vw_ageb_kpis.business_density_km2 IS 'KPI 6. Establishments per km2.';
COMMENT ON COLUMN dw.vw_ageb_kpis.businesses_per_1000 IS 'KPI 7. Establishments per 1,000 residents.';
COMMENT ON COLUMN dw.vw_ageb_kpis.retail_density_km2 IS 'KPI 8. Retail establishments per km2.';
COMMENT ON COLUMN dw.vw_ageb_kpis.service_density_km2 IS 'KPI 9. Service establishments per km2.';
COMMENT ON COLUMN dw.vw_ageb_kpis.dominant_sector_code IS 'KPI 10. Code of the dominant SCIAN sector.';
COMMENT ON COLUMN dw.vw_ageb_kpis.dominant_sector_name IS 'KPI 10. Name of the dominant SCIAN sector.';
COMMENT ON COLUMN dw.vw_ageb_kpis.total_crimes IS 'KPI 11. Crime incidents in 2024.';
COMMENT ON COLUMN dw.vw_ageb_kpis.crime_rate_per_1000 IS 'KPI 12. Incidents per 1,000 residents.';
COMMENT ON COLUMN dw.vw_ageb_kpis.crimes_per_100_businesses IS 'KPI 14. Incidents per 100 establishments (NULL when the AGEB has no business).';
COMMENT ON COLUMN dw.vw_ageb_kpis.geom IS 'AGEB polygon in EPSG:4326.';
