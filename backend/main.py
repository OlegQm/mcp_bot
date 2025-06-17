from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

from mcp.client import MCPClient
from langchain_integration.agent import TehotnaUkrajinkaAgent
from langchain_integration.mcp_graph import TehotnaUkrajinkaMCPGraph

load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY environment variable is not set")

class QueryRequest(BaseModel):
    query: str
    processing_method: str = "langchain"

class ToolCall(BaseModel):
    name: str
    args: Dict[str, Any]

class UploadDocumentRequest(BaseModel):
    document: str
    metadata: Dict[str, Any]

mcp_client = None
langchain_agent = None
langgraph_workflow = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global mcp_client, langchain_agent, langgraph_workflow
    
    mcp_client = MCPClient()
    await mcp_client.initialize()
    
    langchain_agent = TehotnaUkrajinkaAgent()
    await langchain_agent.initialize()
    
    langgraph_workflow = TehotnaUkrajinkaMCPGraph()
    await langgraph_workflow.initialize()
    
    yield
    
    await mcp_client.close()
    await langchain_agent.close()
    await langgraph_workflow.close()

app = FastAPI(
    title="Tehotna Ukrajinka: MCP + LangChain + LangGraph",
    description="AI Assistant with three processing methods",
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
    """Process a user query using different methods."""
    try:
        if request.processing_method == "mcp":
            result = await mcp_client.process_query(request.query)
            return {
                "response": result["response"],
                "tool_calls": result.get("tool_calls", []),
                "method": "MCP Direct"
            }
        elif request.processing_method == "langgraph":
            result = await langgraph_workflow.process_query(request.query)
            return {
                "response": result["response"],
                "tool_calls": result["mcp_tool_calls"],
                "method": "LangGraph + MCP"
            }
        else:
            result = await langchain_agent.process_query(request.query)
            return {
                "response": result["response"],
                "tool_calls": result.get("intermediate_steps", []),
                "method": "LangChain + MCP"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/methods")
async def get_processing_methods():
    """Get available processing methods."""
    return {
        "methods": [
            {
                "id": "langchain",
                "name": "LangChain + MCP",
                "description": "LangChain agent with MCP tool wrappers",
                "mcp_integration": "indirect"
            },
            {
                "id": "langgraph",
                "name": "LangGraph + MCP", 
                "description": "LangGraph workflow with direct MCP integration",
                "mcp_integration": "direct"
            },
            {
                "id": "mcp",
                "name": "MCP Direct",
                "description": "Direct MCP client implementation",
                "mcp_integration": "native"
            }
        ]
    }

@app.get("/tools")
async def get_available_tools():
    """Get available tools from MCP."""
    try:
        mcp_tools = await mcp_client.get_available_tools()
        return {"tools": mcp_tools}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tool")
async def call_specific_tool(tool_call: ToolCall):
    """Call a specific MCP tool directly."""
    try:
        result = await mcp_client.call_tool(tool_call.name, tool_call.args)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/upload_to_chromadb")
async def upload_to_chromadb(request: UploadDocumentRequest):
    """Upload a document to ChromaDB."""
    try:
        result = await mcp_client.call_tool("chromadb", {
            "operation": "add",
            "document": request.document,
            "metadata": request.metadata
        })
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chromadb_stats")
async def get_chromadb_stats():
    """Get statistics about ChromaDB."""
    try:
        result = await mcp_client.call_tool("chromadb", {
            "operation": "stats"
        })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "integrations": ["MCP", "LangChain", "LangGraph"]
    }
