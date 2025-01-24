from flask import Flask, request, jsonify
import psycopg2
import os

app = Flask(__name__)

# Leemos las variables de entorno para la conexión
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'mydatabase')
DB_USER = os.getenv('DB_USER', 'myuser')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'mypassword')

def get_db_connection():
    """Crea y retorna una conexión a la base de datos PostgreSQL."""
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    return conn

@app.route('/healthcheck', methods=['GET'])
def healthcheck():
    """Verifica si el servicio está vivo."""
    return jsonify({"status": "ok"}), 200

@app.route('/query', methods=['POST'])
def run_query():
    """
    Recibe un JSON tipo: {"sql": "SELECT * FROM sales LIMIT 10"} 
    Ejecuta la query en PostgreSQL y retorna los resultados en JSON.
    """
    data = request.get_json()
    sql_query = data.get("sql", "")  # Obtenemos la sentencia SQL desde el JSON
    
    if not sql_query:
        return jsonify({"error": "No SQL query provided"}), 400

    # Conectarnos a la DB, ejecutar la query
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(sql_query)
        # Si es un SELECT, intentamos obtener los rows
        if cursor.description:
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            # Convertimos los resultados a lista de dicts (col: valor)
            results = []
            for row in rows:
                row_dict = dict(zip(columns, row))
                results.append(row_dict)
            
            return jsonify({"results": results}), 200
        else:
            # Para sentencias como INSERT, UPDATE, etc.
            conn.commit()
            return jsonify({"message": "Query executed successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    # Iniciamos Flask en el puerto 5000
    app.run(host='0.0.0.0', port=5000, debug=True)
