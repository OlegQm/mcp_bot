# Tehotna Ukrajinka MCP Assistant Demo

A powerful AI assistant utilizing the Model Context Protocol (MCP) to interact with external tools and databases. Built with FastAPI (backend), Streamlit (frontend), ChromaDB (vector database), and MongoDB (document database).

## ✨ Key Features

- **Conversational AI**: Powered by OpenAI's GPT-4.1 for natural interactions.
- **Tool Integration**: Uses MCP to connect with databases for dynamic actions.
- **Data Management**: Search and manage information in ChromaDB (vector) and MongoDB (document).
- **File Upload**: Supports text files and PDFs for updating the knowledge base.
- **Dockerized**: Easy deployment with Docker Compose.

## 🚀 Quick Start

### 1. Prerequisites

- Docker and Docker Compose installed.
- Your OpenAI API key.

### 2. Setup

Create a `.env` file in the root directory:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

**Replace `your_openai_api_key_here` with your actual OpenAI API key.**

### 3. Run the Application

Navigate to the project root directory in your terminal and run:

```bash
# Build and start all services in detached mode
docker compose up -d
```

### 4. Access Tehotna Ukrajinka

- **Chat Interface**: Open your browser to [http://localhost:8501](http://localhost:8501)
- **API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

## 💬 Usage Examples

- "What is MCP?"
- "Find all users in the database."
- "List electronic products in stock."
- "How many products do we have?"
- **Upload File**: Use the sidebar to upload `.txt`, `.md`, `.csv`, or `.pdf` files to the knowledge base.

## 🛑 Troubleshooting

- **Container Errors**: If services fail to start, check logs: `docker compose logs -f`
- **ChromaDB / MongoDB Connection**: Ensure these services are running (`docker compose ps`).
- **OpenAI API Key**: Double-check your `.env` file and API key validity.
- **Reset**: To clear all data and start fresh: `docker compose down -v && docker compose up -d`
