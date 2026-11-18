CREATE TABLE moustache_markt_dev.bronze_erp.product (
  product_id BIGINT,
  sku STRING COLLATE UTF8_BINARY,
  ean STRING COLLATE UTF8_BINARY,
  product_name STRING COLLATE UTF8_BINARY,
  brand_name STRING COLLATE UTF8_BINARY,
  category_id INT,
  primary_supplier_id INT,
  tax_rate DECIMAL(6,4),
  standard_cost DECIMAL(18,2),
  weight_lb DECIMAL(8,3),
  warranty_months SMALLINT,
  launch_date DATE,
  eol_date DATE,
  status STRING COLLATE UTF8_BINARY,
  created_at TIMESTAMP,
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

