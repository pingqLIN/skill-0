"""Configuration for the Governance Dashboard API"""

from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    database_path: Path = (
        Path(__file__).parent.parent.parent.parent
        / "governance"
        / "db"
        / "governance.db"
    )

    tools_path: Path = Path(__file__).parent.parent.parent.parent / "tools"

    governance_db_path: Path = (
        Path(__file__).parent.parent.parent.parent
        / "governance"
        / "db"
        / "governance.db"
    )

    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    jwt_secret_key: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30

    api_rate_limit: str = "100/minute"

    log_level: str = "INFO"

    device: str = "auto"

    api_title: str = "Skill-0 Governance Dashboard API"
    api_version: str = "1.0.0"

    class Config:
        env_prefix = "SKILL0_"


settings = Settings()
