# Google Drive FAQ Chatbot

This project is a powerful but simple AI Chatbot designed to read documents directly from your Google Drive and answer questions on your website based *only* on those documents. 

It does not require complex database setups, making it perfect for business owners who want to keep their FAQ data easily editable in Google Docs or Sheets.

## 🔑 What You Need Before Starting

You only need three things to make this work:

1. **OpenAI API Key**: Go to [platform.openai.com](https://platform.openai.com/) and create an account to get a secret API key.
2. **Google Drive Folder ID**: Create a distinct folder in Google Drive and put your FAQ documents (PDFs, Google Docs, Sheets, Text files) inside. Look at the URL of the folder (e.g., `https://drive.google.com/drive/folders/1ABCDEFG123456`) — the `1ABCDEFG123456` part is your Folder ID.
3. **Google API Credentials**: You need a `credentials.json` file to allow the bot to read your Drive safely. 
   - Go to the [Google Cloud Console](https://console.cloud.google.com/).
   - Create a New Project.
   - Search for "Google Drive API" and click **Enable**.
   - Go to **APIs & Services > Credentials** and click **Create Credentials > OAuth client ID**.
   - Select "Desktop App", create it, and download the JSON file. Rename it to `credentials.json` and place it in this folder.

## 🛠️ Initial Setup (For Local Testing)

1. **Install Python**: Make sure you have Python installed on your computer.
2. **Add Your Keys**: Open the `.env` file in this folder and add your OpenAI Key and your Google Drive Folder ID.
3. **Run the Setup**: 
   Open your terminal/command prompt in this folder and run:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate   # (On Windows)
   source venv/bin/activate  # (On Mac/Linux)
   pip install -r requirements.txt
   ```
4. **Start the Chatbot Server**:
   ```bash
   uvicorn main:app --host 127.0.0.1 --port 8000 --reload
   ```
5. **Load Your Documents**: Go to `http://127.0.0.1:8000/docs` in your browser. Click on the `/refresh_context` endpoint and click "Try it out" -> "Execute". It will ask you to login to Google once to grant access, and then it will download your text!

## 🚀 How to Connect This to Your Website

To put this on your live website, you need to "host" this code on a server so it runs 24/7.

### Step 1: Hosting the Backend API
We recommend using a beginner-friendly cloud service like **Render.com** or **Heroku**:
1. Upload this folder to a private GitHub repository. (Note: the `.gitignore` file ensures your secret keys aren't uploaded publicly).
2. Create an account on Render.com and create a new "Web Service".
3. Connect it to your GitHub repository.
4. Render will ask for a **Start Command**. Type: `uvicorn main:app --host 0.0.0.0 --port 10000`
5. In Render's "Environment Variables" section, add your `OPENAI_API_KEY` and `GOOGLE_DRIVE_FOLDER_ID`.
6. *(Important: Because cloud servers do not have browsers, you must run Step 5 locally first to generate a `token.json` file. Include this `token.json` securely on your cloud server so it doesn't get blocked asking for a browser login).*

### Step 2: Adding the Chat Box to Your Website
Once your API is hosted (e.g., `https://my-chatbot.onrender.com`), you can add a simple chat interface to your website (whether it's Shopify, WordPress, Wix, or Webflow). 

Whenever a user types a message in the chat box, your website's interface just needs to send a request to `https://my-chatbot.onrender.com/chat` formatted like this:
```json
{
  "message": "What are your shipping times?"
}
```
And the bot will reply with the exact answer extracted directly from your Google Drive files!
