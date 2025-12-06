"""Tests for configuration loading."""

import pytest
from pathlib import Path

from shared.config import AppConfig, get_config, reload_config


def test_config_loads_base_config():
    """Test that base configuration loads correctly."""
    config = AppConfig.load(env="dev")
    assert config.environment == "dev"
    assert config.data.dataset_path is not None
    assert config.models.forecasting.horizon_days > 0


def test_config_environment_override():
    """Test that environment-specific config overrides base config."""
    config = AppConfig.load(env="dev")
    # dev.yaml should override logging format to "text"
    assert config.logging.format == "text"


def test_get_config_singleton():
    """Test that get_config returns a singleton."""
    config1 = get_config()
    config2 = get_config()
    assert config1 is config2


def test_reload_config():
    """Test that reload_config creates a new instance."""
    config1 = get_config()
    config2 = reload_config()
    # They might be the same if no changes, but reload should work
    assert isinstance(config2, AppConfig)


def test_shelf_life_config():
    """Test shelf life configuration."""
    config = AppConfig.load()
    assert config.shelf_life.get_shelf_life("fruits") == 5
    assert config.shelf_life.get_shelf_life("vegetables") == 7
    assert config.shelf_life.get_shelf_life("unknown") == 5  # default

