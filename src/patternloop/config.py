"""Load and validate PatternLoop configuration."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ToolPolicy(BaseModel):
    """Filesystem and shell policy for tools."""

    read_roots: list[str] = Field(default_factory=list)
    allow_bash: bool = False
    allow_write: bool = False


class OllamaConfig(BaseModel):
    base_url: str = "http://127.0.0.1:11434"
    model: str = "llama3.2"
    timeout_seconds: float = 120.0


class ConnectorClaude(BaseModel):
    enabled: bool = False
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096


class ConnectorN8n(BaseModel):
    enabled: bool = False
    webhook_base: str = ""
    hmac_secret_env: str = "PATTERNLOOP_N8N_HMAC_SECRET"


class ConnectorsConfig(BaseModel):
    claude: ConnectorClaude = Field(default_factory=ConnectorClaude)
    n8n: ConnectorN8n = Field(default_factory=ConnectorN8n)


class Limits(BaseModel):
    max_iterations: int = 8
    max_tool_calls: int = 32
    wall_seconds: float = 600.0


class AppConfig(BaseModel):
    """Main config loaded from YAML."""

    version: int = 1
    data_dir: str | None = None
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    tools: ToolPolicy = Field(default_factory=ToolPolicy)
    limits: Limits = Field(default_factory=Limits)
    connectors: ConnectorsConfig = Field(default_factory=ConnectorsConfig)
    human_approve_destructive: bool = False


class EnvSettings(BaseSettings):
    """Environment overrides (optional)."""

    model_config = SettingsConfigDict(env_prefix="PATTERNLOOP_", extra="ignore")

    home: str | None = None


def default_config_path(data_dir: Path) -> Path:
    return data_dir / "config.yaml"


def load_config(path: Path) -> AppConfig:
    if not path.exists():
        return AppConfig()
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return AppConfig.model_validate(raw)


def save_config(path: Path, cfg: AppConfig) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(cfg.model_dump(mode="json"), default_flow_style=False, sort_keys=True),
        encoding="utf-8",
    )


def load_merged_config(data_dir: Path) -> AppConfig:
    path = default_config_path(data_dir)
    cfg = load_config(path)
    env = EnvSettings()
    if env.home:
        cfg = cfg.model_copy(update={"data_dir": env.home})
    if cfg.data_dir:
        # If data_dir overridden in file, use it for subsequent path resolution
        pass
    return cfg
