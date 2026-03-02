import httpx
import pytest


@pytest.fixture
def mock_api_client():
    """Create a mock httpx client for testing."""
    return httpx.AsyncClient(
        base_url="https://elyos-interview-907656039105.europe-west2.run.app",
        headers={"X-API-Key": "test-key"},
        transport=httpx.MockTransport(lambda req: httpx.Response(200, json={})),
    )
