from bson import ObjectId
from fastapi.encoders import jsonable_encoder
from motor.motor_asyncio import AsyncIOMotorCollection
from datetime import datetime
from ..utils import ensure_object_id


class MongoDBService:
    @classmethod
    # async def initialize(cls, collection: AsyncIOMotorCollection):
    #     self = cls.__new__(cls)
    #     await self.__init__(collection)
    #     return self

    async def __init__(self, collection: AsyncIOMotorCollection):
        self.collection = collection

    async def create(self, data: dict):
        """Creates a new document and stores it in the database asynchronously."""
        data["created_at"] = datetime.utcnow()  # Uncomment to use timestamps
        result = await self.collection.insert_one(data)
        print(result.inserted_id)
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
        update_data["updated_at"] = datetime.utcnow()
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

    async def get_by_province(self, province: str = None):
        query = {}
        if province:
            query["Province"] = province
        cursor = self.collection.find(query, {"_id": 1, "name": 1, "photo": 1})
        return await cursor.to_list(length=None)


# Usage example must also be updated to use async/await patterns.
