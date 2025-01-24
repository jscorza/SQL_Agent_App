-- 1) Creamos la tabla (asegúrate de que coincida con las columnas del CSV)
CREATE TABLE IF NOT EXISTS sales (
  date DATE,
  week_day VARCHAR(20),
  hour VARCHAR(10),  -- Podrías usar TIME, pero a veces es más cómodo un VARCHAR
  ticket_number VARCHAR(50),
  waiter INT,
  product_name VARCHAR(100),
  quantity NUMERIC,
  unitary_price DECIMAL(10,2),
  total DECIMAL(10,2)
);

-- 2) Cargamos el CSV
COPY sales(date, week_day, hour, ticket_number, waiter, product_name, quantity, unitary_price, total)
FROM '/docker-entrypoint-initdb.d/data.csv'  -- Ruta en el contenedor
DELIMITER ','
CSV HEADER;
