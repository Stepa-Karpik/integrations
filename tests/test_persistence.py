from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import Base
from app.repositories import IntegrationRepository


def make_repo():
    engine = create_engine('sqlite+pysqlite:///:memory:')
    Base.metadata.create_all(engine)
    return IntegrationRepository(Session(engine))


def test_connection_and_watched_source_persist():
    repo = make_repo()
    connection = repo.create_yandex_connection(owner_subject_id='usr_1', access_token='token', refresh_token='refresh')
    source = repo.create_watched_source(owner_subject_id='usr_1', provider='yandex_disk', root_path='/Docs', connection_id=connection.id)
    assert repo.list_connections('usr_1')[0].provider == 'yandex_disk'
    assert repo.list_watched_sources('usr_1')[0].connection_id == connection.id
    assert source.root_path == '/Docs'
