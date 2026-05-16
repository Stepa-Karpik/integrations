from dataclasses import dataclass
from urllib.parse import urlencode

import httpx


@dataclass(frozen=True, slots=True)
class ExternalFileSnapshot:
    external_file_id: str
    filename: str
    revision: str


class YandexOAuthClient:
    authorize_base_url = "https://oauth.yandex.com/authorize"

    def __init__(self, *, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def build_authorize_url(self, *, state: str) -> str:
        params = urlencode({
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
        })
        return f"{self.authorize_base_url}?{params}"


class YandexDiskClient:
    def __init__(self, *, access_token: str, transport: httpx.BaseTransport | None = None):
        self.access_token = access_token
        self.transport = transport

    def list_folder(self, path: str) -> list[ExternalFileSnapshot]:
        with httpx.Client(base_url="https://cloud-api.yandex.net", transport=self.transport) as client:
            response = client.get(
                "/v1/disk/resources",
                params={"path": path, "limit": 1000},
                headers={"Authorization": f"OAuth {self.access_token}"},
            )
            response.raise_for_status()
        items = response.json().get("_embedded", {}).get("items", [])
        return [
            ExternalFileSnapshot(
                external_file_id=item["resource_id"],
                filename=item["name"],
                revision=str(item.get("revision", "")),
            )
            for item in items
            if item.get("type") == "file"
        ]
