from flask import Flask, render_template, request, redirect, url_for
import requests
import os

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'supersecretkey')

conversation = []

# Service endpoints configuration
MODEL_CONFIG = {
    "openai": {
        "translate": os.getenv("TEXT_TO_SQL_URL", "http://text_to_sql:8000/translate"),
        "summarize": os.getenv("LLM_RESPONDER_URL", "http://llm_responder:9000/summarize")
    },
    "huggingface": {
        "translate": os.getenv("HF_AGENT_TRANSLATE", "http://hf_agent:9100/translate"),
        "summarize": os.getenv("HF_AGENT_SUMMARIZE", "http://hf_agent:9100/summarize")
    }
}

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:5000/query")

@app.route('/')
def index():
    return render_template('index.html', conversation=conversation)

def handle_api_error(response):
    """Handle non-JSON responses from external APIs."""
    try:
        return response.json()
    except requests.JSONDecodeError:
        return {'error': response.text}

@app.route('/ask', methods=['POST'])
def ask():
    user_question = request.form.get('question', '').strip()
    model_choice = request.form.get('model_choice', 'openai')

    if not user_question:
        return redirect(url_for('index'))

    response_data = {
        'friendly_text': '',
        'technical_details': '',
        'raw_sql': 'NO_SQL_GENERATED',
        'raw_results': [],
        'error': False
    }

    try:
        # Translation phase
        translate_response = requests.post(
            MODEL_CONFIG[model_choice]['translate'],
            json={'question': user_question},
            timeout=10
        )
        
        if translate_response.status_code != 200:
            response_data.update({
                'error': True,
                'friendly_text': '⚠️ Could not process your question',
                'technical_details': f'Translation Error {translate_response.status_code}: {handle_api_error(translate_response)}'
            })
            return commit_conversation(user_question, response_data)

        translate_data = translate_response.json()
        if 'sql' not in translate_data:
            response_data.update({
                'error': True,
                'friendly_text': '🔍 Invalid question format',
                'technical_details': f'Missing SQL in response: {translate_data}'
            })
            return commit_conversation(user_question, response_data)

        # Query execution phase
        query_response = requests.post(
            BACKEND_URL,
            json={'sql': translate_data['sql']},
            timeout=15
        )
        
        if query_response.status_code != 200:
            response_data.update({
                'error': True,
                'friendly_text': '🔍 Issue executing query',
                'technical_details': f'Backend Error {query_response.status_code}: {query_response.text[:200]}',
                'raw_sql': translate_data['sql']
            })
            return commit_conversation(user_question, response_data)

        query_data = query_response.json()
        response_data['raw_results'] = query_data.get('results', [])
        response_data['raw_sql'] = translate_data['sql']

        # Results summarization
        if response_data['raw_results']:
            summarize_response = requests.post(
                MODEL_CONFIG[model_choice]['summarize'],
                json={
                    'question': user_question,
                    'sql': response_data['raw_sql'],
                    'results': response_data['raw_results']
                },
                timeout=15
            )
            
            if summarize_response.status_code != 200:
                response_data.update({
                    'error': True,
                    'friendly_text': '📝 Summary generation failed',
                    'technical_details': f'Summarization Error {summarize_response.status_code}: {handle_api_error(summarize_response)}'
                })
            else:
                response_data['friendly_text'] = summarize_response.json().get('summary', 'No summary available')

        else:
            response_data['friendly_text'] = '✅ Query executed successfully (no results)'

    except requests.exceptions.RequestException as e:
        response_data.update({
            'error': True,
            'friendly_text': '🔌 Connection issue',
            'technical_details': f'Network Error: {str(e)}'
        })
    except Exception as e:
        response_data.update({
            'error': True,
            'friendly_text': '❌ System error',
            'technical_details': f'Unexpected Error: {str(e)}'
        })

    return commit_conversation(user_question, response_data)

def commit_conversation(question, response_data):
    """Store conversation history and redirect to index."""
    conversation.append({'role': 'user', 'text': question})
    conversation.append({
        'role': 'system',
        'friendly_text': response_data['friendly_text'],
        'technical_details': response_data['technical_details'],
        'sql': response_data['raw_sql'],
        'raw_results': response_data['raw_results'],
        'model_used': request.form.get('model_choice', 'openai'),
        'error': response_data['error']
    })
    return redirect(url_for('index'))

@app.route('/reset')
def reset():
    conversation.clear()
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)