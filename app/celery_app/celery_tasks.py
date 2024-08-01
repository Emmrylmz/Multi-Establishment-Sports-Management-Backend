from bson import ObjectId
from .celery_setup import celery_task
from fastapi import Depends
from celery.exceptions import Retry
from pymongo import MongoClient, UpdateOne
from celery import shared_task

mongo_client = MongoClient(
    "mongodb+srv://banleue13:Mrfadeaway.1@cluster0.lvzd0dt.mongodb.net/?retryWrites=true&w=majority",
    maxPoolSize=100,
)


@shared_task(bind=True, max_retries=3)
def update_attendance_counts_task(self, event_type, attendances):
    db = mongo_client["DACKA"]
    user_collection = db["User_Info"]
    print("asd", db)

    bulk_operations = []
    user_ids = set()

    for attendance in attendances:
        user_id = ObjectId(attendance["user_id"])
        user_ids.add(user_id)
        present_increment = 1 if attendance["status"] == "present" else 0

        if event_type == "game":
            update_operation = {
                "$inc": {
                    "total_game_events": 1,
                    "present_game_events": present_increment,
                }
            }
        elif event_type == "training":
            update_operation = {
                "$inc": {
                    "total_training_events": 1,
                    "present_training_events": present_increment,
                }
            }
        else:
            raise ValueError(f"Invalid event type: {event_type}")

        bulk_operations.append(UpdateOne({"_id": user_id}, update_operation))

    try:
        if bulk_operations:
            result = user_collection.bulk_write(bulk_operations)
            print(f"Modified {result.modified_count} document(s)")

        pipeline = [
            {"$match": {"_id": {"$in": list(user_ids)}}},
            {
                "$addFields": {
                    f"{event_type}_attendance_ratio": {
                        "$round": [
                            {
                                "$cond": [
                                    {"$eq": [f"$total_{event_type}_events", 0]},
                                    0,
                                    {
                                        "$divide": [
                                            f"$present_{event_type}_events",
                                            f"$total_{event_type}_events",
                                        ]
                                    },
                                ]
                            },
                            2,
                        ]
                    }
                }
            },
            {
                "$merge": {
                    "into": user_collection.name,
                    "on": "_id",
                    "whenMatched": "merge",
                    "whenNotMatched": "discard",
                }
            },
        ]

        user_collection.aggregate(pipeline)

    except Exception as e:
        print(f"Failed to update attendance counts and ratios: {str(e)}")
        raise self.Retry(exc=e, countdown=5, max_retries=3)

    finally:
        if db and db.client:
            db.client.close()


# @celery_task
# def check_db_connection():
#     try:
#         db = get_database_sync()
#         db.client.admin.command("ismaster")
#     except Exception as e:
#         print(f"Database connection lost. Reconnecting... Error: {str(e)}")
#         connect_to_mongo_sync()
