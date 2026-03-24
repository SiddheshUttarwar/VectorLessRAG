from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import os
import subprocess
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

app = FastAPI(title="Vectorless RAG FAQ Chatbot")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
CONTEXT_CACHE_FILE = "context_cache.txt"

class ChatRequest(BaseModel):
    message: str

def get_context():
    if not os.path.exists(CONTEXT_CACHE_FILE):
        return "No context available yet. Please run the /refresh_context endpoint."
    with open(CONTEXT_CACHE_FILE, "r", encoding="utf-8") as f:
        return f.read()

def refresh_drive_context():
    """ Runs the drive loader logic to update the text cache """
    try:
        from drive_loader import load_folder_contents
        load_folder_contents()
    except Exception as e:
        print(f"Error refreshing context: {e}")

@app.post("/refresh_context")
def refresh_context(background_tasks: BackgroundTasks):
    """
    Triggers a background task to fetch latest files from Google Drive
    and update the local context_cache.txt file.
    """
    background_tasks.add_task(refresh_drive_context)
    return {"status": "Context refresh started in the background."}

@app.post("/chat")
def chat_with_bot(request: ChatRequest):
    """
    Endpoint that handles the users natural language queries 
    and answers purely based on the extracted Google Drive context.
    """
    context = get_context()
    
    system_prompt = (
        "You are a helpful and polite FAQ chatbot for a website. "
        "Use the provided context documents to answer the user's questions. "
        "If the answer is not contained in the context, politely inform the user that you don't know the answer. "
        "Do not make up information that is not in the context.\n\n"
        f"--- CONTEXT DOCUMENTS ---\n{context}\n--- END CONTEXT ---\n"
    )
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.message}
            ],
            temperature=0.2, # Low temperature to prevent hallucinations
            max_tokens=600
        )
        return {"response": response.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "ok"}
