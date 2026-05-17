from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_yandex_connection_can_be_saved_and_listed():
    created = client.post('/api/v1/connections/yandex-disk', json={'owner_subject_id': 'usr_1', 'access_token': 'token', 'refresh_token': 'refresh'})
    assert created.status_code == 201
    response = client.get('/api/v1/connections', params={'owner_subject_id': 'usr_1'})
    assert response.status_code == 200
    assert response.json()[0]['provider'] == 'yandex_disk'


def test_yandex_oauth_authorize_returns_redirect_url(monkeypatch):
    monkeypatch.setenv("YANDEX_DISK_CLIENT_ID", "cid")
    monkeypatch.setenv("YANDEX_DISK_CLIENT_SECRET", "secret")
    monkeypatch.setenv("YANDEX_DISK_REDIRECT_URI", "https://documents.nerior.ru/integrations-api/v1/oauth/yandex-disk/callback")
    response = client.get("/api/v1/oauth/yandex-disk/authorize", params={"owner_subject_id": "usr_1"})
    assert response.status_code == 200
    assert response.json()["authorization_url"].startswith("https://oauth.yandex.com/authorize?")


def test_yandex_oauth_callback_saves_connection_and_redirects(monkeypatch):
    from app.yandex import OAuthToken

    class FakeOAuthClient:
        def exchange_code(self, code: str):
            assert code == "code_1"
            return OAuthToken(access_token="ya-token", refresh_token="ya-refresh", expires_in=3600)

    monkeypatch.setenv("YANDEX_DISK_STATE_SECRET", "state-secret")
    monkeypatch.setenv("DOCUMENTS_PUBLIC_BASE_URL", "https://documents.nerior.ru")
    monkeypatch.setattr("app.main._build_yandex_oauth_client", lambda: FakeOAuthClient())
    from app.yandex import encode_oauth_state
    response = client.get(
        "/api/v1/oauth/yandex-disk/callback",
        params={"code": "code_1", "state": encode_oauth_state(owner_subject_id="usr_callback", secret="state-secret")},
        follow_redirects=False,
    )
    assert response.status_code == 307
    assert response.headers["location"] == "https://documents.nerior.ru/?integration=yandex-disk-connected"
