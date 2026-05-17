from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_watched_source_can_be_created(monkeypatch):
    class FakeDocumentsClient:
        def create_watched_source(self, **payload):
            return {"id": "doc_wsrc_1"}
    monkeypatch.setattr("app.main._build_documents_client", lambda: FakeDocumentsClient())
    response = client.post('/api/v1/watched-sources', json={'owner_subject_id': 'usr_1', 'provider': 'yandex_disk', 'root_path': '/Docs'})
    assert response.status_code == 201
    assert response.json()['provider'] == 'yandex_disk'
    assert response.json()['downstream_source_id'] == 'doc_wsrc_1'
