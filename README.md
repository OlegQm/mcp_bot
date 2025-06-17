# Tehotna Ukrajinka: AI Assistant with Flexible Backends

Tehotna Ukrajinka is a versatile AI assistant demonstrating different integration patterns with external tools and databases, built upon the Model Context Protocol (MCP). It features a FastAPI backend, a Streamlit frontend, and utilizes ChromaDB for vector storage and MongoDB for structured data.

## ✨ Key Features

*   **Modular Architecture**: Choose between three distinct processing methods:
    *   **MCP Direct**: Leverages the core Model Context Protocol for direct tool interaction.
    *   **LangChain + MCP**: Integrates LangChain agents, which wrap MCP tools, for flexible agentic reasoning.
    *   **LangGraph + MCP**: Employs LangGraph to build stateful, multi-step workflows that directly call MCP tools.
*   **Conversational AI**: Powered by OpenAI's language models for natural and intelligent interactions.
*   **Tool-Augmented**: Connects with databases (ChromaDB for knowledge base, MongoDB for structured data) via MCP tools for dynamic data retrieval and management.
*   **Knowledge Base Management**: Easily upload text files and PDFs to extend the assistant's knowledge.

## 🚀 Getting Started

### 1. Prerequisites

Ensure you have the following installed:

*   [Docker](https://docs.docker.com/get-docker/)
*   [Docker Compose](https://docs.docker.com/compose/install/)
*   An [OpenAI API Key](https://platform.openai.com/account/api-keys)

### 2. Configuration

Create a `.env` file in the root directory of the project and add your OpenAI API key:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

**Replace `your_openai_api_key_here` with your actual OpenAI API key.**

### 3. Run the Application

Navigate to the project's root directory in your terminal and execute:

```bash
docker compose up -d --build
```

This command will build the Docker images (if not already built) and start all necessary services in detached mode.

### 4. Access the Assistant

Once the services are up, open your web browser:

*   **Chat Interface**: [http://localhost:8501](http://localhost:8501)
*   **Backend API Docs (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)

### 5. Using the Assistant

In the Streamlit interface, you can select your preferred **"Processing Method"** from the sidebar:

*   **MCP Direct**: For a straightforward demonstration of MCP.
*   **LangChain + MCP**: To see the agentic capabilities of LangChain orchestrating MCP tools.
*   **LangGraph + MCP**: To observe a structured, multi-step workflow interacting with MCP.

**Example Queries:**

*   "What is MCP?"
*   "Tell me about Oleh Savchenko."
*   "List all users."
*   "How many products are in the database?"
*   "What is LangGraph?"

You can also use the sidebar to **upload files** (`.txt`, `.md`, `.csv`, `.pdf`) to enrich the ChromaDB knowledge base.

## 🛑 Troubleshooting & Maintenance

*   **Check Logs**: If a service isn't working, view its logs: `docker compose logs <service_name>` (e.g., `docker compose logs backend`).
*   **Container Status**: Verify all services are running: `docker compose ps`.
*   **API Key**: Confirm your `OPENAI_API_KEY` in `.env` is correct and valid.
*   **Rebuild & Clean**: To clear all volumes (database data) and rebuild everything from scratch:
    ```bash
    docker compose down -v
    docker compose up -d --build
    ```