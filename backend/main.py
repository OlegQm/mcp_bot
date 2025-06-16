from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

from mcp.client import MCPClient

load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY environment variable is not set")

class QueryRequest(BaseModel):
    query: str

class ToolCall(BaseModel):
    name: str
    args: Dict[str, Any]

class UploadDocumentRequest(BaseModel):
    document: str
    metadata: Dict[str, Any]

mcp_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global mcp_client
    mcp_client = MCPClient()
    await mcp_client.initialize()
    yield
    await mcp_client.close()

app = FastAPI(
    title="Tehotna Ukrajinka MCP Backend",
    description="Backend for Tehotna Ukrajinka MCP Assistant",
    root_path="/",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/query")
async def process_query(request: QueryRequest):
    """
    Process a user query and return a response using MCP.
    """
    try:
        result = await mcp_client.process_query(request.query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tools")
async def get_available_tools():
    """
    Get a list of available MCP tools.
    """
    try:
        tools = await mcp_client.get_available_tools()
        return {"tools": tools}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tool")
async def call_specific_tool(tool_call: ToolCall):
    """
    Call a specific MCP tool directly.
    """
    try:
        result = await mcp_client.call_tool(tool_call.name, tool_call.args)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/upload_to_chromadb")
async def upload_to_chromadb(request: UploadDocumentRequest):
    """
    Upload a document to ChromaDB.
    """
    try:
        result = await mcp_client.call_tool("chromadb", {
            "operation": "add",
            "document": request.document,
            "metadata": request.metadata
        })
        return {"success": True, "id": result.get("id")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chromadb_stats")
async def get_chromadb_stats():
    """
    Get statistics about the ChromaDB database.
    """
    try:
        result = await mcp_client.call_tool("chromadb", {
            "operation": "stats"
        })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
