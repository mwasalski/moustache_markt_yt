CREATE TABLE moustache_markt_dev.bronze_crm.customer_cdc (
  _commit_ts STRING COLLATE UTF8_BINARY,
  _op STRING COLLATE UTF8_BINARY,
  birth_date STRING COLLATE UTF8_BINARY,
  city STRING COLLATE UTF8_BINARY,
  company_name STRING COLLATE UTF8_BINARY,
  customer_id STRING COLLATE UTF8_BINARY,
  customer_type STRING COLLATE UTF8_BINARY,
  email STRING COLLATE UTF8_BINARY,
  first_name STRING COLLATE UTF8_BINARY,
  is_anonymized BOOLEAN,
  last_name STRING COLLATE UTF8_BINARY,
  loyalty_card_no STRING COLLATE UTF8_BINARY,
  loyalty_tier STRING COLLATE UTF8_BINARY,
  marketing_consent BOOLEAN,
  phone STRING COLLATE UTF8_BINARY,
  postal_code STRING COLLATE UTF8_BINARY,
  registered_at STRING COLLATE UTF8_BINARY,
  registration_channel STRING COLLATE UTF8_BINARY,
  tax_id STRING COLLATE UTF8_BINARY,
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

