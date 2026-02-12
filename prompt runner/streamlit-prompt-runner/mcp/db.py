"""
MCP Database Layer - JSON File Storage
Replacement for MongoDB using simple JSON file storage.
"""
import os
import json
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Storage directory
STORAGE_DIR = Path(__file__).parent.parent / "data" / "storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


class Collections:
    """Collection name constants"""
    RULES = "rules"
    FEEDBACK = "feedback"
    CREATOR_FEEDBACK = "creator_feedback"
    GEOMETRY_OUTPUTS = "geometry_outputs"
    DOCUMENTS = "documents"
    RL_LOGS = "rl_logs"
    CORE_LOGS = "core_logs"
    OUTPUT_SUMMARIES = "output_summaries"
    CLASSIFIED_RULES = "classified_rules"
    PROJECTS = "projects"
    EVALUATIONS = "evaluations"


class JSONCollection:
    """Simple JSON-based collection storage"""
    
    def __init__(self, name: str):
        self.name = name
        self.file_path = STORAGE_DIR / f"{name}.json"
        self._ensure_file()
    
    def _ensure_file(self):
        """Ensure the JSON file exists"""
        if not self.file_path.exists():
            self._write([])
    
    def _read(self) -> List[Dict[str, Any]]:
        """Read all documents from the collection"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    def _write(self, data: List[Dict[str, Any]]):
        """Write all documents to the collection"""
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
    
    def insert_one(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a single document"""
        data = self._read()
        
        # Add metadata
        if '_id' not in document:
            document['_id'] = str(len(data) + 1)
        if 'created_at' not in document:
            document['created_at'] = datetime.now().isoformat()
        
        data.append(document)
        self._write(data)
        
        return {"inserted_id": document['_id']}
    
    def find(self, query: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Find documents matching query"""
        data = self._read()
        
        if query is None or not query:
            return data
        
        # Simple query matching
        results = []
        for doc in data:
            match = True
            for key, value in query.items():
                if key not in doc or doc[key] != value:
                    match = False
                    break
            if match:
                results.append(doc)
        
        return results
    
    def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find a single document"""
        results = self.find(query)
        return results[0] if results else None
    
    def update_one(self, query: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        """Update a single document"""
        data = self._read()
        modified = 0
        
        for doc in data:
            match = True
            for key, value in query.items():
                if key not in doc or doc[key] != value:
                    match = False
                    break
            
            if match:
                # Handle $set operator
                if '$set' in update:
                    doc.update(update['$set'])
                else:
                    doc.update(update)
                doc['updated_at'] = datetime.now().isoformat()
                modified = 1
                break
        
        if modified:
            self._write(data)
        
        return {"modified_count": modified}
    
    def delete_many(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Delete documents matching query"""
        data = self._read()
        original_count = len(data)
        
        # Filter out matching documents
        filtered = []
        for doc in data:
            match = True
            for key, value in query.items():
                if key not in doc or doc[key] != value:
                    match = False
                    break
            if not match:
                filtered.append(doc)
        
        deleted_count = original_count - len(filtered)
        
        if deleted_count > 0:
            self._write(filtered)
        
        return {"deleted_count": deleted_count}
    
    def count_documents(self, query: Optional[Dict[str, Any]] = None) -> int:
        """Count documents matching query"""
        return len(self.find(query or {}))
    
    def create_index(self, *args, **kwargs):
        """Dummy method for index creation (not needed for JSON storage)"""
        pass


class JSONDatabase:
    """Simple JSON-based database"""
    
    def __init__(self, name: str):
        self.name = name
        self._collections: Dict[str, JSONCollection] = {}
    
    def __getitem__(self, collection_name: str) -> JSONCollection:
        """Get or create a collection"""
        if collection_name not in self._collections:
            self._collections[collection_name] = JSONCollection(collection_name)
        return self._collections[collection_name]
    
    @property
    def creator_feedback(self) -> JSONCollection:
        return self[Collections.CREATOR_FEEDBACK]
    
    @property
    def feedback(self) -> JSONCollection:
        return self[Collections.FEEDBACK]
    
    @property
    def core_logs(self) -> JSONCollection:
        return self[Collections.CORE_LOGS]
    
    @property
    def rules(self) -> JSONCollection:
        return self[Collections.RULES]
    
    @property
    def geometry_outputs(self) -> JSONCollection:
        return self[Collections.GEOMETRY_OUTPUTS]


# Global database instance
_database: Optional[JSONDatabase] = None


def get_database() -> JSONDatabase:
    """
    Get database instance (singleton pattern).
    
    Returns:
        JSONDatabase: JSON-based database instance
    """
    global _database
    
    if _database is not None:
        return _database
    
    db_name = os.environ.get("DB_NAME", "prompt_runner")
    _database = JSONDatabase(db_name)
    logger.info(f"Using JSON file storage at {STORAGE_DIR}")
    
    return _database


def close_database():
    """Close database connection (no-op for JSON storage)"""
    global _database
    _database = None
    logger.info("Database closed")


def get_collection(collection_name: str) -> JSONCollection:
    """
    Get a specific collection.
    
    Args:
        collection_name: Name of the collection
        
    Returns:
        JSONCollection object
    """
    db = get_database()
    return db[collection_name]
