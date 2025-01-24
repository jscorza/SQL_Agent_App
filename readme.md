psql -h localhost -p 5432 -U myuser -d mydatabase

docker exec -it my_postgres_db bash
Luego, dentro del contene
psql -U myuser -d mydatabase