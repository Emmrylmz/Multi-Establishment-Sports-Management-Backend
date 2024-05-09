from pymongo.collection import Collection
from bson import ObjectId
from datetime import datetime
from fastapi.encoders import jsonable_encoder


class MongoDBService:
    def __init__(self, collection: Collection):
        self.collection = collection

    async def create(self, data: dict):
        """Creates a new document and stores it in the database."""
        data["created_at"] = datetime.utcnow()
        result = await self.collection.insert_one(data)
        return await self.get_by_id(result.inserted_id)

    async def get_by_id(self, doc_id: ObjectId) -> dict:
        """Retrieves a single document by its ID."""
        document = await self.collection.find_one({"_id": doc_id})
        if document:
            document["_id"] = str(document["_id"])
        return self.entity(document) if document else None
    
    async def get_team_id(self, team_id: str) -> dict:
        """Retrieves a single document by its ID."""
        document = await self.collection.find_one({"team_id": team_id})
        if document:
            document["_id"] = str(document["_id"])
        return self.entity(document) if document else None
    
    async def update_team(self, team_id: str, update_data: dict) -> dict:
        """Updates an existing document."""
        update_result = await self.collection.update_one({"team_id": team_id}, {"$push": update_data})
        if update_result.modified_count == 0:
            return None
        return await self.get_team_id(team_id)

    async def update(self, doc_id: ObjectId, update_data: dict) -> dict:
        """Updates an existing document."""
        await self.collection.update_one({"_id": doc_id}, {"$set": update_data})
        return await self.get_by_id(doc_id)

    async def delete(self, doc_id: ObjectId) -> bool:
        """Deletes a document by its ID."""
        result = await self.collection.delete_one({"_id": doc_id})
        return result.deleted_count > 0

    async def list(self, query: dict) -> list:
        """Lists documents based on a query."""
        documents = await self.collection.find(query)
        return [self.entity(doc) for doc in documents]

    def entity(self, document: dict) -> dict:
        """Transforms the document into a more usable entity, if necessary."""
        # This method can be overridden by subclasses to customize the transformation.
        return document
