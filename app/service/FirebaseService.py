import firebase_admin
from firebase_admin import credentials, exceptions
from ..config import settings
from ..service.MongoDBService import MongoDBService
from motor.motor_asyncio import AsyncIOMotorCollection


class FirebaseService:
    @classmethod
    async def initialize(
        cls,
        cred_path: str = settings.FIREBASE_CREDENTIALS_PATH,
    ):
        self = cls.__new__(cls)
        self.cred_path = cred_path
        self.firebase_app = None
        self.init_firebase()
        return self

    def init_firebase(self):
        try:
            cred = credentials.Certificate(self.cred_path)
            if not firebase_admin._apps:
                self.firebase_app = firebase_admin.initialize_app(cred)
                print("Firebase app initialized:", self.firebase_app.name)
            else:
                self.firebase_app = firebase_admin.get_app()
                print("Using existing Firebase app:", self.firebase_app.name)
        except exceptions.FirebaseError as error:
            print("Firebase initialization failed:", error)

    def delete_firebase_app(self):
        if self.firebase_app:
            firebase_admin.delete_app(self.firebase_app)
            print("Firebase app deleted successfully.")
            self.firebase_app = None
        else:
            print("No Firebase app instance to delete.")
