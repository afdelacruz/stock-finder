"""Configuration management."""

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, rely on environment variables


class FMPConfig(BaseModel):
    """Configuration for FMP (Financial Modeling Prep) API."""

    api_key: str | None = Field(default=None, description="FMP API key (loaded from FMP_API_KEY env var)")
    base_url: str = Field(default="https://financialmodelingprep.com/api/v3")
    batch_size: int = Field(default=50, description="Max tickers per batch request")
    timeout: int = Field(default=30)

    @classmethod
    def from_env(cls) -> "FMPConfig":
        """Load FMP config with API key from environment."""
        return cls(api_key=os.environ.get("FMP_API_KEY"))


class ScanConfig(BaseModel):
    """Configuration for scanning."""

    min_gain_pct: float = Field(default=500.0, description="Minimum gain percentage")
    lookback_years: int = Field(default=3, description="Years to look back")


class CacheConfig(BaseModel):
    """Configuration for disk cache."""

    enabled: bool = Field(default=True, description="Enable disk caching")
    cache_dir: str = Field(default="data/cache", description="Cache directory path")
    ttl_hours: int = Field(default=24, description="TTL for recent data in hours")
    max_size_gb: float = Field(default=5.0, description="Maximum cache size in GB")


class DataConfig(BaseModel):
    """Configuration for data fetching."""

    cache: CacheConfig = Field(default_factory=CacheConfig)
    rate_limit_delay: float = Field(default=0.1, description="Seconds between API calls")
    timeout: int = Field(default=30)


class OutputConfig(BaseModel):
    """Configuration for output."""

    default_format: str = Field(default="table")
    save_dir: str = Field(default="output")


class LoggingConfig(BaseModel):
    """Configuration for logging."""

    level: str = Field(default="INFO")


class ParallelConfig(BaseModel):
    """Configuration for parallel processing."""

    max_workers: int = Field(default=10, description="Maximum concurrent workers")
    enabled: bool = Field(default=True, description="Enable parallel processing")


class Settings(BaseModel):
    """Main settings container."""

    scan: ScanConfig = Field(default_factory=ScanConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    fmp: FMPConfig = Field(default_factory=FMPConfig.from_env)
    output: OutputConfig = Field(default_factory=OutputConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    parallel: ParallelConfig = Field(default_factory=ParallelConfig)
    default_provider: str = Field(default="fmp", description="Default data provider: 'fmp' or 'yfinance'")


def load_settings(config_path: Path | str | None = None) -> Settings:
    """
    Load settings from YAML file.

    Args:
        config_path: Path to config file. If None, uses default config/settings.yaml

    Returns:
        Settings object with validated configuration
    """
    if config_path is None:
        # Look for config relative to project root
        config_path = Path(__file__).parent.parent.parent.parent / "config" / "settings.yaml"

    config_path = Path(config_path)

    if not config_path.exists():
        # Return defaults if no config file
        return Settings()

    with open(config_path) as f:
        data: dict[str, Any] = yaml.safe_load(f) or {}

    return Settings(**data)


# Global settings instance (lazy loaded)
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings
