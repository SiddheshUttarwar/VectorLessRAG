import os
import io
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import PyPDF2
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# We only need read-only access to Drive files
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
CONTEXT_CACHE_FILE = "context_cache.txt"
STATE_FILE = "processed_files.json"

def get_credentials():
    creds = None
    # token.json stores the user's access and refresh tokens
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                raise FileNotFoundError("credentials.json not found! Please download your OAuth client ID credentials from Google Cloud Console and save it as credentials.json in this directory.")
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

def extract_pdf_text(file_stream):
    reader = PyPDF2.PdfReader(file_stream)
    text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"
    return text

def load_folder_contents():
    if not FOLDER_ID:
        raise ValueError("GOOGLE_DRIVE_FOLDER_ID is not set in the .env file")
        
    creds = get_credentials()
    service = build('drive', 'v3', credentials=creds)
    
    # Query for all files in the folder, paginating through all results
    query = f"'{FOLDER_ID}' in parents and trashed=false"
    items = []
    page_token = None
    while True:
        kwargs = dict(q=query, fields="nextPageToken, files(id, name, mimeType, modifiedTime)")
        if page_token:
            kwargs["pageToken"] = page_token
        results = service.files().list(**kwargs).execute()
        items.extend(results.get('files', []))
        page_token = results.get('nextPageToken')
        if not page_token:
            break

    
    if not items:
        print("No files found in the specified Google Drive folder.")
        return ""
    
    # Load previously processed files so we skip duplicates
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
    else:
        state = {}

    new_context = ""
    updated_state = state.copy()
    files_processed = 0

    for item in items:
        file_id = item['id']
        file_name = item['name']
        mime_type = item['mimeType']
        modified_time = item.get('modifiedTime', '')
        
        # Check if we have already extracted this exact version of the file
        if file_id in state and state[file_id] == modified_time:
            continue
            
        print(f"Processing new/updated file: {file_name} ({mime_type})...")
        files_processed += 1
        
        try:
            content = ""
            # Google Docs
            if mime_type == 'application/vnd.google-apps.document':
                request = service.files().export_media(fileId=file_id, mimeType='text/plain')
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                content = fh.getvalue().decode('utf-8')
                
            # Google Sheets
            elif mime_type == 'application/vnd.google-apps.spreadsheet':
                request = service.files().export_media(fileId=file_id, mimeType='text/csv')
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                content = fh.getvalue().decode('utf-8')
                
            # Plain Text
            elif mime_type == 'text/plain':
                request = service.files().get_media(fileId=file_id)
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                content = fh.getvalue().decode('utf-8')
                
            # PDFs
            elif mime_type == 'application/pdf':
                request = service.files().get_media(fileId=file_id)
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                fh.seek(0)
                content = extract_pdf_text(fh)
            else:
                print(f"Skipping unsupported MIME type: {mime_type} for file {file_name}")
                continue
                
            # Append only the new file to the new_context string
            new_context += f"--- START OF NEW/UPDATED DOCUMENT: {file_name} ---\n{content}\n--- END OF DOCUMENT ---\n\n"
            updated_state[file_id] = modified_time
        except Exception as e:
            print(f"Failed to process {file_name}: {e}")
            
    # If no files were updated or added, we stop here entirely and skip OpenAI!
    if files_processed == 0:
        print("No new or updated files found in Google Drive. Knowledge base is already up to date!")
        if os.path.exists(CONTEXT_CACHE_FILE):
            with open(CONTEXT_CACHE_FILE, "r", encoding="utf-8") as f:
                return f.read()
        return ""
            
    print(f"Extracted {files_processed} new/updated files. Merging into existing Knowledge Base via OpenAI...")
    
    existing_kb = ""
    if os.path.exists(CONTEXT_CACHE_FILE):
        with open(CONTEXT_CACHE_FILE, "r", encoding="utf-8") as f:
            existing_kb = f.read()

    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        system_prompt = (
            "You are an expert data compiler maintaining a Knowledge Base. "
            "You will be provided with the EXISTING knowledge base (if any) and a set of NEW or UPDATED documents. "
            "Your job is to cleanly merge the new information into the existing knowledge base. "
            "If the new documents contain updated facts that conflict with the old ones, replace the old facts and prioritize the new ones. "
            "Remove any duplicate information, ensure the structure remains highly clean and concise, "
            "and do NOT lose any unique facts or meaningful data points. "
            "Return ONLY the completely updated knowledge base markdown text."
        )
        
        user_prompt = f"### EXISTING KNOWLEDGE BASE ###\n{existing_kb}\n\n### NEW/UPDATED DOCUMENTS ###\n{new_context}"
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1
        )
        final_context = response.choices[0].message.content
        print("Incremental Update successful!")
        
        # Save the new state so these files are ignored next time
        with open(STATE_FILE, "w") as f:
            json.dump(updated_state, f)
            
    except Exception as e:
        print(f"Failed to update context via OpenAI: {e}")
        # If OpenAI fails, simply append raw text without updating state JSON so it retries next time
        final_context = existing_kb + "\n\n" + new_context
        
    # Overwrite the cache with the new merged Knowledge Base
    with open(CONTEXT_CACHE_FILE, "w", encoding="utf-8") as f:
        f.write(final_context)
    
    print(f"Successfully wrote optimized summary to {CONTEXT_CACHE_FILE}")
    return final_context

if __name__ == '__main__':
    load_folder_contents()
