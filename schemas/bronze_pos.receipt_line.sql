CREATE TABLE moustache_markt_dev.bronze_pos.receipt_line (
  store_code STRING COLLATE UTF8_BINARY,
  register_no STRING COLLATE UTF8_BINARY,
  receipt_no STRING COLLATE UTF8_BINARY,
  receipt_local_ts STRING COLLATE UTF8_BINARY,
  cashier_id STRING COLLATE UTF8_BINARY,
  line_no STRING COLLATE UTF8_BINARY,
  ean STRING COLLATE UTF8_BINARY,
  item_name STRING COLLATE UTF8_BINARY,
  quantity STRING COLLATE UTF8_BINARY,
  item_price STRING COLLATE UTF8_BINARY,
  item_discount STRING COLLATE UTF8_BINARY,
  tax_code STRING COLLATE UTF8_BINARY,
  transaction_type STRING COLLATE UTF8_BINARY,
  payment_type STRING COLLATE UTF8_BINARY,
  loyalty_card_no STRING COLLATE UTF8_BINARY,
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

