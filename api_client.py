import httpx

BASE_URL = "https://elyos-interview-907656039105.europe-west2.run.app"


def create_api_client(api_key: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=BASE_URL,
        headers={"X-API-Key": api_key},
        timeout=httpx.Timeout(5.0, read=15.0),
    )
