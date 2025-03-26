import re

def detect_multiple_conversations(email_text):
    """
    Detects if an email contains multiple conversations by checking for common reply indicators.
    """
    reply_patterns = [
        r"\nOn .* wrote:\n",  # Common format: "On [Date], [Person] wrote:"
        r"From: .*<.*@.*>",    # Email headers
        r"Sent: .*",           # Outlook-style replies
        r"Subject: .*",        # Email subject repetition in replies
    ]
    
    for pattern in reply_patterns:
        if re.search(pattern, email_text):
            return True  # Multiple conversations detected
    return False  # Single email

def extract_latest_email(email_text):
    """
    Extracts the most recent email from a thread by removing quoted text.
    """
    emails = re.split(r"\nOn .* wrote:\n", email_text)
    if emails:
        return emails[0].strip()  # The latest email (before any quoted text)
    return email_text.strip()  # Return as is if no split happens

def generate_prompt(email_text):
    """
    Generates the appropriate prompt based on whether it's a single email or multiple conversations.
    """
    if detect_multiple_conversations(email_text):
        latest_email = extract_latest_email(email_text)
        prompt = f"""
        You are an AI email analyzer for a bank. The provided email thread contains multiple conversations. 
        Extract details **only from the latest email** while ignoring quoted replies. 

        Your output should be a JSON object with the following keys:
        - **request_type**: General category (e.g., "Information Request", "Support Request").  
        - **sub_request_type**: Specific category (e.g., "Password Reset", "Order Status"). If not applicable, return "N/A".  
        - **key_attributes**: A list of key details (e.g., ["Order Number: 12345", "Account ID: ABC1234"]). If none, return an empty list.  
        - **main_intent**: A concise summary of why the latest email was written.  

        Latest Email:  
        ```{latest_email}```
        """
    else:
        prompt = f"""
        You are an AI email analyzer for a bank. Categorize the email and extract key details.

        Your output should be a JSON object with the following keys:
        - **request_type**: General category (e.g., "Information Request", "Support Request").  
        - **sub_request_type**: Specific category (e.g., "Password Reset", "Order Status"). If not applicable, return "N/A".  
        - **key_attributes**: A list of key details (e.g., ["Order Number: 12345", "Account ID: ABC1234"]). If none, return an empty list.  
        - **main_intent**: A concise summary of why the email was written.  

        Email:  
        ```{email_text}```
        """

    return prompt
