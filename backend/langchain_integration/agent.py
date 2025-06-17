import os
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.prompts import ChatPromptTemplate
from langchain.schema import BaseMessage

from .tools import LangChainMCPTools
from mcp.tools.chromadb_tool import ChromaDBTool
from mcp.tools.mongodb_tool import MongoDBTool


class TehotnaUkrajinkaAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4.1",
            temperature=0.3,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        self.chromadb_tool = None
        self.mongodb_tool = None
        self.tools = None
        self.agent_executor = None
        
    async def initialize(self):
        """Initialize the agent with MCP tools."""
        print("Initializing LangChain Agent...")
        
        # Initialize MCP tools
        self.chromadb_tool = ChromaDBTool(
            host=os.getenv("CHROMADB_HOST", "chromadb"),
            port=int(os.getenv("CHROMADB_PORT", "8000"))
        )
        
        self.mongodb_tool = MongoDBTool(
            uri=os.getenv("MONGODB_URI", "mongodb://mongodb:27017/")
        )
        
        await self.chromadb_tool.initialize()
        await self.mongodb_tool.initialize()
        
        # Create LangChain tools
        mcp_tools = LangChainMCPTools(self.chromadb_tool, self.mongodb_tool)
        self.tools = mcp_tools.get_tools()
        
        print(f"Available tools: {[tool.name for tool in self.tools]}")
        
        # Create agent prompt with better instructions
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are Tehotna Ukrajinka, a helpful AI assistant with access to a knowledge base and database.

IMPORTANT INSTRUCTIONS:
1. ALWAYS use the chromadb_search tool when users ask questions that might be answered by stored documents
2. ALWAYS use the mongodb_query tool when users ask about users, products, or database information
3. Be proactive in using tools - don't just answer from your training data
4. When searching, try different keywords if the first search doesn't return results

Available tools:
- chromadb_search: Search the knowledge base for information
- mongodb_query: Query the database for users, products, statistics
- chromadb_add: Add documents to the knowledge base
- mongodb_modify: Modify database records

Examples of when to use tools:
- "What is MCP?" → Use chromadb_search
- "Tell me about users" → Use mongodb_query with collection="users"
- "How many products are there?" → Use mongodb_query with operation="count", collection="products"
- "What is LangChain?" → Use chromadb_search

Always try to use the appropriate tool first, then provide a comprehensive answer based on the results.
"""),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}")
        ])
        
        agent = create_openai_tools_agent(self.llm, self.tools, prompt)
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=3,
            return_intermediate_steps=True
        )
        
        print("LangChain Agent initialized successfully!")
        
    async def close(self):
        """Close all tool connections."""
        if self.chromadb_tool:
            await self.chromadb_tool.close()
        if self.mongodb_tool:
            await self.mongodb_tool.close()
            
    async def process_query(self, query: str, chat_history: List[BaseMessage] = None) -> Dict[str, Any]:
        """Process a user query using the LangChain agent."""
        if not self.agent_executor:
            raise ValueError("Agent not initialized. Call initialize() first.")
            
        try:
            print(f"Processing query with LangChain Agent: {query}")
            
            result = await self.agent_executor.ainvoke({
                "input": query,
                "chat_history": chat_history or []
            })
            
            print(f"Agent result: {result}")
            
            return {
                "response": result["output"],
                "intermediate_steps": result.get("intermediate_steps", [])
            }
        except Exception as e:
            print(f"Agent error: {str(e)}")
            return {
                "response": f"I encountered an error while processing your request: {str(e)}",
                "error": str(e),
                "intermediate_steps": []
            }
    
    async def add_document(self, document: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Add a document to the knowledge base."""
        try:
            result = await self.chromadb_tool.execute({
                "operation": "add",
                "document": document,
                "metadata": metadata
            })
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the databases."""
        try:
            chromadb_stats = await self.chromadb_tool.execute({"operation": "stats"})
            return {"chromadb": chromadb_stats}
        except Exception as e:
            return {"error": str(e)}
