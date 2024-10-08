from bson import ObjectId
from fastapi.encoders import jsonable_encoder
from motor.motor_asyncio import AsyncIOMotorCollection
from datetime import datetime


class MongoDBService:
    def __init__(self, collection: AsyncIOMotorCollection):
        self.collection = collection

    async def create(self, data: dict):
        """Creates a new document and stores it in the database asynchronously."""
        data["created_at"] = datetime.utcnow()  # Uncomment to use timestamps
        result = await self.collection.insert_one(data)
        return await self.get_by_id(result.inserted_id)

    async def get_by_id(self, doc_id: str) -> dict:
        """Retrieves a single document by its ID using an ObjectId asynchronously."""
        document = await self.collection.find_one({"_id": ObjectId(doc_id)})
        if document:
            document["_id"] = str(
                document["_id"]
            )  # Convert ObjectId to string for JSON serialization
        return document

    async def update(self, doc_id: str, update_data: dict) -> dict:
        """Updates an existing document asynchronously."""
        await self.collection.update_one(
            {"_id": ObjectId(doc_id)}, {"$set": update_data}
        )
        return await self.get_by_id(doc_id)

    async def delete(self, doc_id: str) -> bool:
        """Deletes a document by its ID asynchronously."""
        result = await self.collection.delete_one({"_id": ObjectId(doc_id)})
        return result.deleted_count > 0

    async def list(self, query: dict) -> list:
        """Lists documents based on a query asynchronously."""
        jsonable_encoder(query)  # Optionally process query for JSON encoding
        cursor = self.collection.find(query)
        documents = await cursor.to_list(length=None)  # Fetch all documents from cursor
        return documents

    def entity(self, document: dict) -> dict:
        """Transforms the document into a more usable entity, if necessary."""
        # This method can be overridden by subclasses to customize the transformation.
        return document


# Usage example must also be updated to use async/await patterns.
