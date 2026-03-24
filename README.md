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

## 🚀 Running Locally

```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Open **http://127.0.0.1:8000/docs** to use the Swagger UI.

### Step 1 — Load Your Documents
Hit the **POST /refresh_context** endpoint. On the first run, a Google login popup will appear — log in with your whitelisted Google account. Google may show a warning; click **Advanced → Go to app (unsafe)** to proceed.

The bot will:
1. Scan all files in your Google Drive folder
2. Download only new or changed files (incremental sync)
3. Use OpenAI to merge and deduplicate the content into a clean knowledge base
4. Save it to `context_cache.txt`

On subsequent runs, unchanged files are **skipped entirely** — saving time and API tokens.

### Step 2 — Chat
Hit the **POST /chat** endpoint with:
```json
{
  "message": "What are your business hours?",
  "history": []
}
```
Pass previous messages in `history` to maintain a multi-turn conversation.

---

## 🔗 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/chat` | Send a message and get a response |
| `POST` | `/refresh_context` | Sync new/updated files from Google Drive |
| `GET`  | `/health` | Check server health |

### `/chat` Request Body
```json
{
  "message": "Your question here",
  "history": [
    { "role": "user",      "content": "Previous question" },
    { "role": "assistant", "content": "Previous answer" }
  ]
}
```

### 🔒 API Key Header (Production)
Set `BOT_API_KEY` in `.env` to any secret string. All requests must then include the header:
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

### Adding the Chat Widget to Your Website
Once deployed (e.g., `https://my-chatbot.onrender.com`), call the API from your website's JavaScript:

```javascript
let history = [];

async function sendMessage(userMessage) {
  const res = await fetch("https://my-chatbot.onrender.com/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-KEY": "your-secret-key"
    },
    body: JSON.stringify({ message: userMessage, history: history })
  });
  const data = await res.json();
  history.push({ role: "user", content: userMessage });
  history.push({ role: "assistant", content: data.response });
  return data.response;
}
```

---

## ⚠️ Scaling Limits

This project uses the **Full-Context** approach — all document text is sent to OpenAI on every request. The model (`gpt-4o-mini`) supports ~128K tokens (~300 pages). If your knowledge base grows beyond that, consider migrating to a vector database (e.g., ChromaDB or Pinecone) for chunked retrieval.
