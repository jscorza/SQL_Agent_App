from flask import Flask, request, jsonify
import openai
import os
from typing import Any, Dict

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY", "")

PROMPT_TEMPLATE = """\
User question: {question}
SQL query: {sql}
SQL results: {results}

Generate a concise natural language summary that:
- Answers the original question
- Excludes technical details
- Uses simple business terms
- Maximum 150 characters\
"""

@app.route("/summarize", methods=["POST"])
def summarize() -> Dict[str, Any]:
    """Transform SQL results into business-friendly insights using OpenAI."""
    data = request.get_json()
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{
                "role": "system",
                "content": "You summarize data for business users. Avoid technical jargon."
            }, {
                "role": "user",
                "content": PROMPT_TEMPLATE.format(
                    question=data.get("question", ""),
                    sql=data.get("sql", ""),
                    results=data.get("results", [])
                )
            }],
            temperature=0.3,
            max_tokens=150
        )
        return jsonify({
            "summary": response["choices"][0]["message"]["content"].strip()
        })
    except Exception as e:
        return jsonify({"error": f"OpenAI API error: {str(e)}"}), 500

@app.route("/healthcheck", methods=["GET"])
def healthcheck() -> Dict[str, Any]:
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9000)