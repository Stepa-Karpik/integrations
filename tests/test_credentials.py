from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db import get_session
from app.main import app
from app.models import Base


def make_client():
    engine = create_engine('sqlite+pysqlite:///:memory:', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    def override_session():
        with factory() as session:
            yield session
    app.dependency_overrides[get_session] = override_session
    return TestClient(app)


def test_yandex_credentials_are_saved_without_echoing_secret(monkeypatch):
    monkeypatch.setenv('INTEGRATIONS_ENCRYPTION_KEY', 'dev-key')
    client = make_client()
    response = client.put('/api/v1/providers/yandex-disk/credentials', json={'owner_subject_id':'usr_1','client_id':'client','client_secret':'secret'})
    assert response.status_code == 200
    assert response.json() == {'provider':'yandex_disk','configured':True,'client_id_hint':'clie…'}
    status = client.get('/api/v1/providers/yandex-disk/status', params={'owner_subject_id':'usr_1'})
    assert status.json()['credentials_configured'] is True
    assert 'secret' not in str(status.json())


def test_authorize_uses_saved_user_credentials(monkeypatch):
    monkeypatch.setenv('INTEGRATIONS_ENCRYPTION_KEY', 'dev-key')
    client = make_client()
    client.put('/api/v1/providers/yandex-disk/credentials', json={'owner_subject_id':'usr_1','client_id':'user-client','client_secret':'user-secret'})
    response = client.get('/api/v1/oauth/yandex-disk/authorize', params={'owner_subject_id':'usr_1'})
    assert response.status_code == 200
    assert 'client_id=user-client' in response.json()['authorization_url']
