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

<<<<<<< HEAD
=======
    async def create(self, data: dict):
        # Add any event-specific logic before creating an event
        print("Additional logic before creating an event")
        return await super().create(data)
    
    async def update(self, doc_id: ObjectId, update_data: dict):
        # Add any event-specific logic before updating an event
        print("Additional logic before updating an event")
        return await super().update(doc_id, update_data)
    
    async def add_player_to_team(self, team_id: str, player_name: str):
        """Adds a player to the team's player list."""
        player_add = {"team_players": player_name}
        return await self.update_team(team_id, player_add)

>>>>>>> rabbit_stann
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

    async def insert_user(self, team_id, user_id):
        # Ensure team_id and user_id are ObjectIds
        team_id = ObjectId(team_id) if not isinstance(team_id, ObjectId) else team_id
        user_id = ObjectId(user_id) if not isinstance(user_id, ObjectId) else user_id

        # Fetch the team document
        team = await self.get_by_id(team_id)
        print("Team fetched:", team)

        # Determine the appropriate array based on user role
        role = await user_service.check_role(user_id=user_id)
        array = "team_players" if role == "Player" else "team_coaches"
        print("Updating array:", array)

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


team_service = TeamService(Team)
