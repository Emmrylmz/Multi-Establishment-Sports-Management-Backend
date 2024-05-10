from bson import ObjectId
from pymongo.collection import Collection
from datetime import datetime
from app.serializers.eventSerializers import eventEntity
from .MongoDBService import MongoDBService
from ..database import Team
from ..service.UserService import user_service


class TeamService(MongoDBService):
    def __init__(self, collection: str):
        super().__init__(collection)

    # def entity(self, document: dict):
    #     # Customize how event documents are transformed before they are returned
    #     if document:
    #         document["start_date"] = document["start_date"].strftime(
    #             "%Y-%m-%d %H:%M:%S"
    #         )
    #     return super().entity(document)

    # Add event-specific methods if necessary
    def get_upcoming_events(self):
        return self.list({"start_date": {"$gte": datetime.utcnow()}})

    async def insert_user(self, team_id, user_id, to_array):

        # Perform the update operation
        res = await self.collection.update_one(
            {"_id": team_id}, {"$addToSet": {array: user_id}}
        )
        print("Update result:", res.modified_count)

        # Return a response based on the operation success
        if res.modified_count > 0:
            return "User added successfully"
        else:
            return "No changes made"

    async def add_users_to_teams(self, user_ids, team_ids, user_role_field):
        teams_update_result = await self.collection.update_many(
            {"_id": {"$in": team_ids}},
            {"$addToSet": {user_role_field: {"$each": user_ids}}},
        )


team_service = TeamService(Team)
