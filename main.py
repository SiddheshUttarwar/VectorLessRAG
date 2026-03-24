from fastapi import FastAPI, HTTPException, BackgroundTasks, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

app = FastAPI(title="Vectorless RAG FAQ Chatbot")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
CONTEXT_CACHE_FILE = "context_cache.txt"

# --- API Key Security ---
BOT_API_KEY = os.getenv("BOT_API_KEY", "")
api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)

def verify_api_key(key: Optional[str] = Security(api_key_header)):
    # If no BOT_API_KEY is set in .env, security is disabled (local testing mode)
    if not BOT_API_KEY:
        return True
    if key != BOT_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing API Key.")
    return True

# --- Request / Response Models ---
class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[Message] = []  # Optional list of previous messages for multi-turn chat

# --- Helpers ---
def get_context():
    if not os.path.exists(CONTEXT_CACHE_FILE):
        return "No context available yet. Please run the /refresh_context endpoint."
    with open(CONTEXT_CACHE_FILE, "r", encoding="utf-8") as f:
        return f.read()

def refresh_drive_context():
    """Runs the drive loader logic to update the text cache"""
    try:
        from drive_loader import load_folder_contents
        load_folder_contents()
    except Exception as e:
        print(f"Error refreshing context: {e}")

# --- Endpoints ---
@app.post("/refresh_context")
def refresh_context(background_tasks: BackgroundTasks, _: bool = Depends(verify_api_key)):
    """
    Triggers a background task to fetch latest files from Google Drive
    and update the local context_cache.txt file.
    Only processes new or modified files since the last refresh.
    """
    background_tasks.add_task(refresh_drive_context)
    return {"status": "Context refresh started in the background."}

@app.post("/chat")
def chat_with_bot(request: ChatRequest, _: bool = Depends(verify_api_key)):
    """
    Handles natural language queries and answers purely based on the
    extracted Google Drive context. Supports multi-turn conversation history.
    """
    context = get_context()
    
    system_prompt = (
        "You are a professional, empathetic customer support agent. "
        "Always start your message by thanking the user for their question. "
        "Always end your message by offering them to email support@mycompany.com if they need more help. "
        "Use the provided context documents to answer the user's questions. "
        "Do not make up information that is not in the context.\n\n"
        f"--- CONTEXT DOCUMENTS ---\n{context}\n--- END CONTEXT ---\n"
    )
    
    # Build the full message list including conversation history
    messages = [{"role": "system", "content": system_prompt}]
    for msg in request.history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": request.message})
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.2,  # Low temperature to prevent hallucinations
            max_tokens=600
        )
        return {"response": response.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "ok"}
