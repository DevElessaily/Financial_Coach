from typing import Any

from firebase_admin import messaging

from app.core.firebase import initialize_firebase


class PushNotification:
    @staticmethod
    def send(token: str, title: str, body: str, data: dict[str, Any] | None = None) -> str:
        initialize_firebase()
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            token=token,
            data={str(key): str(value) for key, value in (data or {}).items()},
        )
        return messaging.send(message)
