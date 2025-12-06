"""Configuration loading and management using pydantic-settings."""

import os
from pathlib import Path
from typing import Optional, List

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET = "change-this-secret-key-in-production-use-env-var"


class DataConfig(BaseSettings):
    """Data paths and dataset configuration."""

    dataset_path: str = "data/raw"
    processed_path: str = "data/processed"
    cache_dir: str = "data/processed"
    models_dir: str = "data/models"
    hf_dataset_name: str = "FreshRetailNet-50K"
    hf_cache_dir: str = "data/hf_cache"

    model_config = SettingsConfigDict(extra="allow")


class ForecastingConfig(BaseSettings):
    """Forecasting model configuration."""

    horizon_days: int = 7
    model_type: str = "lightgbm"
    default_service_level: float = 0.95
    safety_factor: float = 1.65  # z-score for 95% service level

    model_config = SettingsConfigDict(extra="allow")


class ReplenishmentConfig(BaseSettings):
    """Replenishment policy configuration."""

    target_coverage_days: int = 7
    min_order_quantity: int = 1
    case_pack_size: int = 1
    max_order_quantity: int = 1000

    model_config = SettingsConfigDict(extra="allow")


class MarkdownBucket(BaseSettings):
    """Markdown discount bucket configuration."""

    days_before_expiry: int
    discount_percent: float

    model_config = SettingsConfigDict(extra="allow")


class MarkdownConfig(BaseSettings):
    """Markdown policy configuration."""

    expiry_buckets: list[MarkdownBucket] = Field(default_factory=lambda: [
        MarkdownBucket(days_before_expiry=3, discount_percent=20.0),
        MarkdownBucket(days_before_expiry=2, discount_percent=35.0),
        MarkdownBucket(days_before_expiry=1, discount_percent=50.0),
    ])

    model_config = SettingsConfigDict(extra="allow")


class ModelsConfig(BaseSettings):
    """Models configuration."""

    forecasting: ForecastingConfig = Field(default_factory=ForecastingConfig)
    replenishment: ReplenishmentConfig = Field(default_factory=ReplenishmentConfig)
    markdown: MarkdownConfig = Field(default_factory=MarkdownConfig)

    model_config = SettingsConfigDict(extra="allow")


class ShelfLifeConfig(BaseSettings):
    """Shelf life configuration per category."""

    fruits: int = 5
    vegetables: int = 7
    bakery: int = 3
    chilled: int = 7
    default: int = 5
    category_mapping: dict[int, int] = Field(default_factory=dict)

    def get_shelf_life(
        self,
        category: Optional[str | int] = None,
        category_id: Optional[int] = None
    ) -> int:
        """
        Get shelf life for a category.
        
        Args:
            category: Category name (str) or category ID (int)
            category_id: Explicit numeric category identifier (optional)
            
        Returns:
            Shelf life in days
        """
        if category is None and category_id is not None:
            category = category_id

        if category is None:
            return self.default
        
        # Handle numeric category IDs
        if isinstance(category, int):
            if hasattr(self, 'category_mapping') and self.category_mapping:
                return self.category_mapping.get(category, self.default)
            return self.default
        
        # Handle string category names
        if isinstance(category, str):
            category_lower = category.lower()
            if hasattr(self, category_lower):
                return getattr(self, category_lower)
        
        return self.default

    model_config = SettingsConfigDict(extra="allow")


class APIConfig(BaseSettings):
    """API configuration."""

    host: str = "0.0.0.0"
    port: int = 8000
    version: str = "v1"
    timeout: float = 30.0
    allowed_origins: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:8501",
            "http://localhost:3000"
        ]
    )

    model_config = SettingsConfigDict(extra="allow")


class LoggingConfig(BaseSettings):
    """Logging configuration."""

    level: str = "INFO"
    format: str = "json"  # "json" or "text"
    service_name: str = "replenishment-manager"

    model_config = SettingsConfigDict(extra="allow")


class DatabaseConfig(BaseSettings):
    """Database configuration."""

    url: str = "sqlite:///./data/replenishment.db"
    echo: bool = False

    model_config = SettingsConfigDict(extra="allow")


class AuthConfig(BaseSettings):
    """Authentication configuration."""

    jwt_secret_key: str = Field(
        default=DEFAULT_JWT_SECRET,
        description="JWT secret key for token signing. MUST be set via AUTH_JWT_SECRET_KEY environment variable in production."
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    allow_self_registration: bool = False

    model_config = SettingsConfigDict(
        env_prefix="AUTH_",
        env_file=".env",
        extra="allow"
    )
    
    @field_validator('jwt_secret_key')
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        """Validate JWT secret key is not default in production."""
        if v == DEFAULT_JWT_SECRET:
            env = os.getenv("ENVIRONMENT", "dev")
            if env != "dev":
                raise ValueError(
                    "JWT_SECRET_KEY must be set via AUTH_JWT_SECRET_KEY environment variable "
                    "in non-development environments."
                )
        return v


class PerformanceConfig(BaseSettings):
    """Performance configuration."""

    batch_size: int = 1000
    max_workers: int = 4
    cache_ttl_seconds: int = 3600

    model_config = SettingsConfigDict(extra="allow")


class AppConfig(BaseSettings):
    """Main application configuration."""

    environment: str = Field(default="dev", alias="ENVIRONMENT")
    data: DataConfig = Field(default_factory=DataConfig)
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    shelf_life: ShelfLifeConfig = Field(default_factory=ShelfLifeConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="allow",
    )

    @classmethod
    def load(cls, env: Optional[str] = None) -> "AppConfig":
        """
        Load configuration from YAML files and environment variables.

        Configuration hierarchy (highest priority first):
        1. Environment variables
        2. {env}.yaml (e.g., dev.yaml, prod.yaml)
        3. config.yaml (base config)

        Args:
            env: Environment name (dev, staging, prod). If None, uses ENVIRONMENT env var.

        Returns:
            AppConfig instance with loaded configuration.
        """
        # Determine environment
        if env is None:
            env = os.getenv("ENVIRONMENT", "dev")

        # Get config directory
        config_dir = Path(__file__).parent.parent / "config"

        # Load base config
        base_config_path = config_dir / "config.yaml"
        base_config = {}
        if base_config_path.exists():
            with open(base_config_path, "r", encoding="utf-8") as f:
                base_config = yaml.safe_load(f) or {}

        # Load environment-specific config
        env_config_path = config_dir / f"{env}.yaml"
        env_config = {}
        if env_config_path.exists():
            with open(env_config_path, "r", encoding="utf-8") as f:
                env_config = yaml.safe_load(f) or {}

        # Merge configs (env config overrides base config)
        merged_config = _deep_merge(base_config, env_config)

        # Create config instance from merged config and environment variables
        return cls(**merged_config, environment=env)


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge two dictionaries, with override taking precedence."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


# Global config instance (lazy loaded)
_config: Optional[AppConfig] = None


def get_config(env: Optional[str] = None) -> AppConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = AppConfig.load(env)
    return _config


def reload_config(env: Optional[str] = None) -> AppConfig:
    """Reload the global configuration."""
    global _config
    _config = AppConfig.load(env)
    return _config

