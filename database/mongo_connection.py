from datetime import datetime, timezone
import os

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "rentwear_mongo")

mongo_client = None
mongo_db = None
activity_collection = None

try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    mongo_client.admin.command("ping")
    mongo_db = mongo_client[MONGO_DB_NAME]
    activity_collection = mongo_db["customer_activities"]
    print("MongoDB connected successfully!")
except Exception as error:
    print("MongoDB connection unavailable:", error)


def log_activity(user_id, activity_type, details=None):
    """Save an activity document in MongoDB without interrupting Flask."""
    if activity_collection is None:
        return False
    try:
        activity_collection.insert_one({
            "user_id": int(user_id),
            "activity_type": activity_type,
            "details": details or {},
            "timestamp": datetime.now(timezone.utc)
        })
        return True
    except Exception as error:
        print("MongoDB activity logging failed:", error)
        return False


def get_user_activities(user_id, limit=50):
    """Return the latest activity documents for one user."""
    if activity_collection is None:
        return []
    try:
        return list(activity_collection.find(
            {"user_id": int(user_id)}, {"_id": 0}
        ).sort("timestamp", -1).limit(limit))
    except Exception as error:
        print("MongoDB activity retrieval failed:", error)
        return []
