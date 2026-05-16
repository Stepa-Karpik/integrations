import httpx


class HttpDocumentsClient:
    def __init__(self, *, base_url: str, transport: httpx.BaseTransport | None = None):
        self.base_url = base_url
        self.transport = transport

    def sync_watched_source(self, source_id: str, files: list[dict]) -> list[dict]:
        with httpx.Client(base_url=self.base_url, transport=self.transport) as client:
            response = client.post(f'/api/v1/watched-sources/{source_id}/sync', json={'files': files})
            response.raise_for_status()
            return response.json()
