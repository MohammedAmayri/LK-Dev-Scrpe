import os
from dotenv import load_dotenv
from pymongo import MongoClient
from bson.objectid import ObjectId
import logging

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the MongoDB URI from environment variables
MONGO_URI = os.getenv('MONGO_URI')

if not MONGO_URI:
    logger.error("MONGO_URI is not set in environment variables.")
    raise Exception("MONGO_URI is not set.")

# Get database and collection names from environment variables
DATABASE_NAME = os.getenv('DATABASE_NAME', 'test')  # Default to 'test' if not set
COLLECTION_NAME = os.getenv('COLLECTION_NAME', 'restaurant')  # Default to 'restaurant' if not set

# Initialize MongoDB client
try:
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    restaurants_collection = db[COLLECTION_NAME]
    logger.info(f"Connected to MongoDB database '{DATABASE_NAME}' and collection '{COLLECTION_NAME}'.")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    raise e

def update_restaurant_menus(restaurant_id, lunch_menus):
    try:
        # Ensure restaurant_id is an ObjectId
        if not isinstance(restaurant_id, ObjectId):
            restaurant_id = ObjectId(restaurant_id)
        result = restaurants_collection.update_one(
            {'_id': restaurant_id},
            {'$set': {'lunch_menus': lunch_menus}}
        )
        if result.modified_count > 0:
            logger.info(f"Updated restaurant {restaurant_id}: {result.modified_count} document(s) modified.")
        else:
            logger.warning(f"No documents were modified for restaurant {restaurant_id}.")
        return result.modified_count
    except Exception as e:
        logger.error(f"Failed to update restaurant {restaurant_id}: {e}")
        return 0

# You can add additional database functions here, such as fetching restaurants, etc.
