"""Shared test setup: no network access and no AWS credentials."""

import socket

import pytest

_AWS_ENV_VARS = (
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "AWS_PROFILE",
    "AWS_DEFAULT_PROFILE",
    "AWS_SECURITY_TOKEN",
    "AWS_CREDENTIAL_EXPIRATION",
    "AWS_SHARED_CREDENTIALS_FILE",
    "AWS_CONFIG_FILE",
    "AWS_WEB_IDENTITY_TOKEN_FILE",
    "AWS_ROLE_ARN",
    "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI",
    "AWS_CONTAINER_CREDENTIALS_FULL_URI",
    "AWS_BEARER_TOKEN_BEDROCK",
)


@pytest.fixture(autouse=True)
def _no_aws_credentials(monkeypatch):
    for name in _AWS_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    # Stop botocore from reaching the instance metadata service.
    monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")


@pytest.fixture(autouse=True)
def _block_network(monkeypatch):
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex
    real_create = socket.create_connection

    def _is_loopback(address) -> bool:
        # asyncio's self-pipe (used by TestClient on Windows) connects to loopback.
        return isinstance(address, tuple) and address[:1] in (("127.0.0.1",), ("::1",))

    def _blocked(*args, **kwargs):
        raise RuntimeError("Network access is blocked in tests")

    def _connect(self, address, *args, **kwargs):
        if _is_loopback(address):
            return real_connect(self, address, *args, **kwargs)
        _blocked()

    def _connect_ex(self, address, *args, **kwargs):
        if _is_loopback(address):
            return real_connect_ex(self, address, *args, **kwargs)
        _blocked()

    def _create(address, *args, **kwargs):
        if _is_loopback(address):
            return real_create(address, *args, **kwargs)
        _blocked()

    monkeypatch.setattr(socket.socket, "connect", _connect)
    monkeypatch.setattr(socket.socket, "connect_ex", _connect_ex)
    monkeypatch.setattr(socket, "create_connection", _create)
