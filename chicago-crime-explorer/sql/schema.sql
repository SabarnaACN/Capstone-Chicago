PRAGMA page_size = 1024;
PRAGMA foreign_keys = ON;

CREATE TABLE city_community (
    community_code INTEGER PRIMARY KEY,
    community_name TEXT NOT NULL,
    population INTEGER,
    area_sqmile REAL,
    area_sqkm REAL,
    density_per_sqmi REAL,
    density_per_sqkm REAL
);

CREATE TABLE district_ps_info (
    district_code INTEGER PRIMARY KEY,
    district_name TEXT,
    address TEXT,
    city TEXT,
    state TEXT,
    zip TEXT,
    website TEXT,
    phone TEXT,
    fax TEXT,
    tty TEXT,
    x_coordinate REAL,
    y_coordinate REAL,
    latitude REAL,
    longitude REAL,
    location TEXT
);

CREATE TABLE iucr (
    iucr_code TEXT PRIMARY KEY,
    primary_type TEXT NOT NULL,
    description TEXT,
    index_code TEXT
);

CREATE TABLE police_beat_info (
    beat_num INTEGER PRIMARY KEY,
    district INTEGER,
    sector INTEGER,
    beat INTEGER
);

-- Ward geography is separate from multiple office records to avoid fan-out joins.
CREATE TABLE ward_office (
    ward_no INTEGER PRIMARY KEY
);

CREATE TABLE ward_office_record (
    source_row INTEGER PRIMARY KEY,
    ward_no INTEGER REFERENCES ward_office(ward_no),
    alderman TEXT,
    address TEXT,
    city TEXT,
    state TEXT,
    zipcode TEXT,
    ward_phone TEXT,
    ward_fax TEXT,
    email TEXT,
    website TEXT,
    location_zip TEXT,
    location_city TEXT,
    location TEXT,
    location_address TEXT,
    location_state TEXT,
    city_hall_address TEXT,
    city_hall_city TEXT,
    city_hall_state TEXT,
    city_hall_zipcode TEXT,
    city_hall_phone TEXT
);

CREATE TABLE chicago_crime (
    id INTEGER PRIMARY KEY,
    case_number TEXT NOT NULL UNIQUE,
    date TEXT NOT NULL,
    block TEXT,
    iucr_code TEXT REFERENCES iucr(iucr_code),
    location_desc TEXT,
    arrest INTEGER CHECK(arrest IN (0,1) OR arrest IS NULL),
    domestic INTEGER CHECK(domestic IN (0,1) OR domestic IS NULL),
    beat_num INTEGER REFERENCES police_beat_info(beat_num),
    district_code INTEGER REFERENCES district_ps_info(district_code),
    ward_no INTEGER REFERENCES ward_office(ward_no),
    community_code INTEGER REFERENCES city_community(community_code),
    fbi_code TEXT,
    x_coordinate REAL,
    y_coordinate REAL,
    year INTEGER,
    date_of_update TEXT,
    latitude REAL,
    longitude REAL,
    location TEXT,
    month INTEGER,
    day_of_week INTEGER,
    hour INTEGER,
    has_time INTEGER NOT NULL,
    source_row INTEGER
);

CREATE INDEX ix_crime_year ON chicago_crime(year);

CREATE INDEX ix_crime_community ON chicago_crime(community_code);

CREATE INDEX ix_crime_iucr ON chicago_crime(iucr_code);

CREATE TABLE pipeline_run (
    run_id TEXT PRIMARY KEY,
    completed_at TEXT NOT NULL,
    report_json TEXT NOT NULL
);

CREATE TABLE quarantine (
    source_file TEXT,
    source_row INTEGER,
    reason TEXT,
    raw_record TEXT
);

CREATE TABLE summary_yearly (
    year INTEGER PRIMARY KEY,
    crime_count INTEGER NOT NULL,
    arrest_count INTEGER NOT NULL,
    arrest_known_count INTEGER NOT NULL,
    arrest_percentage REAL
);

CREATE TABLE summary_category (
    primary_type TEXT PRIMARY KEY,
    crime_count INTEGER NOT NULL,
    percentage REAL
);
