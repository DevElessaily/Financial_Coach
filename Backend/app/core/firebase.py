
import os
from pathlib import Path

import firebase_admin

from firebase_admin import credentials


def initialize_firebase():
    if firebase_admin._apps:
        return firebase_admin.get_app()

    credential_path = os.getenv("FIREBASE_SERVICE_ACCOUNT", "firebase-service-account.json")
    if Path(credential_path).is_file():
        credential = credentials.Certificate(credential_path)
        return firebase_admin.initialize_app(credential)

    try:
        credential = credentials.ApplicationDefault()
        return firebase_admin.initialize_app(credential)
    except Exception as error:
        raise RuntimeError(
            "Firebase is not configured. Set FIREBASE_SERVICE_ACCOUNT or configure Application Default Credentials."
        ) from error
