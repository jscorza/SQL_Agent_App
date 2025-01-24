from flask import Flask, request, jsonify
import openai
import os

app = Flask(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
openai.api_key = OPENAI_API_KEY

@app.route("/summarize", methods=["POST"])
def summarize():
    """
    Espera un JSON:
    {
      "question": "<pregunta del usuario>",
      "sql": "<sentencia generada>",
      "results": [{...}, {...}]  # array de dicts
    }
    Devuelve un JSON con { "summary": "...texto en lenguaje natural..." }
    """
    data = request.get_json()
    user_question = data.get("question", "")
    generated_sql = data.get("sql", "")
    raw_results = data.get("results", [])

    # Convierto los resultados a string (o formateo más elegante)
    results_str = str(raw_results)

    # Prompt para GPT
    prompt = (
        f"User question: {user_question}\n"
        f"SQL query: {generated_sql}\n"
        f"SQL results: {results_str}\n\n"
        "Write a concise explanation in natural language of the results above, "
        "without revealing the SQL or the raw data. Summarize in a friendly way."
    )

    try:
        response = openai.ChatCompletion.create(
            #model="gpt-3.5-turbo",
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant summarizing SQL data."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=150
        )
        summary_text = response["choices"][0]["message"]["content"].strip()
        return jsonify({"summary": summary_text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/healthcheck", methods=["GET"])
def healthcheck():
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9000, debug=True)
