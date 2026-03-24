import os
import io
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import PyPDF2
from dotenv import load_dotenv

load_dotenv()

# We only need read-only access to Drive files
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
CONTEXT_CACHE_FILE = "context_cache.txt"

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
    
    # Query for all files in the designated folder
    query = f"'{FOLDER_ID}' in parents and trashed=false"
    results = service.files().list(q=query, fields="nextPageToken, files(id, name, mimeType)").execute()
    items = results.get('files', [])
    
    if not items:
        print("No files found in the specified folder.")
        return ""
    
    all_context = ""
    for item in items:
        file_id = item['id']
        file_name = item['name']
        mime_type = item['mimeType']
        
        print(f"Processing {file_name} ({mime_type})...")
        
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
                
            # Append to massive context string block
            all_context += f"--- START OF DOCUMENT: {file_name} ---\n{content}\n--- END OF DOCUMENT ---\n\n"
        except Exception as e:
            print(f"Failed to process {file_name}: {e}")
            
    # Write aggregated context to the local cache
    with open(CONTEXT_CACHE_FILE, "w", encoding="utf-8") as f:
        f.write(all_context)
    
    print(f"Successfully wrote all content to {CONTEXT_CACHE_FILE}")
    return all_context

if __name__ == '__main__':
    load_folder_contents()
