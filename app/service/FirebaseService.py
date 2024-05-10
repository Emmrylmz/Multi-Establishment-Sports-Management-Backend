import firebase_admin
from firebase_admin import credentials, exceptions


class FirebaseService:
    def __init__(self, cred_path: str):
        self.cred_path = cred_path
        self.firebase_app = None
        self.init_firebase()

    def init_firebase(self):
        try:
            # Load the credentials and initialize the Firebase app
            cred = credentials.Certificate(self.cred_path)
            # Check if app is already initialized to prevent re-initialization errors
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
            # Delete the Firebase app instance
            firebase_admin.delete_app(self.firebase_app)
            print("Firebase app deleted successfully.")
            self.firebase_app = None
        else:
            print("No Firebase app instance to delete.")


# Usage example with the cleanup function
