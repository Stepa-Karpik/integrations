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

    def create_watched_source(self, *, owner_subject_id: str, provider: str, root_path: str) -> dict:
        with httpx.Client(base_url=self.base_url, transport=self.transport) as client:
            response = client.post(
                '/api/v1/watched-sources',
                json={'owner_subject_id': owner_subject_id, 'provider': provider, 'root_path': root_path},
            )
            response.raise_for_status()
            return response.json()
