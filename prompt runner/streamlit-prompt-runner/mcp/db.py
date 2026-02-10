"""
MCP Database Layer
Handles all MongoDB connections and operations for the MCP (Model Context Protocol) system.
"""
import os
import logging
from typing import Optional
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ServerSelectionTimeoutError
from dotenv import load_dotenv
from urllib.parse import quote_plus

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Global database client and instance
_client: Optional[MongoClient] = None
_database: Optional[Database] = None

# Check if we should use mock MongoDB (for testing)
USE_MOCK_MONGO = os.environ.get("USE_MOCK_MONGO") == "1"


def get_database() -> Database:
    """
    Get MongoDB database instance (singleton pattern).
    Creates connection on first call, returns cached instance on subsequent calls.
    
    Returns:
        Database: MongoDB database instance
        
    Raises:
        SystemExit: If connection fails
    """
    global _client, _database
    
    if _database is not None:
        return _database
    
    # Get configuration from environment
    MONGO_URI = os.environ.get("MONGO_URI")
    
    # If MONGO_URI contains literal @ in password, it needs to be escaped
    # Try to parse and re-encode if needed
    if MONGO_URI and MONGO_URI.startswith("mongodb+srv://") and "@" in MONGO_URI:
        try:
            # Check if URI is already properly formatted (has %40 for @)
            from urllib.parse import urlparse
            parts = MONGO_URI.replace("mongodb+srv://", "").split("@")
            if len(parts) > 2:  # Multiple @ means password has unescaped @
                # Re-extract and properly encode
                userpass_part = parts[0]
                rest = "@".join(parts[1:])
                
                if ":" in userpass_part:
                    user, passwd = userpass_part.split(":", 1)
                    escaped_passwd = quote_plus(passwd)
                    MONGO_URI = f"mongodb+srv://{user}:{escaped_passwd}@{rest}"
                    logger.info("Re-encoded MONGO_URI with proper password escaping")
        except Exception as e:
            logger.warning(f"Could not re-encode MONGO_URI: {e}, attempting with original")
    
    MONGO_DB = os.environ.get("MONGO_DB", os.environ.get("MCP_DB", "prompt_runner"))
    
    try:
        if USE_MOCK_MONGO:
            # Use mongomock for testing (no actual MongoDB needed)
            import mongomock
            _client = mongomock.MongoClient()
            logger.info("Using mongomock MongoClient (USE_MOCK_MONGO=1)")
        else:
            # Production MongoDB connection
            _client = MongoClient(
                MONGO_URI,
                serverSelectionTimeoutMS=10000,
                connectTimeoutMS=10000
            )
            # Verify connection
            _client.admin.command("ping")
            logger.info(f"Connected to MongoDB at {MONGO_URI}")
        
        _database = _client[MONGO_DB]
        logger.info(f"Using database: {MONGO_DB}")
        
        # Create indexes for performance (idempotent)
        _create_indexes(_database)
        
        return _database
        
    except ServerSelectionTimeoutError as e:
        logger.error(f"MongoDB connection timeout: {e}")
        raise SystemExit(f"Cannot connect to MongoDB at {MONGO_URI}. Ensure MongoDB is running.")
    except Exception as e:
        logger.error(f"MongoDB connection error: {e}", exc_info=True)
        raise SystemExit(f"MongoDB connection failed: {e}")


def _create_indexes(db: Database):
    """Create database indexes for optimal performance."""
    try:
        # creator_feedback collection indexes
        db.creator_feedback.create_index("session_id")
        db.creator_feedback.create_index("city")
        db.creator_feedback.create_index("timestamp")
        
        # feedback collection indexes
        db.feedback.create_index("case_id")
        
        # core_logs collection indexes
        db.core_logs.create_index("case_id")
        db.core_logs.create_index("timestamp")
        
        # rules collection indexes
        db.rules.create_index([("city", 1), ("rule_id", 1)], unique=True)
        
        # geometry_outputs collection indexes
        db.geometry_outputs.create_index("case_id")
        
        logger.info("Database indexes created successfully")
    except Exception as e:
        logger.warning(f"Index creation warning: {e}")


def close_database():
    """Close MongoDB connection gracefully."""
    global _client, _database
    
    if _client is not None:
        _client.close()
        logger.info("MongoDB connection closed")
        _client = None
        _database = None


def get_collection(collection_name: str):
    """
    Get a specific MongoDB collection.
    
    Args:
        collection_name: Name of the collection
        
    Returns:
        Collection object
    """
    db = get_database()
    return db[collection_name]


# Collection name constants for consistency
class Collections:
    """MongoDB collection name constants."""
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
