"""
Configuration loader using Pydantic and PyYAML.
"""

from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, Field


class SystemConfig(BaseModel):
    name: str = "FamilyRobot"
    wake_word: str = "Hello Puppy"
    language: str = "en"


class AppConfig(BaseModel):
    platform: str = "desktop"
    system: SystemConfig = Field(default_factory=SystemConfig)

    # Cognition (LLM) settings
    llm_model_path: str = "models/llama-3.2-3b.Q4_K_M.gguf"
    llm_n_ctx: int = 2048
    llm_n_threads: int = 4

    # Memory settings
    memory_db_path: str = "data/memory.db"
    embedding_model: Optional[str] = "all-MiniLM-L6-v2"

    # Expression (TTS) settings
    tts_model_path: Optional[str] = None



def load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = base.copy()
    for k, v in override.items():
        if isinstance(v, dict) and k in merged and isinstance(merged[k], dict):
            merged[k] = merge_dicts(merged[k], v)
        else:
            merged[k] = v
    return merged


def load_config(
    platform: Optional[str] = None, config_dir: Optional[Path] = None
) -> AppConfig:
    """Load config/base.yaml + config/<platform>.yaml and merge them."""
    if config_dir is None:
        config_dir = Path("config")

    base_path = config_dir / "base.yaml"
    base_data = load_yaml(base_path)

    # Determine platform
    resolved_platform = platform or base_data.get("platform") or "desktop"

    platform_path = config_dir / f"{resolved_platform}.yaml"
    platform_data = load_yaml(platform_path)

    # Merge base config and platform overrides
    merged_data = merge_dicts(base_data, platform_data)
    # Ensure the resolved platform is written into the config object
    if "platform" not in merged_data or platform:
        merged_data["platform"] = resolved_platform

    return AppConfig(**merged_data)
