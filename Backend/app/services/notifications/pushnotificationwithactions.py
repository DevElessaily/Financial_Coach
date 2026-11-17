import json
from typing import Any

from firebase_admin import messaging

from app.core.firebase import initialize_firebase


class PushNotificationWithActions:
    @staticmethod
    def send(
        token: str,
        title: str,
        body: str,
        actions: list[dict[str, str]],
        data: dict[str, Any] | None = None,
    ) -> str:
        initialize_firebase()
        payload = {str(key): str(value) for key, value in (data or {}).items()}
        payload["actions"] = json.dumps(actions, ensure_ascii=False)
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            token=token,
            data=payload,
        )
        return messaging.send(message)
