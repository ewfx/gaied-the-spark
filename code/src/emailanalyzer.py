import datetime
import os
import random
import re
import json
import string
import streamlit as st
import uuid  # For SR Number Generation
import pandas as pd
import io  # For handling CSV in-memory
from dotenv import load_dotenv
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
import ReadEmailContent  # External script for processing emails

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

# Generate SR Number
def generate_sr_number():
    date_part = datetime.datetime.now().strftime("%d%m%Y-%H%M")
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"SR-{date_part}-{random_part}"

# Improved Confidence Score Calculation
def compute_confidence(response_json):
    W_Lexical = 0.25
    W_Attributes = 0.30
    W_Intent = 0.20
    W_Ambiguity = 0.25

    lexical_score = 1.0 if response_json["request_type"] != "Unknown" else 0.5
    key_attr_score = min(1.0, len(response_json.get("key_attributes", [])) / 5)
    intent_score = 1.0 if response_json["main_intent"] else 0.6
    ambiguous_terms = ["maybe", "not sure", "possibly", "check", "update something"]
    ambiguity_penalty = 0.1 if any(term in response_json["main_intent"].lower() for term in ambiguous_terms) else 0.0

    confidence = (W_Lexical * lexical_score) + (W_Attributes * key_attr_score) + (W_Intent * intent_score) - (W_Ambiguity * ambiguity_penalty)
    return round(max(0.5, min(1.0, confidence)), 2)  # Ensure a reasonable minimum score

# Analyze Email Function
def AnalyzeEmail(email_text):
    if email_text.strip():  
        with st.spinner("Preprocessing email..."):
            clean_email_text = preprocess_email(email_text)

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

            # Compute confidence score
            response_json["confidence_score"] = compute_confidence(response_json)
            response_json["sr_number"] = sr_number

            # Display results
            st.subheader("📜 Final Output (Response)")
            st.json(response_json)

            st.subheader("🔢 Confidence Score")
            st.metric(label="Confidence Score", value=f"{response_json['confidence_score']:.2f}")

            st.subheader("📌 SR Number")
            st.write(f"**{response_json['sr_number']}**")

            # Convert JSON to DataFrame for CSV export
            df = pd.DataFrame([{
                "SR Number": response_json["sr_number"],
                "Request Type": response_json.get("request_type", ""),
                "Sub Request Type": response_json.get("sub_request_type", ""),
                "Key Attributes": ", ".join(response_json.get("key_attributes", [])),
                "Main Intent": response_json.get("main_intent", ""),
                "Confidence Score": response_json["confidence_score"],
                "Confidence Explanation": response_json.get("confidence_explanation", ""),
            }])

            # Convert DataFrame to CSV format
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            csv_data = csv_buffer.getvalue()

            # Add download buttons
            st.download_button(label="📥 Download JSON", data=json.dumps(response_json, indent=4), file_name=f"email_analysis_{sr_number}.json", mime="application/json")
            st.download_button(label="📥 Download CSV", data=csv_data, file_name=f"email_analysis_{sr_number}.csv", mime="text/csv")

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
if uploaded_files:
    for uploaded_file in uploaded_files:
        file_extension = uploaded_file.name.split(".")[-1].lower()
        file_path = os.path.join(INPUT_FOLDER, uploaded_file.name)

        # Save uploaded file
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

    st.success(f"✅ {len(uploaded_files)} file(s) saved in '{INPUT_FOLDER}' folder.")

# Loop through files
st.subheader("📂 Processing Stored Files")
for file_name in os.listdir(INPUT_FOLDER):
    file_path = os.path.join(INPUT_FOLDER, file_name)
    file_extension = file_name.split(".")[-1].lower()

    st.write(f"🔍 Processing: `{file_name}`")

    try:
        if file_extension == "txt":
            with open(file_path, "r", encoding="utf-8") as f:
                email_text = f.read()
        elif file_extension in ["eml", "msg"]:
            email_text = ReadEmailContent.extract_email_content(file_path)  
        else:
            email_text = "⚠️ Unsupported file format. Please use TXT, EML, or MSG."

        st.text_area(f"📄 Content of `{file_name}`", email_text, height=200)

    except Exception as e:
        st.error(f"❌ Error processing `{file_name}`: {str(e)}")

# Run analysis when button is clicked
if st.button("Analyze Email"):
    AnalyzeEmail(email_text)
