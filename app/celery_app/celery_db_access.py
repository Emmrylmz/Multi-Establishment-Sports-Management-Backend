from pymongo import MongoClient
from ..config import settings


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


db = Database()
