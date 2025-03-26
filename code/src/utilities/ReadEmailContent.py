import os
import extract_msg  # For .msg file extraction
import email
import re
from email import policy
from email.parser import BytesParser
from pdfminer.high_level import extract_text  # For PDF extraction
from docx import Document  # For DOCX extraction
import win32com.client  # For reading .doc files on Windows
from PIL import Image  # For image processing
import pytesseract  # For OCR (extracting text from images)

# Get the directory of the currently running Python script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Check if "Input" folder exists in the same directory
input_folder = os.path.join(script_dir, "Input")

# Define the input folder
SHARED_FOLDER = input_folder

# Define a dedicated folder for attachments
ATTACHMENTS_FOLDER = os.path.join(SHARED_FOLDER, "Attachments")
os.makedirs(ATTACHMENTS_FOLDER, exist_ok=True)  # Ensure the folder exists

# Function to read attachment content
def read_attachment_content(file_path):
    try:
        file_extension = os.path.splitext(file_path)[1].lower()

        if file_extension == ".txt":
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read().strip()

        elif file_extension == ".pdf":
            return extract_text(file_path).strip()

        elif file_extension == ".docx":
            doc = Document(file_path)
            return "\n".join([para.text for para in doc.paragraphs]).strip()

        elif file_extension == ".doc":  # Support for older .doc files
            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False  # Run in background
            doc = word.Documents.Open(file_path)
            text = doc.Content.Text.strip()
            doc.Close(False)
            word.Quit()
            return text

        elif file_extension in [".jpg", ".jpeg", ".png"]:  # Extract text from images using OCR
            img = Image.open(file_path)
            return pytesseract.image_to_string(img).strip()

        elif file_extension in [".eml", ".msg"]:  # Process attached email files recursively
            return extract_email_content(file_path)

        else:
            return f"Unsupported file type: {file_extension}"

    except Exception as e:
        return f"Error reading file: {str(e)}"

# Function to extract emails from .msg and .eml files
def extract_email_content(file_path):
    email_content = []
    email_pattern = r"<([^>]+)>"

    if file_path.endswith(".eml"):
        with open(file_path, "rb") as f:
            eml_msg = BytesParser(policy=policy.default).parse(f)

        subject = eml_msg.get("subject", "No Subject")
        sender = eml_msg.get("from", "Unknown Sender")
        sender_name = sender.split("<")[0].strip() if "<" in sender else sender
        email_from_match = re.search(email_pattern, sender)
        email_from = email_from_match.group(1) if email_from_match else sender

        email_body = eml_msg.get_body(preferencelist=("plain", "html"))
        email_body = email_body.get_content().strip() if email_body else "No Content"
        if isinstance(email_body, bytes):
            email_body = email_body.decode("utf-8", errors="ignore").strip()

        # Ensure Attachments folder exists
        os.makedirs(ATTACHMENTS_FOLDER, exist_ok=True)

        # Extract and save attachments, including nested .eml, .msg, and image files
        attachment_contents = ["Attachment Content:"]
        for part in eml_msg.iter_parts():
            filename = part.get_filename()
            content_type = part.get_content_type()

            if filename:
                att_path = os.path.join(ATTACHMENTS_FOLDER, filename)
                try:
                    with open(att_path, "wb") as f:
                        data = part.get_payload(decode=True)
                        if data:
                            f.write(data)
                    
                    print(f"Successfully saved: {att_path}")  # Debugging output
                    
                    # Process nested .eml, .msg, and image files
                    if filename.endswith(".eml") or filename.endswith(".msg") or content_type == "message/rfc822":
                        eml_attachment_content = extract_email_content(att_path)
                        attachment_contents.append(f"Filename: {filename}\nContent:\n{eml_attachment_content}")
                    elif filename.endswith(".jpg") or filename.endswith(".jpeg") or filename.endswith(".png"):
                        content = read_attachment_content(att_path)
                        attachment_contents.append(f"Filename: {filename}\nContent:\n{content}")
                    else:
                        content = read_attachment_content(att_path)
                        attachment_contents.append(f"Filename: {filename}\nContent:\n{content}")
                except Exception as e:
                    print(f"Error saving {filename}: {str(e)}")  # Debugging output
                    attachment_contents.append(f"Error saving {filename}: {str(e)}")

        if not attachment_contents:
            attachment_contents.append("No Attachments")

        attachment_text = "\n".join(attachment_contents)

        # Format the extracted email content with comma separators
        email_content.append(f"Subject: {subject}, Sender: {sender_name}, EmailFrom: {email_from}, EmailBody: {email_body}, {attachment_text}")

    return "\n".join(email_content)

# Function to process emails in the shared folder
def extract_msg_files():
    email_strings = []
    for filename in os.listdir(SHARED_FOLDER):
        file_path = os.path.join(SHARED_FOLDER, filename)

        if filename.endswith(".msg") or filename.endswith(".eml"):
            email_content = extract_email_content(file_path)
            email_strings.append(email_content)

    return email_strings

# Extract and print email data
email_data = extract_msg_files()
for email in email_data:
    print(email)
    print("\n" + "=" * 80 + "\n")  # Separator for readability