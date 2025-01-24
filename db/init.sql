-- Create table matching CSV structure
CREATE TABLE IF NOT EXISTS sales (
  date DATE,
  week_day VARCHAR(20),
  hour VARCHAR(10),        -- Store as string for flexible time formats
  ticket_number VARCHAR(50),
  waiter INT,
  product_name VARCHAR(100),
  quantity NUMERIC,        -- Allows integer/decimal values
  unitary_price DECIMAL(10,2),
  total DECIMAL(10,2)
);

-- Load data from CSV (mounted in container)
COPY sales(
  date,
  week_day,
  hour,
  ticket_number,
  waiter,
  product_name,
  quantity,
  unitary_price,
  total
)
FROM '/docker-entrypoint-initdb.d/data.csv'  -- Container path
DELIMITER ','
CSV HEADER;  -- First row contains column names