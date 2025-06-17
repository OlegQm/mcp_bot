from typing import Dict, Any, List, Optional
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor

from mcp.tools.chromadb_tool import ChromaDBTool
from mcp.tools.mongodb_tool import MongoDBTool


class ChromaDBSearchInput(BaseModel):
    query: str = Field(description="The search query")
    n_results: int = Field(default=3, description="Number of results to return")
    filter: Optional[Dict[str, Any]] = Field(default=None, description="Optional filter")


class ChromaDBAddInput(BaseModel):
    document: str = Field(description="Document text to add")
    metadata: Dict[str, Any] = Field(default={}, description="Document metadata")


class MongoDBQueryInput(BaseModel):
    operation: str = Field(description="MongoDB operation (find, find_one, count, etc.)")
    collection: str = Field(description="Collection name")
    filter: Dict[str, Any] = Field(default={}, description="Query filter")
    limit: int = Field(default=0, description="Limit results")
    sort: Dict[str, Any] = Field(default={}, description="Sort criteria")


class MongoDBModifyInput(BaseModel):
    operation: str = Field(description="MongoDB operation (insert, update, delete)")
    collection: str = Field(description="Collection name")
    filter: Dict[str, Any] = Field(default={}, description="Query filter")
    data: Dict[str, Any] = Field(default={}, description="Data for operation")


def run_async_in_thread(coro):
    """Run async function in a separate thread with its own event loop."""
    def run_in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    
    with ThreadPoolExecutor() as executor:
        future = executor.submit(run_in_thread)
        return future.result()


class ChromaDBSearchTool(BaseTool):
    name: str = "chromadb_search"
    description: str = "Search for information in the ChromaDB vector database. Use this when users ask questions that might be answered by stored documents or knowledge."
    args_schema: type = ChromaDBSearchInput
    chromadb_tool: ChromaDBTool = Field(exclude=True)
    
    def __init__(self, chromadb_tool: ChromaDBTool, **kwargs):
        super().__init__(chromadb_tool=chromadb_tool, **kwargs)
    
    def _run(self, query: str, n_results: int = 3, filter: Optional[Dict[str, Any]] = None) -> str:
        try:
            print(f"ChromaDB Search Tool called with query: {query}")
            print(f"Filter: {filter}")
            
            args = {
                "operation": "query",
                "query": query,
                "n_results": n_results
            }
            
            if filter and len(filter) > 0:
                args["filter"] = filter
            
            print(f"ChromaDB args: {args}")
            
            result = run_async_in_thread(self.chromadb_tool.execute(args))
            
            print(f"ChromaDB Search Result: {result}")
            
            if "error" in result:
                return json.dumps({"error": result["error"], "query": query})
            
            if result.get("documents") and len(result["documents"]) > 0:
                formatted_result = {
                    "found_documents": len(result["documents"]),
                    "documents": result["documents"],
                    "metadata": result.get("metadatas", []),
                    "relevance_scores": result.get("distances", [])
                }
                return json.dumps(formatted_result, indent=2)
            else:
                return json.dumps({
                    "message": "No documents found matching the query", 
                    "query": query,
                    "searched_database": "ChromaDB knowledge base"
                })
                
        except Exception as e:
            error_msg = f"Error searching ChromaDB: {str(e)}"
            print(f"ChromaDB Search Error: {error_msg}")
            return json.dumps({"error": error_msg, "query": query})
    
    async def _arun(self, query: str, n_results: int = 3, filter: Optional[Dict[str, Any]] = None) -> str:
        try:
            args = {
                "operation": "query",
                "query": query,
                "n_results": n_results
            }
            
            if filter and len(filter) > 0:
                args["filter"] = filter
            
            result = await self.chromadb_tool.execute(args)
            
            if "error" in result:
                return json.dumps({"error": result["error"], "query": query})
            
            if result.get("documents") and len(result["documents"]) > 0:
                formatted_result = {
                    "found_documents": len(result["documents"]),
                    "documents": result["documents"],
                    "metadata": result.get("metadatas", []),
                    "relevance_scores": result.get("distances", [])
                }
                return json.dumps(formatted_result, indent=2)
            else:
                return json.dumps({
                    "message": "No documents found matching the query", 
                    "query": query,
                    "searched_database": "ChromaDB knowledge base"
                })
                
        except Exception as e:
            return json.dumps({"error": f"Error searching ChromaDB: {str(e)}", "query": query})


class ChromaDBAddTool(BaseTool):
    name: str = "chromadb_add"
    description: str = "Add a document to the ChromaDB vector database"
    args_schema: type = ChromaDBAddInput
    chromadb_tool: ChromaDBTool = Field(exclude=True)
    
    def __init__(self, chromadb_tool: ChromaDBTool, **kwargs):
        super().__init__(chromadb_tool=chromadb_tool, **kwargs)
    
    def _run(self, document: str, metadata: Dict[str, Any] = {}) -> str:
        try:
            print(f"ChromaDB Add Tool called with document length: {len(document)}")
            
            result = run_async_in_thread(
                self.chromadb_tool.execute({
                    "operation": "add",
                    "document": document,
                    "metadata": metadata
                })
            )
            
            print(f"ChromaDB Add Result: {result}")
            return json.dumps(result, indent=2)
            
        except Exception as e:
            error_msg = f"Error adding to ChromaDB: {str(e)}"
            print(f"ChromaDB Add Error: {error_msg}")
            return json.dumps({"error": error_msg})
    
    async def _arun(self, document: str, metadata: Dict[str, Any] = {}) -> str:
        try:
            result = await self.chromadb_tool.execute({
                "operation": "add",
                "document": document,
                "metadata": metadata
            })
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": f"Error adding to ChromaDB: {str(e)}"})


class MongoDBQueryTool(BaseTool):
    name: str = "mongodb_query"
    description: str = "Query data from MongoDB database. Use this to find users, products, or get database statistics."
    args_schema: type = MongoDBQueryInput
    mongodb_tool: MongoDBTool = Field(exclude=True)
    
    def __init__(self, mongodb_tool: MongoDBTool, **kwargs):
        super().__init__(mongodb_tool=mongodb_tool, **kwargs)
    
    def _run(self, operation: str, collection: str, filter: Dict[str, Any] = {}, 
             limit: int = 0, sort: Dict[str, Any] = {}) -> str:
        try:
            print(f"MongoDB Query Tool called: {operation} on {collection}")
            print(f"Filter: {filter}, Limit: {limit}, Sort: {sort}")
            
            args = {
                "operation": operation,
                "collection": collection,
                "filter": filter
            }
            if limit > 0:
                args["limit"] = limit
            if sort and len(sort) > 0:
                args["sort"] = sort
            
            print(f"MongoDB args: {args}")
            
            result = run_async_in_thread(self.mongodb_tool.execute(args))
            
            print(f"MongoDB Query Result: {result}")
            
            if "error" in result:
                return json.dumps({"error": result["error"], "operation": operation, "collection": collection})
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            error_msg = f"Error querying MongoDB: {str(e)}"
            print(f"MongoDB Query Error: {error_msg}")
            return json.dumps({"error": error_msg, "operation": operation, "collection": collection})
    
    async def _arun(self, operation: str, collection: str, filter: Dict[str, Any] = {}, 
                    limit: int = 0, sort: Dict[str, Any] = {}) -> str:
        try:
            args = {
                "operation": operation,
                "collection": collection,
                "filter": filter
            }
            if limit > 0:
                args["limit"] = limit
            if sort and len(sort) > 0:
                args["sort"] = sort
                
            result = await self.mongodb_tool.execute(args)
            
            if "error" in result:
                return json.dumps({"error": result["error"], "operation": operation, "collection": collection})
            
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": f"Error querying MongoDB: {str(e)}", "operation": operation, "collection": collection})


class MongoDBModifyTool(BaseTool):
    name: str = "mongodb_modify"
    description: str = "Modify data in MongoDB database (insert, update, delete)"
    args_schema: type = MongoDBModifyInput
    mongodb_tool: MongoDBTool = Field(exclude=True)
    
    def __init__(self, mongodb_tool: MongoDBTool, **kwargs):
        super().__init__(mongodb_tool=mongodb_tool, **kwargs)
    
    def _run(self, operation: str, collection: str, filter: Dict[str, Any] = {}, 
             data: Dict[str, Any] = {}) -> str:
        try:
            print(f"MongoDB Modify Tool called: {operation} on {collection}")
            
            args = {
                "operation": operation,
                "collection": collection,
                "filter": filter,
                "data": data
            }
            
            result = run_async_in_thread(self.mongodb_tool.execute(args))
            
            print(f"MongoDB Modify Result: {result}")
            return json.dumps(result, indent=2)
            
        except Exception as e:
            error_msg = f"Error modifying MongoDB: {str(e)}"
            print(f"MongoDB Modify Error: {error_msg}")
            return json.dumps({"error": error_msg})
    
    async def _arun(self, operation: str, collection: str, filter: Dict[str, Any] = {}, 
                    data: Dict[str, Any] = {}) -> str:
        try:
            args = {
                "operation": operation,
                "collection": collection,
                "filter": filter,
                "data": data
            }
            result = await self.mongodb_tool.execute(args)
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": f"Error modifying MongoDB: {str(e)}"})


class LangChainMCPTools:
    def __init__(self, chromadb_tool: ChromaDBTool, mongodb_tool: MongoDBTool):
        self.chromadb_tool = chromadb_tool
        self.mongodb_tool = mongodb_tool
        
    def get_tools(self) -> List[BaseTool]:
        return [
            ChromaDBSearchTool(self.chromadb_tool),
            ChromaDBAddTool(self.chromadb_tool),
            MongoDBQueryTool(self.mongodb_tool),
            MongoDBModifyTool(self.mongodb_tool)
        ]
