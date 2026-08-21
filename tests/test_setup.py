"""Tests for the test setup itself.

The fixtures and the sandbox guard are code, and the guard in particular is the
one thing that must not quietly stop working: it is what keeps the suite from
creating real transactions on a production account.
"""

import json
import pathlib

import pytest

from unzer import UnzerClient

FIXTURE_DIR = pathlib.Path(__file__).parent / "fixtures"


class TestFixtureLoader:

    def test_loads_a_fixture(self, fixture_json):
        assert fixture_json("customer")["id"].startswith("s-cst-")

    def test_unknown_fixture_lists_what_is_available(self, fixture_json):
        with pytest.raises(AssertionError, match="customer"):
            fixture_json("does-not-exist")

    @pytest.mark.parametrize(
        "path", sorted(FIXTURE_DIR.glob("*.json")), ids=lambda p: p.stem)
    def test_every_fixture_is_valid_json(self, path):
        assert json.loads(path.read_text(encoding="utf-8"))


class TestClientFixtures:

    def test_client_has_no_retry_delays(self, client):
        """Otherwise a test that provokes a failure sleeps for fifteen seconds."""
        assert client.retryDelays == ()

    def test_client_uses_a_sandbox_key(self, client):
        assert client.private_key.startswith("s-priv-")

    def test_retrying_client_retries_without_waiting(self, retrying_client):
        assert retrying_client.retryDelays
        assert set(retrying_client.retryDelays) == {0}

    def test_clients_are_usable(self, client):
        assert isinstance(client, UnzerClient)


class TestSandboxGuard:
    """The suite must refuse to run against anything but a sandbox account."""

    @pytest.mark.parametrize("key", [
        "p-priv-0000000000000000000000000000",   # production
        "s-pub-00000000000000000000000000000",   # public, not private
        "priv-000000000000000000000000000000",
        "nonsense",
    ])
    def test_non_sandbox_keys_are_rejected(self, monkeypatch, key):
        from conftest import _sandbox_key
        monkeypatch.setenv("UNZER_PRIVATE_KEY", key)
        with pytest.raises(pytest.UsageError, match="sandbox"):
            _sandbox_key()

    def test_a_sandbox_key_is_accepted(self, monkeypatch):
        from conftest import _sandbox_key
        monkeypatch.setenv("UNZER_PRIVATE_KEY", "s-priv-0000000000000000000000000000")
        assert _sandbox_key() == "s-priv-0000000000000000000000000000"

    def test_no_key_means_no_sandbox(self, monkeypatch, tmp_path):
        from conftest import _sandbox_key
        monkeypatch.delenv("UNZER_PRIVATE_KEY", raising=False)
        # Point the .env lookup at an empty directory so a real one cannot interfere.
        monkeypatch.chdir(tmp_path)
        import conftest
        monkeypatch.setattr(conftest, "_load_dotenv", lambda: None)
        assert _sandbox_key() is None

    def test_sandbox_marker_is_registered(self, pytestconfig):
        """--strict-markers would fail the suite if it were not."""
        markers = pytestconfig.getini("markers")
        assert any(m.startswith("sandbox:") for m in markers)
