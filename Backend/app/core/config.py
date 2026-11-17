from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve paths against the Backend directory so the app behaves the same no
# matter which directory uvicorn is started from.
_BACKEND_DIR = Path(__file__).resolve().parents[2]
_DEFAULT_DATABASE_URL = f"sqlite:///{(_BACKEND_DIR / 'app.db').as_posix()}"


class Settings(BaseSettings):
    DATABASE_URL: str = _DEFAULT_DATABASE_URL

    MAIL_FROM: str | None = None
    MAIL_HOST: str | None = None
    MAIL_PORT: int = 587
    MAIL_USERNAME: str | None = None
    MAIL_PASSWORD: str | None = None

    model_config = SettingsConfigDict(
        env_file=str(_BACKEND_DIR / ".env"),
        extra="ignore"
    )


settings = Settings()
