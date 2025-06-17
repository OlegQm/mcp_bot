from typing import Dict, Any, List, TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain.schema import BaseMessage, HumanMessage, AIMessage
import json

from mcp.client import MCPClient


class MCPGraphState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    query: str
    response: str
    mcp_tool_calls: List[Dict[str, Any]]
    error: str
    context: str


class TehotnaUkrajinkaMCPGraph:
    """LangGraph workflow with direct MCP integration."""
    
    def __init__(self):
        self.mcp_client = None
        self.graph = None
        
    async def initialize(self):
        """Initialize the MCP client and graph."""
        self.mcp_client = MCPClient()
        await self.mcp_client.initialize()
        self.graph = self._create_graph()
        
    async def close(self):
        """Close the MCP client."""
        if self.mcp_client:
            await self.mcp_client.close()
            
    def _create_graph(self) -> StateGraph:
        """Create the LangGraph workflow."""
        workflow = StateGraph(MCPGraphState)
        
        workflow.add_node("analyze_query", self._analyze_query_node)
        workflow.add_node("search_knowledge", self._search_knowledge_node)
        workflow.add_node("query_database", self._query_database_node)
        workflow.add_node("generate_response", self._generate_response_node)
        workflow.add_node("handle_error", self._handle_error_node)
        
        workflow.set_entry_point("analyze_query")
        
        workflow.add_conditional_edges(
            "analyze_query",
            self._route_after_analysis,
            {
                "search": "search_knowledge",
                "database": "query_database", 
                "direct": "generate_response",
                "error": "handle_error"
            }
        )
        
        workflow.add_edge("search_knowledge", "generate_response")
        workflow.add_edge("query_database", "generate_response")
        workflow.add_edge("generate_response", END)
        workflow.add_edge("handle_error", END)
        
        return workflow.compile()
    
    async def _analyze_query_node(self, state: MCPGraphState) -> MCPGraphState:
        """Analyze query to determine processing route."""
        query = state["query"].lower()
        
        try:
            if any(word in query for word in ["search", "find", "what is", "tell me about", "explain", "definition"]):
                state["route"] = "search"
            elif any(word in query for word in ["user", "product", "database", "count", "list", "show"]):
                state["route"] = "database"
            else:
                state["route"] = "direct"
        except Exception as e:
            state["error"] = f"Analysis error: {str(e)}"
            state["route"] = "error"
            
        return state
    
    async def _search_knowledge_node(self, state: MCPGraphState) -> MCPGraphState:
        """Search ChromaDB using MCP."""
        try:
            result = await self.mcp_client.call_tool("chromadb", {
                "operation": "query",
                "query": state["query"],
                "n_results": 3
            })
            
            state["mcp_tool_calls"].append({
                "tool": "chromadb",
                "operation": "search",
                "args": {"query": state["query"], "n_results": 3},
                "result": result
            })
            
            documents = result.get("documents", [])
            if documents:
                state["context"] = f"Knowledge Base Results:\n" + "\n".join(documents)
            else:
                state["context"] = "No relevant information found in knowledge base."
                
        except Exception as e:
            state["error"] = f"Knowledge search error: {str(e)}"
            
        return state
    
    async def _query_database_node(self, state: MCPGraphState) -> MCPGraphState:
        """Query MongoDB using MCP."""
        try:
            query = state["query"].lower()
            
            if "user" in query:
                result = await self.mcp_client.call_tool("mongodb", {
                    "operation": "find",
                    "collection": "users",
                    "limit": 5
                })
                context_title = "Users in Database:"
            elif "product" in query:
                result = await self.mcp_client.call_tool("mongodb", {
                    "operation": "find", 
                    "collection": "products",
                    "limit": 5
                })
                context_title = "Products in Database:"
            else:
                users_result = await self.mcp_client.call_tool("mongodb", {
                    "operation": "count",
                    "collection": "users"
                })
                products_result = await self.mcp_client.call_tool("mongodb", {
                    "operation": "count",
                    "collection": "products"
                })
                result = {
                    "users_count": users_result.get("count", 0),
                    "products_count": products_result.get("count", 0)
                }
                context_title = "Database Statistics:"
            
            state["mcp_tool_calls"].append({
                "tool": "mongodb",
                "operation": "query",
                "args": {"query_type": "auto-detected"},
                "result": result
            })
            
            state["context"] = f"{context_title}\n{json.dumps(result, indent=2)}"
            
        except Exception as e:
            state["error"] = f"Database query error: {str(e)}"
            
        return state
    
    async def _generate_response_node(self, state: MCPGraphState) -> MCPGraphState:
        """Generate response using MCP client with context."""
        try:
            if state.get("context"):
                enhanced_query = f"""
            User Query: {state['query']}

            Available Context:
            {state['context']}

            Please provide a comprehensive answer based on the user's query and the available context. 
            Be helpful and informative.
            """
            else:
                enhanced_query = state['query']
            
            result = await self.mcp_client.process_query(enhanced_query)
            state["response"] = result.get("response", "I couldn't generate a proper response.")
            
            if result.get("tool_calls"):
                state["mcp_tool_calls"].extend(result["tool_calls"])
            
        except Exception as e:
            state["error"] = f"Response generation error: {str(e)}"
            
        return state
    
    async def _handle_error_node(self, state: MCPGraphState) -> MCPGraphState:
        """Handle errors gracefully."""
        state["response"] = f"I apologize, but I encountered an error: {state['error']}"
        return state
    
    def _route_after_analysis(self, state: MCPGraphState) -> str:
        """Route based on analysis results."""
        if state.get("error"):
            return "error"
        return state.get("route", "direct")
    
    async def process_query(self, query: str, messages: List[BaseMessage] = None) -> Dict[str, Any]:
        """Process query through the MCP-integrated graph."""
        if not self.graph:
            raise ValueError("Graph not initialized. Call initialize() first.")
            
        initial_state = MCPGraphState(
            messages=messages or [],
            query=query,
            response="",
            mcp_tool_calls=[],
            error="",
            context=""
        )
        
        result = await self.graph.ainvoke(initial_state)
        
        result["messages"].extend([
            HumanMessage(content=query),
            AIMessage(content=result["response"])
        ])
        
        return {
            "response": result["response"],
            "mcp_tool_calls": result["mcp_tool_calls"],
            "messages": result["messages"]
        }
