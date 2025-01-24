from flask import Flask, render_template, request, redirect, url_for
import requests
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"

conversation = []

TEXT_TO_SQL_URL = os.getenv("TEXT_TO_SQL_URL", "http://text_to_sql:8000/translate")
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:5000/query")
LLM_RESPONDER_URL = os.getenv("LLM_RESPONDER_URL", "http://llm_responder:9000/summarize")

HF_AGENT_TRANSLATE = os.getenv("HF_AGENT_TRANSLATE", "http://hf_agent:9100/translate")
HF_AGENT_SUMMARIZE = os.getenv("HF_AGENT_SUMMARIZE", "http://hf_agent:9100/summarize")

MODEL_CONFIG = {
    "openai": {
        "translate": TEXT_TO_SQL_URL,
        "summarize": LLM_RESPONDER_URL
    },
    "huggingface": {
        "translate": HF_AGENT_TRANSLATE,
        "summarize": HF_AGENT_SUMMARIZE
    }
}

@app.route('/')
def index():
    return render_template('index.html', conversation=conversation)

def handle_hf_response_err(response):
    """Manejo de error en la respuesta HF si viene 503, etc."""
    try:
        err_json = response.json()
        return err_json
    except:
        return {"error": response.text}

@app.route('/ask', methods=['POST'])
def ask():
    user_question = request.form.get('question', '').strip()
    model_choice = request.form.get('model_choice', 'openai')

    if not user_question:
        return redirect(url_for('index'))

    # Nuevas variables para manejo de errores
    friendly_text = ""
    technical_details = ""
    raw_sql = "NO_SQL_GENERATED"
    raw_results = []
    error_occurred = False

    try:
        translate_url = MODEL_CONFIG[model_choice]['translate']
        resp_t = requests.post(translate_url, json={"question": user_question}, timeout=180)
        
        if resp_t.status_code != 200:
            error_occurred = True
            friendly_text = "⚠️ Couldn't process your question. Please try again."
            technical_details = f"Translate Error {resp_t.status_code}: {handle_hf_response_err(resp_t)}"
        else:
            t_data = resp_t.json()
            if "sql" not in t_data:
                error_occurred = True
                friendly_text = "🔍 Invalid question format. Please be more specific."
                technical_details = f"Missing 'sql' in response: {t_data}"
            else:
                raw_sql = t_data["sql"]
                resp_b = requests.post(BACKEND_URL, json={"sql": raw_sql}, timeout=30)
                
                if resp_b.status_code != 200:
                    error_occurred = True
                    friendly_text = "🔍 We found an issue with your question. Please rephrase it."
                    technical_details = f"Backend Error {resp_b.status_code}: {resp_b.text[:200]}"
                else:
                    b_data = resp_b.json()
                    raw_results = b_data.get("results", [])
                    
                    if raw_results:
                        summarize_url = MODEL_CONFIG[model_choice]['summarize']
                        s_payload = {"question": user_question, "sql": raw_sql, "results": raw_results}
                        resp_s = requests.post(summarize_url, json=s_payload, timeout=180)
                        
                        if resp_s.status_code != 200:
                            error_occurred = True
                            friendly_text = "📝 We couldn't summarize the results. Try another question."
                            technical_details = f"Summarize Error {resp_s.status_code}: {handle_hf_response_err(resp_s)}"
                        else:
                            s_data = resp_s.json()
                            friendly_text = s_data.get("summary", "No summary returned")
                    else:
                        friendly_text = "✅ Query executed successfully (no results returned)"
    
    except requests.exceptions.RequestException as e:
        error_occurred = True
        friendly_text = "🔌 Connection error. Please check your internet."
        technical_details = f"RequestException: {str(e)}"
    except Exception as e:
        error_occurred = True
        friendly_text = "❌ Unexpected error. Contact support."
        technical_details = f"General error: {str(e)}"

    conversation.append({
        "role": "user",
        "text": user_question  # Aseguramos que el user message tenga "text"
    })
    
    conversation.append({
        "role": "system",
        "friendly_text": friendly_text,
        "technical_details": technical_details if error_occurred else "",
        "sql": raw_sql,
        "raw_results": raw_results,
        "model_used": model_choice,
        "error": error_occurred
    })

    return redirect(url_for('index'))

@app.route('/reset')
def reset():
    conversation.clear()
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
