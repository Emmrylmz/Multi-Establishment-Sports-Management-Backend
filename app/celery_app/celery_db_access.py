from pymongo import MongoClient
from ..config import settings
from contextlib import contextmanager


class Database:
    def __init__(self):
        self.client = None

    def connect(self):
        if not self.client:
            self.client = MongoClient(settings.DATABASE_URL, maxPoolSize=10)
        return self.client

    def close(self):
        if self.client:
            self.client.close()
            self.client = None


class DatabaseContext:
    def __init__(self, db):
        self.db = db

    @contextmanager
    def connection(self):
        try:
            self.db.connect()
            yield self.db.client
        finally:
            self.db.close()


@contextmanager
def get_db_connection():
    client = db.connect()
    try:
        yield client[settings.MONGO_INITDB_DATABASE]
    finally:
        pass


db = Database()
db_context = DatabaseContext(db)
