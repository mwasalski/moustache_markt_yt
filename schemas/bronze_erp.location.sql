CREATE TABLE moustache_markt_dev.bronze_erp.location (
  location_id INT,
  location_code STRING COLLATE UTF8_BINARY,
  location_name STRING COLLATE UTF8_BINARY,
  location_type STRING COLLATE UTF8_BINARY,
  store_format STRING COLLATE UTF8_BINARY,
  city STRING COLLATE UTF8_BINARY,
  state STRING COLLATE UTF8_BINARY,
  postal_code STRING COLLATE UTF8_BINARY,
  latitude DECIMAL(9,6),
  longitude DECIMAL(9,6),
  floor_area_sqft INT,
  opened_date DATE,
  closed_date DATE,
  updated_at TIMESTAMP,
  load_date DATE,
  _source_file STRING COLLATE UTF8_BINARY,
  _ingested_at TIMESTAMP)
USING delta
DEFAULT COLLATION UTF8_BINARY
TBLPROPERTIES (
  'delta.enableDeletionVectors' = 'true',
  'delta.feature.appendOnly' = 'supported',
  'delta.feature.deletionVectors' = 'supported',
  'delta.feature.invariants' = 'supported',
  'delta.minReaderVersion' = '3',
  'delta.minWriterVersion' = '7',
  'delta.parquet.compression.codec' = 'zstd',
  'delta.parquet.format.version' = '2.12.0',
  'delta.parquet.format.version.afe.internal' = '2.12.0')

