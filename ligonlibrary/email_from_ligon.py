import base64
from email.message import EmailMessage
from email.mime.text import MIMEText
from google_auth_oauthlib.flow import InstalledAppFlow
from requests import HTTPError
from googleapiclient.discovery import build

def is_html(s):
    return bool(s) and s.lstrip().startswith('<')

def email_from_ligon(emails,from_email='ligon@berkeley.edu'):
    """Create and send email from ligon@berkeley.edu.

       - emails : A dictionary with keys which are "to" email addresses, and
                  values which are the (subject,body) of the email message.
    """
    SCOPES = [
        "https://www.googleapis.com/auth/gmail.send"
    ]
    flow = InstalledAppFlow.from_client_secrets_file('./.credentials/email_secret.json', SCOPES)
    creds = flow.run_local_server(port=0)

    try:
        # create gmail api client
        service = build("gmail", "v1", credentials=creds)

        for to,body in emails.items():
            if is_html(body[1]):
                message = MIMEText(body[1], 'html')
            else:
                message = MIMEText(body[1], 'plain')

            message['Subject'] = body[0]
            message['From'] = from_email
            message['To'] = to
            #message['Cc'] = 'eep153@ligon.org'

            create_message = {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}

            msg = (service.users().messages().send(userId="me", body=create_message).execute())
            print(f"Sent message to {message['To']} Message Id: {msg['id']}.")
    except HTTPError as error:
        print(F'An error occurred: {error}')

