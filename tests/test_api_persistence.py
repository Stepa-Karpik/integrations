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


def test_connection_and_source_survive_separate_requests():
    client = make_client()
    connection = client.post('/api/v1/connections/yandex-disk', json={'owner_subject_id': 'usr_1', 'access_token': 'token', 'refresh_token': 'refresh'}).json()
    source = client.post('/api/v1/watched-sources', json={'owner_subject_id': 'usr_1', 'provider': 'yandex_disk', 'root_path': '/Docs', 'connection_id': connection['id']})
    assert source.status_code == 201
    listed = client.get('/api/v1/watched-sources', params={'owner_subject_id': 'usr_1'})
    assert listed.json()[0]['connection_id'] == connection['id']
