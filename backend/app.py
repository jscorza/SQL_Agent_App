from flask import Flask, request, jsonify
import psycopg2
import os

app = Flask(__name__)

# Database connection configuration
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'mydatabase')
DB_USER = os.getenv('DB_USER', 'myuser')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'mypassword')

def get_db_connection():
    """Create PostgreSQL database connection using environment variables."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

@app.route('/healthcheck', methods=['GET'])
def healthcheck():
    """Basic service health monitoring endpoint."""
    return jsonify({"status": "ok"}), 200

@app.route('/query', methods=['POST'])
def run_query():
    """
    Execute SQL query against PostgreSQL database.
    Accepts JSON payload: {"sql": "SELECT ..."}
    Returns JSON response with results or error message.
    """
    data = request.get_json()
    sql_query = data.get("sql", "").strip()
    
    if not sql_query:
        return jsonify({"error": "No SQL query provided"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(sql_query)
        
        # Handle SELECT vs non-SELECT queries
        if cursor.description:  # SELECT queries return description
            columns = [desc[0] for desc in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return jsonify({"results": results}), 200
        else:  # INSERT/UPDATE/DELETE queries
            conn.commit()
            return jsonify({"message": "Query executed successfully"}), 200
    except Exception as e:
        conn.rollback()  # Ensure transaction safety
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    # Start application with production settings
    app.run(host='0.0.0.0', port=5000)