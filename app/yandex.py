from dataclasses import dataclass
import base64
import hashlib
import hmac
import json
from secrets import token_urlsafe
from urllib.parse import urlencode

import httpx


@dataclass(frozen=True, slots=True)
class ExternalFileSnapshot:
    external_file_id: str
    filename: str
    revision: str
    external_path: str


@dataclass(frozen=True, slots=True)
class OAuthToken:
    access_token: str
    refresh_token: str | None
    expires_in: int


def encode_oauth_state(*, owner_subject_id: str, secret: str) -> str:
    payload = json.dumps({"sub": owner_subject_id, "nonce": token_urlsafe(12)}, separators=(",", ":")).encode()
    encoded = base64.urlsafe_b64encode(payload).rstrip(b"=")
    signature = hmac.new(secret.encode(), encoded, hashlib.sha256).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).rstrip(b"=")
    return f"{encoded.decode()}.{encoded_signature.decode()}"


def decode_oauth_state(state: str, *, secret: str) -> str:
    try:
        encoded, encoded_signature = state.split(".", 1)
        expected = base64.urlsafe_b64encode(hmac.new(secret.encode(), encoded.encode(), hashlib.sha256).digest()).rstrip(b"=").decode()
        if not hmac.compare_digest(encoded_signature, expected):
            raise ValueError("invalid state signature")
        payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        return payload["sub"]
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        raise ValueError("invalid oauth state") from exc


class YandexOAuthClient:
    authorize_base_url = "https://oauth.yandex.com/authorize"

    def __init__(self, *, client_id: str, client_secret: str, redirect_uri: str, transport: httpx.BaseTransport | None = None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.transport = transport

    def build_authorize_url(self, *, state: str) -> str:
        payload = {
            "response_type": "code",
            "client_id": self.client_id,
            "state": state,
        }
        if self.redirect_uri:
            payload["redirect_uri"] = self.redirect_uri
        params = urlencode(payload)
        return f"{self.authorize_base_url}?{params}"

    def exchange_code(self, code: str) -> OAuthToken:
        with httpx.Client(base_url="https://oauth.yandex.com", transport=self.transport) as client:
            response = client.post(
                "/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            )
            response.raise_for_status()
        payload = response.json()
        return OAuthToken(
            access_token=payload["access_token"],
            refresh_token=payload.get("refresh_token"),
            expires_in=payload["expires_in"],
        )


class YandexDiskClient:
    def __init__(self, *, access_token: str, transport: httpx.BaseTransport | None = None):
        self.access_token = access_token
        self.transport = transport

    def ensure_folder(self, path: str) -> None:
        normalized_path = path.strip() or "/Docs"
        with httpx.Client(base_url="https://cloud-api.yandex.net", transport=self.transport) as client:
            response = client.put(
                "/v1/disk/resources",
                params={"path": normalized_path},
                headers={"Authorization": f"OAuth {self.access_token}"},
            )
            if response.status_code not in {201, 409}:
                response.raise_for_status()

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
                external_path=item["path"],
            )
            for item in items
            if item.get("type") == "file"
        ]

    def download_file(self, path: str) -> bytes:
        with httpx.Client(base_url="https://cloud-api.yandex.net", transport=self.transport) as client:
            response = client.get(
                "/v1/disk/resources/download",
                params={"path": path},
                headers={"Authorization": f"OAuth {self.access_token}"},
            )
            response.raise_for_status()
            href = response.json()["href"]
            download = client.get(href)
            download.raise_for_status()
            return download.content
