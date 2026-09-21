from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_env: str = "development"
    aws_mode: bool = False
    aws_region: str = "ap-south-1"
    ec2_instance_ids: str = ""
    rds_instance_ids: str = ""
    cloudwatch_lookback_minutes: int = 15
    cloudwatch_period_seconds: int = 60
    database_url: str = "sqlite:///./banking_analytics.db"
    model_path: str = "ai_models/checkpoints/baseline_gcn.pt"
    anomaly_threshold: float = 0.5
    frontend_origin: str = "http://localhost:5173"
    model_seed: int = 42
    model_node_feature_dim: int = 16

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def ec2_ids(self) -> list[str]:
        return [x.strip() for x in self.ec2_instance_ids.split(",") if x.strip()]

    @property
    def rds_ids(self) -> list[str]:
        return [x.strip() for x in self.rds_instance_ids.split(",") if x.strip()]

@lru_cache
def get_settings() -> Settings:
    return Settings()
