import pytest

from apps.familyrobot.wiring import WiredComponents, wire_components
from packages.core.config import AppConfig, load_config
from packages.core.ports.audio import AudioPort
from packages.core.ports.camera import CameraPort
from packages.core.ports.home import HomePort
from packages.core.ports.notify import NotifyPort
from packages.core.ports.power import PowerPort


@pytest.mark.unit
def test_load_config_default():
    """Test loading configuration with default values."""
    config = load_config()
    assert isinstance(config, AppConfig)
    assert config.platform == "desktop"
    assert config.system.name == "FamilyRobot"
    assert config.system.wake_word == "Hello Puppy"
    assert config.system.language == "en"


@pytest.mark.unit
def test_load_config_platform_override(tmp_path):
    """Test loading configuration with platform yaml file overrides."""
    # Create temp config files
    base_yaml = tmp_path / "base.yaml"
    base_yaml.write_text(
        "system:\n  name: TestRobot\n  language: en\n", encoding="utf-8"
    )

    override_yaml = tmp_path / "custom.yaml"
    override_yaml.write_text(
        "system:\n  language: hi\n  wake_word: Namaste\n", encoding="utf-8"
    )

    config = load_config(platform="custom", config_dir=tmp_path)
    assert config.platform == "custom"
    assert config.system.name == "TestRobot"
    assert config.system.language == "hi"
    assert config.system.wake_word == "Namaste"


@pytest.mark.unit
def test_wire_components():
    """Test that wired components return valid port adapters."""
    config = load_config()
    components = wire_components(config)

    assert isinstance(components, WiredComponents)
    assert isinstance(components.audio, AudioPort)
    assert isinstance(components.camera, CameraPort)
    assert isinstance(components.home, HomePort)
    assert isinstance(components.power, PowerPort)
    assert isinstance(components.notify, NotifyPort)
