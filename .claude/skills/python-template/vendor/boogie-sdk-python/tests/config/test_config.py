import os

from boogie_sdk.config.config import BoogieConfig
from boogie_sdk.config.config_client import ConfigClient


def test_load_reads_env_override(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BOOGIE_FOO", "bar")
    config = BoogieConfig.load()
    assert config.get("foo") == "bar"


def test_get_default_when_missing():
    config = BoogieConfig(values={})
    assert config.get("missing", "fallback") == "fallback"


def test_with_override_does_not_mutate_original():
    config = BoogieConfig(values={"a": 1})
    updated = config.with_override("a", 2)
    assert config.get("a") == 1
    assert updated.get("a") == 2


def test_config_client_get_delegates_to_config():
    client = ConfigClient(BoogieConfig(values={"k": "v"}))
    assert client.get("k") == "v"
    assert client.get("missing", "d") == "d"


def test_config_client_reload_notifies_listeners(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    client = ConfigClient(BoogieConfig(values={}))
    seen = []
    client.on_change(lambda cfg: seen.append(cfg))

    monkeypatch.setenv("BOOGIE_X", "1")
    client.reload()

    assert len(seen) == 1
    assert seen[0].get("x") == "1"
    assert client.get("x") == "1"
