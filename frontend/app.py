import streamlit as st
import requests
import json
import os
import PyPDF2
import io

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

st.set_page_config(
    page_title="Tehotna Ukrajinka: AI Assistant", 
    page_icon="🤖"
)

@st.cache_data
def get_processing_methods():
    try:
        response = requests.get(f"{BACKEND_URL}/methods")
        if response.status_code == 200:
            return response.json()["methods"]
    except:
        pass
    return [
        {"id": "langgraph", "name": "LangGraph + MCP", "description": "LangGraph with direct MCP"},
        {"id": "mcp", "name": "MCP Direct", "description": "Direct MCP client"},
        {"id": "langchain", "name": "LangChain + MCP", "description": "LangChain with MCP tools"},
    ]

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
    st.title("⚙️ Configuration")
    
    st.subheader("🔧 Processing Method")
    methods = get_processing_methods()
    method_options = {method["name"]: method["id"] for method in methods}
    
    selected_method_name = st.selectbox(
        "Choose processing method:",
        options=list(method_options.keys()),
        help="Select how queries should be processed"
    )
    selected_method = method_options[selected_method_name]
    
    method_info = next(m for m in methods if m["id"] == selected_method)
    st.info(f"📝 {method_info['description']}")
    
    mcp_integration = method_info.get("mcp_integration", "unknown")
    if mcp_integration == "native":
        st.success("🔗 Native MCP implementation")
    elif mcp_integration == "direct":
        st.success("🔗 Direct MCP integration")
    elif mcp_integration == "indirect":
        st.warning("🔧 MCP through LangChain wrappers")
    
    st.divider()
    
    st.subheader("📚 Knowledge Base")
    uploaded_file = st.file_uploader(
        "Upload document", 
        type=["txt", "csv", "md", "pdf"]
    )
    
    if uploaded_file is not None:
        doc_type = st.selectbox(
            "Document Type", 
            ["article", "manual", "report", "reference"]
        )
        doc_topic = st.text_input("Topic", "")
        
        with st.expander("📄 Preview"):
            if uploaded_file.type == "application/pdf":
                extracted_text = extract_text_from_pdf(uploaded_file)
                if extracted_text:
                    st.text_area("Content", extracted_text[:500] + "...", height=150)
            else:
                content = uploaded_file.getvalue().decode("utf-8")
                st.text_area("Content", content[:500] + "...", height=150)
                
        if st.button("📤 Upload"):
            if uploaded_file.size > 0:
                if uploaded_file.type == "application/pdf":
                    content = extract_text_from_pdf(uploaded_file)
                    if not content:
                        st.error("Failed to extract PDF text")
                        st.stop()
                else:
                    content = uploaded_file.getvalue().decode("utf-8")
                    
                metadata = {
                    "type": doc_type,
                    "topic": doc_topic,
                    "filename": uploaded_file.name
                }
                
                with st.spinner("Uploading..."):
                    try:
                        response = requests.post(
                            f"{BACKEND_URL}/upload_to_chromadb",
                            json={"document": content, "metadata": metadata}
                        )
                        if response.status_code == 200:
                            st.success("✅ Uploaded successfully!")
                        else:
                            st.error(f"❌ Upload failed: {response.text}")
                    except Exception as e:
                        st.error(f"🔌 Connection error: {str(e)}")
    
    if st.button("📊 Database Stats"):
        try:
            response = requests.get(f"{BACKEND_URL}/chromadb_stats")
            if response.status_code == 200:
                stats = response.json()
                st.metric("Documents", stats.get('count', 0))
                if stats.get('collections'):
                    st.write("Collections:", ", ".join(stats['collections']))
        except Exception as e:
            st.error(f"Error: {str(e)}")

st.title("🤖 Tehotna Ukrajinka")
st.caption(f"Current method: **{selected_method_name}**")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])
        
        if message["role"] == "assistant" and message.get("tool_calls"):
            with st.expander("🔧 Tool Usage"):
                for i, tool_call in enumerate(message["tool_calls"]):
                    st.write(f"**Tool {i+1}:**")
                    st.code(json.dumps(tool_call, indent=2), language="json")

query = st.chat_input("Ask me anything...")

if query:
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.write(query)
    
    with st.spinner("🤔 Thinking..."):
        try:
            response = requests.post(
                f"{BACKEND_URL}/query",
                json={"query": query, "processing_method": selected_method},
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            
            assistant_message = result.get("response", "Sorry, I couldn't process that.")
            tool_calls = result.get("tool_calls", [])
            method_used = result.get("method", "Unknown")
            
            message_data = {
                "role": "assistant", 
                "content": assistant_message,
                "tool_calls": tool_calls,
                "method": method_used
            }
            st.session_state.messages.append(message_data)
            
            with st.chat_message("assistant"):
                st.write(assistant_message)
                
                col1, col2 = st.columns([1, 1])
                with col1:
                    st.caption(f"Method: {method_used}")
                with col2:
                    if tool_calls:
                        st.caption(f"Tools used: {len(tool_calls)}")
                
                if tool_calls:
                    with st.expander("🔧 Tool Usage Details"):
                        for i, tool_call in enumerate(tool_calls):
                            st.write(f"**Tool {i+1}:**")
                            st.code(json.dumps(tool_call, indent=2), language="json")
                                
        except requests.RequestException as e:
            st.error(f"🚨 Error: {str(e)}")

with st.expander("ℹ️ Processing Methods Comparison"):
    st.write("""
    **MCP Direct**: Pure MCP implementation - fastest, most direct
    
    **LangGraph + MCP**: Structured workflow with state management and routing
    
    **LangChain + MCP**: Agent-based approach with tool orchestration
    """)
