# 🤖 Vectorless RAG FAQ Chatbot

An AI-powered FAQ chatbot that reads your documents directly from **Google Drive** and answers questions based solely on your content — no vector databases, no complex setup.

> Built with **Python + FastAPI + OpenAI + Google Drive API**

---

## 📁 Project Structure

```
VectorLessRAG/
├── main.py                 # FastAPI server & chat endpoints
├── drive_loader.py         # Google Drive sync & OpenAI compression
├── requirements.txt        # Python dependencies
├── .env                    # Your secret API keys (never committed)
├── credentials.json        # Google OAuth credentials (never committed)
├── token.json              # Auto-generated Google auth token (never committed)
├── context_cache.txt       # Auto-generated compressed knowledge base
└── processed_files.json    # Auto-generated state tracker for incremental sync
```

---

## 🔑 Prerequisites

### 1. OpenAI API Key
Go to [platform.openai.com](https://platform.openai.com/) → API Keys → Create new secret key.

### 2. Google Drive Folder ID
Create a dedicated folder in Google Drive and put your FAQ documents inside (PDFs, Google Docs, Google Sheets, or .txt files). The Folder ID is the last part of the folder's URL:
```
https://drive.google.com/drive/folders/[THIS_PART_IS_YOUR_FOLDER_ID]
```

### 3. Google OAuth `credentials.json`
These steps let the bot securely read your Drive without needing your password:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/) and create a new project.
2. Search for **"Google Drive API"** and click **Enable**.
3. Go to **APIs & Services → OAuth consent screen**:
   - Choose **External** and click Create.
   - Fill in App Name and your email. Click Save and Continue through all steps.
   - On the **Test users** page, click **+ Add Users** and add the Google email you will login with.
4. Go to **APIs & Services → Credentials** → **+ Create Credentials → OAuth client ID**:
   - Application type: **Desktop app**
   - Click Create, then **Download JSON**.
5. Rename the downloaded file to `credentials.json` and place it in the project folder.

---

## 🛠️ Setup

```bash
# 1. Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate      # Windows
source venv/bin/activate     # Mac/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Fill in your .env file
```

Open `.env` and add your keys:
```env
OPENAI_API_KEY="sk-..."
GOOGLE_DRIVE_FOLDER_ID="your_folder_id_here"
BOT_API_KEY=""              # Leave empty during development; set a secret for production
```

---

## ✨ Features

- **Business Analytics Dashboard**: A premium, Flouv-inspired web dashboard with KPI cards and Chart.js visualizations.
- **Auto-Topic Classification**: Every user question is automatically categorized into business topics (e.g., Pricing, Shipping, Returns) with zero extra LLM calls.
- **Server-Side Session Memory**: The bot remembers conversation history per session flawlessly.
- **Incremental Drive Sync**: Downloads only new or modified files, drastically saving API costs, with a live progress modal.
- **Vectorless Compression**: Merges all documents into a single optimized `context_cache.txt`, injected directly into the prompt.
- **API Security**: Built-in API key validation for production deployments.

---

## 🚀 Running Locally

```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### 1. The Interactive Dashboard
Open **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)** in your browser to access the full Business Intelligence Dashboard.
- **Analytics Tab**: View total questions, active sessions, topic distributions, and the most asked questions.
- **Chat Tab**: Test the bot with a beautiful, real-time UI showing live topic thread tracking.
- **Sync Drive**: Click the "Sync Drive" button in the navbar to securely pull the latest files from your Google Drive. 

### 2. Testing the API Directly
To test the raw API endpoints using the auto-generated Swagger UI, open:
**[http://127.0.0.1:8000/docs#/default/chat_with_bot_chat_post](http://127.0.0.1:8000/docs#/default/chat_with_bot_chat_post)**

---

## 🔗 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/` | Serves the interactive Business Dashboard UI |
| `POST` | `/session/new` | Creates a new chat session and returns a `session_id` |
| `POST` | `/chat` | Send a message to the bot (requires `session_id`) |
| `GET`  | `/analytics` | Returns aggregated business intelligence data + charts |
| `GET`  | `/stats` | Returns high-level server KPIs |
| `POST` | `/refresh_context` | Triggers a sync with Google Drive |
| `GET`  | `/sync_status` | Returns the current progress of the Drive sync |

### `/chat` Request Body
```json
{
  "message": "What is the return policy?",
  "session_id": "your-uuid-string-here"
}
```

### 🔒 API Key Header (Production)
Set `BOT_API_KEY` in `.env` to any secret string. All API requests must then include the header:
```
X-API-KEY: your-secret-key
```
If `BOT_API_KEY` is empty, the security check is **automatically disabled** (for local development).

---

## 🤖 Customizing the Bot's Personality

Edit the `system_prompt` in `main.py` to change how the bot behaves:

```python
system_prompt = (
    "You are a professional, empathetic customer support agent. "
    "Always start your message by thanking the user for their question. "
    "Always end your message by offering them to email support@mycompany.com if they need more help. "
    "Use the provided context documents to answer the user's questions. "
    "Do not make up information that is not in the context."
)
```

The server **hot-reloads** on save, so changes take effect immediately.

---

## 🌐 Deploying to Production (Render.com)

1. Push this repo to a **private** GitHub repository (your `.env`, `credentials.json`, `token.json` are all gitignored).
2. Create a new **Web Service** on [render.com](https://render.com) connected to your repo.
3. Set **Start Command**: `uvicorn main:app --host 0.0.0.0 --port 10000`
4. Add Environment Variables on Render: `OPENAI_API_KEY`, `GOOGLE_DRIVE_FOLDER_ID`, `BOT_API_KEY`.
5. **Important**: Run the bot locally first to generate `token.json`, then add its contents as a `token.json` Secret File on Render (under Environment → Secret Files).

---

## ⚠️ Scaling Limits

This project uses the **Full-Context** approach — all document text is sent to OpenAI on every request. The model (`gpt-4o-mini`) supports ~128K tokens (~300 pages). If your knowledge base grows beyond that, consider migrating to a vector database (e.g., ChromaDB or Pinecone) for chunked retrieval.
