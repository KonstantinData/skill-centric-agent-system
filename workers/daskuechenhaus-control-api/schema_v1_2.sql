PRAGMA foreign_keys = ON;

ALTER TABLE customers ADD COLUMN company_name_3 TEXT;
ALTER TABLE customers ADD COLUMN company_name_4 TEXT;
ALTER TABLE customers ADD COLUMN tax_number TEXT;
ALTER TABLE customers ADD COLUMN iso_country_code TEXT;
ALTER TABLE customers ADD COLUMN is_nato INTEGER NOT NULL DEFAULT 0
  CHECK (is_nato IN (0, 1));
ALTER TABLE customers ADD COLUMN has_custom_vat INTEGER NOT NULL DEFAULT 0
  CHECK (has_custom_vat IN (0, 1));
ALTER TABLE customers ADD COLUMN custom_vat_rate TEXT;
ALTER TABLE customers ADD COLUMN custom_vat_rate_label TEXT;
ALTER TABLE customers ADD COLUMN reverse_charge INTEGER NOT NULL DEFAULT 0
  CHECK (reverse_charge IN (0, 1));
ALTER TABLE customers ADD COLUMN marketing_allowed INTEGER NOT NULL DEFAULT 0
  CHECK (marketing_allowed IN (0, 1));
ALTER TABLE customers ADD COLUMN e_invoice INTEGER NOT NULL DEFAULT 0
  CHECK (e_invoice IN (0, 1));

UPDATE customers
SET iso_country_code = country
WHERE iso_country_code IS NULL
  AND country IS NOT NULL;

ALTER TABLE customer_participants ADD COLUMN company_name_3 TEXT;
ALTER TABLE customer_participants ADD COLUMN company_name_4 TEXT;
ALTER TABLE customer_participants ADD COLUMN tax_number TEXT;
ALTER TABLE customer_participants ADD COLUMN iso_country_code TEXT;
ALTER TABLE customer_participants ADD COLUMN is_nato INTEGER NOT NULL DEFAULT 0
  CHECK (is_nato IN (0, 1));
ALTER TABLE customer_participants ADD COLUMN has_custom_vat INTEGER NOT NULL DEFAULT 0
  CHECK (has_custom_vat IN (0, 1));
ALTER TABLE customer_participants ADD COLUMN custom_vat_rate TEXT;
ALTER TABLE customer_participants ADD COLUMN custom_vat_rate_label TEXT;
ALTER TABLE customer_participants ADD COLUMN reverse_charge INTEGER NOT NULL DEFAULT 0
  CHECK (reverse_charge IN (0, 1));
ALTER TABLE customer_participants ADD COLUMN marketing_allowed INTEGER NOT NULL DEFAULT 0
  CHECK (marketing_allowed IN (0, 1));
ALTER TABLE customer_participants ADD COLUMN e_invoice INTEGER NOT NULL DEFAULT 0
  CHECK (e_invoice IN (0, 1));

UPDATE customer_participants
SET iso_country_code = country
WHERE iso_country_code IS NULL
  AND country IS NOT NULL;
