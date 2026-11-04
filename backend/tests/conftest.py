"""
RoverMind Test Suite — Mandatory Global Test Isolation & Network Firewall Fixture
Guarantees 100% offline safety across all test suites, independent of any local .env file.
Prevents accidental paid API calls, token consumption, or secret leakage.
"""

import socket
import pytest
import httpx
from unittest.mock import MagicMock

from backend.app.core.config import settings
from backend.app.core.telemetry import api_telemetry
from backend.app.services.image_service import clear_image_store
from backend.app.services.mission_context import clear_analysis_store
from backend.app.services.reasoning_service import clear_conversation_store

ALLOWED_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1", "testserver"}


@pytest.fixture(autouse=True, scope="function")
def enforce_test_isolation_and_network_block(monkeypatch):
    """
    Mandatory autouse test isolation fixture:
    1. Forces external API access off and enables dry-run by default before ANY test or helper runs.
    2. Wipes credential keys in settings so local .env credentials cannot leak into tests.
    3. Blocks outbound network calls at the socket and httpx levels unless connecting to localhost.
    4. Automatically restores original environment configuration upon test completion.
    """
    # 1. Snapshot original settings
    orig_enabled = settings._external_api_enabled
    orig_dry_run = settings._external_api_dry_run
    orig_meta_key = settings._meta_api_key
    orig_reasoning_key = settings._meta_reasoning_api_key
    orig_reasoning_prov = settings._reasoning_provider

    # 2. Force safe defaults (independent of developer's local .env)
    settings._external_api_enabled = False
    settings._external_api_dry_run = True
    settings._meta_api_key = None
    settings._meta_reasoning_api_key = None

    # 3. Clean in-memory stores and reset telemetry
    clear_image_store()
    clear_analysis_store()
    clear_conversation_store()
    api_telemetry.reset(reset_ledger=True)

    # 4. Outbound Network Firewall (Socket level)
    real_socket_connect = socket.socket.connect

    def guarded_socket_connect(sock_self, address):
        host = address[0] if isinstance(address, tuple) and len(address) > 0 else str(address)
        if host in ALLOWED_LOCAL_HOSTS:
            return real_socket_connect(sock_self, address)
        raise RuntimeError(
            f"TEST ISOLATION VIOLATION: Blocked real outbound network socket connection to '{address}'. "
            f"All external API calls must be mocked during test execution."
        )

    monkeypatch.setattr(socket.socket, "connect", guarded_socket_connect)

    # 5. Outbound Network Firewall (httpx transport level)
    real_httpx_send = httpx.Client.send

    def guarded_httpx_send(client_self, request, *args, **kwargs):
        url = str(request.url)
        if any(h in url for h in ALLOWED_LOCAL_HOSTS):
            return real_httpx_send(client_self, request, *args, **kwargs)
        raise RuntimeError(
            f"TEST ISOLATION VIOLATION: Blocked outbound HTTP request to '{url}'. "
            f"All external API calls must be mocked during test execution."
        )

    monkeypatch.setattr(httpx.Client, "send", guarded_httpx_send)

    yield

    # 6. Teardown: Restore original settings and clear stores
    settings._external_api_enabled = orig_enabled
    settings._external_api_dry_run = orig_dry_run
    settings._meta_api_key = orig_meta_key
    settings._meta_reasoning_api_key = orig_reasoning_key
    settings._reasoning_provider = orig_reasoning_prov

    clear_image_store()
    clear_analysis_store()
    clear_conversation_store()
    api_telemetry.reset(reset_ledger=True)
