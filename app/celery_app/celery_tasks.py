from bson import ObjectId
from .celery_setup import celery_task, celery, celery_app
from celery.exceptions import Retry
from pymongo import UpdateOne
from pymongo.errors import OperationFailure, BulkWriteError
from celery.schedules import crontab
from ..config import settings
from datetime import datetime
from ..models.attendance_schemas import (
    AttendanceStatus,
)
from datetime import datetime, timedelta
from ..utils import setup_logger
from .celery_setup import with_db, with_redis
from bson.errors import InvalidId

logging = setup_logger(__name__)


@celery_task(with_db, max_retries=3, countdown=60)
def update_all_user_attendance_stats(database, *args, **kwargs):
    logging.info("Starting update_user_attendance_stats task")
    db = database.client[settings.MONGO_INITDB_DATABASE]
    player_stats_collection = db["Player_Stats"]
    attendance_collection = db["Attendance"]
    event_collection = db["Event"]

    current_time = datetime.utcnow()
    twelve_hours_ago = current_time - timedelta(hours=12)

    sample_attendance = attendance_collection.find_one(
        {"timestamp": {"$gte": twelve_hours_ago, "$lt": current_time}}
    )
    logging.info(f"Sample attendance record: {sample_attendance}")

    try:
        # Step 1: Get the unique event IDs for the last 12 hours
        event_ids = list(
            attendance_collection.aggregate(
                [
                    {
                        "$match": {
                            "timestamp": {"$gte": twelve_hours_ago, "$lt": current_time}
                        }
                    },
                    {
                        "$group": {
                            "_id": "$event_id",
                        }
                    },
                    {"$project": {"_id": 0, "event_id": "$_id"}},
                ]
            )
        )
        event_ids = [event["event_id"] for event in event_ids]
        logging.info(f"Found {len(event_ids)} unique event IDs to process")

        # Step 2: Look up the event type for each event ID
        event_types = {
            str(event["_id"]): event["event_type"]
            for event in event_collection.find(
                {"_id": {"$in": [ObjectId(event_id) for event_id in event_ids]}},
                {"_id": 1, "event_type": 1},
            )
        }

        logging.info(f"event types = {event_types}")

        # Step 3: Calculate the attendance stats
        recent_stats = list(
            attendance_collection.aggregate(
                [
                    {
                        "$match": {
                            "timestamp": {"$gte": twelve_hours_ago, "$lt": current_time}
                        }
                    },
                    {
                        "$lookup": {
                            "from": "Event",
                            "localField": "event_id",
                            "foreignField": "_id",
                            "as": "event_info",
                        }
                    },
                    {"$unwind": "$event_info"},
                    {
                        "$group": {
                            "_id": {
                                "user_id": {"$toString": "$user_id"},
                                "event_type": {
                                    "$cond": [
                                        {"$ifNull": ["$event_info.event_type", False]},
                                        "$event_info.event_type",
                                        "unknown_event",
                                    ]
                                },
                            },
                            "total_events": {"$sum": 1},
                            "present_events": {
                                "$sum": {
                                    "$cond": [
                                        {"$eq": ["$status", AttendanceStatus.PRESENT]},
                                        1,
                                        0,
                                    ]
                                }
                            },
                        }
                    },
                ]
            )
        )
        logging.info(f"Found {len(recent_stats)} attendance records to process")
    except Exception as e:
        logging.error(f"Aggregation failed: {str(e)}")
        raise self.retry(exc=e, countdown=60)

    bulk_updates = []
    for stat in recent_stats:
        user_id = stat["_id"]["user_id"]
        event_type = stat["_id"]["event_type"]
        if event_type == "unknown":
            event_type = "unknown_event"

        total_field = f"total_{event_type}_events"
        present_field = f"present_{event_type}_events"

        update_op = {
            "$set": {
                "last_update": current_time,
                total_field: stat["total_events"],
                present_field: stat["present_events"],
            }
        }

        try:
            bulk_updates.append(
                UpdateOne({"_id": ObjectId(user_id)}, update_op, upsert=True)
            )
        except InvalidId:
            # Handle the case where user_id is not a valid ObjectId
            logging.warning(f"Invalid user_id '{user_id}' skipped.")
            continue

    # Batching mechanism
    batch_size = 500  # Adjust this value based on your needs
    total_modified = 0
    total_upserted = 0

    for i in range(0, len(bulk_updates), batch_size):
        batch = bulk_updates[i : i + batch_size]
        try:
            result = player_stats_collection.bulk_write(batch)
            total_modified += result.modified_count
            total_upserted += len(result.upserted_ids)
            logging.info(
                f"Batch {i // batch_size + 1}: Modified {result.modified_count} documents, Inserted {len(result.upserted_ids)} new documents"
            )
        except BulkWriteError as bwe:
            logging.error(
                f"Bulk write error in batch {i // batch_size + 1}: {str(bwe.details)}"
            )
            for error in bwe.details["writeErrors"]:
                logging.error(
                    f"Write error for user {error['op']['q']['_id']}: {error['errmsg']}"
                )
        except OperationFailure as e:
            logging.error(
                f"Failed to update player stats in batch {i // batch_size + 1}: {str(e)}"
            )
            # Consider whether you want to retry the entire task or just log the error
            # raise self.retry(exc=e, countdown=60)

    logging.info(
        f"Total documents modified: {total_modified}, Total documents inserted: {total_upserted}"
    )

    # Check a sample user's stats
    if recent_stats:
        sample_user_id = recent_stats[0]["_id"]["user_id"]
        updated_stats = player_stats_collection.find_one(
            {"_id": ObjectId(sample_user_id)}
        )
        logging.info(f"Updated stats for sample user {sample_user_id}: {updated_stats}")

    logging.info("Finished update_user_attendance_stats task")


@celery_task(with_db, max_retries=3, countdown=60)
def update_monthly_balance(
    database,
    year: int,
    month: int,
    province: str,
    amount_change: float,
    *args,
    **kwargs,
):
    client = database.client[settings.MONGO_INITDB_DATABASE]
    balance_collection = client["Monthly_Balance"]
    update_operation = {
        "$inc": {"total_balance": amount_change},
        "$set": {"last_updated": datetime.utcnow()},
    }
    balance_collection.update_one(
        {
            "year": year,
            "month": month,
            "province": province,
            "document_type": "monthly_balance",
        },
        update_operation,
        upsert=True,
    )


@celery_task(with_redis, max_retries=3, countdown=60)
def invalidate_caches(redis_conn, cache_keys, *args, **kwargs):

    for key in cache_keys:
        redis_conn.delete(key)


@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Executes every 12 hours
    sender.add_periodic_task(
        crontab(hour="*/12"),
        update_all_user_attendance_stats.s(),
        name="update attendance stats every 12 hours",
    )
