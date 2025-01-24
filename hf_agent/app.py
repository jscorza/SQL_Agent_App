from flask import Flask, request, jsonify
import requests
import re
import os
from tenacity import retry, wait_exponential, stop_after_attempt

app = Flask(__name__)

# 1) Modelo y configuración HF
MODEL_ID = "google/gemma-2-9b-it"  # Ajusta con el que uses
API_URL = f"https://api-inference.huggingface.co/models/{MODEL_ID}"
HF_API_TOKEN = os.getenv("HF_API_TOKEN", "")
HEADERS = {"Authorization": f"Bearer {HF_API_TOKEN}"}

# 2) Prompt base para Text-to-SQL
TEXT_TO_SQL_PROMPT = """
You are a SQL expert tasked with generating ONLY valid PostgreSQL queries. 

**Database Schema:**
- Table: sales
- Columns:
  1) date (DATE) 
  2) week_day (VARCHAR) 
  3) hour (VARCHAR)
  4) ticket_number (VARCHAR)
  5) waiter (INT)
  6) product_name (VARCHAR)
  7) quantity (INT)
  8) unitary_price (DECIMAL(10,2))
  9) total (DECIMAL(10,2))

**Constraints & Rules:**
1) Output must be strictly valid PostgreSQL (no MySQL or other dialect).
2) Use correct column names (e.g., 'product_name', 'quantity', 'week_day', etc.).
3) Include a semicolon at the end of the query.
4) Never include comments, markdown, or extraneous text—just the SQL.
5) Format the SQL nicely if possible, but correctness is paramount.

**Examples:**

Example A (simple):
- Question: "Which 5 products are the most sold overall?"
- SQL:
  SELECT product_name, SUM(quantity) AS total_sold
  FROM sales
  GROUP BY product_name
  ORDER BY total_sold DESC
  LIMIT 5;

Example B (with a condition):
- Question: "What is the total money spent on Fridays?"
- SQL:
  SELECT SUM(total) AS total_spent
  FROM sales
  WHERE week_day = 'Friday';

Example C (joining multiple conditions):
- Question: "Which hour of Friday has the highest sum of total?"
- SQL:
  SELECT hour, SUM(total) AS total_per_hour
  FROM sales
  WHERE week_day = 'Friday'
  GROUP BY hour
  ORDER BY total_per_hour DESC
  LIMIT 1;

Example D (single best or worst):
- Question: "What is the least sold product?"
- SQL:
  SELECT product_name, SUM(quantity) AS total_quantity
  FROM sales
  GROUP BY product_name
  ORDER BY total_quantity ASC
  LIMIT 1;

**Now your turn**:

Question: "{question}"

SQL:
"""


# 3) Función para llamar a la Inference API con reintentos
@retry(wait=wait_exponential(multiplier=1, max=120), stop=stop_after_attempt(3))
def query_huggingface(prompt, max_tokens=200):
    """
    Llama a la Inference API con reintentos (tenacity).
    Imprime logs para debug.
    """
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": max_tokens,
            "temperature": 0.1
        }
        # No "options" para evitar 'Cannot override task' en algunos modelos
    }

    print("[HF_AGENT] Sending to HF:", payload, flush=True)
    response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=180)
    print("[HF_AGENT] HTTP Status:", response.status_code, flush=True)
    print("[HF_AGENT] HF raw text:", response.text[:500], flush=True)

    # Manejo de error HTTP
    response.raise_for_status()

    result = response.json()
    print("[HF_AGENT] JSON parsed:", result, flush=True)
    return result

def extract_generated_text(hf_response):
    """
    Extrae 'generated_text' o 'translation_text' de la respuesta HF.
    """
    if isinstance(hf_response, list) and len(hf_response) > 0:
        item = hf_response[0]
        txt = item.get("generated_text") or item.get("translation_text")
        if txt:
            return txt.strip()
    raise ValueError(f"No 'generated_text' or 'translation_text' found in HF response: {hf_response}")

def clean_sql_response(text):
    """
    Intenta extraer la sentencia SQL (SELECT ...;).
    Busca patrones en 'text' y devuelve la parte que encaje.
    """
    patterns = [
        r'```sql\s*(.*?)\s*```',
        r'```(.*?)```',
        r'(SELECT|WITH).+?;'
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            if pattern == patterns[2]:
                # group(0) contiene 'SELECT ...;'
                found = match.group(0)
            else:
                found = match.group(1)
            found = re.sub(r'\s+', ' ', found).strip()
            if not found.endswith(';'):
                found += ';'
            return found

    # Si no encontró nada
    if not text.endswith(';'):
        text += ';'
    return text

@app.route("/translate", methods=["POST"])
def translate_to_sql():
    """
    Recibe JSON {"question": "..."}
    Devuelve {"sql": "..."} generada por HF.
    """
    try:
        data = request.get_json()
        question = data.get("question", "").strip()
        if not question:
            return jsonify({"error": "No question provided"}), 400

        prompt = TEXT_TO_SQL_PROMPT.format(question=question)
        hf_resp = query_huggingface(prompt, max_tokens=200)
        raw_text = extract_generated_text(hf_resp)
        sql_final = clean_sql_response(raw_text)

        return jsonify({"sql": sql_final})

    except requests.HTTPError as e:
        # Manejo de error HTTP
        status_code = e.response.status_code
        try:
            err_json = e.response.json()
            return jsonify({"error": err_json}), status_code
        except:
            return jsonify({"error": str(e)}), status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/summarize", methods=["POST"])
def summarize():
    try:
        data = request.get_json()
        question = data.get("question", "")
        sql_query = data.get("sql", "")
        results = data.get("results", [])

        prompt = f"""
You are a helpful data assistant who explains results in exactly one short sentence.
- Do NOT prefix with 'Answer:' or 'Conclusion:' or any label.
- No mention of SQL or raw data. Only the key insight in a friendly style.

Example:
If the results show product='Alfajor DDL' with 123,
respond: "Alfajor DDL is our top seller with 123 units!"

Now do the same for:
Question: {question}
SQL: {sql_query}
Results: {results}

Only produce your final sentence in quotes.
"""

        hf_resp = query_huggingface(prompt, max_tokens=150)
        summary_raw = extract_generated_text(hf_resp)

        # Este step quita saltos de línea y espacios extra
        summary_raw = " ".join(summary_raw.split()).strip()

        # Busca TODAS las ocurrencias entre comillas "..."
        matches = re.findall(r'"([^"]+)"', summary_raw)
        # matches será una lista de strings SIN comillas, ej: ["Alfajor Sin Azucar is top ...", "Otra cosa"]

        if matches:
            # Tomamos la última por si hay más de una
            final_sentence = matches[-1]
        else:
            # Si no encontramos nada en comillas, devolvemos todo
            final_sentence = summary_raw

        return jsonify({"summary": final_sentence})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/healthcheck", methods=["GET"])
def healthcheck():
    return jsonify({"status": "ok", "model": MODEL_ID}), 200

if __name__ == "__main__":
    # debug=True para ver prints en Docker logs
    app.run(host="0.0.0.0", port=9100, debug=True)
