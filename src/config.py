from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Intervals.icu
    intervals_api_key: str = ""
    intervals_athlete_id: str = "0"
    intervals_base_url: str = "https://intervals.icu/api/v1"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_base_url: str = ""

    # Discord
    discord_bot_token: str = ""
    discord_guild_id: str = ""

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/fitness_coach.db"

    # App
    log_level: str = "INFO"
    sync_interval_minutes: int = 60
    api_host: str = "0.0.0.0"
    api_port: int = 8000


settings = Settings()
