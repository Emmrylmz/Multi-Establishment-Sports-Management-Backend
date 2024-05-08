from pymongo.collection import Collection
from bson import ObjectId
from datetime import datetime
from fastapi.encoders import jsonable_encoder
from motor.motor_asyncio import AsyncIOMotorClient
from ..utils import JSONEncoder


class MongoDBService:
    def __init__(self, collection: Collection):
        self.collection = collection

    def create(self, data: dict):
        """Creates a new document and stores it in the database."""
        # data["created_at"] = datetime.utcnow()

        result = self.collection.insert_one(data)
        return self.get_by_id(result.inserted_id)
        # return result

    def get_by_id(self, doc_id: str) -> dict:
        """Retrieves a single document by its ID using an ObjectId."""
        document = self.collection.find_one({"_id": ObjectId(doc_id)})
        if document:
            # Optionally convert '_id' to a string if needed for JSON serialization or similar.
            document["_id"] = str(document["_id"])
        return document

    def update(self, doc_id: ObjectId, update_data: dict) -> dict:
        """Updates an existing document."""
        self.db.collection.update_one({"_id": doc_id}, {"$set": update_data})
        return self.db.get_by_id(doc_id)

    def delete(self, doc_id: ObjectId) -> bool:
        """Deletes a document by its ID."""
        result = self.db.collection.delete_one({"_id": doc_id})
        return result.deleted_count > 0

    async def list(self, query: dict) -> list:
        """Lists documents based on a query."""
        jsonable_encoder(query).encode()
        cursor = self.db.collection.find(query)
        documents = await cursor.to_list(length=None)  # Fetch all documents from cursor
        return documents

    def entity(self, document: dict) -> dict:
        """Transforms the document into a more usable entity, if necessary."""
        # This method can be overridden by subclasses to customize the transformation.
        return document
