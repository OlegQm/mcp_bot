import os
import json
from typing import Dict, Any, List
import openai

from mcp.tools.chromadb_tool import ChromaDBTool
from mcp.tools.mongodb_tool import MongoDBTool

class MCPClient:
    def __init__(self):
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.tools = {}
        self.initialized = False
        
    async def initialize(self):
        """Initialize the MCP client and all tools."""
        if self.initialized:
            return
            
        self.tools["chromadb"] = ChromaDBTool(
            host=os.getenv("CHROMADB_HOST", "chromadb"),
            port=int(os.getenv("CHROMADB_PORT", "8000"))
        )
        
        self.tools["mongodb"] = MongoDBTool(
            uri=os.getenv("MONGODB_URI", "mongodb://mongodb:27017/")
        )
        
        for _, tool in self.tools.items():
            await tool.initialize()
            
        self.initialized = True
        
    async def close(self):
        """Close all tool connections."""
        for tool in self.tools.values():
            await tool.close()
        
    async def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get a list of available tools for OpenAI."""
        tool_configs = []
        
        for tool_name, tool in self.tools.items():
            tool_configs.append(tool.get_tool_config())
            
        return tool_configs
        
    async def process_query(self, query: str) -> Dict[str, Any]:
        """Process a user query using the OpenAI API with MCP tools."""
        tools = await self.get_available_tools()
        
        response = self.client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": "You are Tehotna Ukrajinka, a helpful assistant. Use the available tools to retrieve information when needed."},
                {"role": "user", "content": query}
            ],
            tools=tools,
            tool_choice="auto"
        )
        
        response_message = response.choices[0].message
        tool_calls = []
        
        if response_message.tool_calls:
            for tool_call in response_message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                
                if tool_name in self.tools:
                    tool_result = await self.tools[tool_name].execute(tool_args)
                    tool_calls.append({
                        "name": tool_name,
                        "args": tool_args,
                        "result": tool_result
                    })
                    
            follow_up_messages = [
                {"role": "system", "content": "You are Tehotna Ukrajinka, a helpful assistant. Use the available tools to retrieve information when needed."},
                {"role": "user", "content": query}
            ]
            
            follow_up_messages.append({
                "role": "assistant",
                "content": response_message.content or "",
                "tool_calls": [tc.model_dump() for tc in response_message.tool_calls]
            })
            
            for i, tool_call in enumerate(tool_calls):
                follow_up_messages.append({
                    "role": "tool",
                    "tool_call_id": response_message.tool_calls[i].id,
                    "name": tool_call["name"],
                    "content": json.dumps(tool_call["result"])
                })
                
            final_response = self.client.chat.completions.create(
                model="gpt-4.1",
                messages=follow_up_messages
            )
            
            final_content = final_response.choices[0].message.content
        else:
            final_content = response_message.content
            
        return {
            "response": final_content,
            "tool_calls": tool_calls if tool_calls else None
        }
        
    async def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Call a specific tool directly."""
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not found")
            
        return await self.tools[tool_name].execute(args)
