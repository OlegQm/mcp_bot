import streamlit as st
import requests
import json
import os
import PyPDF2
import io

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

st.set_page_config(page_title="Tehotna Ukrajinka: Your Smart Assistant", page_icon="🤖")

def extract_text_from_pdf(pdf_file):
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_file.getvalue()))
        text = ""
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text += page.extract_text() + "\n\n"
        return text
    except Exception as e:
        st.error(f"PDF processing error: {str(e)}")
        return None

with st.sidebar:
    st.title("Knowledge Base Management")
    st.subheader("Upload Data")
    uploaded_file = st.file_uploader("Choose a file", type=["txt", "csv", "md", "pdf"])
    if uploaded_file is not None:
        st.write("Document Metadata:")
        doc_type = st.selectbox("Document Type", ["article", "manual", "report", "reference"])
        doc_topic = st.text_input("Document Topic", "")
        with st.expander("Preview"):
            if uploaded_file.type == "application/pdf":
                extracted_text = extract_text_from_pdf(uploaded_file)
                if extracted_text:
                    st.text_area("PDF Content", extracted_text, height=200)
                else:
                    st.warning("Failed to extract text from PDF")
            else:
                content = uploaded_file.getvalue().decode("utf-8")
                st.text_area("File Content", content, height=200)
        if st.button("Upload to Knowledge Base"):
            if uploaded_file.size > 0:
                if uploaded_file.type == "application/pdf":
                    content = extract_text_from_pdf(uploaded_file)
                    if not content:
                        st.error("Failed to extract text from PDF.")
                        st.stop()
                else:
                    content = uploaded_file.getvalue().decode("utf-8")
                metadata = {
                    "type": doc_type,
                    "topic": doc_topic,
                    "filename": uploaded_file.name,
                    "file_type": uploaded_file.type
                }
                with st.spinner("Uploading to knowledge base..."):
                    try:
                        response = requests.post(
                            f"{BACKEND_URL}/upload_to_chromadb",
                            json={
                                "document": content,
                                "metadata": metadata
                            }
                        )
                        if response.status_code == 200:
                            st.success("Document successfully uploaded to the knowledge base!")
                        else:
                            st.error(f"Upload error: {response.text}")
                    except Exception as e:
                        st.error(f"Connection error: {str(e)}")
            else:
                st.warning("Uploaded file is empty.")
    if st.button("Show Knowledge Base Stats"):
        try:
            response = requests.get(f"{BACKEND_URL}/chromadb_stats")
            if response.status_code == 200:
                stats = response.json()
                st.write(f"Documents in database: {stats['count']}")
                if stats.get('collections'):
                    st.write("Collections:")
                    for collection in stats['collections']:
                        st.write(f"- {collection}")
            else:
                st.error("Failed to get statistics")
        except Exception as e:
            st.error(f"Connection error: {str(e)}")

st.title("Chat with Tehotna Ukrajinka! 🤖")
st.write("Ask me anything, and I'll use my knowledge base to help!")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

query = st.chat_input("What's on your mind?")

if query:
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.write(query)
    with st.spinner("Tehotna Ukrajinka is thinking..."):
        try:
            response = requests.post(f"{BACKEND_URL}/query", json={"query": query}, timeout=60)
            response.raise_for_status()
            result = response.json()
            assistant_message = result.get("response", "Sorry, I couldn't process that request.")
            st.session_state.messages.append({"role": "assistant", "content": assistant_message})
            with st.chat_message("assistant"):
                st.write(assistant_message)
                if "tool_calls" in result and result["tool_calls"]:
                    with st.expander("See how I found this information"):
                        for tool_call in result["tool_calls"]:
                            st.write(f"📊 Used {tool_call['name']} tool")
                            st.code(json.dumps(tool_call['args'], indent=2), language="json")
                            st.write("Result:")
                            st.code(json.dumps(tool_call['result'], indent=2), language="json")
        except requests.RequestException as e:
            st.error(f"Oops, something went wrong: {str(e)}")
