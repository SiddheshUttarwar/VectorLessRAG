# Google Drive FAQ Chatbot

This project is a powerful but simple AI Chatbot designed to read documents directly from your Google Drive and answer questions on your website based *only* on those documents. 

It does not require complex database setups, making it perfect for business owners who want to keep their FAQ data easily editable in Google Docs or Sheets.

## 🔑 What You Need Before Starting

You only need three things to make this work:

1. **OpenAI API Key**: Go to [platform.openai.com](https://platform.openai.com/) and create an account to get a secret API key.
2. **Google Drive Folder ID**: Create a distinct folder in Google Drive and put your FAQ documents (PDFs, Google Docs, Sheets, Text files) inside. Look at the URL of the folder (e.g., `https://drive.google.com/drive/folders/1ABCDEFG123456`) — the `1ABCDEFG123456` part is your Folder ID.
3. **Google API Credentials**: You need a `credentials.json` file. See the section below for exact steps on how to get this.

---

## 🛠️ Step-by-Step: How to get your Google `credentials.json`

Because this app reads from your Google Drive, Google requires you to prove you own the app using OAuth. Follow these exact steps:

1. Go to the **[Google Cloud Console](https://console.cloud.google.com/)**.
2. **Create a Project**: Look at the top left (next to the Google Cloud logo), click the dropdown, and click **New Project**. Name it "FAQ Chatbot" and click Create. Make sure this new project is selected.
3. **Enable the Drive API**: 
   - In the top search bar, type **"Google Drive API"** and click on the official result.
   - Click the blue **Enable** button.
4. **Configure the Consent Screen**:
   - On the left sidebar, click **OAuth consent screen**.
   - Choose **External** and click Create.
   - Fill in the required fields (App name: "FAQ Bot", User support email: your email, Developer contact information: your email). You can leave everything else blank.
   - Click **Save and Continue** until you reach the "Test Users" page.
   - **Crucial**: Under "Test users", click **Add Users** and add your own Google email address so you have permission to test it. Click Save and Continue, then Back to Dashboard.
5. **Create the Credentials**:
   - On the left sidebar, click **Credentials**.
   - Click **+ CREATE CREDENTIALS** at the top and select **OAuth client ID**.
   - Under "Application type", choose **Desktop app** (even though this will eventually run on a server, for the initial authentication step, "Desktop app" is required).
   - Name it "Local Bot" and click Create.
   - A window will pop up. Click **DOWNLOAD JSON**.
6. **Rename and Move**:
   - Find the downloaded file on your computer.
   - Rename it to exactly `credentials.json` (make sure it doesn't accidentally become `credentials.json.json`).
   - Drag and drop it into this `VectorLessRAG` project folder.

---

## 💻 Initial Setup (For Local Testing)

1. **Install Python**: Make sure you have Python installed on your computer.
2. **Add Your Keys**: Open the `.env` file in this folder and add your OpenAI Key and your Google Drive Folder ID.
3. **Run the Setup**: 
   Open your terminal/command prompt in this folder and run:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate   # (On Windows)
   pip install -r requirements.txt
   ```
4. **Start the Chatbot Server**:
   ```bash
   uvicorn main:app --host 127.0.0.1 --port 8000 --reload
   ```
5. **Load Your Documents**: Go to `http://127.0.0.1:8000/docs` in your browser. Click on the `/refresh_context` endpoint and click "Try it out" -> "Execute". 
   - *A Google Login window will pop up.* Log in with the email you added as a "Test user" in Step 4.
   - Google might say "Google hasn't verified this app." Click **Advanced** -> **Go to FAQ Bot (unsafe)**.
   - Click **Continue** to give it access.
   - Your text will now download! Notice that a file called `token.json` has appeared in your folder. This remembers your login.

## 🚀 How to Connect This to Your Website

To put this on your live website, you need to "host" this code on a server so it runs 24/7.

### Step 1: Hosting the Backend API
We recommend using a beginner-friendly cloud service like **Render.com** or **Heroku**:
1. Upload this folder to a private GitHub repository.
2. Create an account on Render.com and create a new "Web Service".
3. Connect it to your GitHub repository.
4. Render will ask for a **Start Command**. Type: `uvicorn main:app --host 0.0.0.0 --port 10000`
5. In Render's "Environment Variables" section, add your `OPENAI_API_KEY` and `GOOGLE_DRIVE_FOLDER_ID`.
6. *(Important: Because cloud servers do not have web browsers to log in with, you MUST run Step 5 locally on your computer first. This generates the `token.json` file. You must upload this `token.json` securely to your cloud server or add its contents to the environment variables so it remembers your login!)*

### Step 2: Adding the Chat Box to Your Website
Once your API is hosted (e.g., `https://my-chatbot.onrender.com`), you can add a simple chat interface to your website. 

Whenever a user types a message in the chat box, your website's interface just needs to send a request to `https://my-chatbot.onrender.com/chat` formatted like this:
```json
{
  "message": "What are your shipping times?"
}
```
And the bot will reply with the exact answer extracted directly from your Google Drive files!
