import chromadb
import asyncio
from typing import Dict, Any
import uuid

class ChromaDBTool:
    def __init__(self, host: str = "localhost", port: int = 8000):
        self.host = host
        self.port = port
        self.client = None
        self.collection = None
        
    async def initialize(self):
        """Initialize the ChromaDB client and collection."""
        max_retries = 5
        for i in range(max_retries):
            try:
                self.client = chromadb.HttpClient(host=self.host, port=self.port)
                self.client.heartbeat()
                break
            except Exception as e:
                if i < max_retries - 1:
                    print(f"Failed to connect to ChromaDB, retrying in 5 seconds... ({e})")
                    await asyncio.sleep(5)
                else:
                    raise e
        
        try:
            self.collection = self.client.get_collection("knowledge_base")
        except:
            self.collection = self.client.create_collection("knowledge_base")
            
        if self.collection.count() == 0:
            await self._add_sample_data()
            
    async def close(self):
        """Close the ChromaDB connection."""
        pass
        
    async def _add_sample_data(self):
        """Add sample data to the ChromaDB collection."""
        documents = [
            "Tehotna Ukrajinka is an AI assistant built with MCP (Model Context Protocol).",
            "MCP allows AI assistants to use tools to perform actions.",
            "ChromaDB is a vector database used for semantic search.",
            "MongoDB is a NoSQL database used for storing structured data.",
            "FastAPI is a modern web framework for building APIs with Python.",
            "Streamlit is a framework for building data applications quickly.",
            "Docker Compose is a tool for defining and running multi-container Docker applications.",
            "The Model Context Protocol (MCP) is a framework that enables AI models to use tools.",
            "Vector databases store data as high-dimensional vectors for semantic similarity search.",
            "NoSQL databases provide flexible schema design for storing unstructured data.",
            "LangChain is a framework for developing applications powered by language models.",
            "LangGraph is a library for building stateful, multi-actor applications with LLMs.",
            "Oleh Savchenko is a software developer who works with AI and machine learning technologies.",
            "Python is a popular programming language used for AI, web development, and data science.",
            "OpenAI provides powerful language models like GPT-4 for various applications."
        ]
        
        metadata = [
            {"type": "definition", "topic": "ava"},
            {"type": "definition", "topic": "mcp"},
            {"type": "definition", "topic": "chromadb"},
            {"type": "definition", "topic": "mongodb"},
            {"type": "definition", "topic": "fastapi"},
            {"type": "definition", "topic": "streamlit"},
            {"type": "definition", "topic": "docker"},
            {"type": "definition", "topic": "mcp"},
            {"type": "definition", "topic": "vector_databases"},
            {"type": "definition", "topic": "nosql"},
            {"type": "definition", "topic": "langchain"},
            {"type": "definition", "topic": "langgraph"},
            {"type": "person", "topic": "developer"},
            {"type": "definition", "topic": "programming"},
            {"type": "definition", "topic": "ai"}
        ]
        
        ids = [f"doc_{i}" for i in range(len(documents))]
        
        self.collection.add(
            documents=documents,
            metadatas=metadata,
            ids=ids
        )
        
    def get_tool_config(self) -> Dict[str, Any]:
        """Get the tool configuration for OpenAI API."""
        return {
            "type": "function",
            "function": {
                "name": "chromadb",
                "description": "Search for information or manage data in the ChromaDB vector database",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "operation": {
                            "type": "string",
                            "enum": ["query", "add", "delete", "stats"],
                            "description": "The operation to perform (query, add, delete, or get stats)"
                        },
                        "query": {
                            "type": "string",
                            "description": "The query to search for in the database (for query operation)"
                        },
                        "n_results": {
                            "type": "integer",
                            "description": "Number of results to return (for query operation)",
                            "default": 3
                        },
                        "filter": {
                            "type": "object",
                            "description": "Optional filter to apply to the search (for query operation)"
                        },
                        "document": {
                            "type": "string",
                            "description": "Document text to add to the database (for add operation)"
                        },
                        "metadata": {
                            "type": "object",
                            "description": "Metadata for the document (for add operation)"
                        },
                        "id": {
                            "type": "string",
                            "description": "ID of the document (for delete operation)"
                        }
                    },
                    "required": ["operation"]
                }
            }
        }

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation on ChromaDB."""
        operation = args.get("operation")
        
        if not operation:
            return {"error": "Operation is required"}
            
        try:
            if operation == "query":
                return await self._execute_query(args)
            elif operation == "add":
                return await self._execute_add(args)
            elif operation == "delete":
                return await self._execute_delete(args)
            elif operation == "stats":
                return await self._execute_stats()
            else:
                return {"error": f"Unknown operation '{operation}'"}
        except Exception as e:
            return {"error": f"Failed to execute {operation}: {str(e)}"}

    async def _execute_query(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a query operation."""
        query = args.get("query")
        n_results = args.get("n_results", 3)
        filter_dict = args.get("filter")
        
        if not query:
            return {"error": "Query is required for query operation"}

        try:
            query_args = {
                "query_texts": [query],
                "n_results": n_results
            }
            
            if filter_dict and len(filter_dict) > 0:
                query_args["where"] = filter_dict
            
            print(f"ChromaDB query args: {query_args}")
            
            results = self.collection.query(**query_args)
            
            print(f"ChromaDB raw results: {results}")

            return {
                "documents": results.get("documents", [[]])[0],
                "metadatas": results.get("metadatas", [[]])[0],
                "distances": results.get("distances", [[]])[0],
                "ids": results.get("ids", [[]])[0]
            }
            
        except Exception as e:
            print(f"ChromaDB query error: {str(e)}")
            return {"error": f"Query failed: {str(e)}"}

    async def _execute_add(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an add operation."""
        document = args.get("document")
        metadata = args.get("metadata", {})

        if not document:
            return {"error": "Document is required for add operation"}

        try:
            doc_id = str(uuid.uuid4())
            self.collection.add(
                documents=[document],
                metadatas=[metadata],
                ids=[doc_id]
            )
            
            return {"id": doc_id, "status": "added"}
        except Exception as e:
            return {"error": f"Failed to add document: {str(e)}"}
    
    async def _execute_delete(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a delete operation."""
        doc_id = args.get("id")
        
        if not doc_id:
            return {"error": "ID is required for delete operation"}
        
        try:
            self.collection.delete(ids=[doc_id])
            return {"id": doc_id, "status": "deleted"}
        except Exception as e:
            return {"error": f"Failed to delete document: {str(e)}"}
    
    async def _execute_stats(self) -> Dict[str, Any]:
        """Get statistics about the ChromaDB database."""
        try:
            count = self.collection.count()
            collections = [c.name for c in self.client.list_collections()]
            
            return {
                "count": count,
                "collections": collections
            }
        except Exception as e:
            return {"error": f"Failed to get stats: {str(e)}"}
