import unittest
from unittest.mock import patch
from urllib.error import URLError

from gttt.api_client import APIClient
from gttt.models import Credentials


class _FakeResponse:
    def __init__(self, payload: str) -> None:
        self.payload = payload

    def read(self) -> bytes:
        return self.payload.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class APIClientTests(unittest.TestCase):
    def test_request_retries_on_network_error(self) -> None:
        client = APIClient(
            Credentials(user_id="u", api_key="k", base_url="https://example.com"),
            timeout_seconds=1,
            max_retries=1,
            retry_backoff_seconds=0,
        )

        calls = [URLError("temporary"), _FakeResponse('{"code":"OK","teams":[]}')]

        def fake_urlopen(*args, **kwargs):
            item = calls.pop(0)
            if isinstance(item, Exception):
                raise item
            return item

        with patch("gttt.api_client.urlopen", side_effect=fake_urlopen):
            teams = client.get_my_teams()

        self.assertEqual(teams, [])


if __name__ == "__main__":
    unittest.main()
