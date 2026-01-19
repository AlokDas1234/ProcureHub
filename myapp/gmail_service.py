import os
import base64
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import hashlib
# Scopes for Gmail API
SCOPES = ['https://www.googleapis.com/auth/gmail.send']


def get_gmail_service():
    creds = None
    token_file = "D:\\Projects\\Django-projects\\websocket_\\myproject2\\myproject2\\myapp\\token.json"
    creds_file = "D:\\Projects\\Django-projects\\websocket_\\myproject2\\myproject2\\myapp\\credentials.json"

    # Load saved credentials
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    # If there are no valid credentials available, prompt login flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            from google_auth_oauthlib.flow import InstalledAppFlow
            flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for future use
        with open(token_file, 'w') as token:
            token.write(creds.to_json())

    # Create Gmail API service
    service = build('gmail', 'v1', credentials=creds)
    return service


def send_email(service, to_email, subject, body_text):
    message = MIMEMultipart()
    message['to'] = to_email
    message['subject'] = subject

    msg = MIMEText(body_text)
    message.attach(msg)

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    body = {'raw': raw}

    message = service.users().messages().send(userId="me", body=body).execute()
    return message


# Function to hash the password
def hash_password(password):
    # Hash the password using SHA-256
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    # Convert the hash to a format with # characters
    hashed_as_hashes = '#' * len(hashed_password)  # Replace with # characters
    return hashed_as_hashes


# def hash_password(password):
#     return hashlib.sha256(password.encode()).hexdigest()
# def generate_otp():
#     return ''.join(random.choices(string.digits, k=6))
