CREATE TABLE moustache_markt_dev.bronze_ecom.orders (
  channel STRING COLLATE UTF8_BINARY,
  created_at STRING COLLATE UTF8_BINARY,
  currency_code STRING COLLATE UTF8_BINARY,
  customer_id STRING COLLATE UTF8_BINARY,
  delivery STRUCT<city: STRING COLLATE UTF8_BINARY, method: STRING COLLATE UTF8_BINARY, pickup_location_id: BIGINT, postal_code: STRING COLLATE UTF8_BINARY, shipping_fee: DOUBLE>,
  guest_email STRING COLLATE UTF8_BINARY,
  is_b2b BOOLEAN,
  items ARRAY<STRUCT<discount: DOUBLE, extended_warranty: BOOLEAN, line_no: BIGINT, quantity: BIGINT, sku: STRING COLLATE UTF8_BINARY, unit_price: DOUBLE>>,
  order_id STRING COLLATE UTF8_BINARY,
  order_status STRING COLLATE UTF8_BINARY,
  order_total DOUBLE,
  payment STRUCT<method: STRING COLLATE UTF8_BINARY, paid_at: STRING COLLATE UTF8_BINARY, status: STRING COLLATE UTF8_BINARY>,
  tax_amount DOUBLE,
  updated_at STRING COLLATE UTF8_BINARY,
  voucher_code STRING COLLATE UTF8_BINARY,
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

