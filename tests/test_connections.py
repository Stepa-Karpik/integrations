from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_yandex_connection_can_be_saved_and_listed():
    created = client.post('/api/v1/connections/yandex-disk', json={'owner_subject_id': 'usr_1', 'access_token': 'token', 'refresh_token': 'refresh'})
    assert created.status_code == 201
    response = client.get('/api/v1/connections', params={'owner_subject_id': 'usr_1'})
    assert response.status_code == 200
    assert response.json()[0]['provider'] == 'yandex_disk'
