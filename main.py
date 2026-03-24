from fastapi import FastAPI, HTTPException, BackgroundTasks, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import uuid
from datetime import datetime
from collections import Counter
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

app = FastAPI(title="Vectorless RAG FAQ Chatbot")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
CONTEXT_CACHE_FILE = "context_cache.txt"

# --- In-memory stores ---
sessions = {}
questions_log = []
topic_transitions = []
total_questions_all_time = 0

sync_state = {"status": "idle", "files_processed": 0, "message": "Never synced"}  # idle | running | done

TOPICS = [
    "Pricing & Plans", "Shipping & Delivery", "Returns & Refunds",
    "Product Info", "Account & Login", "Contact & Support", "Hours & Location", "Other"
]

def detect_topic(question: str) -> str:
    """Simple keyword-based topic detection (no extra OpenAI calls)."""
    q = question.lower()
    if any(w in q for w in ["price","cost","fee","plan","subscription","pay","cheap","discount","rate","charge"]): return "Pricing & Plans"
    if any(w in q for w in ["ship","deliver","track","transit","arrival","dispatch","courier","postal"]): return "Shipping & Delivery"
    if any(w in q for w in ["return","refund","exchange","cancel","money back","policy","warranty"]): return "Returns & Refunds"
    if any(w in q for w in ["product","item","feature","spec","material","size","color","stock","available"]): return "Product Info"
    if any(w in q for w in ["account","login","password","profile","signup","register","forgot","email"]): return "Account & Login"
    if any(w in q for w in ["contact","phone","email","reach","support","help","talk","agent","chat"]): return "Contact & Support"
    if any(w in q for w in ["hours","open","close","location","address","office","store","visit","timing"]): return "Hours & Location"
    return "Other"

# --- API Key Security ---
BOT_API_KEY = os.getenv("BOT_API_KEY", "")
api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)

def verify_api_key(key: Optional[str] = Security(api_key_header)):
    if not BOT_API_KEY:
        return True
    if key != BOT_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing API Key.")
    return True

# --- Models ---
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

# --- Helpers ---
def get_context():
    if not os.path.exists(CONTEXT_CACHE_FILE):
        return "No context available yet. Please run the /refresh_context endpoint."
    with open(CONTEXT_CACHE_FILE, "r", encoding="utf-8") as f:
        return f.read()

def refresh_drive_context():
    global sync_state
    sync_state = {"status": "running", "files_processed": 0, "message": "Connecting to Google Drive…"}
    try:
        from drive_loader import load_folder_contents
        files_processed, message = load_folder_contents()
        sync_state = {"status": "done", "files_processed": files_processed, "message": message}
    except Exception as e:
        sync_state = {"status": "done", "files_processed": 0, "message": f"Error: {e}"}



# --- Endpoints ---
@app.get("/")
def serve_dashboard():
    return FileResponse("dashboard.html")

@app.get("/sync_status")
def get_sync_status():
    """Returns current status of the Drive sync operation."""
    return sync_state

@app.post("/session/new")
def create_session():
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "history": [], "question_count": 0,
        "created_at": datetime.now().isoformat(), "topics": []
    }
    return {"session_id": session_id}

@app.get("/stats")
def get_stats():
    return {
        "total_questions_all_sessions": total_questions_all_time,
        "active_sessions": len(sessions),
        "sessions": {
            sid: {"question_count": s["question_count"], "created_at": s["created_at"]}
            for sid, s in sessions.items()
        }
    }

@app.get("/analytics")
def get_analytics():
    """Rich analytics data for the business dashboard."""
    if not questions_log:
        return {
            "top_topics": [], "top_questions": [], "questions_by_hour": {},
            "topic_flow": [], "avg_session_length": 0, "total_sessions": len(sessions)
        }

    # Top topics
    all_topics = [q["topic"] for q in questions_log]
    topic_counts = dict(Counter(all_topics).most_common(8))

    # Topic-to-topic flow transitions
    flow_counts = Counter(topic_transitions)
    topic_flow = [
        {"from": f, "to": t, "count": c}
        for (f, t), c in flow_counts.most_common(15)
    ]

    # Top unique questions (by normalized text)
    question_texts = [q["text"][:80] for q in questions_log]
    top_questions = [{"text": t, "count": c} for t, c in Counter(question_texts).most_common(10)]

    # Questions by hour of day
    hour_counts = Counter(datetime.fromisoformat(q["timestamp"]).hour for q in questions_log)
    questions_by_hour = {str(h): hour_counts.get(h, 0) for h in range(24)}

    # Questions per day (last 7 days)
    day_counts = Counter(datetime.fromisoformat(q["timestamp"]).strftime("%Y-%m-%d") for q in questions_log)

    # Avg session length
    session_lengths = [s["question_count"] for s in sessions.values() if s["question_count"] > 0]
    avg_session_length = round(sum(session_lengths) / len(session_lengths), 1) if session_lengths else 0

    # Questions grouped by topic (with sample questions list)
    from collections import defaultdict
    by_topic = defaultdict(list)
    for q in questions_log:
        by_topic[q["topic"]].append(q["text"])
    questions_by_topic = {
        topic: {"count": len(qs), "samples": list(dict.fromkeys(qs))[:5]}  # unique, max 5 samples
        for topic, qs in sorted(by_topic.items(), key=lambda x: -len(x[1]))
    }

    return {
        "top_topics": [{"topic": k, "count": v} for k, v in topic_counts.items()],
        "top_questions": top_questions,
        "questions_by_hour": questions_by_hour,
        "questions_per_day": dict(day_counts),
        "topic_flow": topic_flow,
        "questions_by_topic": questions_by_topic,
        "avg_session_length": avg_session_length,
        "total_sessions": len(sessions)
    }

@app.post("/refresh_context")
def refresh_context(background_tasks: BackgroundTasks, _: bool = Depends(verify_api_key)):
    background_tasks.add_task(refresh_drive_context)
    return {"status": "Context refresh started in the background."}

@app.post("/chat")
def chat_with_bot(request: ChatRequest, _: bool = Depends(verify_api_key)):
    global total_questions_all_time

    session_id = request.session_id
    if not session_id or session_id not in sessions:
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "history": [], "question_count": 0,
            "created_at": datetime.now().isoformat(), "topics": []
        }

    session = sessions[session_id]
    context = get_context()
    topic = detect_topic(request.message)

    # Track topic transitions (e.g. Pricing → Shipping)
    if session["topics"]:
        topic_transitions.append((session["topics"][-1], topic))
    session["topics"].append(topic)

    system_prompt = (
        "You are a professional, empathetic customer support agent. "
        "Always start your message by thanking the user for their question. "
        "Always end your message by offering them to email support@mycompany.com if they need more help. "
        "Use the provided context documents to answer the user's questions. "
        "Do not make up information that is not in the context.\n\n"
        f"--- CONTEXT DOCUMENTS ---\n{context}\n--- END CONTEXT ---\n"
    )

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(session["history"])
    messages.append({"role": "user", "content": request.message})

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", messages=messages, temperature=0.2, max_tokens=600
        )
        answer = response.choices[0].message.content

        session["history"].append({"role": "user", "content": request.message})
        session["history"].append({"role": "assistant", "content": answer})
        session["question_count"] += 1
        total_questions_all_time += 1

        questions_log.append({
            "text": request.message,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "topic": topic,
            "response_length": len(answer)
        })

        return {
            "response": answer,
            "session_id": session_id,
            "topic": topic,
            "session_question_count": session["question_count"],
            "total_questions": total_questions_all_time
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/session/{session_id}/clear")
def clear_session(session_id: str):
    if session_id in sessions:
        sessions[session_id]["history"] = []
        sessions[session_id]["question_count"] = 0
        sessions[session_id]["topics"] = []
        return {"status": "Session cleared."}
    raise HTTPException(status_code=404, detail="Session not found.")

@app.get("/health")
def health_check():
    return {"status": "ok"}
