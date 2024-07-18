import base64
import json
import os

import msal
import requests
from dotenv import load_dotenv


# WILL NOT WORK -- .env FILE REMOVED FOR SECURITY
# MSAL CREDENTIALS MOVED TO AWS PARAMETER STORE (SSM)


load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
TENANT_ID = os.getenv("TENANT_ID")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://graph.microsoft.com/.default"]
BASE_URL = "https://graph.microsoft.com/v1.0"

app = msal.ConfidentialClientApplication(
    client_id=CLIENT_ID,
    authority=AUTHORITY,
    client_credential=CLIENT_SECRET
)

access_token_response = app.acquire_token_for_client(scopes=SCOPE)
access_token = access_token_response["access_token"]

sender = "yhavin@beitel.com"
to_recipient = "yhavin@beitel.com"
cc_recipient = "yhavin@beitel.com"
subject = "Test automated email"
content = "This email was sent via Microsoft Graph API."

filename = "23P_3187 ARKANSAS MULTI LLC 1 BEITEL, BINYAMIN.PDF"
with open(f"Samples/{filename}", "rb") as pdf:
    pdf_bytes = base64.b64encode(pdf.read()).decode()

email_message = {
    "message": {
        "subject": subject,
        "body": {
            "contentType": "Text",
            "content": content
        },
        "toRecipients": [
            {
                "emailAddress": {
                    "address": to_recipient
                }
            }
        ],
        "ccRecipients": [
            {
                "emailAddress": {
                    "address": cc_recipient
                }
            }
        ],
        "attachments": [
            {
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": filename,
                "contentType": "application/pdf",
                "contentBytes": pdf_bytes
            }
        ]
    }
}

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {access_token}"
}

api_url = f"{BASE_URL}/users/{sender}/sendMail"

response = requests.post(url=api_url, headers=headers, data=json.dumps(email_message))

print(response)