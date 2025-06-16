from typing import Dict, Any
import pymongo
import asyncio

class MongoDBTool:
    def __init__(self, uri: str = "mongodb://localhost:27017/"):
        self.uri = uri
        self.client = None
        self.db = None
        
    async def initialize(self):
        """Initialize the MongoDB client and database."""
        max_retries = 5
        for i in range(max_retries):
            try:
                self.client = pymongo.MongoClient(self.uri, serverSelectionTimeoutMS=5000)
                self.client.admin.command('ping')
                break
            except Exception as e:
                if i < max_retries - 1:
                    print(f"Failed to connect to MongoDB, retrying in 5 seconds... ({e})")
                    await asyncio.sleep(5)
                else:
                    raise e
                    
        self.db = self.client.ava_database
        
        if "users" not in self.db.list_collection_names():
            self.db.users.insert_many([
                {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "role": "admin",
                    "preferences": {
                        "theme": "dark",
                        "notifications": True
                    }
                },
                {
                    "name": "Jane Smith",
                    "email": "jane@example.com",
                    "role": "user",
                    "preferences": {
                        "theme": "light",
                        "notifications": False
                    }
                }
            ])
            
        if "products" not in self.db.list_collection_names():
            self.db.products.insert_many([
                {
                    "name": "Laptop",
                    "price": 1200,
                    "category": "electronics",
                    "in_stock": True
                },
                {
                    "name": "Phone",
                    "price": 800,
                    "category": "electronics",
                    "in_stock": True
                },
                {
                    "name": "Desk",
                    "price": 350,
                    "category": "furniture",
                    "in_stock": False
                }
            ])
            
    async def close(self):
        """Close the MongoDB connection."""
        if self.client:
            self.client.close()
            
    def get_tool_config(self) -> Dict[str, Any]:
        """Get the tool configuration for OpenAI API."""
        return {
            "type": "function",
            "function": {
                "name": "mongodb",
                "description": "Query or modify data in MongoDB",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "operation": {
                            "type": "string",
                            "description": "The operation to perform",
                            "enum": ["find", "find_one", "count", "insert", "update", "delete"]
                        },
                        "collection": {
                            "type": "string",
                            "description": "The collection to operate on",
                            "enum": ["users", "products"]
                        },
                        "filter": {
                            "type": "object",
                            "description": "Filter criteria for the operation"
                        },
                        "data": {
                            "type": "object",
                            "description": "Data for insert or update operations"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of documents to return"
                        },
                        "sort": {
                            "type": "object",
                            "description": "Sort criteria for find operations"
                        }
                    },
                    "required": ["operation", "collection"]
                }
            }
        }
        
    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a MongoDB operation."""
        operation = args.get("operation")
        collection_name = args.get("collection")
        filter_dict = args.get("filter", {})
        data = args.get("data", {})
        limit = args.get("limit", 0)
        sort = args.get("sort", None)
        
        if not operation or not collection_name:
            return {"error": "Operation and collection are required"}
            
        if collection_name not in self.db.list_collection_names():
            return {"error": f"Collection '{collection_name}' does not exist"}
            
        collection = self.db[collection_name]
        
        if operation == "find":
            cursor = collection.find(filter_dict)
            
            if limit > 0:
                cursor = cursor.limit(limit)
            if sort:
                cursor = cursor.sort([(k, v) for k, v in sort.items()])
                
            results = []
            for doc in cursor:
                doc["_id"] = str(doc["_id"])
                results.append(doc)
                
            return {"results": results}

        elif operation == "find_one":
            result = collection.find_one(filter_dict)
            if result:
                result["_id"] = str(result["_id"])
                
            return {"result": result}

        elif operation == "count":
            count = collection.count_documents(filter_dict)
            return {"count": count}

        elif operation == "insert":
            if not data:
                return {"error": "Data is required for insert operation"}
                
            if isinstance(data, list):
                result = collection.insert_many(data)
                return {"inserted_ids": [str(id) for id in result.inserted_ids]}
            else:
                result = collection.insert_one(data)
                return {"inserted_id": str(result.inserted_id)}
    
        elif operation == "update":
            if not data:
                return {"error": "Data is required for update operation"}
            result = collection.update_many(filter_dict, {"$set": data})
            return {"matched_count": result.matched_count, "modified_count": result.modified_count}

        elif operation == "delete":
            result = collection.delete_many(filter_dict)
            return {"deleted_count": result.deleted_count}

        else:
            return {"error": f"Operation '{operation}' is not supported"}
