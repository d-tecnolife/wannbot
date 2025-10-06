import email
import imaplib
import os

import dotenv

dotenv.load_dotenv()
M = imaplib.IMAP4_SSL(host="imap.gmail.com", port=993)
M.login(os.getenv("user"), os.getenv("pass"))
M.select()
typ, data = M.search(None, 'UNSEEN HEADER FROM "accounts.google.com"')
for i in data[0].split():
    typ, data = M.fetch(i, "(RFC822)")
    msg = email.message_from_bytes(data[0][1])
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain" and not part.is_multipart():
                print(part.get_payload(decode=True))
                break
M.close()
M.logout()
