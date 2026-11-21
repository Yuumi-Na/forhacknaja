"""Model ID, Region, guard and Bedrock model factory (aws.md rules).

Importing this module needs no credentials or network: `strands` and
`botocore` are imported inside `make_bedrock_model`.
"""

from __future__ import annotations

import os

MODEL_ID = "anthropic.claude-sonnet-5"
REGION = "ap-southeast-1"

READER_MAX_TOKENS = 1024
EXPLAINER_MAX_TOKENS = 1500

_FORBIDDEN_PREFIXES = ("global.", "apac.")


class ConfigError(Exception):
    """Raised when the model ID or Region is not allowed."""


def guard(model_id: str, region: str) -> None:
    """Raise ConfigError unless model_id and region are the approved values."""
    if region != REGION:
        raise ConfigError(f"Region must be {REGION}, got {region!r}")
    if model_id.startswith(_FORBIDDEN_PREFIXES):
        raise ConfigError(f"Model ID {model_id!r} routes to another Region and is refused")
    if model_id != MODEL_ID:
        raise ConfigError(f"Model ID must be {MODEL_ID}, got {model_id!r}")


def vision_stub_enabled() -> bool:
    """True when MORDIN_VISION_STUB=1 (default off, so the app calls Bedrock)."""
    return os.environ.get("MORDIN_VISION_STUB", "").strip() == "1"


def make_bedrock_model(max_tokens: int):
    """Build a Strands BedrockModel after guard(), with explicit max_tokens and timeouts."""
    guard(MODEL_ID, REGION)

    from botocore.config import Config as BotocoreConfig
    from strands.models import BedrockModel

    client_config = BotocoreConfig(
        connect_timeout=5,
        read_timeout=20,
        retries={"max_attempts": 2, "mode": "standard"},
    )
    return BedrockModel(
        model_id=MODEL_ID,
        region_name=REGION,
        max_tokens=max_tokens,
        boto_client_config=client_config,
    )
