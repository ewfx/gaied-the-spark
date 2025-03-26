import os
import re
import json
import streamlit as st
import numpy as np
from dotenv import load_dotenv
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

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
    email_text = re.sub(r"(\d{1,2})[-/]([A-Za-z]{3,})[-/](\d{4})", r"\3-\2-\1", email_text)
    email_text = re.sub(r"(Account #:\s?)\d{6,}", r"\1[REDACTED]", email_text)
    email_text = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "[EMAIL REDACTED]", email_text)
    return email_text

# Streamlit UI
st.title("📩 Commercial Banking Email Analyzer")
st.subheader("1️⃣ Enter or Upload Email Content")
email_text = st.text_area("Paste email content here", height=200)

uploaded_file = st.file_uploader("Or upload a file", type=["txt", "eml", "msg", "pdf"])
if uploaded_file is not None:
    email_text = uploaded_file.read().decode("utf-8")

# Process email when the user clicks "Analyze Email"
if st.button("Analyze Email") and email_text.strip():
    with st.spinner("Preprocessing email..."):
        clean_email_text = preprocess_email(email_text)

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

        # New Confidence Score Calculation
        def compute_confidence(response_json):
            W_Lexical = 0.25
            W_Attributes = 0.30
            W_Intent = 0.20
            W_Ambiguity = 0.25

            lexical_score = 1.0 if response_json["request_type"] != "Unknown" else 0.3
            key_attr_score = min(1.0, len(response_json["key_attributes"]) / 5)
            intent_score = 0.8 if response_json["main_intent"] else 0.4
            ambiguous_terms = ["maybe", "not sure", "possibly", "check", "update something"]
            ambiguity_penalty = 0.2 if any(term in response_json["main_intent"].lower() for term in ambiguous_terms) else 0.0

            confidence = (W_Lexical * lexical_score) + (W_Attributes * key_attr_score) + (W_Intent * intent_score) - (W_Ambiguity * ambiguity_penalty)
            return round(max(0.1, min(1.0, confidence)), 2)

        response_json["confidence_score"] = compute_confidence(response_json)

        st.subheader("📜 Final Output (Response)")
        st.json(response_json)

        st.subheader("🔢 Confidence Score")
        st.metric(label="Confidence Score", value=f"{response_json['confidence_score']:.2f}")

    except json.JSONDecodeError:
        st.error("Error parsing AI response. AI did not return valid JSON.")
        st.text(f"Raw AI Response: {response_text}")
