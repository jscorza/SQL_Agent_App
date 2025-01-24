import os
import openai
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# 1) Obtenemos la API Key de OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "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")
openai.api_key = OPENAI_API_KEY

# 2) Esquema de tu tabla (Prompt Engineering)
SCHEMA_PROMPT = """
You are an AI assistant that converts natural language questions into SQL queries.
The database has a table called 'sales' with the following columns:
- date (DATE)
- week_day (VARCHAR)
- hour (VARCHAR)
- ticket_number (VARCHAR)
- waiter (INT)
- product_name (VARCHAR)
- quantity (INT)
- unitary_price (DECIMAL)
- total (DECIMAL)

Follow these rules:
1. Only generate a syntactically correct SQL query based on the question.
2. Do not include any additional commentary or text, just the SQL.
3. If the user question is ambiguous, make a reasonable guess or ask for clarification.

"""

class QueryRequest(BaseModel):
    question: str

@app.get("/healthcheck")
def healthcheck():
    return {"status": "ok"}

@app.post("/translate")
def translate_to_sql(payload: QueryRequest):
    """ 
    Endpoint que recibe {"question": "..."} y retorna {"sql": "..."} 
    usando la API de OpenAI para la tarea de text-to-sql.
    """
    user_question = payload.question

    # 3) Construir el prompt para OpenAI
    # Usaremos el esquema + la pregunta en un solo string:
    prompt = f"{SCHEMA_PROMPT}\nQuestion: {user_question}\nSQL:"

    # 4) Llamar a la API de OpenAI
    # Opción A: Usando ChatCompletion (GPT-3.5 / GPT-4)
    try:
        response = openai.ChatCompletion.create(
            #model="gpt-3.5-turbo",
            model="gpt-4",
            messages=[
                {"role": "system", "content": SCHEMA_PROMPT},
                {"role": "user", "content": f"Question: {user_question}\nSQL:"}
            ],
            temperature=0.0,  # más determinista
            max_tokens=150
        )
        # Extraer la respuesta
        generated_sql = response["choices"][0]["message"]["content"].strip()

    except Exception as e:
        return {"error": str(e)}

    # 5) Devolver la sentencia SQL
    return {"sql": generated_sql}
