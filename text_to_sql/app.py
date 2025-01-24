import os
import openai
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()
openai.api_key = os.getenv("OPENAI_API_KEY", "")

SCHEMA_PROMPT = """You are a SQL expert generating PostgreSQL queries for sales data analysis.

Table Schema:
- sales (date DATE, week_day VARCHAR, hour VARCHAR, ticket_number VARCHAR, 
         waiter INT, product_name VARCHAR, quantity INT, 
         unitary_price DECIMAL, total DECIMAL)

Rules:
1. Generate syntactically correct SQL only
2. No explanations/comments
3. Handle ambiguity with reasonable assumptions"""

class QueryRequest(BaseModel):
    """Request payload schema for SQL translation."""
    question: str

@app.get("/healthcheck")
def healthcheck() -> dict:
    return {"status": "ok"}

@app.post("/translate")
def translate_to_sql(payload: QueryRequest) -> dict:
    """Convert natural language questions to SQL using OpenAI GPT-4."""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{
                "role": "system", 
                "content": SCHEMA_PROMPT
            }, {
                "role": "user", 
                "content": f"Question: {payload.question}\nSQL:"
            }],
            temperature=0.0,
            max_tokens=150
        )
        return {"sql": response["choices"][0]["message"]["content"].strip()}
    
    except Exception as e:
        return {"error": f"OpenAI API error: {str(e)}"}