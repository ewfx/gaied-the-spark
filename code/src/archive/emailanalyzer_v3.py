import datetime
import os
import random
import re
import json
import string
import streamlit as st
import uuid  # For SR Number Generation
from dotenv import load_dotenv
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
import ReadEmailContent

# Load API Key from .env file
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# Load Configuration File
with open("config.json", "r") as config_file:
    config = json.load(config_file)

# Extract predefined request types and key attributes
request_type_options = config["request_types"]
key_attributes_options = config["key_attributes"]

# Initialize LangChain Chat Model
llm = ChatOpenAI(model="gpt-4o-mini", openai_api_key=api_key, temperature=0.3)

# Set Streamlit page config
st.set_page_config(page_title="📩 Email Analyzer", layout="wide")

# Email Preprocessing Function
def preprocess_email(email_text):
    email_text = re.sub(r"\n{2,}", "\n", email_text.strip())  
    email_text = re.sub(r"\s{2,}", " ", email_text)  
    return email_text

# Function to check if an existing SR number is in the email
def check_existing_sr_number(email_text):
    sr_match = re.search(r"\bSR-\d{8}-\d{4}-[A-Z0-9]{6}\b", email_text, re.IGNORECASE)  
    return sr_match.group(0) if sr_match else None

# Generate SR Number in DDMMYYYY-XXXXXX format
def generate_sr_number():
    date_part = datetime.datetime.now().strftime("%d%m%Y-%H%M")
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"SR-{date_part}-{random_part}"

def AnalyzeEmail(email_text):
    if email_text.strip():  # Ensure input is not empty
        with st.spinner("Preprocessing email..."):
            clean_email_text = preprocess_email(email_text)

        # Check for existing SR number
        existing_sr_number = check_existing_sr_number(clean_email_text)
        sr_number = f"Duplicate/Follow-up - {existing_sr_number}" if existing_sr_number else generate_sr_number()

        final_prompt = f"""
        You are an AI email analyzer for a commercial bank lending service team. Categorize the email and extract key details.
        Return a **valid JSON** with:
        - `request_type`
        - `sub_request_type`
        - `key_attributes`
        - `main_intent`
        - `confidence_score`
        - `confidence_explanation`
        {clean_email_text}
        """

        response = llm([SystemMessage(content=final_prompt), HumanMessage(content="Analyze this email.")])
        try:
            response_text = response.content.strip()
            json_match = re.search(r"```json\n(.*?)\n```", response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(1)
            response_json = json.loads(response_text)

            # Confidence Score Calculation
            def compute_confidence(response_json):
                W_Lexical, W_Attributes, W_Intent, W_Ambiguity = 0.25, 0.30, 0.20, 0.25
                lexical_score = 1.0 if response_json["request_type"] != "Unknown" else 0.3
                key_attr_score = min(1.0, len(response_json["key_attributes"]) / 5)
                intent_score = 0.8 if response_json["main_intent"] else 0.4
                ambiguous_terms = ["maybe", "not sure", "possibly", "check", "update something"]
                ambiguity_penalty = 0.2 if any(term in response_json["main_intent"].lower() for term in ambiguous_terms) else 0.0

                confidence = (W_Lexical * lexical_score) + (W_Attributes * key_attr_score) + (W_Intent * intent_score) - (W_Ambiguity * ambiguity_penalty)
                return round(max(0.1, min(1.0, confidence)), 2)

            response_json["confidence_score"] = compute_confidence(response_json)
            response_json["sr_number"] = sr_number

            st.subheader("📜 Final Output (Response)")
            st.json(response_json)

            st.subheader("🔢 Confidence Score")
            st.metric(label="Confidence Score", value=f"{response_json['confidence_score']:.2f}")

            st.subheader("📌 SR Number")
            st.write(f"**{response_json['sr_number']}**")

        except json.JSONDecodeError:
            st.error("Error parsing AI response. AI did not return valid JSON.")
            st.text(f"Raw AI Response: {response_text}")

# Create input folder if not exists
INPUT_FOLDER = "input"
os.makedirs(INPUT_FOLDER, exist_ok=True)

st.title("📩 Commercial Banking Email Analyzer")
st.subheader("1️⃣ Enter or Upload Email Content")

# Text area for manual email input
email_text = st.text_area("Paste email content here", height=200)

# File uploader for email files
uploaded_files = st.file_uploader("Or upload files", type=["txt", "eml", "msg", "pdf"], accept_multiple_files=True)

# Process uploaded files
file_contents = []
if uploaded_files:
    for uploaded_file in uploaded_files:
        file_extension = uploaded_file.name.split(".")[-1].lower()
        file_path = os.path.join(INPUT_FOLDER, uploaded_file.name)

        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # Read content from uploaded file
        if file_extension == "txt":
            with open(file_path, "r", encoding="utf-8") as f:
                file_contents.append(f.read())
        elif file_extension in ["eml", "msg"]:
            file_contents.append(ReadEmailContent.extract_email_content(file_path))
        else:
            st.error(f"⚠️ Unsupported file format: {file_extension}")

    st.success(f"✅ {len(uploaded_files)} file(s) saved in '{INPUT_FOLDER}' folder.")

# Display and process emails only when "Analyze Email" is clicked
if st.button("Analyze Email"):
    if email_text.strip():
        st.subheader("📄 Analyzing Entered Email")
        AnalyzeEmail(email_text)
    elif file_contents:
        st.subheader("📂 Processing Uploaded Files")
        for idx, content in enumerate(file_contents):
            st.write(f"🔍 Processing File {idx + 1}")
            AnalyzeEmail(content)
    else:
        st.warning("⚠️ No email content provided. Please enter text or upload a file.")
