import os
import re
import streamlit as st
from dotenv import load_dotenv
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

# Load API Key from .env file
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# Initialize LangChain Chat Model
llm = ChatOpenAI(model="gpt-4o-mini", openai_api_key=api_key, temperature=0.3)

# Set Streamlit page config
st.set_page_config(page_title="📩 Email Analyzer", layout="wide")

# Define Request Types and Corresponding Sub-Request Types
request_type_options = {
    "Loan Servicing": ["Loan Facility Update", "Loan Account Status Inquiry", "Interest Rate Adjustment"],
    "Loan Origination": ["New Loan Request", "Loan Application Status", "Pre-qualification Inquiry"],
    "Credit & Risk Assessment": ["Credit Limit Increase", "Financial Statement Review", "Covenant Compliance"],
    "Information Request": ["Document Requirement", "Regulatory Compliance Inquiry", "General Inquiry"],
}

# Define Key Attributes
key_attributes_options = [
    "Loan Reference", "Borrower Name", "Bank Name", "Deal Name", "Commitment Amount",
    "Interest Rate", "Payment Schedule", "Collateral Details", "Regulatory Compliance"
]

# Supported file types
allowed_file_types = ["txt", "eml", "msg", "pdf"]
max_file_size_mb = 10  # Max file size in MB

# Email Preprocessing Function
def preprocess_email(email_text):
    """Cleans up email text: removes extra whitespace, standardizes numbers/dates, and redacts sensitive info."""
    
    # Remove unnecessary line breaks and extra spaces
    email_text = re.sub(r"\n{2,}", "\n", email_text.strip())  
    email_text = re.sub(r"\s{2,}", " ", email_text)  

    # Standardize date formats (e.g., 32-Mar-2025 → 2025-03-32)
    email_text = re.sub(r"(\d{1,2})[-/]([A-Za-z]{3,})[-/](\d{4})", r"\3-\2-\1", email_text)

    # Standardize currency formatting (e.g., "$ 150000" → "$150,000")
    email_text = re.sub(r"\$\s?(\d{1,3})(\d{3})", r"$\1,\2", email_text)

    # Redact sensitive account numbers
    email_text = re.sub(r"(Account #:\s?)\d{6,}", r"\1[REDACTED]", email_text)

    # Redact email addresses
    email_text = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "[EMAIL REDACTED]", email_text)

    return email_text

# Streamlit UI
st.title("📩 Commercial Banking Email Analyzer")

st.subheader("1️⃣ Select Request Type(s)")
selected_request_types = st.multiselect("Choose Request Type(s)", list(request_type_options.keys()))

st.subheader("2️⃣ Select Sub-Request Type(s)")
all_sub_requests = []
for request_type in selected_request_types:
    all_sub_requests.extend(request_type_options[request_type])
selected_sub_request_types = st.multiselect("Choose Sub-Request Type(s)", list(set(all_sub_requests)))

st.subheader("3️⃣ Select Key Attributes")
selected_key_attributes = st.multiselect("Choose key attributes to extract", key_attributes_options)

st.subheader("4️⃣ Enter or Upload Email Content")
email_text = st.text_area("Paste email content here", height=200)

uploaded_file = st.file_uploader("Or upload a file (.txt, .eml, .msg, .pdf)", type=allowed_file_types)
if uploaded_file is not None:
    # Check file size
    if uploaded_file.size > max_file_size_mb * 1024 * 1024:
        st.error(f"File is too large! Maximum allowed size is {max_file_size_mb}MB.")
        uploaded_file = None
    else:
        # Read file content
        file_extension = uploaded_file.name.split(".")[-1].lower()
        if file_extension == "txt":
            email_text = uploaded_file.read().decode("utf-8")
        elif file_extension in ["eml", "msg", "pdf"]:
            email_text = f"[File uploaded: {uploaded_file.name}] (File parsing required)"

# Process email when the user clicks "Analyze Email"
if st.button("Analyze Email") and email_text.strip():
    with st.spinner("Preprocessing email..."):
        clean_email_text = preprocess_email(email_text)

    # Construct the final prompt
    request_types_str = ", ".join(selected_request_types)
    sub_request_types_str = ", ".join(selected_sub_request_types)
    key_attributes_str = ", ".join(selected_key_attributes)

    final_prompt = f"""You are an AI email analyzer for a commercial bank lending service team. Categorize the email and extract key details.  
Your output should be a JSON object with the following keys:

- **request_type**: One of {request_types_str}.  
- **sub_request_type**: One of {sub_request_types_str}.  
- **key_attributes**: Extract details based on: {key_attributes_str}. If none are found, return an empty list.  
- **main_intent**: A concise summary of why the email was written.  

Email content:
{clean_email_text}
"""

    st.subheader("📝 Final Input (Prompt)")
    st.text_area("This is the full input that would be sent to the API:", final_prompt, height=300)

    # # Commenting out actual API call
    response = llm([SystemMessage(content=final_prompt), HumanMessage(content="Analyze this email.")])
    result = response.content.strip()

    # # Display the final output
    st.subheader("📜 Final Output (Response)")
    st.text_area("This is the AI-generated categorization result:", result, height=300)
