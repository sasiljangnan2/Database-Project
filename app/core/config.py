from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Train Reservation"
    database_url: str = (
        "mysql+pymysql://train_app:train_local_pw@127.0.0.1:3307/train_app?charset=utf8mb4"
    )
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
