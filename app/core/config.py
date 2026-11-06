from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Train Reservation"
    database_url: str = (
        "mysql+pymysql://train_app:train_local_pw@127.0.0.1:3307/train_app?charset=utf8mb4"
    )
    jwt_secret_key: SecretStr = SecretStr("")
    access_token_expire_minutes: int = Field(default=30, ge=1, le=1440)
    jwt_issuer: str = "train-reservation"
    jwt_audience: str = "train-web"
    enable_frontend_preview: bool = False
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_secret(cls, value: SecretStr) -> SecretStr:
        secret = value.get_secret_value()
        if secret and len(secret.encode("utf-8")) < 32:
            raise ValueError("JWT_SECRET_KEY는 최소 32바이트여야 합니다.")
        return value


settings = Settings()
