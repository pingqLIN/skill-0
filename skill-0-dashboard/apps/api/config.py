"""Configuration for the Governance Dashboard API"""

from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Database path (relative to skill-0 project root)
    database_path: Path = (
        Path(__file__).parent.parent.parent.parent
        / "governance"
        / "db"
        / "governance.db"
    )

    # Tools path (where governance_db.py lives)
    tools_path: Path = Path(__file__).parent.parent.parent.parent / "tools"

    # API settings
    api_title: str = "Skill-0 Governance Dashboard API"
    api_version: str = "1.0.0"

    class Config:
        env_prefix = "SKILL0_"


settings = Settings()
