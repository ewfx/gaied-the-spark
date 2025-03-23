import streamlit as st
import json
import re
from llama_cpp import Llama

# Path to the locally stored LLaMA 2 model
MODEL_PATH = "llama_model/llama-2-7b-chat.Q4_K_M.gguf"

# Load LLaMA 2 Model
llm = Llama(model_path=MODEL_PATH)

def categorize_email(email_text):
    """
    Uses LLaMA 2 (locally) to categorize an email and extract key details.
    """
    prompt = f"""
    You are an AI email analyzer for a bank. Categorize the email and extract key details.
    Your output should be a JSON object with the following keys:

    - **request_type**: General category (e.g., "Information Request", "Support Request").
    - **sub_request_type**: Specific category (e.g., "Password Reset", "Order Status"). If not applicable, return "N/A".
    - **key_attributes**: A list of key details (e.g., ["Order Number: 12345", "Account ID: ABC1234"]). If none, return an empty list.
    - **main_intent**: A concise summary of why the email was written.

    Email:
    ```{email_text}```

    Return JSON only, with no extra text before or after.
    """

    # Generate response
    response = llm(prompt, max_tokens=512)

    # Extract the text output
    response_text = response["choices"][0]["text"].strip()

    # Extract JSON using regex
    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)

    if json_match:
        try:
            result = json.loads(json_match.group(0))
            return json.dumps(result, indent=4)
        except json.JSONDecodeError:
            return json.dumps({"error": "Failed to parse JSON from the model response."}, indent=4)

    return json.dumps({"error": "No JSON response detected from the model."}, indent=4)

# Streamlit UI
st.title("Email Categorization using LLaMA 2")

# User input for email content
email_text = st.text_area("Enter email content for analysis:")

if st.button("Analyze Email"):
    if email_text.strip():
        with st.spinner("Processing..."):
            categorized_output = categorize_email(email_text)
        st.subheader("Categorized Output")
        st.json(json.loads(categorized_output))
    else:
        st.warning("Please enter email content before analyzing.")
