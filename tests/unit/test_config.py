import pytest

from mordin import config
from mordin.config import MODEL_ID, REGION, ConfigError, guard, vision_stub_enabled


def test_guard_accepts_defaults():
    guard(MODEL_ID, REGION)


def test_guard_rejects_wrong_region():
    with pytest.raises(ConfigError):
        guard(MODEL_ID, "us-west-2")


@pytest.mark.parametrize("model_id", ["global." + MODEL_ID, "apac." + MODEL_ID, "other-model"])
def test_guard_rejects_bad_model_ids(model_id):
    with pytest.raises(ConfigError):
        guard(model_id, REGION)


def test_stub_flag_reads_env(monkeypatch):
    monkeypatch.delenv("MORDIN_VISION_STUB", raising=False)
    assert vision_stub_enabled() is False
    monkeypatch.setenv("MORDIN_VISION_STUB", "1")
    assert vision_stub_enabled() is True
    monkeypatch.setenv("MORDIN_VISION_STUB", "0")
    assert vision_stub_enabled() is False


def test_make_bedrock_model_builds_without_network():
    model = config.make_bedrock_model(config.READER_MAX_TOKENS)
    cfg = model.get_config()
    assert cfg["model_id"] == MODEL_ID
    assert cfg["max_tokens"] == config.READER_MAX_TOKENS
