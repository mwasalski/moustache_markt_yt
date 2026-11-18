CREATE TABLE moustache_markt_dev.bronze_erp.category (
  category_id INT,
  parent_category_id INT,
  category_code STRING COLLATE UTF8_BINARY,
  category_name STRING COLLATE UTF8_BINARY,
  category_level TINYINT,
  is_active BOOLEAN,
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

